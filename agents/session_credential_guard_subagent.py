"""
Subagent #34: Cross-App Session & Credential Guard Subagent (AMAF v8.0)
Inspired by Mobile-Agent-E and AndroidWorld cross-app authentication workflows.
Audits current screen authentication barriers (CAPTCHA, 2FA/OTP, Biometric, OEM Security,
Login Credential forms), inspects registered device accounts & Autofill services, and
extracts replay-deduplicated OTP codes from notifications/SMS.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.session_credential_engine import SessionAndCredentialEngine


class CrossAppSessionAndCredentialGuardSubagent:
    """
    Subagent #34: Audits cross-app authentication states, registered Android accounts,
    Autofill / Credential Manager readiness, and fresh OTP tokens with replay protection.
    """

    def __init__(self, adb: Any = None, memory: Any = None):
        self.adb = adb
        self.memory = memory
        self.engine = SessionAndCredentialEngine()
        self.consumed_otps: List[str] = []

    def _safe_shell(self, serial: str, command: str) -> str:
        """Execute an ADB shell command only when an `adb` instance is configured."""
        if self.adb is None:
            return ""
        try:
            if hasattr(self.adb, "shell"):
                return self.adb.shell(serial, command) or ""
        except Exception:
            pass
        return ""

    def _safe_ui_xml(self, serial: str, ui_xml_override: Optional[str] = None) -> str:
        """Retrieve UI XML from override or configured `adb` instance."""
        if ui_xml_override is not None:
            return ui_xml_override
        if self.adb is None:
            return ""
        try:
            if hasattr(self.adb, "dump_ui_hierarchy"):
                return self.adb.dump_ui_hierarchy(serial) or ""
        except Exception:
            pass
        return ""

    def audit_and_advance_auth_state(
        self,
        serial: str,
        ui_xml_override: Optional[str] = None,
        account_raw_override: Optional[str] = None,
        autofill_raw_override: Optional[str] = None,
        notif_raw_override: Optional[str] = None,
        sms_raw_override: Optional[str] = None,
        current_focus: str = "",
    ) -> Dict[str, Any]:
        """
        Inspects `ui_xml` (from `ui_xml_override` or `self.adb`), `dumpsys account`,
        `dumpsys autofill`, and notifications.
        Classifies the authentication screen state, extracts any fresh OTP code, and
        returns a structured orchestration decision:
          {
            "status": "AUTH_STATE_AUDITED",
            "serial": serial,
            "auth_state_info": auth_state_info,
            "accounts_summary": accounts_summary,
            "fresh_otp": fresh_otp_result,
            "consumed_otps": list(self.consumed_otps),
            "timestamp": float
          }
        """
        ui_xml = self._safe_ui_xml(serial, ui_xml_override=ui_xml_override)

        account_raw = (
            account_raw_override
            if account_raw_override is not None
            else self._safe_shell(serial, "dumpsys account")
        )
        autofill_raw = (
            autofill_raw_override
            if autofill_raw_override is not None
            else self._safe_shell(serial, "dumpsys autofill")
        )
        notif_raw = (
            notif_raw_override
            if notif_raw_override is not None
            else self._safe_shell(serial, "dumpsys notification --noredact")
        )
        sms_raw = (
            sms_raw_override
            if sms_raw_override is not None
            else ""
        )

        if not current_focus and self.adb is not None:
            current_focus = self._safe_shell(serial, "dumpsys window | grep mCurrentFocus")

        auth_state_info = self.engine.classify_auth_screen_state(
            ui_xml=ui_xml,
            current_focus=current_focus,
        )
        accounts_summary = self.engine.parse_dumpsys_accounts_and_autofill(
            account_raw=account_raw,
            autofill_raw=autofill_raw,
        )
        fresh_otp_info = self.engine.extract_fresh_otp_from_notifications(
            notif_raw=notif_raw,
            sms_raw=sms_raw,
            consumed_codes=self.consumed_otps,
        )

        extracted_code = fresh_otp_info.get("fresh_otp")
        if extracted_code and extracted_code not in self.consumed_otps:
            self.consumed_otps.append(extracted_code)

        result = {
            "status": "AUTH_STATE_AUDITED",
            "serial": serial,
            "auth_state_info": auth_state_info,
            "accounts_summary": accounts_summary,
            "fresh_otp": fresh_otp_info,
            "consumed_otps": list(self.consumed_otps),
            "timestamp": time.time(),
        }

        if self.memory is not None and hasattr(self.memory, "remember"):
            try:
                self.memory.remember(
                    content=(
                        f"Audited auth state on {serial}: {auth_state_info.get('auth_state')} "
                        f"-> {auth_state_info.get('recommended_subagent')}"
                    ),
                    tags=["session_credential_guard", serial, auth_state_info.get("auth_state", "").lower()],
                    metadata=result,
                )
            except Exception:
                pass

        return result
