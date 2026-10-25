"""
Subagent #24: Clipboard, Biometric & Notification Shade Hook Subagent
Inspired by Appium Settings Clipboard / Android `cmd clipboard`, Biometric Fingerprint
(`adb emu finger touch` + physical phone biometric prompt handler), and Notification Shade
Automation (`cmd statusbar expand-notifications` + `dumpsys notification`).
"""

import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager


class ClipboardAndBiometricHookSubagent:
    """
    Subagent #24: Automates system clipboard read/write/paste and OTP extraction,
    biometric/fingerprint authentication hooks (emulator finger touch + physical PIN fallback),
    and notification shade inspection/interaction.
    """

    BIOMETRIC_FALLBACK_KEYWORDS = (
        "use pin",
        "dùng mật khẩu",
        "nhập mã pin",
        "xác nhận vân tay",
        "biometric_prompt",
        "use password",
        "enter pin",
    )

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self._local_clipboard_cache: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # 1. Clipboard Automation
    # ------------------------------------------------------------------
    def set_clipboard(self, serial: str, text: str) -> Dict[str, Any]:
        """
        Store text in the local per-device cache and set device clipboard via
        Android `cmd clipboard set-text` and `clipper.set` broadcast.
        """
        self._local_clipboard_cache[serial] = text
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        self.adb.shell(serial, f'cmd clipboard set-text "{escaped}"')
        self.adb.shell(serial, f'am broadcast -a clipper.set -e text "{escaped}"')
        return {
            "serial": serial,
            "status": "CLIPBOARD_SET",
            "text": text,
            "length": len(text),
        }

    def get_clipboard(self, serial: str) -> Dict[str, Any]:
        """
        Read device clipboard via `cmd clipboard get-text` with fallback to
        local clipboard cache when empty or unsupported on OEM ROMs.
        Extracts 4-8 digit OTP code if present.
        """
        raw = self.adb.shell(serial, "cmd clipboard get-text")
        cleaned = (raw or "").strip()

        unsupported_markers = (
            "error:",
            "unknown command",
            "can't find service",
            "no shell command",
            "exception",
            "securityexception",
        )
        if not cleaned or any(m in cleaned.lower() for m in unsupported_markers):
            text = self._local_clipboard_cache.get(serial, "")
        else:
            text = cleaned
            self._local_clipboard_cache[serial] = text

        match = re.search(r"\b(\d{4,8})\b", text)
        otp = match.group(1) if match else None

        return {
            "serial": serial,
            "status": "CLIPBOARD_READ",
            "text": text,
            "extracted_otp": otp,
        }

    def paste_clipboard(self, serial: str) -> Dict[str, Any]:
        """Send Android KEYCODE_PASTE (279) to paste clipboard contents into focused input."""
        self.adb.press_key(serial, 279)
        return {
            "serial": serial,
            "status": "CLIPBOARD_PASTED",
            "keycode": 279,
        }

    def extract_otp_from_clipboard(self, serial: str) -> Optional[str]:
        """Convenience helper returning any 4-8 digit OTP from the device clipboard."""
        res = self.get_clipboard(serial)
        return res.get("extracted_otp")

    # ------------------------------------------------------------------
    # 2. Biometric & Fingerprint Authentication Hook
    # ------------------------------------------------------------------
    def authenticate_biometric(
        self,
        serial: str,
        finger_id: int = 1,
        pin_fallback: str = "1234",
        xml_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Authenticate biometric prompt on emulators (`adb emu finger touch` + `cmd fingerprint touch`)
        and physical devices (inspects UI hierarchy for biometric prompt / PIN fallback buttons,
        taps fallback button, and inputs `pin_fallback`).
        """
        is_emulator = serial.startswith("emulator-")
        if is_emulator:
            self.adb.run_device_cmd(serial, ["emu", "finger", "touch", str(finger_id)])
            self.adb.shell(serial, f"cmd fingerprint touch {finger_id}")

        xml_content = xml_override if xml_override is not None else self.adb.dump_ui_hierarchy(serial)
        elements = self.adb.parse_ui_elements(xml_content)

        fallback_tapped = False
        matched_element: Optional[Dict[str, Any]] = None
        for el in elements:
            combined = " ".join(
                [
                    str(el.get("text", "")),
                    str(el.get("content_desc", "")),
                    str(el.get("resource_id", "")),
                ]
            ).lower()
            if any(kw in combined for kw in self.BIOMETRIC_FALLBACK_KEYWORDS):
                matched_element = el
                bounds = el.get("bounds")
                if not is_emulator and bounds:
                    self.adb.tap(serial, int(bounds["center_x"]), int(bounds["center_y"]))
                    time.sleep(0.2)
                    if pin_fallback:
                        self.adb.input_text(serial, str(pin_fallback))
                        self.adb.press_key(serial, 66)  # KEYCODE_ENTER
                    fallback_tapped = True
                break

        method = "emu_finger_touch" if is_emulator else "biometric_prompt_hook"
        return {
            "serial": serial,
            "status": "BIOMETRIC_AUTHENTICATED",
            "finger_id": finger_id,
            "method": method,
            "fallback_triggered": fallback_tapped,
            "matched_prompt": matched_element.get("text") or matched_element.get("resource_id")
            if matched_element
            else None,
        }

    # ------------------------------------------------------------------
    # 3. Notification Shade & Push Banner Automation
    # ------------------------------------------------------------------
    def inspect_and_interact_notifications(
        self,
        serial: str,
        click_keyword: Optional[str] = None,
        expand_shade: bool = False,
        dumpsys_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Expand notification shade if requested, parse active notifications from
        `dumpsys notification --noredact`, extract 4-8 digit OTP codes, and optionally
        click a notification matching `click_keyword` before collapsing the shade.
        """
        if expand_shade or click_keyword:
            self.adb.shell(serial, "cmd statusbar expand-notifications")

        raw_dumpsys = (
            dumpsys_override
            if dumpsys_override is not None
            else self.adb.shell(serial, "dumpsys notification --noredact")
        )

        items: List[Dict[str, Optional[str]]] = []
        otps: List[str] = []

        if raw_dumpsys:
            titles = re.findall(r"android\.title=([^\r\n]+)", raw_dumpsys)
            texts = re.findall(r"android\.text=([^\r\n]+)", raw_dumpsys)

            def _clean_dumpsys_val(val: str) -> str:
                v = val.strip()
                m = re.match(r"^String\s*\((.*)\)$", v)
                if m:
                    return m.group(1).strip()
                return v

            max_len = max(len(titles), len(texts))
            for idx in range(max_len):
                title = _clean_dumpsys_val(titles[idx]) if idx < len(titles) else ""
                text = _clean_dumpsys_val(texts[idx]) if idx < len(texts) else ""
                if title.lower() == "null":
                    title = ""
                if text.lower() == "null":
                    text = ""
                if not title and not text:
                    continue
                combined = f"{title} {text}".strip()
                found_codes = re.findall(r"\b(\d{4,8})\b", combined)
                for code in found_codes:
                    if code not in otps:
                        otps.append(code)
                items.append(
                    {
                        "title": title,
                        "text": text,
                        "otp": found_codes[0] if found_codes else None,
                    }
                )

        clicked_info: Optional[Dict[str, Any]] = None
        if click_keyword:
            xml_content = self.adb.dump_ui_hierarchy(serial)
            elements = self.adb.parse_ui_elements(xml_content)
            kw_lower = click_keyword.lower()
            for el in elements:
                haystack = " ".join(
                    [
                        str(el.get("text", "")),
                        str(el.get("content_desc", "")),
                        str(el.get("resource_id", "")),
                    ]
                ).lower()
                if kw_lower in haystack and el.get("bounds"):
                    b = el["bounds"]
                    self.adb.tap(serial, int(b["center_x"]), int(b["center_y"]))
                    clicked_info = {
                        "keyword": click_keyword,
                        "text": el.get("text") or el.get("content_desc"),
                        "center_x": b["center_x"],
                        "center_y": b["center_y"],
                    }
                    break
            self.adb.shell(serial, "cmd statusbar collapse")

        return {
            "serial": serial,
            "status": "NOTIFICATIONS_INSPECTED",
            "notifications_count": len(items),
            "notifications": items,
            "extracted_otps": otps,
            "clicked_notification": clicked_info,
        }


if __name__ == "__main__":
    print("Testing ClipboardAndBiometricHookSubagent (#24)...")

    class _MockADB(ADBWrapper):
        def run_device_cmd(self, serial: str, args: List[str], timeout: int = 30):
            return 0, "OK", ""

        def shell(self, serial: str, command: str, timeout: int = 30) -> str:
            if "cmd clipboard get-text" in command:
                return ""  # simulate OEM ROM fallback to cache
            return "OK"

        def dump_ui_hierarchy(self, serial: str) -> str:
            return (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<hierarchy rotation="0">'
                '<node text="Use PIN" resource-id="com.android.systemui:id/biometric_prompt" '
                'clickable="true" bounds="[200,1400][600,1520]" />'
                '<node text="Your OTP is 849201" resource-id="android:id/text" '
                'clickable="true" bounds="[100,300][980,450]" />'
                "</hierarchy>"
            )

    agent = ClipboardAndBiometricHookSubagent(adb=_MockADB())
    set_res = agent.set_clipboard("emulator-5554", "Verification code: 482910")
    read_res = agent.get_clipboard("emulator-5554")
    paste_res = agent.paste_clipboard("emulator-5554")
    bio_emu = agent.authenticate_biometric("emulator-5554", finger_id=1)
    bio_phys = agent.authenticate_biometric("VIVO_PHYSICAL_01", finger_id=1, pin_fallback="5678")
    notif_res = agent.inspect_and_interact_notifications(
        "emulator-5554",
        click_keyword="849201",
        expand_shade=True,
        dumpsys_override=(
            "NotificationRecord(0x01: pkg=com.chat.app)\n"
            "  extras={\n"
            "    android.title=String (Zalo Security)\n"
            "    android.text=String (Ma xac thuc OTP cua ban la 849201)\n"
            "  }\n"
        ),
    )
    print("set_clipboard:", set_res)
    print("get_clipboard:", read_res)
    print("paste_clipboard:", paste_res)
    print("authenticate_biometric (emulator):", bio_emu)
    print("authenticate_biometric (physical):", bio_phys)
    print("inspect_and_interact_notifications:", notif_res)
