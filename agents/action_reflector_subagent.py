"""
Action Reflector Subagent (Subagent #14)
Inspired by Mobile-Agent-E Action Reflector (2025/2026 Self-Evolving GUI Agents).
Performs pre/post-action UI state comparison, structural SHA-256 UI hashing,
permission/crash dialog detection, and unexpected package switch verification.
"""

import hashlib
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager


class ActionReflectorSubagent:
    """
    Subagent #14: Verifies whether an executed UI action produced the expected
    screen transition, got stuck on the same UI state, triggered a system permission
    or ANR/Crash dialog, or accidentally switched out of the target application.
    """

    TRANSIENT_CHOOSER_PACKAGES = {
        "android",
        "com.android.intentresolver",
        "com.android.permissioncontroller",
        "com.google.android.permissioncontroller",
        "com.android.packageinstaller",
    }

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.reflection_history: List[Dict[str, Any]] = []

    def compute_ui_signature(self, xml_content: str, foreground_app: str = "") -> Dict[str, Any]:
        """
        Parse UIAutomator XML hierarchy (with regex fallback if malformed/empty)
        to count clickable elements, scrollable elements, text labels, and compute
        a deterministic SHA-256 structural hash (`ui_hash`).
        Also detects blocking system permission dialogs and ANR/Crash dialogs.
        """
        xml_str = (xml_content or "").strip()
        node_count = 0
        clickable_count = 0
        scrollable_count = 0
        texts: List[str] = []
        structural_tokens: List[str] = [f"app:{foreground_app}"]

        if xml_str:
            try:
                root = ET.fromstring(xml_str)
                for node in root.iter("node"):
                    node_count += 1
                    attrib = node.attrib
                    cls_name = attrib.get("class", "")
                    res_id = attrib.get("resource-id", "")
                    text = attrib.get("text", "").strip()
                    desc = attrib.get("content-desc", "").strip()
                    clickable = attrib.get("clickable", "false") == "true"
                    scrollable = attrib.get("scrollable", "false") == "true"
                    pkg = attrib.get("package", "")

                    if clickable:
                        clickable_count += 1
                    if scrollable:
                        scrollable_count += 1
                    if text:
                        texts.append(text)
                    elif desc:
                        texts.append(desc)

                    structural_tokens.append(
                        f"{pkg}|{cls_name}|{res_id}|{text}|{desc}|{int(clickable)}|{int(scrollable)}"
                    )
            except Exception:
                # Regex fallback for malformed/partial XML
                node_count = len(re.findall(r"<node\b", xml_str))
                clickable_count = len(re.findall(r'clickable="true"', xml_str))
                scrollable_count = len(re.findall(r'scrollable="true"', xml_str))
                for m in re.finditer(r'\btext="([^"]+)"', xml_str):
                    val = m.group(1).strip()
                    if val:
                        texts.append(val)
                for m in re.finditer(r'\bcontent-desc="([^"]+)"', xml_str):
                    val = m.group(1).strip()
                    if val and val not in texts:
                        texts.append(val)
                structural_tokens.append(
                    f"fallback:{node_count}:{clickable_count}:{scrollable_count}:{'|'.join(texts[:20])}"
                )

        canonical_payload = "\n".join(structural_tokens)
        ui_hash = hashlib.sha256(canonical_payload.encode("utf-8", errors="replace")).hexdigest()[:16]

        combined_lower = f"{foreground_app} {xml_str} {' '.join(texts)}".lower()

        lower_texts = [t.lower() for t in texts]
        has_perm = (
            any(
                kw in combined_lower
                for kw in (
                    "com.android.permissioncontroller",
                    "com.google.android.permissioncontroller",
                    "grantdialog",
                    "permission_allow",
                    "while using the app",
                    "allow only while using the app",
                )
            )
            or any(t in ("allow", "while using the app", "only this time") for t in lower_texts)
        )

        has_crash = any(
            kw in combined_lower
            for kw in (
                "isn't responding",
                "keeps stopping",
                "has stopped",
                "aerr_close",
                "aerr_wait",
            )
        )

        return {
            "ui_hash": ui_hash,
            "foreground_app": foreground_app,
            "node_count": node_count,
            "clickable_count": clickable_count,
            "scrollable_count": scrollable_count,
            "sample_texts": texts[:10],
            "has_permission_dialog": has_perm,
            "has_crash_dialog": has_crash,
        }

    def _query_foreground_package(self, serial: str) -> str:
        """Query current foreground package via dumpsys window or dumpsys activity."""
        if hasattr(self.adb, "get_current_app"):
            app_info = self.adb.get_current_app(serial)
            pkg = app_info.get("package", "unknown")
            if pkg and pkg != "unknown":
                return pkg

        out = self.adb.shell(serial, "dumpsys window | grep mCurrentFocus")
        if not out or "/" not in out:
            out = self.adb.shell(serial, "dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity'")

        for line in (out or "").splitlines():
            if "/" in line:
                for token in line.split():
                    if "/" in token:
                        clean = token.strip("{}")
                        pkg = clean.split("/")[0]
                        if pkg and "." in pkg:
                            return pkg
        return ""

    def capture_state_snapshot(self, serial: str) -> Dict[str, Any]:
        """
        Capture current foreground app package and UIAutomator XML hierarchy,
        returning the computed UI signature enriched with device serial and timestamp.
        """
        fg_app = self._query_foreground_package(serial)
        xml_content = self.adb.dump_ui_hierarchy(serial)
        sig = self.compute_ui_signature(xml_content, foreground_app=fg_app)
        sig["serial"] = serial
        sig["timestamp"] = time.time()
        return sig

    def reflect_on_action(
        self,
        serial: str,
        action: Dict[str, Any],
        before_state: Dict[str, Any],
        after_state: Dict[str, Any],
        expected_package: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compare pre-action and post-action UI snapshots to classify action outcome
        and recommend an immediate recovery or continuation strategy.
        """
        after_fg = (after_state.get("foreground_app") or "").strip()
        after_pkg = after_fg.split("/")[0] if "/" in after_fg else after_fg
        action_type = str(action.get("action", "")).strip()

        if after_state.get("has_crash_dialog"):
            outcome = "CRASH_OR_ANR_DETECTED"
            recommendation = "dismiss_anr_and_relaunch"
        elif after_state.get("has_permission_dialog"):
            outcome = "PERMISSION_DIALOG_BLOCKED"
            recommendation = "auto_grant_permission"
        elif (
            expected_package
            and after_pkg
            and after_pkg != "unknown"
            and after_pkg != expected_package
            and after_pkg not in self.TRANSIENT_CHOOSER_PACKAGES
        ):
            outcome = "UNEXPECTED_APP_SWITCH"
            recommendation = "relaunch_expected_package"
        elif (
            before_state.get("ui_hash") == after_state.get("ui_hash")
            and action_type in ("tap", "tapOn", "swipe", "launch", "launchApp")
        ):
            outcome = "NO_CHANGE_STUCK"
            recommendation = "scroll_or_fuzzy_relocate"
        else:
            outcome = "PROGRESS_VERIFIED"
            recommendation = "continue"

        record = {
            "serial": serial,
            "action": action,
            "outcome": outcome,
            "recommended_action": recommendation,
            "recommendation": recommendation,
            "before_ui_hash": before_state.get("ui_hash", ""),
            "after_ui_hash": after_state.get("ui_hash", ""),
            "foreground_app": after_fg,
            "expected_package": expected_package,
            "ui_changed": before_state.get("ui_hash") != after_state.get("ui_hash"),
            "timestamp": time.time(),
        }
        self.reflection_history.append(record)
        return record


if __name__ == "__main__":
    reflector = ActionReflectorSubagent()
    sample_xml = '<hierarchy><node text="Network &amp; internet" clickable="true" class="android.widget.TextView"/></hierarchy>'
    sig = reflector.compute_ui_signature(sample_xml, "com.android.settings")
    print("Sample UI Signature:", sig)
