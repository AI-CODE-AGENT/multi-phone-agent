"""
Comprehensive Unit & Integration Tests for AMAF 5.0:
- HumanTouchEngine & HumanTouchSubagent (#17) (Gaussian jitter, Cubic Bezier trajectory, overshoot slider drag)
- OEMPopupWatcher & OEMPopupGuardSubagent (#18) (Vivo/OriginOS 'Tiếp tục cài đặt' / 'Cho phép cài đặt qua USB' bypass + APK install guard)
- CaptchaSolverSubagent (#19) (Slider Puzzle, Math/Text OCR, Checkbox, Image Grid)
- NetworkAndVisualQASubagent (#20) (48dp touch-target audit, overlapping clickables, Wi-Fi resilience)
- SelfEvolutionEngine (20 Subagents) & AndroidFarmMCPServer (28 Tools)
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.adb_wrapper import ADBWrapper
from core.real_device_manager import RealDeviceManager
from core.human_touch_engine import HumanTouchEngine
from core.oem_popup_watcher import OEMPopupWatcher
from core.memory_manager import MemoryManager
from agents.human_touch_subagent import HumanTouchSubagent
from agents.oem_popup_guard_subagent import OEMPopupGuardSubagent
from agents.captcha_solver_subagent import CaptchaSolverSubagent
from agents.network_visual_qa_subagent import NetworkAndVisualQASubagent
from agents.self_evolution_engine import SelfEvolutionEngine
from mcp_bridge.android_farm_mcp_server import AndroidFarmMCPServer


XML_VIVO_INSTALL_POPUP = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="Cảnh báo bảo mật OriginOS" resource-id="com.vivo.secime:id/title" class="android.widget.TextView" package="com.vivo.secime" clickable="false" bounds="[80,1400][1000,1500]" />
  <node index="1" text="Tiếp tục cài đặt" resource-id="com.vivo.secime:id/continue_install_btn" class="android.widget.Button" package="com.vivo.secime" content-desc="Cho phép cài đặt qua USB" clickable="true" bounds="[140,2020][940,2160]" />
</hierarchy>
"""

XML_SLIDER_CAPTCHA = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="Kéo thanh trượt để hoàn thành hình ghép" resource-id="com.app:id/captcha_title" class="android.widget.TextView" package="com.app" clickable="false" bounds="[80,500][980,580]" />
  <node index="1" text="Slide to verify" resource-id="com.app:id/captcha_slider" class="android.widget.SeekBar" package="com.app" content-desc="Drag the slider" clickable="true" bounds="[100,1100][900,1220]" />
</hierarchy>
"""

XML_MATH_CAPTCHA = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="Nhập mã xác nhận: 15 + 8 = ?" resource-id="com.app:id/math_prompt" class="android.widget.TextView" package="com.app" clickable="false" bounds="[80,500][900,600]" />
  <node index="1" text="" resource-id="com.app:id/captcha_input" class="android.widget.EditText" package="com.app" clickable="true" bounds="[80,620][600,720]" />
  <node index="2" text="Xác nhận" resource-id="com.app:id/submit_btn" class="android.widget.Button" package="com.app" clickable="true" bounds="[620,620][900,720]" />
</hierarchy>
"""

XML_CHECKBOX_CAPTCHA = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="Tôi không phải là người máy" resource-id="com.app:id/recaptcha_checkbox" class="android.widget.CheckBox" package="com.app" content-desc="I'm not a robot" clickable="true" bounds="[120,800][680,920]" />
</hierarchy>
"""

XML_LAYOUT_DEFECTS = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="" content-desc="" resource-id="com.app:id/tiny_icon_btn" class="android.widget.ImageButton" package="com.app" clickable="true" bounds="[100,200][128,228]" />
  <node index="1" text="Button A" content-desc="Button A" resource-id="com.app:id/btn_a" class="android.widget.Button" package="com.app" clickable="true" bounds="[200,400][500,500]" />
  <node index="2" text="Button B" content-desc="Button B" resource-id="com.app:id/btn_b" class="android.widget.Button" package="com.app" clickable="true" bounds="[210,410][490,495]" />
</hierarchy>
"""


class FakeVivoAndCaptchaADB(ADBWrapper):
    def __init__(self):
        super().__init__()
        self.current_xml = XML_VIVO_INSTALL_POPUP
        self.commands_executed = []

    def get_connected_devices(self):
        return [
            {"serial": "emulator-5554", "status": "device", "model": "sdk_gphone64_x86_64"},
            {"serial": "10CF5L0TYL00312", "status": "device", "model": "Vivo_V23_OriginOS"},
        ]

    def dump_ui_hierarchy(self, serial: str) -> str:
        return self.current_xml

    def shell(self, serial: str, command: str, timeout: int = 30) -> str:
        self.commands_executed.append((serial, command))
        if "wm size" in command:
            return "Physical size: 1080x2400"
        if "mCurrentFocus" in command:
            return "mCurrentFocus=Window{111 u0 com.vivo.secime/com.vivo.secime.InstallConfirmActivity}"
        if "dumpsys battery" in command:
            return "  USB powered: true\n  level: 88\n  temperature: 340\n  voltage: 4100"
        return "OK"

    def run_device_cmd(self, serial: str, args, timeout: int = 30):
        if args and args[0] == "install":
            return 0, "Performing Streamed Install\nSuccess", ""
        return 0, "OK", ""


class TestAMAFv5HumanTouchCaptchaAndOEM(unittest.TestCase):
    def setUp(self):
        self.fake_adb = FakeVivoAndCaptchaADB()
        self.real_mgr = RealDeviceManager(self.fake_adb)
        self.memory = MemoryManager()

    def test_01_human_touch_engine_bezier_and_gaussian_jitter(self):
        engine = HumanTouchEngine(self.fake_adb, self.real_mgr)
        bounds = {"left": 100, "top": 200, "right": 300, "bottom": 280}
        jx, jy = engine.apply_gaussian_jitter(200, 240, bounds=bounds, sigma=5.0)
        self.assertTrue(100 <= jx <= 300)
        self.assertTrue(200 <= jy <= 280)

        traj = engine.generate_bezier_trajectory(100, 1160, 620, 1160, steps=16, include_overshoot=True)
        self.assertGreaterEqual(len(traj), 17)
        # Final point settles back on target end_x (620)
        self.assertEqual(traj[-1]["x"], 620)

        tap_res = engine.human_tap("10CF5L0TYL00312", 0.5, 0.88, is_normalized=True)
        self.assertEqual(tap_res["status"], "HUMAN_TAP_OK")
        self.assertTrue(50 <= tap_res["dwell_ms"] <= 150)

        drag_res = engine.human_slider_drag("10CF5L0TYL00312", 120, 1160, distance_px=420)
        self.assertEqual(drag_res["status"], "HUMAN_SLIDER_DRAG_OK")
        self.assertEqual(drag_res["end_x"], 540)

        sub = HumanTouchSubagent(self.fake_adb, self.memory)
        type_res = sub.execute_human_action("10CF5L0TYL00312", {"action": "type_text", "text": "OriginOS2026"})
        self.assertEqual(type_res["status"], "HUMAN_TYPE_OK")

    def test_02_vivo_originos_popup_watcher_and_guarded_apk_install(self):
        watcher = OEMPopupWatcher(self.fake_adb)
        self.fake_adb.current_xml = XML_VIVO_INSTALL_POPUP

        # 1. Direct XML match on Vivo 'Tiếp tục cài đặt'
        res_xml = watcher.scan_and_dismiss_oem_popup("10CF5L0TYL00312", use_vivo_coordinate_fallback=False)
        self.assertEqual(res_xml["status"], "POPUP_DISMISSED")
        self.assertEqual(res_xml["method"], "ui_xml_match")

        # 2. Coordinate fallback when Vivo security overlay blocks XML dump
        self.fake_adb.current_xml = "<hierarchy></hierarchy>"
        res_fb = watcher.scan_and_dismiss_oem_popup("10CF5L0TYL00312", use_vivo_coordinate_fallback=True)
        self.assertEqual(res_fb["status"], "POPUP_DISMISSED_FALLBACK")
        self.assertEqual(res_fb["method"], "vivo_originos_coord_fallback")

        # 3. Guarded APK installation with concurrent watcher thread
        self.fake_adb.current_xml = XML_VIVO_INSTALL_POPUP
        with tempfile.NamedTemporaryFile(suffix=".apk", delete=False) as tf:
            tf.write(b"DUMMY_APK_BYTES")
            temp_apk = tf.name
        try:
            guard_sub = OEMPopupGuardSubagent(self.fake_adb, self.memory)
            inst_res = guard_sub.guarded_apk_install("10CF5L0TYL00312", temp_apk)
            self.assertTrue(inst_res["success"])
        finally:
            if os.path.exists(temp_apk):
                os.remove(temp_apk)

    def test_03_captcha_solver_slider_math_and_checkbox(self):
        solver = CaptchaSolverSubagent(self.fake_adb, self.memory)

        # 1. Slider Puzzle CAPTCHA
        res_slider = solver.solve_captcha("10CF5L0TYL00312", xml_override=XML_SLIDER_CAPTCHA, hint_distance_px=380)
        self.assertEqual(res_slider["status"], "CAPTCHA_SOLVED")
        self.assertEqual(res_slider["captcha_type"], "SLIDER_PUZZLE")
        self.assertEqual(res_slider["drag_distance_px"], 380)

        # 2. Math / Text CAPTCHA (15 + 8 = 23)
        res_math = solver.solve_captcha("10CF5L0TYL00312", xml_override=XML_MATH_CAPTCHA)
        self.assertEqual(res_math["status"], "CAPTCHA_SOLVED")
        self.assertEqual(res_math["captcha_type"], "TEXT_MATH_OCR")
        self.assertEqual(res_math["answer"], "23")

        # 3. Checkbox Challenge ('Tôi không phải là người máy')
        res_cb = solver.solve_captcha("10CF5L0TYL00312", xml_override=XML_CHECKBOX_CAPTCHA)
        self.assertEqual(res_cb["status"], "CAPTCHA_SOLVED")
        self.assertEqual(res_cb["captcha_type"], "CHECKBOX_CHALLENGE")

    def test_04_network_and_visual_qa_subagent_20(self):
        qa = NetworkAndVisualQASubagent(self.fake_adb, self.memory)
        audit = qa.audit_ui_accessibility_and_layout("10CF5L0TYL00312", xml_override=XML_LAYOUT_DEFECTS)
        self.assertEqual(audit["status"], "LAYOUT_AUDIT_COMPLETED")
        self.assertGreaterEqual(audit["warnings_count"], 2)
        warning_types = [w.get("type") or w.get("code") or str(w) for w in audit["warnings"]]
        joined_warnings = " ".join(warning_types)
        self.assertIn("SMALL_TOUCH_TARGET", joined_warnings)
        self.assertIn("MISSING_ACCESSIBILITY_LABEL", joined_warnings)

        net_res = qa.run_network_resilience_check("10CF5L0TYL00312", "com.android.settings", toggle_wifi=True)
        self.assertEqual(net_res["status"], "NETWORK_RESILIENCE_VERIFIED")
        self.assertTrue(net_res["wifi_restored"])

    def test_05_20_subagent_evolution_and_28_mcp_tools(self):
        engine = SelfEvolutionEngine(self.fake_adb, self.memory)
        evo = engine.run_evolution_loop(iterations=1, package_name="com.android.settings")
        self.assertEqual(evo["status"], "EVOLUTION_COMPLETED")
        self.assertGreaterEqual(evo["subagents_count"], 20)

        mcp = AndroidFarmMCPServer()
        mcp.adb = self.fake_adb
        mcp.human_subagent = HumanTouchSubagent(self.fake_adb, memory=self.memory)
        mcp.oem_guard = OEMPopupGuardSubagent(self.fake_adb, memory=self.memory)
        mcp.captcha_solver = CaptchaSolverSubagent(self.fake_adb, self.memory)
        self.assertGreaterEqual(len(mcp.tools), 28)

        r_ht = mcp.handle_tool_call("android_human_touch_action", {
            "serial": "10CF5L0TYL00312",
            "action": "slider_drag",
            "x": 120,
            "y": 1160,
            "distance_px": 360
        })
        self.assertTrue(r_ht["success"])

        r_oem = mcp.handle_tool_call("android_oem_popup_guard", {
            "serial": "10CF5L0TYL00312",
            "action": "scan_and_dismiss",
            "use_vivo_fallback": True
        })
        self.assertTrue(r_oem["success"])

        self.fake_adb.current_xml = XML_SLIDER_CAPTCHA
        r_cap = mcp.handle_tool_call("android_solve_captcha", {
            "serial": "10CF5L0TYL00312",
            "action": "solve",
            "hint_distance_px": 340
        })
        self.assertTrue(r_cap["success"])
        self.assertEqual(r_cap["status"], "CAPTCHA_SOLVED")


if __name__ == "__main__":
    unittest.main()
