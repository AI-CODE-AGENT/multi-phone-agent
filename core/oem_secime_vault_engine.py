"""
OEM Vault & Vivo SecIME Secure Keyboard Engine (Iteration #5)
=============================================================
Zero-AI-token engine for detecting and handling Vivo OriginOS / OEM security overlays:
  - Vivo Security Keyboard (`com.vivo.secime/.SecIME`, `com.vivo.secime.service`)
  - Vivo Account / Developer Options Auth Prompts (`com.bbk.account`, `BiometricPrompt`,
    `"Nhập mật khẩu tài khoản Vivo"`, `"Xác minh danh tính"`, `"Mật khẩu màn hình khóa"`)
  - `FLAG_SECURE` black-screen / 0-actionable-node XML lockouts
  - Calibrated relative coordinate grid for Vivo OriginOS numeric PIN pad & QWERTY bottom confirm button
  - Safe credential entry or `VAULT_CREDENTIAL_REQUIRED` diagnostic reporting without crashing
"""

from __future__ import annotations

import logging
import re
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OEMSecIMEVaultEngine:
    """
    Detects Vivo Security Keyboard (`com.vivo.secime/.SecIME`), Vivo Account / PIN prompts,
    and `FLAG_SECURE` black-screen lockouts from `dumpsys window` and UIAutomator XML.
    """

    SECIME_MARKERS: Tuple[str, ...] = (
        "com.vivo.secime/.SecIME",
        "com.vivo.secime",
        "SecIME",
    )

    OEM_ACCOUNT_PROMPT_MARKERS: Tuple[str, ...] = (
        "com.bbk.account",
        "com.vivo.secime",
        "BiometricPrompt",
        "ConfirmDeviceCredentialActivity",
        "Nhập mật khẩu tài khoản Vivo",
        "Xác minh danh tính",
        "Mật khẩu màn hình khóa",
        "Nhập mật khẩu",
        "Enter Vivo account password",
        "Verify identity",
    )

    FLAG_SECURE_FOCUS_MARKERS: Tuple[str, ...] = (
        "secime",
        "BiometricPrompt",
        "ConfirmDeviceCredential",
        "PasswordActivity",
        "LoginActivity",
    )

    # Calibrated relative coordinates (rx, ry) on Vivo OriginOS 1260x2800 screen
    # for numeric PIN pad (digits 0-9, backspace, confirm) and QWERTY bottom confirm
    RELATIVE_NUMERIC_PAD: Dict[str, Tuple[float, float]] = {
        "1": (0.185, 0.695),
        "2": (0.500, 0.695),
        "3": (0.815, 0.695),
        "4": (0.185, 0.765),
        "5": (0.500, 0.765),
        "6": (0.815, 0.765),
        "7": (0.185, 0.835),
        "8": (0.500, 0.835),
        "9": (0.815, 0.835),
        "backspace": (0.815, 0.905),
        "0": (0.500, 0.905),
        "confirm": (0.880, 0.905),
        "qwerty_confirm": (0.885, 0.910),
        "dialog_ok": (0.760, 0.560),
        "dialog_cancel": (0.240, 0.560),
    }

    # Calibrated relative QWERTY row layout for Vivo SecIME keyboard (bottom 38% of screen)
    RELATIVE_QWERTY_KEYS: Dict[str, Tuple[float, float]] = {
        "q": (0.055, 0.685), "w": (0.155, 0.685), "e": (0.255, 0.685), "r": (0.355, 0.685),
        "t": (0.455, 0.685), "y": (0.555, 0.685), "u": (0.655, 0.685), "i": (0.755, 0.685),
        "o": (0.855, 0.685), "p": (0.945, 0.685),
        "a": (0.105, 0.755), "s": (0.205, 0.755), "d": (0.305, 0.755), "f": (0.405, 0.755),
        "g": (0.505, 0.755), "h": (0.605, 0.755), "j": (0.705, 0.755), "k": (0.805, 0.755),
        "l": (0.905, 0.755),
        "z": (0.205, 0.825), "x": (0.305, 0.825), "c": (0.405, 0.825), "v": (0.505, 0.825),
        "b": (0.605, 0.825), "n": (0.705, 0.825), "m": (0.805, 0.825),
        "space": (0.500, 0.905),
    }

    def __init__(self, vault_credentials: Optional[Dict[str, str]] = None) -> None:
        self.vault_credentials: Dict[str, str] = dict(vault_credentials or {})

    def detect_secime_and_auth_prompt(
        self,
        dumpsys_window_output: str = "",
        xml_content: str = "",
    ) -> Dict[str, Any]:
        """
        Analyzes `dumpsys window` output and UIAutomator XML to detect:
          - Vivo Security Keyboard (`com.vivo.secime/.SecIME`)
          - Vivo Account / Lockscreen PIN Prompt (`com.bbk.account`, Vietnamese/English prompt texts)
          - `FLAG_SECURE` / black-screen lockout (0 actionable XML nodes or `secime` / `BiometricPrompt` focus)
        """
        dumpsys_text = dumpsys_window_output or ""
        xml_text = xml_content or ""

        # Extract mCurrentFocus and mInputMethodWindow from dumpsys window
        current_focus = ""
        focus_match = re.search(r"mCurrentFocus=Window\{[^\}]*\s+([^\s\}]+)\}", dumpsys_text)
        if focus_match:
            current_focus = focus_match.group(1)
        elif "mCurrentFocus=" in dumpsys_text:
            for line in dumpsys_text.splitlines():
                if "mCurrentFocus=" in line:
                    current_focus = line.strip()
                    break

        ime_window = ""
        ime_match = re.search(r"mInputMethodWindow=Window\{[^\}]*\s+([^\s\}]+)\}", dumpsys_text)
        if ime_match:
            ime_window = ime_match.group(1)

        combined_text = f"{dumpsys_text}\n{xml_text}"
        combined_lower = combined_text.lower()

        secime_active = any(m.lower() in combined_lower for m in self.SECIME_MARKERS)
        matched_prompts: List[str] = [
            marker for marker in self.OEM_ACCOUNT_PROMPT_MARKERS
            if marker.lower() in combined_lower
        ]
        auth_prompt_detected = len(matched_prompts) > 0 or secime_active

        # Parse XML nodes to check actionable count and locate input fields
        actionable_nodes = 0
        input_field_bounds: Optional[Tuple[int, int, int, int]] = None
        input_center: Optional[Tuple[int, int]] = None
        confirm_button_center: Optional[Tuple[int, int]] = None

        if xml_text.strip():
            try:
                root = ET.fromstring(xml_text.strip())
                for node in root.iter("node"):
                    clickable = node.attrib.get("clickable", "false") == "true"
                    editable = node.attrib.get("focusable", "false") == "true"
                    cls_name = node.attrib.get("class", "")
                    text_val = node.attrib.get("text", "")
                    desc_val = node.attrib.get("content-desc", "")
                    res_id = node.attrib.get("resource-id", "")
                    bounds_str = node.attrib.get("bounds", "")

                    if clickable or "EditText" in cls_name or bool(text_val.strip()):
                        actionable_nodes += 1

                    if "EditText" in cls_name or "password" in res_id.lower() or "pwd" in res_id.lower():
                        parsed_bounds = self._parse_bounds(bounds_str)
                        if parsed_bounds and input_field_bounds is None:
                            input_field_bounds = parsed_bounds
                            input_center = (
                                (parsed_bounds[0] + parsed_bounds[2]) // 2,
                                (parsed_bounds[1] + parsed_bounds[3]) // 2,
                            )

                    label_combined = f"{text_val} {desc_val} {res_id}".lower()
                    if any(k in label_combined for k in ("ok", "xác nhận", "đồng ý", "tiếp tục", "confirm", "button1")):
                        parsed_bounds = self._parse_bounds(bounds_str)
                        if parsed_bounds and confirm_button_center is None:
                            confirm_button_center = (
                                (parsed_bounds[0] + parsed_bounds[2]) // 2,
                                (parsed_bounds[1] + parsed_bounds[3]) // 2,
                            )
            except ET.ParseError:
                actionable_nodes = 0

        focus_indicates_secure = any(
            marker.lower() in current_focus.lower() or marker.lower() in ime_window.lower()
            for marker in self.FLAG_SECURE_FOCUS_MARKERS
        ) or ("flag_secure" in combined_lower)

        flag_secure_lockout = (actionable_nodes == 0 and (not xml_text.strip() or "<hierarchy" in xml_text or focus_indicates_secure)) or focus_indicates_secure

        return {
            "secime_active": secime_active,
            "auth_prompt_detected": auth_prompt_detected,
            "flag_secure_lockout": flag_secure_lockout,
            "current_focus": current_focus,
            "ime_window": ime_window,
            "matched_prompts": matched_prompts,
            "actionable_xml_nodes": actionable_nodes,
            "input_field_bounds": input_field_bounds,
            "input_center": input_center,
            "confirm_button_center": confirm_button_center,
            "tokens_used": 0,
        }

    @classmethod
    def compute_secime_key_coordinates(
        cls,
        screen_width: int = 1260,
        screen_height: int = 2800,
    ) -> Dict[str, Any]:
        """
        Computes calibrated pixel coordinate grids for Vivo OriginOS `com.vivo.secime/.SecIME`
        numeric PIN pad, QWERTY keys, and bottom confirm button for the given resolution.
        """
        width = max(1, int(screen_width))
        height = max(1, int(screen_height))

        numeric_pad: Dict[str, Tuple[int, int]] = {
            key: (int(round(rx * width)), int(round(ry * height)))
            for key, (rx, ry) in cls.RELATIVE_NUMERIC_PAD.items()
        }
        qwerty_keys: Dict[str, Tuple[int, int]] = {
            key: (int(round(rx * width)), int(round(ry * height)))
            for key, (rx, ry) in cls.RELATIVE_QWERTY_KEYS.items()
        }

        return {
            "screen_width": width,
            "screen_height": height,
            "numeric_pad": numeric_pad,
            "qwerty_keys": qwerty_keys,
            "confirm_button": numeric_pad["qwerty_confirm"],
            "pin_confirm_button": numeric_pad["confirm"],
            "backspace_button": numeric_pad["backspace"],
        }

    def handle_oem_auth_prompt(
        self,
        adb_wrapper: Any = None,
        password_or_pin: Optional[str] = None,
        dumpsys_output: str = "",
        xml_content: str = "",
        screen_width: int = 1260,
        screen_height: int = 2800,
    ) -> Dict[str, Any]:
        """
        Handles Vivo OEM Account / PIN / SecIME authentication prompt:
          - Inspects `dumpsys window` and XML (or queries `adb_wrapper` if available).
          - If no credential is provided and none is in `self.vault_credentials`,
            returns `status="VAULT_CREDENTIAL_REQUIRED"` cleanly without crashing.
          - If a credential is provided:
            - Focuses the input field if detected in XML.
            - If `secime_active` is True and credential is numeric PIN, taps calibrated PIN coordinates.
            - Otherwise enters credential via ADB `input text` or coordinate sequence and taps confirm.
        """
        if not dumpsys_output and adb_wrapper is not None and hasattr(adb_wrapper, "shell"):
            try:
                dumpsys_output = str(adb_wrapper.shell("dumpsys window") or "")
            except Exception as exc:
                logger.debug("dumpsys window query failed: %s", exc)

        detection = self.detect_secime_and_auth_prompt(
            dumpsys_window_output=dumpsys_output,
            xml_content=xml_content,
        )
        grid = self.compute_secime_key_coordinates(
            screen_width=screen_width,
            screen_height=screen_height,
        )

        credential = password_or_pin
        if not credential:
            credential = (
                self.vault_credentials.get("vivo_account_password")
                or self.vault_credentials.get("lockscreen_pin")
            )

        if not credential:
            logger.warning(
                "VAULT_CREDENTIAL_REQUIRED: OEM auth prompt detected (focus=%s, prompts=%s) "
                "but no password_or_pin was configured.",
                detection["current_focus"],
                detection["matched_prompts"],
            )
            return {
                "status": "VAULT_CREDENTIAL_REQUIRED",
                "handled": False,
                "diagnostic": (
                    "Vivo OEM security prompt / SecIME detected, but no password or PIN "
                    "is configured in vault. Provide password_or_pin to proceed."
                ),
                "detection": detection,
                "key_grid": grid,
                "actions_executed": [],
                "tokens_used": 0,
                "timestamp": time.time(),
            }

        actions_executed: List[Dict[str, Any]] = []

        # 1. Focus the XML input field if available
        if detection["input_center"] is not None:
            ix, iy = detection["input_center"]
            self._exec_tap(adb_wrapper, ix, iy, actions_executed, reason="focus_input_field")

        # 2. Enter password or PIN
        is_numeric_pin = credential.isdigit()
        if detection["secime_active"] and is_numeric_pin:
            for ch in credential:
                pt = grid["numeric_pad"].get(ch)
                if pt:
                    self._exec_tap(adb_wrapper, pt[0], pt[1], actions_executed, reason=f"secime_pin_{ch}")
        elif detection["input_center"] is not None and not detection["secime_active"]:
            self._exec_input_text(adb_wrapper, credential, actions_executed)
        else:
            # Hybrid fallback: try ADB input text first, and record SecIME key taps for alphanumeric characters
            self._exec_input_text(adb_wrapper, credential, actions_executed)
            for ch in credential.lower():
                if ch in grid["numeric_pad"]:
                    pt = grid["numeric_pad"][ch]
                    self._exec_tap(adb_wrapper, pt[0], pt[1], actions_executed, reason=f"secime_num_{ch}")
                elif ch in grid["qwerty_keys"]:
                    pt = grid["qwerty_keys"][ch]
                    self._exec_tap(adb_wrapper, pt[0], pt[1], actions_executed, reason=f"secime_key_{ch}")

        # 3. Tap Confirm button
        if detection["confirm_button_center"] is not None:
            cx, cy = detection["confirm_button_center"]
            self._exec_tap(adb_wrapper, cx, cy, actions_executed, reason="xml_confirm_button")
        else:
            cx, cy = grid["confirm_button"]
            self._exec_tap(adb_wrapper, cx, cy, actions_executed, reason="secime_confirm_button")

        return {
            "status": "OEM_AUTH_PROMPT_HANDLED",
            "handled": True,
            "detection": detection,
            "key_grid": grid,
            "actions_executed": actions_executed,
            "tokens_used": 0,
            "timestamp": time.time(),
        }

    @staticmethod
    def _parse_bounds(bounds_str: str) -> Optional[Tuple[int, int, int, int]]:
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str or "")
        if not m:
            return None
        return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))

    @staticmethod
    def _exec_tap(
        adb_wrapper: Any,
        x: int,
        y: int,
        actions_log: List[Dict[str, Any]],
        reason: str = "tap",
    ) -> None:
        actions_log.append({"type": "tap", "x": int(x), "y": int(y), "reason": reason})
        if adb_wrapper is None:
            return
        try:
            if hasattr(adb_wrapper, "tap"):
                adb_wrapper.tap(int(x), int(y))
            elif hasattr(adb_wrapper, "shell"):
                adb_wrapper.shell(f"input tap {int(x)} {int(y)}")
        except Exception as exc:
            logger.debug("ADB tap (%s, %s) failed: %s", x, y, exc)

    @staticmethod
    def _exec_input_text(
        adb_wrapper: Any,
        text: str,
        actions_log: List[Dict[str, Any]],
    ) -> None:
        escaped = text.replace(" ", "%s")
        actions_log.append({"type": "input_text", "length": len(text)})
        if adb_wrapper is None:
            return
        try:
            if hasattr(adb_wrapper, "input_text"):
                adb_wrapper.input_text(text)
            elif hasattr(adb_wrapper, "shell"):
                adb_wrapper.shell(f"input text '{escaped}'")
        except Exception as exc:
            logger.debug("ADB input text failed: %s", exc)
