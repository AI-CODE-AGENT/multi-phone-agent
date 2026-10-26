"""
ADB Wrapper for Multi-Device Android Farm (AMAF 5.0)
Thread-safe, robust ADB communication layer with multi-device serial routing
and automatic Vivo/OriginOS/MIUI/ColorOS USB installation popup bypass.
"""

import subprocess
import time
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.farm_config import ADB_PATH


class ADBWrapper:
    def __init__(self, adb_path: Optional[Path] = None):
        self.adb_path = str(adb_path or ADB_PATH)
        if not os.path.exists(self.adb_path):
            self.adb_path = "adb"

    def run_command(self, args: List[str], timeout: int = 30) -> Tuple[int, str, str]:
        """Execute a raw ADB command and return (returncode, stdout, stderr)."""
        cmd = [self.adb_path] + args
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s: {' '.join(cmd)}"
        except Exception as e:
            return -1, "", str(e)

    def run_device_cmd(self, serial: str, args: List[str], timeout: int = 30) -> Tuple[int, str, str]:
        """Execute ADB command targeting a specific device serial."""
        return self.run_command(["-s", serial] + args, timeout=timeout)

    def shell(self, serial: str, command: str, timeout: int = 30) -> str:
        """Run adb shell command and return stdout."""
        code, out, err = self.run_device_cmd(serial, ["shell", command], timeout=timeout)
        if code != 0 and err:
            return f"ERROR: {err}"
        return out

    def get_connected_devices(self) -> List[Dict[str, str]]:
        """List all connected ADB devices with serial and status."""
        code, out, _ = self.run_command(["devices", "-l"])
        if code != 0:
            return []

        devices = []
        for line in out.splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                status = parts[1]
                model = "unknown"
                for p in parts[2:]:
                    if p.startswith("model:"):
                        model = p.split(":", 1)[1]
                devices.append({
                    "serial": serial,
                    "status": status,
                    "model": model
                })
        return devices

    def is_boot_completed(self, serial: str) -> bool:
        """Check if Android OS has finished booting."""
        out = self.shell(serial, "getprop sys.boot_completed", timeout=5)
        return out.strip() == "1"

    def wait_for_boot(self, serial: str, timeout_seconds: int = 120, poll_interval: float = 2.0) -> bool:
        """Wait until device is fully booted and responsive."""
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            devices = [d["serial"] for d in self.get_connected_devices() if d["status"] == "device"]
            if serial in devices and self.is_boot_completed(serial):
                self.optimize_system_animations(serial)
                return True
            time.sleep(poll_interval)
        return False

    def optimize_system_animations(self, serial: str):
        """Disable OS animations to make apps and AI testing 2x faster with 0% extra GPU load."""
        self.shell(serial, "settings put global window_animation_scale 0.0")
        self.shell(serial, "settings put global transition_animation_scale 0.0")
        self.shell(serial, "settings put global animator_duration_scale 0.0")

    def install_apk(
        self,
        serial: str,
        apk_path: str,
        replace: bool = True,
        auto_accept_oem_popups: bool = True
    ) -> Tuple[bool, str]:
        """
        Install an APK file on the target device.
        When `auto_accept_oem_popups=True`, spawns a concurrent OEMPopupWatcher thread to
        auto-click 'Tiếp tục cài đặt' / 'Cho phép cài đặt qua USB' on Vivo/OriginOS, MIUI, and ColorOS.
        """
        if not os.path.exists(apk_path):
            return False, f"APK file not found: {apk_path}"
        if auto_accept_oem_popups:
            try:
                from core.oem_popup_watcher import OEMPopupWatcher
                watcher = OEMPopupWatcher(self)
                res = watcher.install_apk_with_oem_guard(serial, apk_path, timeout=120)
                return bool(res.get("success")), str(res.get("output", ""))
            except Exception:
                pass
        args = ["install"]
        if replace:
            args.append("-r")
        args.append(apk_path)
        code, out, err = self.run_device_cmd(serial, args, timeout=120)
        success = "Success" in out or "Success" in err
        msg = out if out else err
        return success, msg

    def uninstall_package(self, serial: str, package_name: str) -> Tuple[bool, str]:
        """Uninstall an app package."""
        code, out, err = self.run_device_cmd(serial, ["uninstall", package_name])
        return "Success" in out, out or err

    def launch_app(self, serial: str, package_name: str, activity_name: Optional[str] = None) -> bool:
        """Launch an app by package name or specific activity."""
        if activity_name:
            component = f"{package_name}/{activity_name}"
            out = self.shell(serial, f"am start -n {component}")
        else:
            out = self.shell(serial, f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
        return "Error" not in out and "Exception" not in out

    def stop_app(self, serial: str, package_name: str):
        """Force stop an application."""
        self.shell(serial, f"am force-stop {package_name}")

    def capture_screenshot(self, serial: str, local_output_path: str) -> bool:
        """Capture screen as PNG image with minimal latency."""
        try:
            cmd = [self.adb_path, "-s", serial, "exec-out", "screencap", "-p"]
            with open(local_output_path, "wb") as f:
                res = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
            return res.returncode == 0 and os.path.getsize(local_output_path) > 1000
        except Exception:
            try:
                remote_path = "/sdcard/screen_temp.png"
                self.shell(serial, f"screencap -p {remote_path}")
                self.run_device_cmd(serial, ["pull", remote_path, local_output_path])
                self.shell(serial, f"rm {remote_path}")
                return os.path.exists(local_output_path) and os.path.getsize(local_output_path) > 1000
            except Exception:
                return False

    def take_screenshot(self, serial: str, local_output_path: str) -> bool:
        return self.capture_screenshot(serial, local_output_path)

    def dump_ui_xml(self, serial: str) -> str:
        return self.dump_ui_hierarchy(serial)

    def dump_ui_hierarchy(self, serial: str) -> str:
        """Dump UIAutomator XML hierarchy string with self-healing against stale uiautomator sessions."""
        remote_xml = "/sdcard/window_dump.xml"
        out = self.shell(serial, f"uiautomator dump {remote_xml}")
        if "already registered" in out.lower() or "error" in out.lower() or "exception" in out.lower():
            self.shell(serial, "pkill -f uiautomator")
            time.sleep(0.6)
            self.shell(serial, f"uiautomator dump {remote_xml}")
        code, xml_content, _ = self.run_device_cmd(serial, ["exec-out", f"cat {remote_xml}"])
        self.shell(serial, f"rm {remote_xml}")
        return xml_content if code == 0 else ""

    def parse_ui_elements(self, xml_string: str) -> List[Dict[str, Any]]:
        """Parse UIAutomator XML into structured element nodes."""
        if not xml_string:
            return []
        try:
            root = ET.fromstring(xml_string)
            elements = []
            for node in root.iter("node"):
                attrib = node.attrib
                bounds_str = attrib.get("bounds", "")
                bounds = None
                if bounds_str and bounds_str.startswith("["):
                    try:
                        clean = bounds_str.replace("][", ",").replace("[", "").replace("]", "")
                        coords = [int(c) for c in clean.split(",")]
                        if len(coords) == 4:
                            x1, y1, x2, y2 = coords
                            center_x = (x1 + x2) // 2
                            center_y = (y1 + y2) // 2
                            bounds = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "center_x": center_x, "center_y": center_y}
                    except Exception:
                        pass

                text = attrib.get("text", "")
                content_desc = attrib.get("content-desc", "")
                resource_id = attrib.get("resource-id", "")
                class_name = attrib.get("class", "")
                clickable = attrib.get("clickable", "false") == "true"
                scrollable = attrib.get("scrollable", "false") == "true"
                checkable = attrib.get("checkable", "false") == "true"
                checked = attrib.get("checked", "false") == "true"
                enabled = attrib.get("enabled", "true") == "true"

                if text or content_desc or resource_id or clickable or checkable:
                    elements.append({
                        "text": text,
                        "content_desc": content_desc,
                        "resource_id": resource_id,
                        "class": class_name,
                        "clickable": clickable,
                        "scrollable": scrollable,
                        "checkable": checkable,
                        "checked": checked,
                        "enabled": enabled,
                        "bounds": bounds
                    })
            return elements
        except Exception:
            return []

    def tap(self, serial: str, x: int, y: int):
        """Simulate touch tap at (x, y)."""
        self.shell(serial, f"input tap {x} {y}")

    def swipe(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        """Simulate drag / swipe."""
        self.shell(serial, f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def input_text(self, serial: str, text: str):
        """Input text (escapes spaces and special characters)."""
        escaped = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
        self.shell(serial, f"input text '{escaped}'")

    def press_key(self, serial: str, keycode: int):
        """Press Android keycode (3: Home, 4: Back, 66: Enter, 82: Menu)."""
        self.shell(serial, f"input keyevent {keycode}")

    def get_current_app(self, serial: str) -> Dict[str, str]:
        """Get currently focused app package and activity."""
        out = self.shell(serial, "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'")
        package = "unknown"
        activity = "unknown"
        for line in out.splitlines():
            if "/" in line:
                try:
                    parts = line.split()
                    for p in parts:
                        if "/" in p:
                            clean = p.replace("}", "").replace("{", "")
                            subparts = clean.split("/")
                            package = subparts[0]
                            activity = subparts[1]
                            return {"package": package, "activity": activity}
                except Exception:
                    pass
        return {"package": package, "activity": activity}

    def get_logcat_crashes(self, serial: str, lines: int = 200) -> str:
        """Extract fatal crashes, ANR, and Java/Kotlin exceptions from logcat."""
        out = self.shell(serial, f"logcat -d -b crash -t {lines}")
        if not out.strip():
            out = self.shell(serial, f"logcat -d -t {lines} *:E | grep -E 'FATAL EXCEPTION|ANR in|Crash|NullPointerException'")
        return out.strip()


if __name__ == "__main__":
    adb = ADBWrapper()
    print("Testing ADBWrapper...")
    devs = adb.get_connected_devices()
    print("Connected devices:", devs)
