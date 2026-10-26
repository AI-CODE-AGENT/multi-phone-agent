"""
Comprehensive Verification Suite for AMAF 7.0:
- Subagent #26: Universal2FASubagent & Universal2FAEngine (RFC 6238 TOTP SHA1/SHA256/SHA512, RFC 4226 HOTP, 6-Box Split-Digit OTP, Push Number-Matching, Cross-App Authenticator, Passkey/WebAuthn, Backup Recovery Codes)
- Subagent #27: WebAndAdvancedCaptchaSubagent & WebAndAdvancedCaptchaEngine (Concentric Ring Rotation `xoay ảnh`, 3x3 & 4x4 Multi-Image Grid `chọn nhiều ảnh`, Web Browser URL Navigation `truy cập trang web giải capcha`, WebView DevTools Socket Discovery & Forwarding)
- Subagent #28: AccessibilityAndWCAGContrastSubagent (WCAG 2.1 AA/AAA Relative Luminance Contrast Ratio `>= 4.5:1` / `>= 7.0:1`, TalkBack Focus Order, Unlabeled Interactive & Duplicate Content-Desc)
- Subagent #29: CrashTombstoneAndANRSubagent (Java/Kotlin Fatal Exceptions, Native C/C++ SIGSEGV/SIGABRT Tombstones, ANR Stack-Trace Demangling & SHA-256 Deduplication)
- Subagent #30: NetworkTrafficAndAPILatencySubagent (`/proc/net/dev` RX/TX Throughput, HTTP/HTTPS API Latency & Status Codes, Cleartext `http://` Risk Detection)
- SelfEvolutionEngine v7.0 (30 Subagents) & AndroidFarmMCPServer v7.0 (40 MCP Tools)
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.memory_manager import MemoryManager
from core.universal_2fa_engine import Universal2FAEngine
from core.web_and_advanced_captcha_engine import WebAndAdvancedCaptchaEngine
from agents.universal_2fa_subagent import Universal2FASubagent
from agents.web_and_advanced_captcha_subagent import WebAndAdvancedCaptchaSubagent
from agents.accessibility_wcag_subagent import AccessibilityAndWCAGContrastSubagent
from agents.crash_tombstone_anr_subagent import CrashTombstoneAndANRSubagent
from agents.network_api_latency_subagent import NetworkTrafficAndAPILatencySubagent
from agents.self_evolution_engine import SelfEvolutionEngine
from mcp_bridge.android_farm_mcp_server import AndroidFarmMCPServer
from tests.test_amaf_v6_complex_captcha_vision_and_25_subagents import FakeV6ADB


class FakeV7ADB(FakeV6ADB):
    """Extended deterministic fake ADB for AMAF 7.0 unit tests."""

    def shell(self, serial, command, timeout=30):
        if "/proc/net/unix" in command:
            return (
                "00000000: 00000002 00000000 00010000 0001 01 112233 @chrome_devtools_remote\n"
                "00000000: 00000002 00000000 00010000 0001 01 445566 @webview_devtools_remote_24680\n"
            )
        if "/proc/net/dev" in command:
            return (
                "Inter-|   Receive                                                |  Transmit\n"
                " wlan0: 5242880    4100    0    0    0     0          0         0  2097152    2100    0    0    0     0       0          0\n"
            )
        return super().shell(serial, command, timeout=timeout)


class TestAMAFv7Universal2FAWebCaptchaAnd30Subagents(unittest.TestCase):

    def setUp(self):
        self.fake_adb = FakeV7ADB()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mem_file = Path(self.temp_dir.name) / "v7_test_memory.json"
        self.memory = MemoryManager(memory_file=self.mem_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_universal_2fa_all_7_modes_and_rfc6238_rfc4226_vectors(self):
        vault_path = Path(self.temp_dir.name) / "vault_2fa.json"
        engine = Universal2FAEngine(vault_file=vault_path)
        subagent = Universal2FASubagent(adb=self.fake_adb, memory=self.memory, engine=engine)

        self.assertEqual(len(subagent.SUPPORTED_2FA_MODES), 7)

        # RFC 4226 Appendix D official test vector for ASCII "12345678901234567890"
        rfc_secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        self.assertEqual(engine.generate_hotp(rfc_secret, counter=0), "755224")
        self.assertEqual(engine.generate_hotp(rfc_secret, counter=1), "287082")

        # RFC 6238 Appendix B official test vector at timestamp=59 (8 digits)
        self.assertEqual(
            engine.generate_totp(rfc_secret, digits=8, period=30, algorithm="SHA1", timestamp=59.0)["code"],
            "94287082"
        )

        # 1. TOTP_RFC6238 single-field
        xml_totp = (
            '<hierarchy>'
            '<node text="Nhập mã xác thực 2 bước từ Google Authenticator" class="android.widget.TextView" bounds="[60,200][1020,280]"/>'
            '<node text="" class="android.widget.EditText" clickable="true" bounds="[60,320][1020,440]"/>'
            '<node text="Xác nhận" class="android.widget.Button" clickable="true" bounds="[60,500][1020,620]"/>'
            '</hierarchy>'
        )
        r_totp = subagent.solve_2fa_challenge("10CF5L0TYL00312", secret="JBSWY3DPEHPK3PXP", xml_override=xml_totp)
        self.assertEqual(r_totp["status"], "2FA_SOLVED")
        self.assertEqual(r_totp["mode"], "TOTP_RFC6238")
        self.assertEqual(len(r_totp["code_used"]), 6)

        # 2. HOTP_RFC4226
        engine.register_otpauth_uri("otpauth://hotp/CorpVPN:alice?secret=JBSWY3DPEHPK3PXP&counter=0&digits=6")
        xml_hotp = (
            '<hierarchy>'
            '<node text="Enter HOTP counter-based code" class="android.widget.TextView" bounds="[60,200][1020,280]"/>'
            '<node text="" class="android.widget.EditText" clickable="true" bounds="[60,320][1020,440]"/>'
            '<node text="Submit" class="android.widget.Button" clickable="true" bounds="[60,500][1020,620]"/>'
            '</hierarchy>'
        )
        r_hotp = subagent.solve_2fa_challenge("10CF5L0TYL00312", account_id="CorpVPN:alice", xml_override=xml_hotp)
        self.assertEqual(r_hotp["status"], "2FA_SOLVED")
        self.assertEqual(r_hotp["mode"], "HOTP_RFC4226")

        # 3. SPLIT_DIGIT_BOX_OTP (6 separate small EditText boxes sorted left-to-right by x1)
        xml_split = (
            '<hierarchy>'
            '<node text="Verification Code" class="android.widget.TextView" bounds="[60,180][1020,250]"/>'
            '<node class="android.widget.EditText" bounds="[210,300][330,420]"/>'
            '<node class="android.widget.EditText" bounds="[60,300][180,420]"/>'
            '<node class="android.widget.EditText" bounds="[360,300][480,420]"/>'
            '<node class="android.widget.EditText" bounds="[510,300][630,420]"/>'
            '<node class="android.widget.EditText" bounds="[660,300][780,420]"/>'
            '<node class="android.widget.EditText" bounds="[810,300][930,420]"/>'
            '<node text="Confirm" class="android.widget.Button" clickable="true" bounds="[60,500][1020,620]"/>'
            '</hierarchy>'
        )
        r_split = subagent.solve_2fa_challenge("10CF5L0TYL00312", secret="JBSWY3DPEHPK3PXP", xml_override=xml_split)
        self.assertEqual(r_split["status"], "2FA_SOLVED")
        self.assertEqual(r_split["mode"], "SPLIT_DIGIT_BOX_OTP")
        self.assertEqual([b["center_x"] for b in r_split["details"]["box_actions"]], [120, 270, 420, 570, 720, 870])

        # 4. PUSH_NUMBER_MATCH ("Chạm vào số 84")
        xml_push = (
            '<hierarchy>'
            '<node text="Chạm vào số 84 trên thiết bị của bạn" class="android.widget.TextView" bounds="[60,200][1020,280]"/>'
            '<node text="31" class="android.widget.Button" clickable="true" bounds="[100,400][320,550]"/>'
            '<node text="84" class="android.widget.Button" clickable="true" bounds="[420,400][640,550]"/>'
            '<node text="59" class="android.widget.Button" clickable="true" bounds="[740,400][960,550]"/>'
            '</hierarchy>'
        )
        r_push = subagent.solve_2fa_challenge("10CF5L0TYL00312", xml_override=xml_push)
        self.assertEqual(r_push["status"], "2FA_SOLVED")
        self.assertEqual(r_push["mode"], "PUSH_NUMBER_MATCH")
        self.assertEqual(r_push["code_used"], "84")
        self.assertEqual(r_push["details"]["tapped_coords"], (530, 475))

        # 5. CROSS_APP_AUTHENTICATOR
        r_cross = subagent.solve_2fa_challenge(
            "10CF5L0TYL00312",
            secret="JBSWY3DPEHPK3PXP",
            authenticator_pkg="com.google.android.apps.authenticator2",
            xml_override=xml_totp
        )
        self.assertEqual(r_cross["status"], "2FA_SOLVED")
        self.assertEqual(r_cross["mode"], "CROSS_APP_AUTHENTICATOR")

        # 6. PASSKEY_WEBAUTHN
        xml_passkey = (
            '<hierarchy>'
            '<node text="Sign in with a passkey" package="androidx.credentials" class="android.widget.TextView" bounds="[60,800][1020,880]"/>'
            '<node text="Continue with passkey" class="android.widget.Button" clickable="true" bounds="[100,950][980,1080]"/>'
            '</hierarchy>'
        )
        r_passkey = subagent.solve_2fa_challenge("10CF5L0TYL00312", xml_override=xml_passkey)
        self.assertEqual(r_passkey["status"], "2FA_SOLVED")
        self.assertEqual(r_passkey["mode"], "PASSKEY_WEBAUTHN")

        # 7. BACKUP_RECOVERY_CODE
        engine.register_backup_codes("GitHub:octocat", ["9911-2233", "4455-6677"])
        xml_backup = (
            '<hierarchy>'
            '<node text="Nhập mã dự phòng 8 chữ số (backup code)" class="android.widget.TextView" bounds="[60,200][1020,280]"/>'
            '<node class="android.widget.EditText" clickable="true" bounds="[60,320][1020,440]"/>'
            '<node text="Verify" class="android.widget.Button" clickable="true" bounds="[60,500][1020,620]"/>'
            '</hierarchy>'
        )
        r_backup = subagent.solve_2fa_challenge("10CF5L0TYL00312", account_id="GitHub:octocat", xml_override=xml_backup)
        self.assertEqual(r_backup["status"], "2FA_SOLVED")
        self.assertEqual(r_backup["mode"], "BACKUP_RECOVERY_CODE")
        self.assertEqual(r_backup["code_used"], "9911-2233")

    def test_02_concentric_rotation_multi_image_grid_and_web_captcha_subagent_27(self):
        engine = WebAndAdvancedCaptchaEngine()
        subagent = WebAndAdvancedCaptchaSubagent(adb=self.fake_adb, memory=self.memory, engine=engine)

        # 1. Concentric Dual-Ring Image Rotation CAPTCHA (`xoay ảnh`) at 125°
        rot_png = str(Path(self.temp_dir.name) / "concentric_rot_125.png")
        engine.generate_synthetic_concentric_rotation_image(rot_png, size=320, true_angle_deg=125)
        rot_res = subagent.solve_rotation_captcha_advanced("10CF5L0TYL00312", screenshot_path=rot_png, track_width=520)
        self.assertEqual(rot_res["status"], "ROTATION_CAPTCHA_SOLVED")
        self.assertAlmostEqual(rot_res["angle_deg"], 125, delta=5)
        self.assertEqual(rot_res["trajectory_points"], 18)

        # 2. Multi-Image 3x3 & 4x4 Grid Selection CAPTCHA (`chọn nhiều ảnh`)
        grid3_png = str(Path(self.temp_dir.name) / "grid_3x3.png")
        engine.generate_synthetic_multi_image_grid(grid3_png, grid_size=3, target_indices=[0, 2, 4, 7])
        grid3_res = subagent.solve_multi_image_grid_captcha("10CF5L0TYL00312", screenshot_path=grid3_png, grid_size=3, rounds=2)
        self.assertEqual(grid3_res["status"], "MULTI_IMAGE_GRID_SOLVED")
        self.assertEqual(grid3_res["selected_indices"], [0, 2, 4, 7])
        self.assertGreaterEqual(grid3_res["tiles_tapped_count"], 4)

        grid4_png = str(Path(self.temp_dir.name) / "grid_4x4.png")
        engine.generate_synthetic_multi_image_grid(grid4_png, grid_size=4, target_indices=[1, 5, 10, 14])
        grid4_res = subagent.solve_multi_image_grid_captcha("10CF5L0TYL00312", screenshot_path=grid4_png, grid_size=4, rounds=1)
        self.assertEqual(grid4_res["status"], "MULTI_IMAGE_GRID_SOLVED")
        self.assertEqual(grid4_res["selected_indices"], [1, 5, 10, 14])

        # 3. Navigate to Web Page & Solve Browser/WebView CAPTCHA (`truy cập trang web giải capcha`)
        web_xml = (
            '<hierarchy>'
            '<node text="Kéo để xoay hình cho đúng chiều" bounds="[80,300][640,380]" class="android.widget.TextView"/>'
            '<node text="" resource-id="rotation_slider_track" bounds="[100,980][620,1060]" class="android.widget.SeekBar"/>'
            '</hierarchy>'
        )
        web_res = subagent.navigate_and_solve_web_captcha(
            serial="10CF5L0TYL00312",
            url="https://captcha.example.com/challenge",
            xml_override=web_xml,
            screenshot_path=rot_png,
            enable_cdp_forward=True
        )
        self.assertEqual(web_res["status"], "WEB_CAPTCHA_SOLVED")
        self.assertIn("chrome_devtools_remote", web_res["cdp_sockets"])
        self.assertEqual(web_res["captcha_result"]["status"], "ROTATION_CAPTCHA_SOLVED")

    def test_03_accessibility_wcag_contrast_and_talkback_focus_subagent_28(self):
        wcag = AccessibilityAndWCAGContrastSubagent(adb=self.fake_adb, memory=self.memory)

        self.assertEqual(wcag.compute_contrast_ratio((0, 0, 0), (255, 255, 255)), 21.0)
        self.assertLess(wcag.compute_contrast_ratio((140, 140, 140), (160, 160, 160)), 2.0)

        img_path = Path(self.temp_dir.name) / "wcag_screen.png"
        img = Image.new("RGB", (400, 600), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 200, 80], fill=(255, 255, 255))
        draw.rectangle([40, 35, 160, 65], fill=(0, 0, 0))
        draw.rectangle([20, 120, 200, 180], fill=(160, 160, 160))
        draw.rectangle([40, 135, 160, 165], fill=(140, 140, 140))
        img.save(img_path)

        sample_xml = (
            '<hierarchy rotation="0">'
            '<node index="0" text="High Contrast Header" content-desc="" clickable="false" focusable="true" bounds="[20,20][200,80]" />'
            '<node index="1" text="Low Contrast Subtitle" content-desc="" clickable="false" focusable="true" bounds="[20,120][200,180]" />'
            '<node index="2" text="" content-desc="Button" clickable="true" focusable="true" bounds="[20,450][120,510]" />'
            '<node index="3" text="" content-desc="Button" clickable="true" focusable="true" bounds="[20,220][120,280]" />'
            '<node index="4" text="" content-desc="" clickable="true" focusable="true" bounds="[140,220][220,280]" />'
            '</hierarchy>'
        )
        audit = wcag.audit_wcag_and_talkback_tree(
            "10CF5L0TYL00312",
            xml_override=sample_xml,
            screenshot_path=str(img_path)
        )
        self.assertEqual(audit["status"], "WCAG_AUDIT_COMPLETED")
        self.assertIn("LOW_CONTRAST_TEXT", audit["violations"])
        self.assertIn("UNLABELED_INTERACTIVE", audit["violations"])
        self.assertIn("ILLOGICAL_FOCUS_ORDER", audit["violations"])
        self.assertIn("DUPLICATE_CONTENT_DESC", audit["violations"])

    def test_04_crash_tombstone_anr_and_network_api_latency_subagents_29_30(self):
        crash_sub = CrashTombstoneAndANRSubagent(adb=self.fake_adb, memory=self.memory)
        sample_crash_log = (
            "10-25 19:45:01.112  4512  4512 E AndroidRuntime: FATAL EXCEPTION: main\n"
            "10-25 19:45:01.112  4512  4512 E AndroidRuntime: Process: com.wallet.app, PID: 4512\n"
            "10-25 19:45:01.112  4512  4512 E AndroidRuntime: java.lang.NullPointerException: null ref\n"
            "10-25 19:45:01.112  4512  4512 E AndroidRuntime:     at com.wallet.app.MainActivity.onClick(MainActivity.kt:42)\n"
            "10-25 19:45:05.300  4890  4890 F libc    : Fatal signal 11 (SIGSEGV), code 1 (SEGV_MAPERR) (>>> com.wallet.app <<<)\n"
            "10-25 19:45:05.350  4900  4900 F DEBUG   :       #00 pc 0001a2b4  /data/app/com.wallet.app/lib/arm64/libnative.so (processFrame+24)\n"
            "10-25 19:45:12.900  1024  1088 E ActivityManager: ANR in com.wallet.app (com.wallet.app/.MainActivity)\n"
            "10-25 19:45:12.900  1024  1088 E ActivityManager: Reason: Input dispatching timed out\n"
            "10-25 19:45:12.900  1024  1088 E ActivityManager: CPU usage from 0ms to 5210ms later: 88% TOTAL: 64% user + 24% kernel\n"
        )
        c_rep = crash_sub.analyze_logcat_and_tombstones(
            "10CF5L0TYL00312",
            package_name="com.wallet.app",
            raw_logcat_override=sample_crash_log
        )
        self.assertEqual(c_rep["status"], "CRASH_ANALYSIS_COMPLETED")
        self.assertEqual(c_rep["total_faults"], 3)
        self.assertEqual(c_rep["unique_signatures"], 3)
        self.assertTrue(c_rep["has_critical_fault"])

        net_sub = NetworkTrafficAndAPILatencySubagent(adb=self.fake_adb, memory=self.memory)
        sample_api_log = (
            "I/OkHttp: --> GET https://api.wallet.com/v1/balance HTTP/1.1 200 (95ms)\n"
            "W/OkHttp: --> POST http://cleartext.wallet.com/auth HTTP/1.1 502 (1920ms)\n"
        )
        n_rep = net_sub.run_network_api_telemetry_audit(
            "10CF5L0TYL00312",
            package_name="com.wallet.app",
            raw_logcat_override=sample_api_log
        )
        self.assertEqual(n_rep["status"], "NETWORK_API_AUDITED")
        self.assertEqual(n_rep["api_telemetry"]["api_calls_detected"], 2)
        self.assertEqual(n_rep["api_telemetry"]["cleartext_urls_count"], 1)
        self.assertEqual(n_rep["api_telemetry"]["failed_requests_count"], 1)
        self.assertEqual(n_rep["api_telemetry"]["slow_requests_count"], 1)
        self.assertLess(n_rep["api_health_score"], 100)

    def test_05_30_subagent_self_evolution_and_40_mcp_tools(self):
        engine = SelfEvolutionEngine(self.fake_adb, self.memory)
        evo = engine.run_evolution_loop(iterations=1, package_name="com.android.settings")
        self.assertEqual(evo["status"], "EVOLUTION_COMPLETED")
        self.assertGreaterEqual(evo["subagents_count"], 30)
        self.assertEqual(evo["cycles"][0]["supported_2fa_modes"], 7)

        mcp = AndroidFarmMCPServer()
        mcp.adb = self.fake_adb
        mcp.universal_2fa = Universal2FASubagent(self.fake_adb, self.memory)
        mcp.web_adv_captcha = WebAndAdvancedCaptchaSubagent(self.fake_adb, self.memory)
        mcp.wcag_auditor = AccessibilityAndWCAGContrastSubagent(self.fake_adb, self.memory)
        mcp.crash_analyzer = CrashTombstoneAndANRSubagent(self.fake_adb, self.memory)
        mcp.net_api_profiler = NetworkTrafficAndAPILatencySubagent(self.fake_adb, self.memory)

        self.assertGreaterEqual(len(mcp.tools), 40)

        r_2fa = mcp.handle_tool_call("android_universal_2fa_automation", {
            "serial": "10CF5L0TYL00312",
            "action": "generate_totp",
            "secret": "JBSWY3DPEHPK3PXP"
        })
        self.assertTrue(r_2fa["success"])
        self.assertEqual(len(r_2fa["code"]), 6)

        r_cdp = mcp.handle_tool_call("android_webview_devtools_bridge", {
            "serial": "10CF5L0TYL00312",
            "action": "discover_sockets"
        })
        self.assertTrue(r_cdp["success"])
        self.assertGreaterEqual(r_cdp["sockets_count"], 1)

        r_wcag = mcp.handle_tool_call("android_audit_wcag_accessibility", {
            "serial": "10CF5L0TYL00312"
        })
        self.assertTrue(r_wcag["success"])

        r_crash = mcp.handle_tool_call("android_analyze_crashes_and_anr", {
            "serial": "10CF5L0TYL00312"
        })
        self.assertTrue(r_crash["success"])

        r_net = mcp.handle_tool_call("android_audit_network_api_telemetry", {
            "serial": "10CF5L0TYL00312"
        })
        self.assertTrue(r_net["success"])


if __name__ == "__main__":
    unittest.main()
