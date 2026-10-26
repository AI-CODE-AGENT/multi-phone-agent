"""
Subagent #48: OEM Vault & Vivo SecIME Secure Keyboard Handler Subagent
======================================================================
Wraps `OEMSecIMEVaultEngine` to detect and handle Vivo Security Keyboard
(`com.vivo.secime/.SecIME`), Vivo Account / Lockscreen PIN prompts
(`com.bbk.account`, `BiometricPrompt`, `"Nhập mật khẩu tài khoản Vivo"`),
and `FLAG_SECURE` black-screen lockouts with zero AI tokens at runtime.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.oem_secime_vault_engine import OEMSecIMEVaultEngine


class OEMVaultAndSecIMEHandlerSubagent:
    """
    Subagent #48: Detects Vivo `com.vivo.secime/.SecIME` secure keyboard overlays,
    computes calibrated OriginOS numeric/QWERTY coordinates, and executes or diagnoses
    OEM authentication prompts with 0 AI tokens.
    """

    SUBAGENT_ID = 48
    SUBAGENT_NAME = "OEMVaultAndSecIMEHandlerSubagent"

    def __init__(
        self,
        vault_credentials: Optional[Dict[str, str]] = None,
        adb: Any = None,
        memory: Any = None,
    ) -> None:
        self.subagent_id = self.SUBAGENT_ID
        self.subagent_name = self.SUBAGENT_NAME
        self.adb = adb
        self.memory = memory
        self.engine = OEMSecIMEVaultEngine(vault_credentials=vault_credentials)

    def inspect_and_handle_secime(
        self,
        dumpsys_window_output: str = "",
        xml_content: str = "",
        password_or_pin: Optional[str] = None,
        screen_width: int = 1260,
        screen_height: int = 2800,
    ) -> Dict[str, Any]:
        """
        Inspects `dumpsys window` and UIAutomator XML for Vivo SecIME / OEM auth prompts
        and handles them via `OEMSecIMEVaultEngine`.
        """
        result = self.engine.handle_oem_auth_prompt(
            adb_wrapper=self.adb,
            password_or_pin=password_or_pin,
            dumpsys_output=dumpsys_window_output,
            xml_content=xml_content,
            screen_width=screen_width,
            screen_height=screen_height,
        )

        report = {
            "subagent_id": self.SUBAGENT_ID,
            "subagent_name": self.SUBAGENT_NAME,
            "status": result["status"],
            "handled": result["handled"],
            "detection": result["detection"],
            "key_grid": result["key_grid"],
            "actions_executed": result["actions_executed"],
            "diagnostic": result.get("diagnostic", ""),
            "tokens_used": 0,
            "timestamp": time.time(),
        }

        if self.memory is not None and hasattr(self.memory, "remember"):
            try:
                self.memory.remember(
                    content=(
                        f"Subagent #48 status={report['status']} "
                        f"secime={report['detection']['secime_active']} "
                        f"flag_secure={report['detection']['flag_secure_lockout']}"
                    ),
                    tags=["oem_secime", "vivo_vault", report["status"]],
                    metadata=report,
                )
            except Exception:
                pass

        return report


OEMSecIMEVaultSubagent = OEMVaultAndSecIMEHandlerSubagent
