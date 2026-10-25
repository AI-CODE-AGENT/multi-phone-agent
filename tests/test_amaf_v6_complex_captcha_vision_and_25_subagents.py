"""
Comprehensive Verification Suite for AMAF 6.0:
- Subagent #21: AutoScreenshotSubagent & ScreenshotPerceptionEngine (Set-of-Mark, Crop/Zoom, NCC Template Match, Visual Diff)
- Subagent #22 & #19: ComplexCaptchaSubagent & UniversalCaptchaCVEngine (All 10 Complex CAPTCHA Types + Opaque WebView Canvas)
- Subagent #23: DeepLinkAndQRScannerSubagent (DeepLink Fuzzing, QR Viewfinder Detection & ZXing/Gallery QR Injection)
- Subagent #24: ClipboardAndBiometricHookSubagent (Clipboard OTP, Biometric Fingerprint/PIN, Notification Shade)
- Subagent #25: PerformanceAndMemLeakSubagent (FPS Jank Percentiles & PSS/Java/Native Heap Memory Leak Detection)
- SelfEvolutionEngine v6.0+ (25+ Subagents) & AndroidFarmMCPServer v6.0+ (34+ MCP Tools)
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.memory_manager import MemoryManager
from core.screenshot_perception_engine import ScreenshotPerceptionEngine
from core.universal_captcha_cv_engine import UniversalCaptchaCVEngine
from agents.auto_screenshot_subagent import AutoScreenshotSubagent
from agents.captcha_solver_subagent import CaptchaSolverSubagent
from agents.complex_captcha_subagent import ComplexCaptchaSubagent
from agents.deeplink_qr_scanner_subagent import DeepLinkAndQRScannerSubagent
from agents.clipboard_biometric_subagent import ClipboardAndBiometricHookSubagent
from agents.performance_memleak_subagent import PerformanceAndMemLeakSubagent
from agents.self_evolution_engine import SelfEvolutionEngine
from mcp_bridge.android_farm_mcp_server import AndroidFarmMCPServer


XML_ROTATION_CAPTCHA = (
    '<hierarchy>'
    '<node text="Kéo thanh trượt để xoay hình cho đúng chiều" resource-id="com.app:id/rotation_captcha" '
    'class="android.widget.TextView" bounds="[80,420][640,500]"/>'
    '<node text="" resource-id="com.app:id/seekbar_rotate" class="android.widget.SeekBar" '
    'bounds="[100,980][620,1060]" clickable="true"/>'
    '</hierarchy>'
)

XML_CLICK_ORDER_CAPTCHA = (
    '<hierarchy>'
    '<node text="Bấm theo thứ tự: Minh, Tâm, Phát" resource-id="com.app:id/click_order_prompt" '
    'class="android.widget.TextView" bounds="[60,360][660,430]"/>'
    '<node text="Minh" class="android.widget.TextView" clickable="true" bounds="[120,520][220,600]"/>'
    '<node text="Tâm" class="android.widget.TextView" clickable="true" bounds="[310,680][410,760]"/>'
    '<node text="Phát" class="android.widget.TextView" clickable="true" bounds="[480,550][580,630]"/>'
    '<node text="Xác nhận" class="android.widget.Button" clickable="true" bounds="[200,920][520,1000]"/>'
    '</hierarchy>'
)

XML_ICON_MATCH_CAPTCHA = (
    '<hierarchy>'
    '<node text="Chọn hình khác biệt với các hình còn lại" resource-id="com.app:id/icon_match" '
    'class="android.widget.TextView" bounds="[60,360][660,430]"/>'
    '<node text="" class="android.widget.ImageView" clickable="true" bounds="[80,500][220,640]"/>'
    '<node text="" class="android.widget.ImageView" clickable="true" bounds="[260,500][400,640]"/>'
    '<node text="" class="android.widget.ImageView" clickable="true" bounds="[440,500][580,640]"/>'
    '</hierarchy>'
)

XML_SLIDE_PATH_CAPTCHA = (
    '<hierarchy>'
    '<node text="Vẽ theo đường dẫn từ điểm đầu đến điểm cuối" resource-id="com.app:id/trajectory_captcha" '
    'class="android.widget.TextView" bounds="[60,360][660,430]"/>'
    '<node text="" class="android.view.View" clickable="true" bounds="[100,520][620,920]"/>'
    '</hierarchy>'
)

XML_HOLD_PRESS_CAPTCHA = (
    '<hierarchy>'
    '<node text="Nhấn và giữ nút để xác minh bạn là con người" resource-id="com.app:id/hold_captcha" '
    'class="android.widget.Button" clickable="true" bounds="[140,720][580,840]"/>'
    '</hierarchy>'
)

XML_AUDIO_CAPTCHA = (
    '<hierarchy>'
    '<node text="Nghe mã xác nhận âm thanh: 8 4 1 9" resource-id="com.app:id/audio_challenge" '
    'class="android.widget.TextView" bounds="[80,450][640,530]"/>'
    '<node text="" resource-id="com.app:id/audio_input" class="android.widget.EditText" '
    'clickable="true" bounds="[120,580][600,660]"/>'
    '<node text="Xác nhận" class="android.widget.Button" clickable="true" bounds="[200,720][520,800]"/>'
    '</hierarchy>'
)

XML_OPAQUE_WEBVIEW_CAPTCHA = (
    '<hierarchy>'
    '<node text="" resource-id="com.app:id/captcha_webview_container" '
    'class="android.webkit.WebView" clickable="true" bounds="[40,300][680,1200]"/>'
    '</hierarchy>'
)

XML_QR_SCANNER_SCREEN = (
    '<hierarchy>'
    '<node text="Quét mã QR để thanh toán" resource-id="com.wallet:id/scan_qr_title" '
    'class="android.widget.TextView" bounds="[100,120][620,200]"/>'
    '<node text="" content-desc="camera_preview viewfinder" resource-id="com.wallet:id/zxing_viewfinder" '
    'class="android.view.SurfaceView" bounds="[120,380][600,860]"/>'
    '</hierarchy>'
)


class FakeV6ADB:
    """Deterministic fake ADB layer for AMAF 6.0 unit tests."""

    def __init__(self):
        self.commands = []
        self.current_xml = "<hierarchy><node text='Settings' bounds='[80,120][360,220]' clickable='true'/></hierarchy>"

    def get_connected_devices(self):
        return [
            {"serial": "emulator-5554", "status": "device", "model": "sdk_gphone64_x86_64"},
            {"serial": "10CF5L0TYL00312", "status": "device", "model": "V2417A"},
        ]

    def run_command(self, args, timeout=30):
        self.commands.append(("host", args))
        return 0, "connected", ""

    def run_device_cmd(self, serial, args, timeout=30):
        self.commands.append((serial, args))
        joined = " ".join(args)
        if "wm size" in joined:
            return 0, "Physical size: 1080x2400", ""
        if "emu finger touch" in joined:
            return 0, "OK", ""
        if "install" in joined:
            return 0, "Success", ""
        return 0, "OK", ""

    def shell(self, serial, command, timeout=30):
        self.commands.append((serial, ["shell", command]))
        if "wm size" in command:
            return "Physical size: 1080x2400"
        if "getprop ro.product.manufacturer" in command:
            return "vivo" if serial == "10CF5L0TYL00312" else "Google"
        if "getprop ro.product.model" in command:
            return "V2417A" if serial == "10CF5L0TYL00312" else "sdk_gphone64"
        if "dumpsys battery" in command:
            return "level: 88\nvoltage: 4210\ntemperature: 325\n"
        if "pm list packages" in command:
            return "package:com.android.settings\npackage:com.wallet.app\n"
        if "am start -W -a android.intent.action.VIEW" in command:
            return "Status: ok\nLaunchState: COLD\nActivity: com.wallet.app/.DeepLinkActivity\nTotalTime: 142\n"
        if "dumpsys gfxinfo" in command:
            return (
                "Total frames rendered: 300\n"
                "Janky frames: 5 (1.67%)\n"
                "50th percentile: 6ms\n"
                "90th percentile: 10ms\n"
                "95th percentile: 13ms\n"
                "99th percentile: 18ms\n"
            )
        if "dumpsys meminfo" in command:
            return (
                "Applications Memory Usage (in Kilobytes):\n"
                "  Java Heap: 22400\n"
                "  Native Heap: 26100\n"
                "  TOTAL PSS: 79400\n"
                "  Activities: 2\n"
                "  ViewRootImpl: 2\n"
            )
        if "dumpsys notification" in command:
            return (
                "NotificationRecord(0x01: pkg=com.wallet.app)\n"
                "  extras={\n"
                "    android.title=String (Xác thực giao dịch)\n"
                "    android.text=String (Mã OTP của bạn là 948271)\n"
                "  }\n"
            )
        if "cmd clipboard get-text" in command:
            return ""
        return "OK"

    def dump_ui_hierarchy(self, serial):
        return self.current_xml

    def parse_ui_elements(self, xml_string):
        from core.adb_wrapper import ADBWrapper
        return ADBWrapper().parse_ui_elements(xml_string)

    def capture_screenshot(self, serial, local_output_path):
        img = Image.new("RGB", (720, 1600), (242, 244, 248))
        draw = ImageDraw.Draw(img)
        draw.rectangle([80, 120, 360, 220], fill=(35, 115, 235), outline=(10, 40, 90), width=3)
        draw.rectangle([100, 500, 620, 620], fill=(220, 80, 60), outline=(40, 20, 20), width=3)
        draw.ellipse([145, 515, 215, 585], fill=(255, 235, 60), outline=(15, 15, 15), width=4)
        draw.line([145, 550, 215, 550], fill=(15, 15, 15), width=3)
        draw.line([180, 515, 180, 585], fill=(15, 15, 15), width=3)
        img.save(local_output_path, "PNG")
        return True

    def tap(self, serial, x, y):
        self.commands.append((serial, ["tap", x, y]))

    def swipe(self, serial, x1, y1, x2, y2, duration_ms=300):
        self.commands.append((serial, ["swipe", x1, y1, x2, y2, duration_ms]))

    def input_text(self, serial, text):
        self.commands.append((serial, ["input_text", text]))

    def press_key(self, serial, keycode):
        self.commands.append((serial, ["press_key", keycode]))

    def launch_app(self, serial, package_name, activity_name=None):
        return True

    def stop_app(self, serial, package_name):
        pass

    def optimize_system_animations(self, serial):
        pass

    def is_boot_completed(self, serial):
        return True

    def get_current_app(self, serial):
        return {"package": "com.android.settings", "activity": ".Settings"}

    def get_logcat_crashes(self, serial, lines=100):
        return ""


class TestAMAFv6ComplexCaptchaVisionAnd25Subagents(unittest.TestCase):

    def setUp(self):
        self.fake_adb = FakeV6ADB()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mem_file = Path(self.temp_dir.name) / "v6_test_memory.json"
        self.memory = MemoryManager(memory_file=self.mem_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_auto_screenshot_set_of_mark_ncc_template_and_visual_diff(self):
        out_dir = Path(self.temp_dir.name) / "shots"
        engine = ScreenshotPerceptionEngine(adb=self.fake_adb, output_dir=out_dir)
        subagent = AutoScreenshotSubagent(adb=self.fake_adb, memory=self.memory, engine=engine)

        res_som = subagent.capture_smart_screenshot("10CF5L0TYL00312", tag="unit_som", annotate_som=True)
        self.assertEqual(res_som["status"], "SCREENSHOT_CAPTURED")
        self.assertTrue(os.path.exists(res_som["screenshot_path"]))
        self.assertTrue(os.path.exists(res_som["annotated_screenshot_path"]))
        self.assertGreaterEqual(res_som["marks_count"], 1)

        loc_mark = subagent.locate_by_template_or_som(
            "10CF5L0TYL00312",
            mark_id=1,
            screenshot_path=res_som["screenshot_path"]
        )
        self.assertEqual(loc_mark["status"], "LOCATED")
        self.assertGreater(loc_mark["center_x"], 0)

        crop_res = engine.crop_and_zoom_region(
            res_som["screenshot_path"],
            {"x1": 80, "y1": 120, "x2": 360, "y2": 220},
            zoom_factor=2
        )
        self.assertTrue(os.path.exists(crop_res["cropped_path"]))
        self.assertEqual(crop_res["zoomed_width"], 560)
        self.assertEqual(crop_res["zoomed_height"], 200)

        tmpl_path = str(out_dir / "template_btn.png")
        with Image.open(res_som["screenshot_path"]) as full_im:
            full_im.crop((100, 500, 260, 600)).save(tmpl_path, "PNG")
        ncc_res = engine.find_template_on_screen(res_som["screenshot_path"], tmpl_path, threshold=0.65)
        self.assertTrue(ncc_res["matched"])
        self.assertGreaterEqual(ncc_res["confidence"], 0.70)
        self.assertAlmostEqual(ncc_res["center_x"], 180, delta=16)
        self.assertAlmostEqual(ncc_res["center_y"], 550, delta=16)

        diff_same = engine.compare_screenshots(res_som["screenshot_path"], res_som["screenshot_path"])
        self.assertTrue(diff_same["is_visually_identical"])
        self.assertEqual(diff_same["similarity_score"], 100.0)

    def test_02_universal_complex_captcha_all_10_types_plus_opaque_webview(self):
        cv = UniversalCaptchaCVEngine()
        solver = CaptchaSolverSubagent(self.fake_adb, self.memory, cv_engine=cv)
        complex_sub = ComplexCaptchaSubagent(self.fake_adb, self.memory, cv_engine=cv, solver=solver)

        supported = complex_sub.get_supported_captcha_types()
        self.assertEqual(len(supported), 10)

        slider_png = str(Path(self.temp_dir.name) / "slider_gap_350.png")
        cv.generate_synthetic_slider_puzzle_image(slider_png, width=520, height=260, gap_x=350, gap_y=110)
        sobel_res = cv.detect_slider_gap_sobel(slider_png, track_width=520)
        self.assertEqual(sobel_res["method"], "sobel_vertical_projection")
        self.assertAlmostEqual(sobel_res["distance_px"], 350, delta=18)

        rot_png = str(Path(self.temp_dir.name) / "rotation_140.png")
        cv.generate_synthetic_rotation_puzzle_image(rot_png, size=300, target_angle_deg=140)
        res_rot = complex_sub.solve_any_captcha_with_vision(
            "10CF5L0TYL00312",
            xml_override=XML_ROTATION_CAPTCHA,
            screenshot_path=rot_png,
            auto_screenshot=False
        )
        self.assertEqual(res_rot["status"], "CAPTCHA_SOLVED")
        self.assertEqual(res_rot["captcha_type"], "ROTATION_PUZZLE")
        self.assertEqual(res_rot["cv_method"], "polar_ring_gradient")

        click_png = str(Path(self.temp_dir.name) / "click_order.png")
        cv.generate_synthetic_click_order_image(click_png)
        res_order = complex_sub.solve_any_captcha_with_vision(
            "10CF5L0TYL00312",
            xml_override=XML_CLICK_ORDER_CAPTCHA,
            screenshot_path=click_png,
            auto_screenshot=False
        )
        self.assertEqual(res_order["status"], "CAPTCHA_SOLVED")
        self.assertEqual(res_order["captcha_type"], "CLICK_ORDER_CAPTCHA")

        res_icon = complex_sub.solve_any_captcha_with_vision(
            "10CF5L0TYL00312",
            xml_override=XML_ICON_MATCH_CAPTCHA,
            screenshot_path=slider_png,
            auto_screenshot=False
        )
        self.assertEqual(res_icon["status"], "CAPTCHA_SOLVED")
        self.assertEqual(res_icon["captcha_type"], "ICON_SHAPE_MATCH_CAPTCHA")

        res_path = complex_sub.solve_any_captcha_with_vision(
            "10CF5L0TYL00312",
            xml_override=XML_SLIDE_PATH_CAPTCHA,
            auto_screenshot=False
        )
        self.assertEqual(res_path["status"], "CAPTCHA_SOLVED")
        self.assertEqual(res_path["captcha_type"], "SLIDE_PATH_TRAJECTORY_CAPTCHA")

        res_hold = complex_sub.solve_any_captcha_with_vision(
            "10CF5L0TYL00312",
            xml_override=XML_HOLD_PRESS_CAPTCHA,
            auto_screenshot=False
        )
        self.assertEqual(res_hold["status"], "CAPTCHA_SOLVED")
        self.assertEqual(res_hold["captcha_type"], "HOLD_PRESS_CHALLENGE")

        res_audio = complex_sub.solve_any_captcha_with_vision(
            "10CF5L0TYL00312",
            xml_override=XML_AUDIO_CAPTCHA,
            auto_screenshot=False
        )
        self.assertEqual(res_audio["status"], "CAPTCHA_SOLVED")
        self.assertEqual(res_audio["captcha_type"], "AUDIO_ACCESSIBILITY_CHALLENGE")

        res_webview = complex_sub.solve_any_captcha_with_vision(
            "10CF5L0TYL00312",
            xml_override=XML_OPAQUE_WEBVIEW_CAPTCHA,
            screenshot_path=slider_png,
            auto_screenshot=False
        )
        self.assertEqual(res_webview["status"], "CAPTCHA_SOLVED")
        self.assertEqual(res_webview["captcha_type"], "CANVAS_WEBVIEW_OPAQUE_CAPTCHA")

    def test_03_deeplink_qr_scanner_and_clipboard_biometric_notifications(self):
        dl_qr = DeepLinkAndQRScannerSubagent(self.fake_adb, self.memory)

        res_dl = dl_qr.open_deep_link("10CF5L0TYL00312", "myapp://checkout?order_id=991", "com.wallet.app")
        self.assertEqual(res_dl["status"], "DEEPLINK_OPENED")
        self.assertEqual(res_dl["launch_time_ms"], 142)

        res_fuzz = dl_qr.fuzz_deep_link_routes("10CF5L0TYL00312", "myapp://checkout")
        self.assertGreaterEqual(res_fuzz["routes_tested"], 3)
        self.assertEqual(res_fuzz["passed_count"], res_fuzz["routes_tested"])

        det_qr = dl_qr.detect_qr_scanner_screen("10CF5L0TYL00312", xml_override=XML_QR_SCANNER_SCREEN)
        self.assertTrue(det_qr["scanner_detected"])

        inj_qr = dl_qr.inject_qr_or_barcode_payload("10CF5L0TYL00312", "https://pay.example.com/qr/88219")
        self.assertEqual(inj_qr["status"], "QR_PAYLOAD_INJECTED")
        self.assertTrue(os.path.exists(inj_qr["local_qr_image"]))

        cb_bio = ClipboardAndBiometricHookSubagent(self.fake_adb, self.memory)
        cb_bio.set_clipboard("10CF5L0TYL00312", "Ma xac thuc Vietcombank: 583920")
        read_cb = cb_bio.get_clipboard("10CF5L0TYL00312")
        self.assertEqual(read_cb["status"], "CLIPBOARD_READ")
        self.assertEqual(read_cb["extracted_otp"], "583920")

        paste_res = cb_bio.paste_clipboard("10CF5L0TYL00312")
        self.assertEqual(paste_res["status"], "CLIPBOARD_PASTED")

        bio_emu = cb_bio.authenticate_biometric("emulator-5554", finger_id=1)
        self.assertEqual(bio_emu["status"], "BIOMETRIC_AUTHENTICATED")

        notif_res = cb_bio.inspect_and_interact_notifications("10CF5L0TYL00312")
        self.assertEqual(notif_res["status"], "NOTIFICATIONS_INSPECTED")
        self.assertIn("948271", notif_res["extracted_otps"])

    def test_04_performance_and_memleak_profiler_subagent_25(self):
        perf = PerformanceAndMemLeakSubagent(self.fake_adb, self.memory)

        healthy = perf.run_comprehensive_performance_audit("10CF5L0TYL00312", "com.wallet.app")
        self.assertEqual(healthy["status"], "PERFORMANCE_AUDITED")
        self.assertIn(healthy["performance_grade"], ("A+", "A"))
        self.assertFalse(healthy["memory_leak_suspected"])

        leaking_mem = (
            "Applications Memory Usage (in Kilobytes):\n"
            "  Java Heap: 95000\n"
            "  Native Heap: 110000\n"
            "  TOTAL PSS: 195000\n"
            "  Activities: 9\n"
            "  ViewRootImpl: 11\n"
        )
        leaky = perf.run_comprehensive_performance_audit(
            "10CF5L0TYL00312",
            "com.wallet.app",
            raw_mem_override=leaking_mem,
            baseline_pss_kb=80000
        )
        self.assertTrue(leaky["memory_leak_suspected"])
        self.assertGreaterEqual(len(leaky["memory"]["leak_warnings"]), 2)

    def test_05_25_subagent_self_evolution_and_34_mcp_tools(self):
        engine = SelfEvolutionEngine(self.fake_adb, self.memory)
        evo = engine.run_evolution_loop(iterations=1, package_name="com.android.settings")
        self.assertEqual(evo["status"], "EVOLUTION_COMPLETED")
        self.assertGreaterEqual(evo["subagents_count"], 25)
        self.assertEqual(evo["cycles"][0]["supported_captcha_types"], 10)

        mcp = AndroidFarmMCPServer()
        mcp.adb = self.fake_adb
        mcp.auto_screenshot = AutoScreenshotSubagent(self.fake_adb, self.memory)
        mcp.complex_captcha = ComplexCaptchaSubagent(self.fake_adb, self.memory)
        mcp.deeplink_qr = DeepLinkAndQRScannerSubagent(self.fake_adb, self.memory)
        mcp.clipboard_bio = ClipboardAndBiometricHookSubagent(self.fake_adb, self.memory)
        mcp.perf_profiler = PerformanceAndMemLeakSubagent(self.fake_adb, self.memory)

        self.assertGreaterEqual(len(mcp.tools), 34)

        r_som = mcp.handle_tool_call("android_auto_screenshot_som", {
            "serial": "10CF5L0TYL00312",
            "action": "capture_som"
        })
        self.assertTrue(r_som["success"])

        r_cap = mcp.handle_tool_call("android_solve_complex_captcha_cv", {
            "serial": "10CF5L0TYL00312",
            "action": "list_supported_types"
        })
        self.assertTrue(r_cap["success"])
        self.assertEqual(r_cap["count"], 10)

        r_qr = mcp.handle_tool_call("android_deeplink_and_qr_scanner", {
            "serial": "10CF5L0TYL00312",
            "action": "inject_qr",
            "payload": "https://example.com/qr"
        })
        self.assertTrue(r_qr["success"])

        r_cb = mcp.handle_tool_call("android_clipboard_biometric_and_notifications", {
            "serial": "10CF5L0TYL00312",
            "action": "inspect_notifications"
        })
        self.assertTrue(r_cb["success"])

        r_perf = mcp.handle_tool_call("android_profile_performance_and_memleak", {
            "serial": "10CF5L0TYL00312",
            "package_name": "com.android.settings",
            "action": "full_audit"
        })
        self.assertTrue(r_perf["success"])


if __name__ == "__main__":
    unittest.main()
