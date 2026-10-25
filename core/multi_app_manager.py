"""
Multi-App Automation Manager (AMAF 3.0)
Provides cross-application orchestration across one or multiple Android devices:
- Installed package discovery & launcher activity resolution
- Automated runtime permission & overlay granting
- App data reset & persistent state snapshotting/restoration
- Deep link routing & cold/warm launch latency telemetry
- Active notification parsing (with --noredact support)
- Declarative Maestro-style multi-app flow execution with shared notes & OTP injection
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.real_device_manager import RealDeviceManager
from core.group_control_broadcaster import GroupControlBroadcaster
from core.mock_otp_service import MockOTPService

SNAPSHOTS_FILE = Path(__file__).resolve().parent.parent / "config" / "app_state_snapshots.json"

DEFAULT_RUNTIME_PERMISSIONS = [
    "android.permission.POST_NOTIFICATIONS",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.CAMERA",
    "android.permission.READ_EXTERNAL_STORAGE",
    "android.permission.WRITE_EXTERNAL_STORAGE",
    "android.permission.RECORD_AUDIO",
]

FALLBACK_TEST_PACKAGES = [
    "com.android.settings",
    "com.android.chrome",
    "com.google.android.apps.messaging",
]


class MultiAppAutomationManager:
    """Orchestrates multi-app workflows, state snapshots, permissions, deep links, and notifications."""

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        real_mgr: Optional[RealDeviceManager] = None,
        broadcaster: Optional[GroupControlBroadcaster] = None,
        otp_service: Optional[MockOTPService] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.real_mgr = real_mgr or RealDeviceManager(self.adb)
        self.broadcaster = broadcaster or GroupControlBroadcaster(self.adb, self.real_mgr)
        self.otp_service = otp_service or MockOTPService(self.adb)
        self.snapshot_file = SNAPSHOTS_FILE
        self.snapshots_store: Dict[str, Dict[str, Any]] = self._load_snapshots_file()

    def _load_snapshots_file(self) -> Dict[str, Dict[str, Any]]:
        try:
            if self.snapshot_file.exists():
                with open(self.snapshot_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
        except Exception:
            pass
        return {}

    def _save_snapshots_file(self) -> None:
        try:
            self.snapshot_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.snapshot_file, "w", encoding="utf-8") as f:
                json.dump(self.snapshots_store, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def list_installed_apps(self, serial: str, include_system: bool = False) -> Dict[str, Any]:
        """List installed packages on a device with offline fallback."""
        cmd = "pm list packages" if include_system else "pm list packages -3"
        out = self.adb.shell(serial, cmd)
        pkgs: List[str] = []
        if out and not out.startswith("ERROR"):
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("package:"):
                    pkg_name = line.split("package:", 1)[1].strip()
                    if pkg_name:
                        pkgs.append(pkg_name)
        pkgs = sorted(set(pkgs))
        is_fallback = False
        if not pkgs:
            pkgs = list(FALLBACK_TEST_PACKAGES)
            is_fallback = True

        return {
            "serial": serial,
            "include_system": include_system,
            "apps_count": len(pkgs),
            "packages": pkgs,
            "offline_fallback": is_fallback,
        }

    def resolve_launcher_activity(self, serial: str, package: str) -> str:
        """Resolve the main launcher activity component for a package."""
        out = self.adb.shell(serial, f"cmd package resolve-activity --brief {package}")
        if out and not out.startswith("ERROR"):
            lines = [ln.strip() for ln in out.splitlines() if ln.strip() and "/" in ln]
            if lines:
                return lines[-1]
        return f"{package}/.MainActivity"

    def grant_all_runtime_permissions(
        self,
        serial: str,
        package: str,
        permissions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Grant runtime permissions and SYSTEM_ALERT_WINDOW appops to a target package."""
        perms = list(permissions) if permissions is not None else list(DEFAULT_RUNTIME_PERMISSIONS)
        for perm in perms:
            self.adb.shell(serial, f"pm grant {package} {perm}")
        self.adb.shell(serial, f"appops set {package} SYSTEM_ALERT_WINDOW allow")
        return {
            "serial": serial,
            "package": package,
            "granted_count": len(perms),
            "permissions": perms,
            "status": "PERMISSIONS_GRANTED",
        }

    def clear_app_data(self, serial: str, package: str) -> Dict[str, Any]:
        """Clear application data and cache via pm clear."""
        out = self.adb.shell(serial, f"pm clear {package}")
        out_str = (out or "").strip()
        success = "Success" in out_str or not out_str.startswith("ERROR")
        return {
            "serial": serial,
            "package": package,
            "success": success,
            "output": out_str,
        }

    def snapshot_app_state(
        self,
        serial: str,
        package: str,
        label: str = "checkpoint_1",
    ) -> Dict[str, Any]:
        """Capture current foreground activity and package version metadata into a named checkpoint."""
        focus_out = self.adb.shell(serial, "dumpsys window | grep mCurrentFocus")
        if not focus_out or focus_out.startswith("ERROR"):
            focus_out = self.adb.shell(serial, "dumpsys activity activities")

        foreground_activity = self.resolve_launcher_activity(serial, package)
        if focus_out and not focus_out.startswith("ERROR"):
            for line in focus_out.splitlines():
                if "/" in line:
                    for token in line.split():
                        if "/" in token:
                            clean = token.strip("{}[]()")
                            foreground_activity = clean
                            break

        pkg_out = self.adb.shell(serial, f"dumpsys package {package}")
        version_name = "unknown"
        if pkg_out and not pkg_out.startswith("ERROR"):
            m = re.search(r"versionName=([^\s]+)", pkg_out)
            if m:
                version_name = m.group(1)

        key = f"{serial}::{package}::{label}"
        snapshot = {
            "key": key,
            "serial": serial,
            "package": package,
            "label": label,
            "foreground_activity": foreground_activity,
            "version_name": version_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "SNAPSHOT_SAVED",
        }
        self.snapshots_store[key] = snapshot
        self._save_snapshots_file()
        return snapshot

    def restore_app_state(
        self,
        serial: str,
        package: str,
        label: str = "checkpoint_1",
    ) -> Dict[str, Any]:
        """Restore a previously saved application state checkpoint."""
        key = f"{serial}::{package}::{label}"
        if key not in self.snapshots_store:
            self.snapshots_store.update(self._load_snapshots_file())

        snap = self.snapshots_store.get(key)
        if not snap:
            return {
                "serial": serial,
                "package": package,
                "label": label,
                "status": "SNAPSHOT_NOT_FOUND",
            }

        self.grant_all_runtime_permissions(serial, package)
        fg_act = snap.get("foreground_activity", "")
        if fg_act and "/" in fg_act:
            pkg_part, act_part = fg_act.split("/", 1)
            self.adb.launch_app(serial, pkg_part or package, act_part)
        else:
            self.adb.launch_app(serial, package)

        return {
            "serial": serial,
            "package": package,
            "label": label,
            "restored_activity": fg_act,
            "snapshot": snap,
            "status": "STATE_RESTORED",
        }

    def open_deep_link(
        self,
        serial: str,
        uri: str,
        package: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Launch a deep link URI via Android VIEW intent and measure launch latency."""
        cmd = f'am start -W -a android.intent.action.VIEW -d "{uri}"'
        if package:
            cmd += f" -p {package}"
        t0 = time.time()
        out = self.adb.shell(serial, cmd)
        elapsed_ms = int(round((time.time() - t0) * 1000))
        out_str = out or ""
        m = re.search(r"TotalTime:\s*(\d+)", out_str)
        launch_ms = int(m.group(1)) if m else elapsed_ms
        return {
            "serial": serial,
            "uri": uri,
            "package": package,
            "launch_time_ms": launch_ms,
            "status": "DEEPLINK_OPENED",
            "raw_output": out_str[:300],
        }

    def get_active_notifications(
        self,
        serial: str,
        package_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract active status bar notifications via dumpsys notification --noredact."""
        out = self.adb.shell(serial, "dumpsys notification --noredact")
        items: List[Dict[str, str]] = []
        if out and not out.startswith("ERROR"):
            current_pkg = ""
            current_title = ""
            for line in out.splitlines():
                stripped = line.strip()
                m_pkg = re.search(r"(?:pkg|package)=([a-zA-Z0-9_.]+)", stripped)
                if m_pkg:
                    current_pkg = m_pkg.group(1)
                m_title = re.search(r"android\.title=(?:String\s*\()?([^\n\r)]+)", stripped)
                if m_title:
                    current_title = m_title.group(1).strip()
                m_text = re.search(r"android\.text=(?:String\s*\()?([^\n\r)]+)", stripped)
                if m_text:
                    text_val = m_text.group(1).strip()
                    if not package_filter or package_filter == current_pkg:
                        items.append({
                            "package": current_pkg or (package_filter or "unknown"),
                            "title": current_title,
                            "text": text_val,
                        })
        return {
            "serial": serial,
            "notifications_count": len(items),
            "notifications": items,
        }

    def _find_element_by_text(self, serial: str, text: str) -> Optional[Dict[str, Any]]:
        """Search UI hierarchy for an element matching text or content-desc."""
        finder = getattr(self.adb, "find_element_by_text", None)
        if callable(finder):
            try:
                res = finder(serial, text)
                if res:
                    return res
            except Exception:
                pass

        xml_str = self.adb.dump_ui_hierarchy(serial)
        if not xml_str:
            return None
        elements = self.adb.parse_ui_elements(xml_str)
        target_lower = text.lower()
        for el in elements:
            el_text = (el.get("text") or "").lower()
            el_desc = (el.get("content_desc") or "").lower()
            if target_lower in el_text or target_lower in el_desc:
                return el
        return None

    def run_declarative_multi_app_flow(
        self,
        flow_steps: List[Dict[str, Any]],
        serials: Optional[List[str]] = None,
        shared_notes: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute a Maestro-inspired declarative multi-app flow across one or multiple devices."""
        t_start = time.time()
        if serials:
            target_serials = list(dict.fromkeys(serials))
        else:
            connected = [d["serial"] for d in self.adb.get_connected_devices() if d.get("status") == "device"]
            target_serials = connected if connected else ["emulator-5554"]

        notes: Dict[str, str] = dict(shared_notes) if shared_notes else {}
        step_results: List[Dict[str, Any]] = []

        for idx, step in enumerate(flow_steps, start=1):
            action = step.get("action") or step.get("type") or ""
            step_record: Dict[str, Any] = {"step": idx, "action": action, "status": "OK"}

            if action == "launchApp":
                pkg = step["package"]
                if step.get("clearState"):
                    for s in target_serials:
                        self.clear_app_data(s, pkg)
                if step.get("grantPermissions"):
                    for s in target_serials:
                        self.grant_all_runtime_permissions(s, pkg)
                res = self.broadcaster.broadcast_launch_app(pkg, serials=target_serials)
                step_record["package"] = pkg
                step_record["broadcast"] = res

            elif action == "clearState":
                pkg = step["package"]
                step_record["results"] = {s: self.clear_app_data(s, pkg) for s in target_serials}

            elif action == "grantPermissions":
                pkg = step["package"]
                perms = step.get("permissions")
                step_record["results"] = {
                    s: self.grant_all_runtime_permissions(s, pkg, perms) for s in target_serials
                }

            elif action == "openLink":
                uri = step["uri"]
                pkg = step.get("package")
                step_record["results"] = {
                    s: self.open_deep_link(s, uri, pkg) for s in target_serials
                }

            elif action == "tapOn":
                if "x" in step and "y" in step:
                    x_val = float(step["x"])
                    y_val = float(step["y"])
                    is_norm = bool(step.get("is_normalized", 0.0 <= x_val <= 1.0 and 0.0 <= y_val <= 1.0))
                    step_record["broadcast"] = self.broadcaster.broadcast_tap(
                        x_val, y_val, serials=target_serials, is_normalized=is_norm
                    )
                elif "text" in step:
                    target_text = str(step["text"])
                    per_device: Dict[str, Any] = {}
                    for s in target_serials:
                        el = self._find_element_by_text(s, target_text)
                        bounds = el.get("bounds") if isinstance(el, dict) else None
                        if bounds and "center_x" in bounds and "center_y" in bounds:
                            cx, cy = int(bounds["center_x"]), int(bounds["center_y"])
                            self.adb.tap(s, cx, cy)
                            per_device[s] = {"matched": True, "coords": [cx, cy]}
                        elif isinstance(el, dict) and "x" in el and "y" in el:
                            cx, cy = int(el["x"]), int(el["y"])
                            self.adb.tap(s, cx, cy)
                            per_device[s] = {"matched": True, "coords": [cx, cy]}
                        else:
                            # Fallback to normalized center (0.5, 0.5)
                            self.broadcaster.broadcast_tap(0.5, 0.5, serials=[s], is_normalized=True)
                            per_device[s] = {"matched": False, "fallback_normalized": [0.5, 0.5]}
                    step_record["results"] = per_device

            elif action == "inputText":
                raw_text = str(step.get("text", ""))
                resolved_text = raw_text
                for k, v in notes.items():
                    resolved_text = resolved_text.replace(f"$NOTE:{k}", str(v))
                step_record["resolved_text"] = resolved_text
                step_record["broadcast"] = self.broadcaster.broadcast_text(
                    resolved_text, serials=target_serials
                )

            elif action == "assertVisible":
                expected_text = str(step.get("text", ""))
                assertions: Dict[str, Any] = {}
                for s in target_serials:
                    xml_dump = self.adb.dump_ui_hierarchy(s)
                    visible = bool(xml_dump and expected_text.lower() in xml_dump.lower())
                    assertions[s] = {
                        "expected": expected_text,
                        "visible": visible,
                        "diagnostic": "Matched in UI hierarchy" if visible else "Fallback diagnostic: UI dump empty or text not present",
                    }
                step_record["assertions"] = assertions

            elif action == "switchApp":
                pkg = step["package"]
                per_dev: Dict[str, Any] = {}
                for s in target_serials:
                    out = self.adb.shell(
                        s, f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1"
                    )
                    per_dev[s] = {"package": pkg, "output": (out or "")[:200]}
                step_record["results"] = per_dev

            elif action == "injectMockOtp":
                phone = step.get("phone", "0987654321")
                service_name = step.get("service", "MultiAppTest")
                otp_results: Dict[str, Any] = {}
                last_code = ""
                send_fn = getattr(self.otp_service, "send_mock_otp_sms", None)
                for s in target_serials:
                    if callable(send_fn):
                        res = send_fn(s, phone, service_name)
                        if isinstance(res, dict):
                            last_code = str(res.get("code") or res.get("otp") or last_code)
                        elif isinstance(res, str):
                            extracted = MockOTPService.extract_otp_from_text(res)
                            last_code = extracted or res
                        otp_results[s] = res
                    else:
                        code = self.otp_service.generate_otp(phone, brand=service_name)
                        ok, msg = self.otp_service.deliver_mock_sms_to_device(s, phone, code=code)
                        last_code = code
                        otp_results[s] = {"success": ok, "code": code, "message": msg}
                if last_code:
                    notes["last_otp"] = last_code
                step_record["otp_code"] = last_code
                step_record["results"] = otp_results

            elif action == "extractNote":
                key = str(step.get("key", "note"))
                val = str(step.get("value", ""))
                notes[key] = val
                step_record["key"] = key
                step_record["value"] = val

            else:
                step_record["status"] = "SKIPPED_UNKNOWN_ACTION"

            step_results.append(step_record)

        dur = round(time.time() - t_start, 3)
        return {
            "status": "FLOW_COMPLETED",
            "target_serials": target_serials,
            "steps_executed": len(step_results),
            "step_results": step_results,
            "shared_notes": notes,
            "duration_seconds": dur,
        }
