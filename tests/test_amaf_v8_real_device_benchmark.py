"""
Unit Tests for AMAF 8.0 Subagent #35 (`RealDeviceE2EBenchmarkAndSelfHealerSubagent`)
and `RealDeviceBenchmarkRunner` (`core/real_device_benchmark_runner.py`).
All tests use a deterministic Mock ADB (`FakeBenchmarkADB`) and never execute real ADB commands.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager
from core.real_device_benchmark_runner import RealDeviceBenchmarkRunner
from agents.real_device_e2e_benchmark_subagent import RealDeviceE2EBenchmarkAndSelfHealerSubagent


class FakeBenchmarkADB(ADBWrapper):
    """Deterministic zero-I/O mock ADB for testing Subagent #35 without physical ADB execution."""

    def __init__(self):
        self.adb_path = "mock_adb"
        self.commands_log = []

    def run_command(self, args, timeout=30):
        self.commands_log.append(list(args))
        return 0, "", ""

    def run_device_cmd(self, serial, args, timeout=30):
        self.commands_log.append(["-s", serial] + list(args))
        return 0, "", ""

    def shell(self, serial, command, timeout=30):
        self.commands_log.append(["-s", serial, "shell", command])
        if "wm size" in command:
            return "Physical size: 720x1600"
        if "wm density" in command:
            return "Physical density: 320"
        if "ro.product.model" in command:
            return "V2417A"
        if "ro.product.manufacturer" in command:
            return "vivo"
        if "ro.build.version.release" in command:
            return "14"
        if "ro.build.version.sdk" in command:
            return "34"
        if "/proc/net/dev" in command:
            return (
                "Inter-|   Receive                                                |  Transmit\n"
                " wlan0: 8388608    6200    0    0    0     0          0         0  3145728    2900    0    0    0     0       0          0\n"
            )
        return ""

    def dump_ui_hierarchy(self, serial):
        return (
            '<hierarchy rotation="0">'
            '<node index="0" text="Settings" resource-id="android:id/title" '
            'class="android.widget.TextView" clickable="true" focusable="true" bounds="[48,180][672,280]" />'
            "</hierarchy>"
        )

    def capture_screenshot(self, serial, local_output_path):
        Path(local_output_path).parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (720, 1600), color=(245, 247, 250))
        draw = ImageDraw.Draw(img)
        draw.rectangle([48, 180, 672, 280], fill=(35, 95, 215), outline=(20, 40, 90), width=3)
        draw.rectangle([48, 320, 672, 420], fill=(40, 165, 95), outline=(20, 80, 45), width=3)
        img.save(local_output_path, format="PNG")
        return True

    def get_logcat_crashes(self, serial, lines=300):
        return ""


class TestAMAFv8RealDeviceBenchmark(unittest.TestCase):
    """Verification suite for `RealDeviceBenchmarkRunner` and `RealDeviceE2EBenchmarkAndSelfHealerSubagent`."""

    def setUp(self):
        self.mock_adb = FakeBenchmarkADB()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.mem_path = Path(self.temp_dir.name) / "test_v8_memory.json"
        self.memory = MemoryManager(memory_file=self.mem_path)
        self.reports_dir = Path(self.temp_dir.name) / "reports"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_01_runner_executes_all_8_stages_with_high_score_and_grade(self):
        runner = RealDeviceBenchmarkRunner(adb=self.mock_adb, memory=self.memory)
        result = runner.execute_benchmark_suite(
            serial="10CF5L0TYL00312",
            package_name="com.android.settings",
            execute_touch=True,
        )

        self.assertEqual(result["status"], "E2E_BENCHMARK_COMPLETED")
        self.assertEqual(result["serial"], "10CF5L0TYL00312")
        self.assertEqual(result["stages_total"], 8)
        self.assertEqual(result["stages_passed"], 8)
        self.assertGreaterEqual(result["total_benchmark_score"], 90.0)
        self.assertIn(result["grade"], ("S+", "A+"))

        stage_names = [s["stage"] for s in result["stage_results"]]
        self.assertEqual(stage_names, RealDeviceBenchmarkRunner.STAGE_NAMES)
        for st in result["stage_results"]:
            self.assertTrue(st["passed"], f"Stage failed: {st}")
            self.assertGreaterEqual(st["score"], 85.0)

    def test_02_markdown_benchmark_report_generation(self):
        runner = RealDeviceBenchmarkRunner(adb=self.mock_adb, memory=self.memory)
        result = runner.execute_benchmark_suite(
            serial="10CF5L0TYL00312",
            package_name="com.android.settings",
            execute_touch=False,
        )
        report_path = runner.write_benchmark_markdown_report(result, output_dir=self.reports_dir)

        self.assertTrue(os.path.exists(report_path))
        self.assertIn("REAL_DEVICE_E2E_BENCHMARK_10CF5L0TYL00312_", Path(report_path).name)
        content = Path(report_path).read_text(encoding="utf-8")
        self.assertIn("STAGE_1_HARDWARE_AND_OEM_GUARD", content)
        self.assertIn("STAGE_3_CONCENTRIC_ROTATION_CAPTCHA_CV", content)
        self.assertIn("STAGE_5_UNIVERSAL_7MODE_2FA", content)
        self.assertIn("STAGE_8_NETWORK_API_AND_FPS_PROFILING", content)
        self.assertIn(result["grade"], content)

    def test_03_subagent_35_full_device_e2e_benchmark_and_memory_persistence(self):
        subagent = RealDeviceE2EBenchmarkAndSelfHealerSubagent(
            adb=self.mock_adb,
            memory=self.memory,
        )
        res = subagent.run_full_device_e2e_benchmark(
            serial="10CF5L0TYL00312",
            package_name="com.android.settings",
            execute_touch=True,
            output_dir=self.reports_dir,
        )

        self.assertEqual(res["status"], "E2E_BENCHMARK_COMPLETED")
        self.assertEqual(res["serial"], "10CF5L0TYL00312")
        self.assertEqual(res["stages_passed"], 8)
        self.assertEqual(res["stages_total"], 8)
        self.assertGreaterEqual(res["total_benchmark_score"], 90.0)
        self.assertIn(res["grade"], ("S+", "A+"))
        self.assertTrue(os.path.exists(res["report_path"]))
        self.assertEqual(len(res["stage_results"]), 8)

        recalled = self.memory.recall(query="10CF5L0TYL00312", category="real_device_e2e_benchmark")
        self.assertGreaterEqual(len(recalled), 1)

    def test_04_captcha_and_2fa_stage_accuracy_inside_suite(self):
        runner = RealDeviceBenchmarkRunner(adb=self.mock_adb, memory=self.memory)
        res = runner.execute_benchmark_suite("emulator-5554", execute_touch=False)
        by_stage = {s["stage"]: s for s in res["stage_results"]}

        s3 = by_stage["STAGE_3_CONCENTRIC_ROTATION_CAPTCHA_CV"]["details"]
        self.assertLessEqual(s3["angle_error_deg"], 5)

        s4 = by_stage["STAGE_4_MULTI_IMAGE_GRID_CAPTCHA_CV"]["details"]
        self.assertEqual(s4["grid_3x3_selected"], [0, 2, 4, 7])
        self.assertEqual(s4["grid_4x4_selected"], [1, 5, 10, 14])

        s5 = by_stage["STAGE_5_UNIVERSAL_7MODE_2FA"]["details"]
        self.assertEqual(s5["rfc4226_hotp_counter0"], "755224")
        self.assertEqual(s5["rfc6238_totp_59s"], "94287082")
        self.assertTrue(s5["totp_window_verified"])
        self.assertEqual(s5["consumed_backup_code"], "8821-4490")


if __name__ == "__main__":
    unittest.main()
