"""
OEM Security & USB Install Popup Watcher
Automatically detects and dismisses OEM-specific security, USB installation, and runtime permission dialogs
across Vivo OriginOS / FuntouchOS ("Tiếp tục cài đặt", "Cho phép cài đặt qua USB"), Xiaomi HyperOS / MIUI
("Install via USB"), OPPO / Realme ColorOS, Samsung OneUI, and Google Play Protect.
"""

import os
import re
import sys
import time
import random
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper


OEM_CONSENT_KEYWORDS: List[str] = [
    # Vietnamese (Vivo OriginOS / FuntouchOS / MIUI / ColorOS)
    "tiếp tục cài đặt",
    "cho phép cài đặt qua usb",
    "cài đặt qua usb",
    "vẫn cài đặt",
    "tiếp tục",
    "cho phép",
    "đồng ý",
    "đã hiểu",
    "cài đặt",
    "chấp nhận",
    "trong khi dùng ứng dụng",
    "luôn cho phép",
    # English
    "continue installing",
    "install via usb",
    "install anyway",
    "continue",
    "allow",
    "while using the app",
    "got it",
    "accept",
    "install",
    "ok",
    # Chinese (OriginOS / MIUI CN ROMs)
    "继续安装",
    "允许通过USB安装",
    "继续",
    "允许",
    "始终允许",
    "安装",
]

OEM_SECURITY_PACKAGES: List[str] = [
    "com.vivo.secime",
    "com.bbk.account",
    "com.vivo.permissionmanager",
    "com.android.packageinstaller",
    "com.google.android.packageinstaller",
    "com.miui.securitycenter",
    "com.oplus.appdetail",
    "com.coloros.safecenter",
    "com.android.permissioncontroller",
]

VIVO_ORIGINOS_FALLBACK_BUTTON_COORDS: List[Tuple[float, float]] = [
    (0.5, 0.88),
    (0.72, 0.90),
    (0.5, 0.92),
]

OEM_RESOURCE_ID_HINTS: List[str] = [
    "vivo:id/",
    "permission_allow_button",
    "permission_allow_foreground_only_button",
    "continue_button",
    "ok_button",
    "button1",
]


class OEMPopupWatcher:
    """
    Watches for and auto-confirms OEM USB install and runtime permission dialogs,
    including Vivo OriginOS security bottom-sheets that hide nodes from UIAutomator.
    """

    def __init__(self, adb: Optional[ADBWrapper] = None):
        self.adb = adb or ADBWrapper()
        self._stop_events: Dict[str, threading.Event] = {}
        self._watcher_threads: Dict[str, threading.Thread] = {}
        self.dismissed_history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def _get_device_resolution(self, serial: str) -> Tuple[int, int]:
        """Query physical or override screen resolution via `wm size`, defaulting to 1080x2400."""
        out = self.adb.shell(serial, "wm size", timeout=5)
        matches = re.findall(r"(\d+)x(\d+)", out or "")
        if matches:
            w, h = int(matches[-1][0]), int(matches[-1][1])
            if w > 0 and h > 0:
                return w, h
        return 1080, 2400

    def _human_micro_dwell_tap(self, serial: str, x: int, y: int) -> Tuple[int, int]:
        """Perform a human-like micro-dwell touch swipe (`input swipe jx jy jx+1 jy+1 85`)."""
        jx = max(1, x + random.randint(-2, 2))
        jy = max(1, y + random.randint(-2, 2))
        self.adb.shell(serial, f"input swipe {jx} {jy} {jx + 1} {jy + 1} 85", timeout=5)
        return jx, jy

    def _record_dismissal(self, record: Dict[str, Any]):
        """Thread-safely record a popup dismissal event."""
        with self._lock:
            self.dismissed_history.append(record)

    def scan_and_dismiss_oem_popup(
        self,
        serial: str,
        use_vivo_coordinate_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Inspect foreground window and UI hierarchy to detect and dismiss OEM security / install dialogs.
        Falls back to Vivo OriginOS normalized bottom-sheet coordinates when UIAutomator nodes are hidden.
        """
        focus_out = self.adb.shell(serial, "dumpsys window | grep mCurrentFocus", timeout=5) or ""
        focus_lower = focus_out.lower()

        xml_str = self.adb.dump_ui_hierarchy(serial)
        elements = self.adb.parse_ui_elements(xml_str)

        # 1. Search parsed UI nodes for matching consent keywords or OEM resource-id hints
        for el in elements:
            bounds = el.get("bounds")
            if not bounds:
                continue

            text_raw = (el.get("text") or "").strip()
            desc_raw = (el.get("content_desc") or "").strip()
            res_id = (el.get("resource_id") or "").strip()

            text_lower = text_raw.lower()
            desc_lower = desc_raw.lower()
            res_lower = res_id.lower()

            matched_label: Optional[str] = None

            # Check keyword match (exact or substring for multi-word consent phrases)
            for kw in OEM_CONSENT_KEYWORDS:
                kw_lower = kw.lower()
                if (
                    text_lower == kw_lower
                    or desc_lower == kw_lower
                    or (len(kw_lower) >= 6 and (kw_lower in text_lower or kw_lower in desc_lower))
                ):
                    matched_label = text_raw or desc_raw or kw
                    break

            # Check resource-id hints if not matched by text
            if not matched_label and res_lower:
                for id_hint in OEM_RESOURCE_ID_HINTS:
                    if id_hint in res_lower:
                        # If it's a generic vivo:id/ or button1, prefer clickable or non-empty text
                        if id_hint == "vivo:id/" and not (el.get("clickable") or text_raw or desc_raw):
                            continue
                        matched_label = text_raw or desc_raw or res_id
                        break

            if matched_label:
                cx = int(bounds["center_x"])
                cy = int(bounds["center_y"])
                jx, jy = self._human_micro_dwell_tap(serial, cx, cy)
                result = {
                    "status": "POPUP_DISMISSED",
                    "serial": serial,
                    "matched_label": matched_label,
                    "tapped_coords": [jx, jy],
                    "method": "ui_xml_match",
                    "foreground_window": focus_out.strip(),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                self._record_dismissal(result)
                return result

        # 2. Check if Vivo / OEM coordinate fallback should trigger
        oem_window_triggers = (
            "com.vivo",
            "com.bbk",
            "packageinstaller",
            "securitycenter",
            "permissioncontroller",
            "safecenter",
            "appdetail",
        )
        is_oem_security_window = any(tok in focus_lower for tok in oem_window_triggers) or any(
            pkg.lower() in focus_lower for pkg in OEM_SECURITY_PACKAGES
        )

        if use_vivo_coordinate_fallback or is_oem_security_window:
            width, height = self._get_device_resolution(serial)
            last_tapped: List[int] = [int(width * 0.5), int(height * 0.88)]
            for norm_x, norm_y in VIVO_ORIGINOS_FALLBACK_BUTTON_COORDS:
                tx = int(width * norm_x)
                ty = int(height * norm_y)
                jx, jy = self._human_micro_dwell_tap(serial, tx, ty)
                last_tapped = [jx, jy]
                time.sleep(0.12)

            result = {
                "status": "POPUP_DISMISSED_FALLBACK",
                "serial": serial,
                "matched_label": "Vivo/OriginOS Bottom-Sheet Fallback",
                "tapped_coords": last_tapped,
                "method": "vivo_originos_coord_fallback",
                "foreground_window": focus_out.strip(),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._record_dismissal(result)
            return result

        return {
            "status": "NO_POPUP_DETECTED",
            "serial": serial,
        }

    def start_background_watcher(
        self,
        serial: str,
        interval_sec: float = 0.8,
        use_vivo_fallback: bool = True
    ) -> Dict[str, Any]:
        """Start a daemon thread for `serial` that polls and dismisses OEM popups."""
        if serial in self._watcher_threads and self._watcher_threads[serial].is_alive():
            return {
                "status": "ALREADY_RUNNING",
                "serial": serial,
                "interval_sec": interval_sec,
            }

        stop_event = threading.Event()
        self._stop_events[serial] = stop_event

        def _watch_loop():
            while not stop_event.is_set():
                try:
                    self.scan_and_dismiss_oem_popup(
                        serial,
                        use_vivo_coordinate_fallback=use_vivo_fallback
                    )
                except Exception:
                    pass
                stop_event.wait(interval_sec)

        thread = threading.Thread(
            target=_watch_loop,
            name=f"OEMPopupWatcher-{serial}",
            daemon=True
        )
        self._watcher_threads[serial] = thread
        thread.start()

        return {
            "status": "WATCHER_STARTED",
            "serial": serial,
            "interval_sec": interval_sec,
            "use_vivo_fallback": use_vivo_fallback,
        }

    def stop_background_watcher(self, serial: str) -> Dict[str, Any]:
        """Signal the stop event for `serial` and return total popups dismissed for that device."""
        stop_event = self._stop_events.get(serial)
        if stop_event:
            stop_event.set()

        thread = self._watcher_threads.get(serial)
        if thread and thread.is_alive():
            thread.join(timeout=2.5)

        self._stop_events.pop(serial, None)
        self._watcher_threads.pop(serial, None)

        with self._lock:
            device_dismissals = [d for d in self.dismissed_history if d.get("serial") == serial]

        return {
            "status": "WATCHER_STOPPED",
            "serial": serial,
            "total_popups_dismissed": len(device_dismissals),
            "dismissed_events": device_dismissals,
        }

    def install_apk_with_oem_guard(
        self,
        serial: str,
        apk_path: str,
        timeout: int = 90
    ) -> Dict[str, Any]:
        """
        Install an APK while running the background OEM popup watcher to automatically click
        'Tiếp tục cài đặt' / 'Cho phép cài đặt qua USB' on Vivo OriginOS and MIUI/HyperOS.
        """
        with self._lock:
            before_count = len([d for d in self.dismissed_history if d.get("serial") == serial])

        self.start_background_watcher(
            serial=serial,
            interval_sec=0.6,
            use_vivo_fallback=True
        )
        try:
            code, out, err = self.adb.run_device_cmd(
                serial,
                ["install", "-r", "-g", apk_path],
                timeout=timeout
            )
            ok = code == 0 and ("Success" in out or "Success" in err)
        finally:
            self.stop_background_watcher(serial)

        with self._lock:
            after_count = len([d for d in self.dismissed_history if d.get("serial") == serial])

        return {
            "success": ok,
            "serial": serial,
            "apk_path": apk_path,
            "popups_auto_clicked": max(0, after_count - before_count),
            "output": out or err,
        }


if __name__ == "__main__":
    watcher = OEMPopupWatcher()
    print("OEMPopupWatcher initialized with", len(OEM_CONSENT_KEYWORDS), "consent keywords.")
