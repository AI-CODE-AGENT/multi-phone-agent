"""
Sideload Source Permission Guard & Runtime Auto-Grant Engine.
Iteration #4 of the 10x Recursive Evolution Plan.

Runs with ZERO AI TOKENS at runtime, handling Android `ManageExternalSourcesActivity`
("Install unknown apps" / "Cài đặt ứng dụng không xác định"), pre-authorizing sideload
host packages via `appops`, and auto-granting runtime permissions via `pm grant` and `appops`.
"""

from __future__ import annotations

import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from typing import Any


def _normalize_text(text: str) -> str:
    """Normalize text with NFC and lowercasing for reliable Vietnamese/English matching."""
    if not text:
        return ""
    return unicodedata.normalize("NFC", text).strip().lower()


def _parse_bounds(bounds_str: str) -> dict[str, int] | None:
    """Parse Android UIAutomator bounds '[x1,y1][x2,y2]' into coordinates and center point."""
    if not bounds_str:
        return None
    match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str.strip())
    if not match:
        return None
    x1, y1, x2, y2 = (int(match.group(i)) for i in range(1, 5))
    return {
        "x1": x1,
        "y1": y1,
        "x2": x2,
        "y2": y2,
        "center_x": (x1 + x2) // 2,
        "center_y": (y1 + y2) // 2,
    }


class SideloadSourceGuardEngine:
    """
    Deterministic engine for managing sideload source permissions ('Install unknown apps')
    and runtime package permissions on Android devices with zero LLM tokens.
    """

    SIDELOAD_KEYWORDS: list[str] = [
        unicodedata.normalize("NFC", kw).lower()
        for kw in [
            "cho phép từ nguồn này",
            "allow from this source",
            "cài đặt ứng dụng không xác định",
            "install unknown apps",
            "cho phép cài đặt ứng dụng",
            "nguồn không xác định",
        ]
    ]

    DEFAULT_SIDELOAD_SOURCES: list[str] = [
        "com.android.chrome",
        "com.zing.zalo",
        "com.android.fileexplorer",
        "com.vivo.browser",
        "com.google.android.packageinstaller",
        "com.android.packageinstaller",
    ]

    DEFAULT_RUNTIME_PERMISSIONS: list[str] = [
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.CAMERA",
        "android.permission.RECORD_AUDIO",
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_COARSE_LOCATION",
        "android.permission.POST_NOTIFICATIONS",
    ]

    APPOPS_SPECIAL_PERMISSIONS: set[str] = {
        "SYSTEM_ALERT_WINDOW",
        "MANAGE_EXTERNAL_STORAGE",
        "REQUEST_INSTALL_PACKAGES",
        "android.permission.SYSTEM_ALERT_WINDOW",
        "android.permission.MANAGE_EXTERNAL_STORAGE",
        "android.permission.REQUEST_INSTALL_PACKAGES",
    }

    TOGGLE_CLASSES: set[str] = {
        "android.widget.Switch",
        "android.widget.CheckBox",
        "android.widget.CompoundButton",
        "androidx.appcompat.widget.SwitchCompat",
    }

    TOGGLE_RESOURCE_IDS: set[str] = {
        "android:id/switch_widget",
        "com.android.settings:id/switch_widget",
        "android:id/checkbox",
    }

    def __init__(self, tap_settle_delay_s: float = 0.25) -> None:
        self.tap_settle_delay_s = tap_settle_delay_s
        self.stats: dict[str, int] = {
            "pre_authorizations_run": 0,
            "screens_analyzed": 0,
            "toggles_flipped": 0,
            "runtime_grants_run": 0,
        }

    @staticmethod
    def _exec_adb_shell(adb_wrapper: Any, command: str) -> str:
        """
        Execute a shell command on the provided adb_wrapper supporting multiple common interfaces
        (e.g., `.shell(cmd)`, `.run_shell(cmd)`, `.execute(cmd)`, or callable).
        """
        if adb_wrapper is None:
            return ""
        if hasattr(adb_wrapper, "shell") and callable(adb_wrapper.shell):
            res = adb_wrapper.shell(command)
            return str(res) if res is not None else ""
        if hasattr(adb_wrapper, "run_shell") and callable(adb_wrapper.run_shell):
            res = adb_wrapper.run_shell(command)
            return str(res) if res is not None else ""
        if hasattr(adb_wrapper, "run_command") and callable(adb_wrapper.run_command):
            res = adb_wrapper.run_command(command)
            return str(res) if res is not None else ""
        if hasattr(adb_wrapper, "execute") and callable(adb_wrapper.execute):
            res = adb_wrapper.execute(command)
            return str(res) if res is not None else ""
        if callable(adb_wrapper):
            res = adb_wrapper(command)
            return str(res) if res is not None else ""
        raise TypeError("Unsupported adb_wrapper interface: missing shell/run_shell/execute method.")

    @staticmethod
    def _dump_ui_xml(adb_wrapper: Any) -> str:
        """Obtain current UI hierarchy XML from adb_wrapper."""
        if hasattr(adb_wrapper, "dump_xml") and callable(adb_wrapper.dump_xml):
            return str(adb_wrapper.dump_xml() or "")
        if hasattr(adb_wrapper, "get_ui_xml") and callable(adb_wrapper.get_ui_xml):
            return str(adb_wrapper.get_ui_xml() or "")
        if hasattr(adb_wrapper, "dump_hierarchy") and callable(adb_wrapper.dump_hierarchy):
            return str(adb_wrapper.dump_hierarchy() or "")
        return SideloadSourceGuardEngine._exec_adb_shell(
            adb_wrapper, "uiautomator dump /sdcard/window_dump.xml && cat /sdcard/window_dump.xml"
        )

    @staticmethod
    def _tap_coordinates(adb_wrapper: Any, x: int, y: int) -> str:
        """Tap coordinates via adb_wrapper.tap(x, y) if available or shell `input tap`."""
        if hasattr(adb_wrapper, "tap") and callable(adb_wrapper.tap):
            res = adb_wrapper.tap(x, y)
            return str(res) if res is not None else ""
        return SideloadSourceGuardEngine._exec_adb_shell(adb_wrapper, f"input tap {x} {y}")

    @staticmethod
    def _send_keyevent(adb_wrapper: Any, keycode: int) -> str:
        """Send keyevent via adb_wrapper.keyevent(keycode) or shell `input keyevent`."""
        if hasattr(adb_wrapper, "keyevent") and callable(adb_wrapper.keyevent):
            res = adb_wrapper.keyevent(keycode)
            return str(res) if res is not None else ""
        return SideloadSourceGuardEngine._exec_adb_shell(adb_wrapper, f"input keyevent {keycode}")

    def pre_authorize_sideload_sources(
        self,
        adb_wrapper: Any,
        source_packages: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Pre-authorizes sideload host packages via:
        `adb shell appops set --user 0 <pkg> REQUEST_INSTALL_PACKAGES allow`
        """
        packages = list(source_packages) if source_packages is not None else list(self.DEFAULT_SIDELOAD_SOURCES)
        commands_executed: list[str] = []
        results: dict[str, str] = {}
        succeeded: list[str] = []
        failed: list[str] = []

        for pkg in packages:
            pkg_clean = pkg.strip()
            if not pkg_clean:
                continue
            cmd = f"appops set --user 0 {pkg_clean} REQUEST_INSTALL_PACKAGES allow"
            commands_executed.append(cmd)
            try:
                out = self._exec_adb_shell(adb_wrapper, cmd)
                results[pkg_clean] = out
                if "error" in out.lower() or "exception" in out.lower():
                    failed.append(pkg_clean)
                else:
                    succeeded.append(pkg_clean)
            except Exception as exc:
                results[pkg_clean] = str(exc)
                failed.append(pkg_clean)

        self.stats["pre_authorizations_run"] += 1
        return {
            "status": "ok" if not failed else "partial",
            "packages": packages,
            "succeeded": succeeded,
            "failed": failed,
            "commands": commands_executed,
            "results": results,
        }

    def analyze_sideload_settings_xml(self, xml_str: str) -> dict[str, Any]:
        """
        Detects if the current screen is `ManageExternalSourcesActivity` /
        "Cài đặt ứng dụng không xác định" ("Allow from this source").
        Finds the toggle (`android.widget.Switch`, `android.widget.CheckBox`,
        or `android:id/switch_widget`) and checks whether `checked="false"` or `checked="true"`.

        Returns:
            {
                "is_sideload_screen": bool,
                "is_enabled": bool,
                "toggle_target": dict | None,
                "needs_back_navigation": bool,
                "matched_keywords": list[str],
            }
        """
        self.stats["screens_analyzed"] += 1
        if not xml_str or not xml_str.strip():
            return {
                "is_sideload_screen": False,
                "is_enabled": False,
                "toggle_target": None,
                "needs_back_navigation": False,
                "matched_keywords": [],
            }

        normalized_full = _normalize_text(xml_str)
        matched_keywords = [kw for kw in self.SIDELOAD_KEYWORDS if kw in normalized_full]
        has_activity_marker = "manageexternalsourcesactivity" in normalized_full

        try:
            # Strip potential leading garbage before <?xml or <hierarchy
            xml_start = xml_str.find("<")
            clean_xml = xml_str[xml_start:] if xml_start >= 0 else xml_str
            root = ET.fromstring(clean_xml)
        except ET.ParseError:
            return {
                "is_sideload_screen": False,
                "is_enabled": False,
                "toggle_target": None,
                "needs_back_navigation": False,
                "matched_keywords": matched_keywords,
            }

        nodes = list(root.iter("node"))
        if not nodes and root.tag == "node":
            nodes = [root]

        toggle_candidates: list[dict[str, Any]] = []
        keyword_nodes: list[dict[str, Any]] = []

        for node in nodes:
            cls = node.attrib.get("class", "")
            res_id = node.attrib.get("resource-id", "")
            text = node.attrib.get("text", "")
            desc = node.attrib.get("content-desc", "")
            checkable = node.attrib.get("checkable", "false").lower() == "true"
            checked_attr = node.attrib.get("checked", "false").lower() == "true"
            bounds_str = node.attrib.get("bounds", "")
            bounds = _parse_bounds(bounds_str)

            combined_text = _normalize_text(f"{text} {desc}")
            node_matched_kws = [kw for kw in self.SIDELOAD_KEYWORDS if kw in combined_text]

            if node_matched_kws:
                keyword_nodes.append(
                    {
                        "class": cls,
                        "resource_id": res_id,
                        "text": text,
                        "content_desc": desc,
                        "checked": checked_attr,
                        "bounds": bounds,
                        "bounds_str": bounds_str,
                    }
                )

            is_toggle = (
                cls in self.TOGGLE_CLASSES
                or res_id in self.TOGGLE_RESOURCE_IDS
                or res_id.endswith(":id/switch_widget")
                or res_id.endswith(":id/switchWidget")
                or checkable
            )
            if is_toggle:
                priority = 0
                if res_id in self.TOGGLE_RESOURCE_IDS or res_id.endswith("switch_widget"):
                    priority += 4
                if cls in self.TOGGLE_CLASSES:
                    priority += 3
                if node_matched_kws:
                    priority += 2
                if checkable:
                    priority += 1

                toggle_candidates.append(
                    {
                        "class": cls,
                        "resource_id": res_id,
                        "text": text,
                        "content_desc": desc,
                        "checked": checked_attr,
                        "bounds": bounds,
                        "bounds_str": bounds_str,
                        "priority": priority,
                        "x": bounds["center_x"] if bounds else 0,
                        "y": bounds["center_y"] if bounds else 0,
                    }
                )

        is_sideload_screen = bool(matched_keywords or has_activity_marker)
        if not is_sideload_screen:
            return {
                "is_sideload_screen": False,
                "is_enabled": False,
                "toggle_target": None,
                "needs_back_navigation": False,
                "matched_keywords": [],
            }

        toggle_target: dict[str, Any] | None = None
        if toggle_candidates:
            toggle_candidates.sort(key=lambda item: item["priority"], reverse=True)
            best = toggle_candidates[0]
            # If the toggle itself has no valid bounds or (0,0) center, fall back to keyword node bounds if available
            if (not best["bounds"] or (best["x"] == 0 and best["y"] == 0)) and keyword_nodes:
                for kw_node in keyword_nodes:
                    if kw_node["bounds"]:
                        best["bounds"] = kw_node["bounds"]
                        best["bounds_str"] = kw_node["bounds_str"]
                        best["x"] = kw_node["bounds"]["center_x"]
                        best["y"] = kw_node["bounds"]["center_y"]
                        break
            toggle_target = best
        elif keyword_nodes:
            # Fallback to tapping the keyword label row if switch node wasn't separately exposed
            kw_node = keyword_nodes[0]
            bounds = kw_node["bounds"]
            toggle_target = {
                "class": kw_node["class"],
                "resource_id": kw_node["resource_id"],
                "text": kw_node["text"],
                "content_desc": kw_node["content_desc"],
                "checked": kw_node["checked"],
                "bounds": bounds,
                "bounds_str": kw_node["bounds_str"],
                "priority": 1,
                "x": bounds["center_x"] if bounds else 0,
                "y": bounds["center_y"] if bounds else 0,
            }

        is_enabled = bool(toggle_target and toggle_target.get("checked", False))
        needs_back_navigation = bool(is_sideload_screen and is_enabled)

        return {
            "is_sideload_screen": is_sideload_screen,
            "is_enabled": is_enabled,
            "toggle_target": toggle_target,
            "needs_back_navigation": needs_back_navigation,
            "matched_keywords": matched_keywords,
        }

    def handle_sideload_settings_screen(
        self,
        adb_wrapper: Any,
        xml_str: str | None = None,
    ) -> dict[str, Any]:
        """
        Inspects the current screen (or provided `xml_str`).
        If `is_sideload_screen` and not `is_enabled`, taps `toggle_target`,
        waits briefly, and sends `input keyevent 4` (`KEYCODE_BACK`) to return
        to the package installer flow.
        If `is_sideload_screen` and already `is_enabled`, sends `input keyevent 4`
        to return to the installer flow.
        """
        raw_xml = xml_str if xml_str is not None else self._dump_ui_xml(adb_wrapper)
        analysis = self.analyze_sideload_settings_xml(raw_xml)

        if not analysis["is_sideload_screen"]:
            return {
                "handled": False,
                "action": "none",
                "tapped": False,
                "back_sent": False,
                "analysis": analysis,
            }

        toggle_target = analysis["toggle_target"]
        tapped = False
        back_sent = False
        commands: list[str] = []

        if not analysis["is_enabled"] and toggle_target is not None:
            x = int(toggle_target.get("x", 0))
            y = int(toggle_target.get("y", 0))
            self._tap_coordinates(adb_wrapper, x, y)
            commands.append(f"input tap {x} {y}")
            tapped = True
            self.stats["toggles_flipped"] += 1
            if self.tap_settle_delay_s > 0:
                time.sleep(self.tap_settle_delay_s)

        # Navigate back to package installer flow
        self._send_keyevent(adb_wrapper, 4)
        commands.append("input keyevent 4")
        back_sent = True

        return {
            "handled": True,
            "action": "toggled_and_returned" if tapped else "already_enabled_returned",
            "tapped": tapped,
            "tap_coords": (toggle_target["x"], toggle_target["y"]) if (tapped and toggle_target) else None,
            "back_sent": back_sent,
            "commands": commands,
            "analysis": analysis,
        }

    def auto_grant_runtime_permissions(
        self,
        adb_wrapper: Any,
        package_name: str,
        permissions: list[str] | None = None,
        include_special_appops: bool = True,
    ) -> dict[str, Any]:
        """
        Grants runtime permissions via `pm grant --user 0 <package_name> <perm>`
        and sets `appops set --user 0 <package_name> SYSTEM_ALERT_WINDOW allow`
        and `MANAGE_EXTERNAL_STORAGE allow` if requested.
        """
        pkg = package_name.strip()
        if not pkg:
            raise ValueError("package_name must not be empty.")

        requested_perms = (
            list(permissions) if permissions is not None else list(self.DEFAULT_RUNTIME_PERMISSIONS)
        )

        commands_executed: list[str] = []
        granted_permissions: list[str] = []
        granted_appops: list[str] = []
        failed: list[str] = []

        appops_to_set: list[str] = []
        if include_special_appops:
            appops_to_set.extend(["SYSTEM_ALERT_WINDOW", "MANAGE_EXTERNAL_STORAGE"])

        for perm in requested_perms:
            perm_clean = perm.strip()
            if not perm_clean:
                continue

            # Check if this permission is actually a special appops permission
            if perm_clean in self.APPOPS_SPECIAL_PERMISSIONS:
                op_name = perm_clean.split(".")[-1]
                if op_name not in appops_to_set:
                    appops_to_set.append(op_name)
                continue

            cmd = f"pm grant --user 0 {pkg} {perm_clean}"
            commands_executed.append(cmd)
            try:
                out = self._exec_adb_shell(adb_wrapper, cmd)
                if "error" in out.lower() or "exception" in out.lower() or "failure" in out.lower():
                    failed.append(perm_clean)
                else:
                    granted_permissions.append(perm_clean)
            except Exception:
                failed.append(perm_clean)

        for op_name in appops_to_set:
            cmd = f"appops set --user 0 {pkg} {op_name} allow"
            commands_executed.append(cmd)
            try:
                out = self._exec_adb_shell(adb_wrapper, cmd)
                if "error" in out.lower() or "exception" in out.lower():
                    failed.append(op_name)
                else:
                    granted_appops.append(op_name)
            except Exception:
                failed.append(op_name)

        self.stats["runtime_grants_run"] += 1
        return {
            "status": "ok" if not failed else "partial",
            "package_name": pkg,
            "granted_permissions": granted_permissions,
            "granted_appops": granted_appops,
            "failed": failed,
            "commands": commands_executed,
        }
