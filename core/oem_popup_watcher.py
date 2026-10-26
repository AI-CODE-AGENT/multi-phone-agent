import unicodedata
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


OEM_CONSENT_KEYWORDS_PRIORITY: List[str] = [
    # High-priority full phrases (matched first, never false-positive)
    "tiếp tục cài đặt",
    "cho phép cài đặt qua usb",
    "cài đặt qua usb",
    "vẫn cài đặt",
    "continue installing",
    "install via usb",
    "install anyway",
    "继续安装",
    "允许通过USB安装",
]

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
    "ok",
    # Chinese (OriginOS / MIUI CN ROMs)
    "继续安装",
    "允许通过USB安装",
    "继续",
    "允许",
    "始终允许",
    # Generic single words (lowest priority)
    "cài đặt",
    "install",
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

OEM_CHECKBOX_KEYWORDS: List[str] = [
    # Vietnamese (Vivo OriginOS, Xiaomi HyperOS, OPPO ColorOS)
    "tôi đã hiểu",
    "tôi nhận thức",
    "kết quả phát hiện rủi ro",
    "rủi ro của ứng dụng",
    "rủi ro liên quan",
    "đã hiểu rủi ro",
    "rủi ro bảo mật",
    "đồng ý với điều khoản",
    "không nhắc lại",
    "nhận thức được rủi ro",
    # English
    "i understand",
    "i am aware",
    "understand the risks",
    "aware of the risks",
    "remember my choice",
    "don't ask again",
    # Chinese
    "我已了解",
    "已了解风险",
    "已知晓风险",
    "不再提示",
]

OEM_CHECKBOX_ID_HINTS: List[str] = [
    "deleted_file_state_cb",
    "cb_risk",
    "risk_cb",
    "checkbox",
    "check_box",
    "agreement",
    "agree",
    "remember",
]

VIVO_ORIGINOS_FALLBACK_CHECKBOX_COORDS: Tuple[float, float] = (0.50, 0.875)

VIVO_ORIGINOS_FALLBACK_BUTTON_COORDS: List[Tuple[float, float]] = [
    (0.50, 0.936),  # Continue install button center on OriginOS 6 (1260x2800) -> y=2621 (never tap y=0.88 which is the checkbox!)
    (0.50, 0.945),
    (0.72, 0.90),
    (0.50, 0.92),
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
        self.adb.shell(serial, f"input tap {jx} {jy}", timeout=5)
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

        # 1. Search parsed UI nodes for unticked consent / risk checkboxes (e.g. Vivo 'Tôi đã hiểu kết quả phát hiện rủi ro')
        checkbox_ticked = False
        ticked_checkbox_info = None

        for el in elements:
            bounds = el.get("bounds")
            if not bounds:
                continue

            text_raw = (el.get("text") or "").strip()
            desc_raw = (el.get("content_desc") or "").strip()
            res_id = (el.get("resource_id") or "").strip()
            cls_name = (el.get("class") or "").strip()
            checkable = str(el.get("checkable", "")).lower() == "true"
            checked = str(el.get("checked", "")).lower() == "true"

            text_lower = unicodedata.normalize("NFC", text_raw).lower()
            desc_lower = unicodedata.normalize("NFC", desc_raw).lower()
            res_lower = res_id.lower()

            is_checkbox = (
                "checkbox" in cls_name.lower()
                or checkable
                or any(cid in res_lower for cid in OEM_CHECKBOX_ID_HINTS)
            )

            is_risk_prompt = any(
                kw in text_lower or kw in desc_lower for kw in OEM_CHECKBOX_KEYWORDS
            ) or any(cid in res_lower for cid in OEM_CHECKBOX_ID_HINTS)

            if is_checkbox and is_risk_prompt and not checked:
                # Tap the checkbox to check it!
                x1 = bounds.get("x1", bounds.get("left", 0))
                x2 = bounds.get("x2", bounds.get("right", x1 + 80))
                cx = int(bounds.get("center_x", (x1 + x2) // 2))
                cy = int(bounds["center_y"])
                self._human_micro_dwell_tap(serial, cx, cy)
                checkbox_ticked = True
                ticked_checkbox_info = text_raw or desc_raw or res_id
                time.sleep(0.35)  # Allow UI to animate checkmark and enable install button
                break

        # 2. Search parsed UI nodes for matching consent buttons
        # Rule: Filter out top toolbar buttons (y < 450) to avoid false-positives on search/menu icons!
        # Match high-priority full phrases ('Tiếp tục cài đặt', 'button1') before generic single words.
        width, height = self._get_device_resolution(serial)
        candidate_buttons = []

        for el in elements:
            bounds = el.get("bounds")
            if not bounds:
                continue

            cy = bounds.get("center_y", (bounds.get("y1", 0) + bounds.get("y2", 0)) // 2)
            # Dialog consent buttons are never in the top header/toolbar
            if cy < int(height * 0.20):
                continue

            if str(el.get("checkable", "")).lower() == "true" or "checkbox" in (el.get("class") or "").lower():
                continue

            text_raw = (el.get("text") or "").strip()
            desc_raw = (el.get("content_desc") or "").strip()
            res_id = (el.get("resource_id") or "").strip()

            text_lower = unicodedata.normalize("NFC", text_raw).lower()
            desc_lower = unicodedata.normalize("NFC", desc_raw).lower()
            res_lower = res_id.lower()

            # Priority 1: Exact positive button ID (android:id/button1, continue_install_btn)
            if "button1" in res_lower or "continue" in res_lower:
                candidate_buttons.append((100, text_raw or desc_raw or res_id, bounds))
                continue

            # Priority 2: High-priority phrases ('tiếp tục cài đặt', 'cho phép cài đặt qua usb')
            is_priority = False
            for pkw in OEM_CONSENT_KEYWORDS_PRIORITY:
                if pkw in text_lower or pkw in desc_lower:
                    candidate_buttons.append((90, text_raw or desc_raw or pkw, bounds))
                    is_priority = True
                    break
            if is_priority:
                continue

            # Priority 3: General consent keywords
            for kw in OEM_CONSENT_KEYWORDS:
                kw_lower = kw.lower()
                if (
                    text_lower == kw_lower
                    or desc_lower == kw_lower
                    or (len(kw_lower) >= 6 and (kw_lower in text_lower or kw_lower in desc_lower))
                ):
                    candidate_buttons.append((50, text_raw or desc_raw or kw, bounds))
                    break

            # Priority 4: Resource ID hints
            if not candidate_buttons or candidate_buttons[-1][2] != bounds:
                for id_hint in OEM_RESOURCE_ID_HINTS:
                    if id_hint in res_lower:
                        if id_hint == "vivo:id/" and not (el.get("clickable") or text_raw or desc_raw):
                            continue
                        candidate_buttons.append((40, text_raw or desc_raw or res_id, bounds))
                        break

        if candidate_buttons:
            # Sort by priority score (descending) and prefer lower on screen (larger center_y)
            candidate_buttons.sort(key=lambda item: (item[0], item[2].get("center_y", 0)), reverse=True)
            best_score, matched_label, best_bounds = candidate_buttons[0]
            cx = int(best_bounds.get("center_x", (best_bounds.get("x1", 0) + best_bounds.get("x2", 0)) // 2))
            cy = int(best_bounds.get("center_y", (best_bounds.get("y1", 0) + best_bounds.get("y2", 0)) // 2))
            jx, jy = self._human_micro_dwell_tap(serial, cx, cy)
            result = {
                "status": "POPUP_DISMISSED",
                "serial": serial,
                "matched_label": matched_label,
                "checkbox_ticked": checkbox_ticked,
                "checkbox_info": ticked_checkbox_info,
                "tapped_coords": [jx, jy],
                "method": "ui_xml_match",
                "foreground_window": focus_out.strip(),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._record_dismissal(result)
            return result

        # 3. Check if Vivo / OEM coordinate fallback should trigger
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

        if use_vivo_coordinate_fallback and (is_oem_security_window or not focus_lower.strip()):
            width, height = self._get_device_resolution(serial)
            # Step A: Tap checkbox location (left bottom area: ~12% width, ~87.5% height)
            cb_x = int(width * VIVO_ORIGINOS_FALLBACK_CHECKBOX_COORDS[0])
            cb_y = int(height * VIVO_ORIGINOS_FALLBACK_CHECKBOX_COORDS[1])
            self._human_micro_dwell_tap(serial, cb_x, cb_y)
            time.sleep(0.35)

            # Step B: Tap Continue Install button
            last_tapped: List[int] = [int(width * 0.50), int(height * 0.936)]
            for norm_x, norm_y in VIVO_ORIGINOS_FALLBACK_BUTTON_COORDS:
                tx = int(width * norm_x)
                ty = int(height * norm_y)
                jx, jy = self._human_micro_dwell_tap(serial, tx, ty)
                last_tapped = [jx, jy]
                time.sleep(0.12)

            result = {
                "status": "POPUP_DISMISSED_FALLBACK",
                "serial": serial,
                "matched_label": "Vivo/OriginOS Bottom-Sheet Fallback (Checkbox+Button)",
                "checkbox_ticked": True,
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
            interval_sec=0.35,
            use_vivo_fallback=True
        )
        try:
            code, out, err = self.adb.run_device_cmd(
                serial,
                ["install", "-r", apk_path],
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
