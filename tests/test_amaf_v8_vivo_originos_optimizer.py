"""
Unit Test Suite for AMAF 8.0 Subagent #32:
- VivoOriginOSEngine (`core/vivo_originos_engine.py`)
- VivoOriginOSDeepOptimizerSubagent (`agents/vivo_originos_optimizer_subagent.py`)
All tests use deterministic mock ADB without touching physical devices.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.memory_manager import MemoryManager
from core.vivo_originos_engine import VivoOriginOSEngine
from agents.vivo_originos_optimizer_subagent import VivoOriginOSDeepOptimizerSubagent


class MockVivoOriginOSADB:
    """Deterministic Mock ADB for Vivo V2417A / OriginOS 6 unit tests."""

    def __init__(self, xml_response: str = ""):
        self.commands_executed: List[str] = []
        self.xml_response = xml_response or (
            '<hierarchy rotation="0">'
            '<node index="0" text="Cảnh báo bảo mật Vivo" class="android.widget.TextView" bounds="[100,1800][1160,1920]" />'
            '<node index="1" text="Tiếp tục cài đặt" resource-id="com.bbk.account:id/continue_btn" '
            'clickable="true" class="android.widget.Button" bounds="[180,2480][1080,2620]" />'
            '</hierarchy>'
        )

    def shell(self, serial: str, command: str, timeout: int = 30) -> str:
        self.commands_executed.append(command)
        if "ro.product.model" in command:
            return "V2417A"
        if "ro.product.device" in command:
            return "PD2417"
        if "ro.vivo.os.build.display.id" in command:
            return "OriginOS 6"
        if "wm size" in command:
            return "Physical size: 1260x2800"
        if "wm density" in command:
            return "Physical density: 560"
        if "dumpsys window" in command:
            return "  mCurrentFocus=Window{1a2b3c u0 com.bbk.launcher2/com.bbk.launcher2.Launcher}"
        return "OK"

    def dump_ui_hierarchy(self, serial: str) -> str:
        self.commands_executed.append("uiautomator dump")
        return self.xml_response


class TestAMAFv8VivoOriginOSOptimizer(unittest.TestCase):

    def setUp(self):
        self.engine = VivoOriginOSEngine()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mem_file = Path(self.temp_dir.name) / "v8_vivo_memory.json"
        self.memory = MemoryManager(memory_file=self.mem_file)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_parse_originos_telemetry_v2417a_1260x2800_560dpi(self):
        props_raw = (
            "[ro.product.model]: [V2417A]\n"
            "[ro.product.device]: [PD2417]\n"
            "[ro.vivo.os.build.display.id]: [OriginOS 6]\n"
        )
        size_raw = "Physical size: 1260x2800"
        density_raw = "Physical density: 560"
        window_raw = "mCurrentFocus=Window{99aabb u0 com.vivo.permissionmanager/com.vivo.permissionmanager.MainActivity}"

        telemetry = self.engine.parse_originos_telemetry(
            props_raw=props_raw,
            size_raw=size_raw,
            density_raw=density_raw,
            window_raw=window_raw
        )

        self.assertTrue(telemetry["is_vivo_originos"])
        self.assertEqual(telemetry["model"], "V2417A")
        self.assertEqual(telemetry["device_code"], "PD2417")
        self.assertEqual(telemetry["os_display_id"], "OriginOS 6")
        self.assertEqual(telemetry["width"], 1260)
        self.assertEqual(telemetry["height"], 2800)
        self.assertEqual(telemetry["density"], 560)
        self.assertAlmostEqual(telemetry["aspect_ratio"], round(2800 / 1260, 4), places=4)
        self.assertEqual(telemetry["focused_package"], "com.vivo.permissionmanager")

        bounds = telemetry["safe_touch_bounds"]
        self.assertEqual(bounds["top_inset_px"], int(2800 * 0.042))
        self.assertEqual(bounds["bottom_inset_px"], int(2800 * 0.038))
        self.assertEqual(bounds["y_min"], 117)
        self.assertEqual(bounds["y_max"], 2800 - 106)

    def test_02_calibrate_normalized_coordinates_clamping_and_center(self):
        # Center of 1260x2800 screen should not be clamped
        center_cal = self.engine.calibrate_normalized_coordinates(0.5, 0.5, width=1260, height=2800, respect_insets=True)
        self.assertEqual(center_cal["px"], 630)
        self.assertEqual(center_cal["py"], 1400)
        self.assertFalse(center_cal["clamped"])

        # Top edge (0.0, 0.0) should clamp inside top status bar inset and left side inset
        top_cal = self.engine.calibrate_normalized_coordinates(0.0, 0.0, width=1260, height=2800, respect_insets=True)
        self.assertEqual(top_cal["py"], int(2800 * 0.042))
        self.assertGreater(top_cal["px"], 0)
        self.assertTrue(top_cal["clamped"])

        # Bottom edge (1.0, 1.0) should clamp above OriginOS gesture bar inset
        bot_cal = self.engine.calibrate_normalized_coordinates(1.0, 1.0, width=1260, height=2800, respect_insets=True)
        self.assertEqual(bot_cal["py"], 2800 - int(2800 * 0.038))
        self.assertLess(bot_cal["px"], 1260)
        self.assertTrue(bot_cal["clamped"])

    def test_03_detect_vivo_system_interceptions_vietnamese_xml_and_fallback(self):
        vn_xml = (
            '<hierarchy rotation="0">'
            '<node index="0" text="Phát hiện ứng dụng chưa rõ nguồn gốc" class="android.widget.TextView" bounds="[80,1900][1180,2000]" />'
            '<node index="1" text="Cho phép cài đặt qua USB" clickable="true" class="android.widget.Button" bounds="[160,2420][1100,2580]" />'
            '</hierarchy>'
        )
        res = self.engine.detect_vivo_system_interceptions(vn_xml)
        self.assertTrue(res["interception_detected"])
        self.assertEqual(res["matched_label"], "Cho phép cài đặt qua USB")
        self.assertEqual(res["bounds"]["x1"], 160)
        self.assertEqual(res["bounds"]["y1"], 2420)
        self.assertEqual(res["bounds"]["x2"], 1100)
        self.assertEqual(res["bounds"]["y2"], 2580)
        self.assertEqual(res["center"], (630, 2500))

        # Test clean XML without any interception
        clean_xml = '<hierarchy rotation="0"><node text="Home Screen" bounds="[0,0][1260,2800]"/></hierarchy>'
        clean_res = self.engine.detect_vivo_system_interceptions(clean_xml)
        self.assertFalse(clean_res["interception_detected"])
        self.assertEqual(clean_res["fallback_coords"], {"cx": 630, "cy": 2550})

    def test_04_subagent_inspect_and_optimize_vivo_device_with_mock_adb(self):
        mock_adb = MockVivoOriginOSADB()
        subagent = VivoOriginOSDeepOptimizerSubagent(adb=mock_adb, memory=self.memory)

        report = subagent.inspect_and_optimize_vivo_device(
            serial="10CF5L0TYL00312",
            keep_awake=True,
            dismiss_keyguard=True
        )

        self.assertEqual(report["status"], "VIVO_ORIGINOS_OPTIMIZED")
        self.assertEqual(report["serial"], "10CF5L0TYL00312")
        self.assertTrue(report["telemetry"]["is_vivo_originos"])
        self.assertEqual(report["telemetry"]["model"], "V2417A")
        self.assertEqual(report["telemetry"]["os_display_id"], "OriginOS 6")
        self.assertEqual(report["telemetry"]["width"], 1260)
        self.assertEqual(report["telemetry"]["height"], 2800)
        self.assertEqual(report["telemetry"]["density"], 560)

        self.assertIn("svc power stayon usb", report["optimizations_applied"])
        self.assertIn("input keyevent 224", report["optimizations_applied"])
        self.assertIn("wm dismiss-keyguard", report["optimizations_applied"])

        self.assertTrue(report["interception_check"]["interception_detected"])
        self.assertEqual(report["interception_check"]["matched_label"], "Tiếp tục cài đặt")
        self.assertEqual(report["interception_check"]["center"], (630, 2550))


if __name__ == "__main__":
    unittest.main()
