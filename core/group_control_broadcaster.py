"""
Group Control & Multi-Device Synchronized Broadcaster (AMAF 3.0)
Inspired by Sigma-RT Total Control, SonicCloud Group Control, and ws-scrcpy.
Broadcasts touch, swipe, text, keyevent, app launch, and shell commands
synchronously across N physical real phones and virtual AVDs in parallel,
with automatic normalized coordinate scaling across heterogeneous screen resolutions.
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.real_device_manager import RealDeviceManager


class GroupControlBroadcaster:
    """Synchronized multi-device broadcaster with resolution-aware coordinate normalization."""

    def __init__(self, adb: Optional[ADBWrapper] = None, real_mgr: Optional[RealDeviceManager] = None):
        self.adb = adb or ADBWrapper()
        self.real_mgr = real_mgr or RealDeviceManager(self.adb)

    def resolve_target_serials(
        self,
        serials: Optional[List[str]] = None,
        group_filter: str = "ALL"
    ) -> List[str]:
        """
        Resolve target device serials based on explicit list or group filter:
        - 'ALL': All online emulators and real phones
        - 'REAL_ONLY': Only online physical real phones
        - 'AVD_ONLY': Only online headless emulators
        """
        if serials:
            return list(dict.fromkeys(serials))

        connected = [d["serial"] for d in self.adb.get_connected_devices() if d["status"] == "device"]
        gf = group_filter.upper()
        if gf == "REAL_ONLY":
            return [s for s in connected if self.real_mgr.is_real_device(s)]
        elif gf == "AVD_ONLY":
            return [s for s in connected if not self.real_mgr.is_real_device(s)]
        return connected

    def scale_coordinates_for_device(
        self,
        target_serial: str,
        x: float,
        y: float,
        reference_width: int = 720,
        reference_height: int = 1600,
        is_normalized: bool = False
    ) -> Tuple[int, int]:
        """
        Convert either normalized coordinates (0.0..1.0) or reference-screen coordinates
        into exact pixel coordinates for the target device's actual resolution.
        """
        dev_w, dev_h = self.real_mgr.get_device_resolution(target_serial)
        if is_normalized or (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and (x < 1.0 or y < 1.0)):
            norm_x = max(0.0, min(1.0, float(x)))
            norm_y = max(0.0, min(1.0, float(y)))
        else:
            norm_x = float(x) / max(1, reference_width)
            norm_y = float(y) / max(1, reference_height)

        scaled_x = int(round(norm_x * dev_w))
        scaled_y = int(round(norm_y * dev_h))
        return scaled_x, scaled_y

    def broadcast_tap(
        self,
        x: float,
        y: float,
        serials: Optional[List[str]] = None,
        group_filter: str = "ALL",
        reference_width: int = 720,
        reference_height: int = 1600,
        is_normalized: bool = False
    ) -> Dict[str, Any]:
        """Broadcast a resolution-scaled tap across multiple devices simultaneously."""
        targets = self.resolve_target_serials(serials, group_filter)
        if not targets:
            return {"success": False, "action": "tap", "targets_count": 0, "results": {}}

        start = time.time()
        results: Dict[str, Any] = {}

        def _tap_one(s: str):
            t0 = time.time()
            sx, sy = self.scale_coordinates_for_device(
                s, x, y, reference_width, reference_height, is_normalized
            )
            self.adb.tap(s, sx, sy)
            return s, {"success": True, "scaled_coords": [sx, sy], "latency_ms": round((time.time() - t0) * 1000, 1)}

        with ThreadPoolExecutor(max_workers=max(1, len(targets))) as ex:
            futures = [ex.submit(_tap_one, s) for s in targets]
            for fut in as_completed(futures):
                s, data = fut.result()
                results[s] = data

        return {
            "success": True,
            "action": "broadcast_tap",
            "targets_count": len(targets),
            "total_duration_ms": round((time.time() - start) * 1000, 1),
            "results": results
        }

    def broadcast_swipe(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        duration_ms: int = 300,
        serials: Optional[List[str]] = None,
        group_filter: str = "ALL",
        reference_width: int = 720,
        reference_height: int = 1600,
        is_normalized: bool = False
    ) -> Dict[str, Any]:
        """Broadcast a resolution-scaled swipe gesture across multiple devices simultaneously."""
        targets = self.resolve_target_serials(serials, group_filter)
        if not targets:
            return {"success": False, "action": "swipe", "targets_count": 0, "results": {}}

        start = time.time()
        results: Dict[str, Any] = {}

        def _swipe_one(s: str):
            t0 = time.time()
            sx1, sy1 = self.scale_coordinates_for_device(s, x1, y1, reference_width, reference_height, is_normalized)
            sx2, sy2 = self.scale_coordinates_for_device(s, x2, y2, reference_width, reference_height, is_normalized)
            self.adb.swipe(s, sx1, sy1, sx2, sy2, duration_ms=duration_ms)
            return s, {
                "success": True,
                "from": [sx1, sy1],
                "to": [sx2, sy2],
                "latency_ms": round((time.time() - t0) * 1000, 1)
            }

        with ThreadPoolExecutor(max_workers=max(1, len(targets))) as ex:
            futures = [ex.submit(_swipe_one, s) for s in targets]
            for fut in as_completed(futures):
                s, data = fut.result()
                results[s] = data

        return {
            "success": True,
            "action": "broadcast_swipe",
            "targets_count": len(targets),
            "total_duration_ms": round((time.time() - start) * 1000, 1),
            "results": results
        }

    def broadcast_text(
        self,
        text: str,
        serials: Optional[List[str]] = None,
        group_filter: str = "ALL"
    ) -> Dict[str, Any]:
        """Broadcast text input across multiple devices simultaneously."""
        targets = self.resolve_target_serials(serials, group_filter)
        if not targets:
            return {"success": False, "action": "text", "targets_count": 0, "results": {}}

        start = time.time()
        results: Dict[str, Any] = {}

        def _type_one(s: str):
            t0 = time.time()
            self.adb.input_text(s, text)
            return s, {"success": True, "text": text, "latency_ms": round((time.time() - t0) * 1000, 1)}

        with ThreadPoolExecutor(max_workers=max(1, len(targets))) as ex:
            futures = [ex.submit(_type_one, s) for s in targets]
            for fut in as_completed(futures):
                s, data = fut.result()
                results[s] = data

        return {
            "success": True,
            "action": "broadcast_text",
            "targets_count": len(targets),
            "total_duration_ms": round((time.time() - start) * 1000, 1),
            "results": results
        }

    def broadcast_key(
        self,
        key: str,
        serials: Optional[List[str]] = None,
        group_filter: str = "ALL"
    ) -> Dict[str, Any]:
        """Broadcast hardware key press (HOME, BACK, ENTER, APP_SWITCH, VOLUME_UP, VOLUME_DOWN) across devices."""
        keymap = {
            "BACK": 4,
            "HOME": 3,
            "ENTER": 66,
            "APP_SWITCH": 187,
            "VOLUME_UP": 24,
            "VOLUME_DOWN": 25,
            "POWER": 26
        }
        keycode = keymap.get(str(key).upper(), 4)
        targets = self.resolve_target_serials(serials, group_filter)
        if not targets:
            return {"success": False, "action": "key", "targets_count": 0, "results": {}}

        start = time.time()
        results: Dict[str, Any] = {}

        def _key_one(s: str):
            t0 = time.time()
            self.adb.press_key(s, keycode)
            return s, {"success": True, "key": key, "keycode": keycode, "latency_ms": round((time.time() - t0) * 1000, 1)}

        with ThreadPoolExecutor(max_workers=max(1, len(targets))) as ex:
            futures = [ex.submit(_key_one, s) for s in targets]
            for fut in as_completed(futures):
                s, data = fut.result()
                results[s] = data

        return {
            "success": True,
            "action": "broadcast_key",
            "targets_count": len(targets),
            "total_duration_ms": round((time.time() - start) * 1000, 1),
            "results": results
        }

    def broadcast_launch_app(
        self,
        package_name: str,
        activity_name: Optional[str] = None,
        serials: Optional[List[str]] = None,
        group_filter: str = "ALL"
    ) -> Dict[str, Any]:
        """Launch an application package across all target devices simultaneously."""
        targets = self.resolve_target_serials(serials, group_filter)
        if not targets:
            return {"success": False, "action": "launch_app", "targets_count": 0, "results": {}}

        start = time.time()
        results: Dict[str, Any] = {}

        def _launch_one(s: str):
            t0 = time.time()
            ok = self.adb.launch_app(s, package_name, activity_name)
            return s, {"success": ok, "package": package_name, "latency_ms": round((time.time() - t0) * 1000, 1)}

        with ThreadPoolExecutor(max_workers=max(1, len(targets))) as ex:
            futures = [ex.submit(_launch_one, s) for s in targets]
            for fut in as_completed(futures):
                s, data = fut.result()
                results[s] = data

        return {
            "success": True,
            "action": "broadcast_launch_app",
            "targets_count": len(targets),
            "total_duration_ms": round((time.time() - start) * 1000, 1),
            "results": results
        }

    def broadcast_shell(
        self,
        command: str,
        serials: Optional[List[str]] = None,
        group_filter: str = "ALL"
    ) -> Dict[str, Any]:
        """Execute an ADB shell command across multiple devices in parallel."""
        targets = self.resolve_target_serials(serials, group_filter)
        if not targets:
            return {"success": False, "action": "shell", "targets_count": 0, "results": {}}

        start = time.time()
        results: Dict[str, Any] = {}

        def _shell_one(s: str):
            t0 = time.time()
            out = self.adb.shell(s, command, timeout=15)
            return s, {"success": "ERROR:" not in out, "output": out[:200], "latency_ms": round((time.time() - t0) * 1000, 1)}

        with ThreadPoolExecutor(max_workers=max(1, len(targets))) as ex:
            futures = [ex.submit(_shell_one, s) for s in targets]
            for fut in as_completed(futures):
                s, data = fut.result()
                results[s] = data

        return {
            "success": True,
            "action": "broadcast_shell",
            "targets_count": len(targets),
            "total_duration_ms": round((time.time() - start) * 1000, 1),
            "results": results
        }


if __name__ == "__main__":
    bc = GroupControlBroadcaster()
    print("Online broadcast targets:", bc.resolve_target_serials())
