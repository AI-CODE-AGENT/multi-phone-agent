"""
Unit tests for AMAF v8.0 SessionAndCredentialEngine and
CrossAppSessionAndCredentialGuardSubagent (Subagent #34).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.session_credential_guard_subagent import CrossAppSessionAndCredentialGuardSubagent
from core.session_credential_engine import SessionAndCredentialEngine


class _FakeADB:
    """In-memory mock ADB object for deterministic unit testing without physical devices."""

    def __init__(self, ui_xml: str = "", account_out: str = "", autofill_out: str = "", notif_out: str = ""):
        self.ui_xml = ui_xml
        self.account_out = account_out
        self.autofill_out = autofill_out
        self.notif_out = notif_out

    def dump_ui_hierarchy(self, serial: str) -> str:
        return self.ui_xml

    def shell(self, serial: str, command: str) -> str:
        if "dumpsys account" in command:
            return self.account_out
        if "dumpsys autofill" in command:
            return self.autofill_out
        if "dumpsys notification" in command:
            return self.notif_out
        return ""


class TestAMAFv8SessionCredentialGuard(unittest.TestCase):
    def setUp(self):
        self.engine = SessionAndCredentialEngine()

    def test_classify_auth_screen_state_all_states(self):
        # 1. CAPTCHA_WALL
        xml_captcha = """
        <hierarchy rotation="0">
          <node text="Verify you are human - Slide to verify" class="android.widget.TextView" />
          <node content-desc="geetest_slider" class="android.view.View" />
        </hierarchy>
        """
        res_captcha = self.engine.classify_auth_screen_state(xml_captcha)
        self.assertEqual(res_captcha["auth_state"], "CAPTCHA_WALL")
        self.assertEqual(res_captcha["recommended_subagent"], "WebAndAdvancedCaptchaSubagent")
        self.assertGreater(res_captcha["confidence"], 0.85)
        self.assertTrue(len(res_captcha["indicators_matched"]) >= 1)

        # 2. TWO_FACTOR_PROMPT
        xml_2fa = """
        <hierarchy rotation="0">
          <node text="Two-Factor Authentication: Enter the 6-digit verification code" class="android.widget.TextView" />
          <node resource-id="com.app:id/otp_input" class="android.widget.EditText" />
        </hierarchy>
        """
        res_2fa = self.engine.classify_auth_screen_state(xml_2fa)
        self.assertEqual(res_2fa["auth_state"], "TWO_FACTOR_PROMPT")
        self.assertEqual(res_2fa["recommended_subagent"], "Universal2FASubagent")
        self.assertTrue(len(res_2fa["indicators_matched"]) >= 1)

        # 3. BIOMETRIC_PROMPT
        xml_bio = """
        <hierarchy rotation="0">
          <node text="Xác nhận vân tay để tiếp tục" resource-id="com.android.systemui:id/biometric_prompt" />
        </hierarchy>
        """
        res_bio = self.engine.classify_auth_screen_state(xml_bio)
        self.assertEqual(res_bio["auth_state"], "BIOMETRIC_PROMPT")
        self.assertEqual(res_bio["recommended_subagent"], "ClipboardAndBiometricHookSubagent")

        # 4. OEM_SECURITY_DIALOG
        xml_oem = """
        <hierarchy rotation="0">
          <node text="Vivo Security Warning: High risk app" package="com.vivo.permissionmanager" />
          <node text="Tiếp tục cài đặt" class="android.widget.Button" clickable="true" />
        </hierarchy>
        """
        res_oem = self.engine.classify_auth_screen_state(xml_oem)
        self.assertEqual(res_oem["auth_state"], "OEM_SECURITY_DIALOG")
        self.assertEqual(res_oem["recommended_subagent"], "OEMPopupGuardSubagent")

        # 5. LOGIN_CREDENTIALS_FORM
        xml_login = """
        <hierarchy rotation="0">
          <node text="Email or Username" class="android.widget.EditText" />
          <node text="Password" password="true" class="android.widget.EditText" />
          <node text="Sign In" class="android.widget.Button" clickable="true" />
        </hierarchy>
        """
        res_login = self.engine.classify_auth_screen_state(xml_login)
        self.assertEqual(res_login["auth_state"], "LOGIN_CREDENTIALS_FORM")
        self.assertEqual(res_login["recommended_subagent"], "CrossAppSessionAndCredentialGuardSubagent")

        # 6. AUTHENTICATED_OR_GENERAL
        xml_home = """
        <hierarchy rotation="0">
          <node text="Home Feed" class="android.widget.TextView" />
          <node text="Welcome back!" class="android.widget.TextView" />
        </hierarchy>
        """
        res_home = self.engine.classify_auth_screen_state(xml_home)
        self.assertEqual(res_home["auth_state"], "AUTHENTICATED_OR_GENERAL")
        self.assertEqual(res_home["recommended_subagent"], "OperatorSubagent")

    def test_parse_dumpsys_accounts_and_autofill(self):
        account_dump = """
        Accounts: 2
          Account {name=alice.tester@gmail.com, type=com.google}
          Account {name=corp_admin@enterprise.io, type=com.microsoft.workaccount}
          Account {name=alice.tester@gmail.com, type=com.google}
        """
        autofill_dump = """
        AutofillManagerService:
          mService=com.google.android.gms/.autofill.service.AutofillService
          CredentialManager: enabled
        """
        parsed = self.engine.parse_dumpsys_accounts_and_autofill(account_dump, autofill_dump)
        self.assertEqual(parsed["account_count"], 2)
        self.assertTrue(parsed["autofill_enabled"])
        self.assertTrue(parsed["credential_manager_enabled"])
        self.assertEqual(
            parsed["autofill_service"],
            "com.google.android.gms/.autofill.service.AutofillService",
        )
        masked_names = [a["masked_name"] for a in parsed["accounts"]]
        self.assertIn("al***@gmail.com", masked_names)
        self.assertIn("co***@enterprise.io", masked_names)
        # Ensure raw full email prefix is not leaked
        for acct in parsed["accounts"]:
            self.assertNotIn("alice.tester", acct["masked_name"])
            self.assertNotIn("corp_admin", acct["masked_name"])

    def test_extract_fresh_otp_from_notifications_with_replay_dedup(self):
        notif_dump = """
        NotificationRecord(0x11a: pkg=com.google.android.apps.messaging)
          when=2026-10-25 23:30:00
          extras={
            android.title=String (2026 Security Alert)
            android.text=String (Your old verification code is 482910. Sent in 2026.)
          }
        NotificationRecord(0x11b: pkg=com.google.android.apps.messaging)
          extras={
            android.title=String (GitHub Auth)
            android.text=String (Your fresh OTP verification code is 937461)
          }
        """
        res = self.engine.extract_fresh_otp_from_notifications(
            notif_raw=notif_dump,
            consumed_codes=["482910"],
        )
        self.assertTrue(res["found"])
        self.assertEqual(res["fresh_otp"], "937461")
        self.assertIn("482910", res["skipped_consumed"])
        self.assertIn("2026", res["skipped_timestamps"])

    def test_subagent_audit_and_advance_auth_state(self):
        fake_adb = _FakeADB(
            ui_xml="""
            <hierarchy rotation="0">
              <node text="Enter 6-digit verification code" class="android.widget.TextView" />
              <node resource-id="com.app:id/otp_box" class="android.widget.EditText" />
            </hierarchy>
            """,
            account_out="Account {name=developer.bot@company.org, type=com.google}",
            autofill_out="mService=com.google.android.gms/.autofill.service.AutofillService",
            notif_out=(
                "NotificationRecord(0x01: pkg=com.chat)\n"
                "  android.text=String (Ma xac thuc OTP cua ban la 718293 nam 2026)\n"
            ),
        )
        subagent = CrossAppSessionAndCredentialGuardSubagent(adb=fake_adb)

        first_audit = subagent.audit_and_advance_auth_state(serial="VIVO_V2250_01")
        self.assertEqual(first_audit["status"], "AUTH_STATE_AUDITED")
        self.assertEqual(first_audit["serial"], "VIVO_V2250_01")
        self.assertEqual(first_audit["auth_state_info"]["auth_state"], "TWO_FACTOR_PROMPT")
        self.assertEqual(first_audit["accounts_summary"]["account_count"], 1)
        self.assertEqual(first_audit["fresh_otp"]["fresh_otp"], "718293")
        self.assertIn("718293", subagent.consumed_otps)

        # Second audit with the same notification dump must deduplicate the consumed OTP
        second_audit = subagent.audit_and_advance_auth_state(serial="VIVO_V2250_01")
        self.assertFalse(second_audit["fresh_otp"]["found"])
        self.assertIsNone(second_audit["fresh_otp"]["fresh_otp"])
        self.assertIn("718293", second_audit["fresh_otp"]["skipped_consumed"])


if __name__ == "__main__":
    unittest.main()
