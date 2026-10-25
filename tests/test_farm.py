"""
Comprehensive Test Suite for Android Multi-Agent Farm
"""

import unittest
import os
import sys
import json
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.farm_config import DEFAULT_FARM_DEVICES, AVD_STORAGE_DIR, AVD_METADATA_DIR, find_scrcpy
from core.avd_cloner import get_farm_status, setup_farm
from core.adb_wrapper import ADBWrapper
from core.hardware_simulator import HardwareSimulator, PRESET_LOCATIONS
from core.scrcpy_manager import ScrcpyManager
from agents.device_lock_manager import DeviceLockManager
from agents.bug_reporter import BugReporter
from core.mock_otp_service import MockOTPService
from agents.planner_subagent import PlannerSubagent
from agents.healing_subagent import SelfHealingSubagent
from agents.auditor_subagent import AuditorSubagent


class TestAndroidFarm(unittest.TestCase):

    def test_01_avd_provisioning(self):
        """Test that all 4 AVD configs and metadata exist on D: drive."""
        status = get_farm_status()
        self.assertEqual(len(status), 4)
        for s in status:
            self.assertTrue(s["provisioned"], f"AVD {s['name']} is not provisioned")
            self.assertTrue(os.path.exists(s["path"]), f"Directory {s['path']} missing")

    def test_02_scrcpy_discovery(self):
        """Test that scrcpy executable was installed and can be located."""
        path = find_scrcpy()
        self.assertTrue(bool(path), "scrcpy path could not be resolved")
        sm = ScrcpyManager()
        self.assertTrue(sm.is_available(), "ScrcpyManager reports not available")

    def test_03_hardware_simulator_syntax(self):
        """Test hardware simulator methods and preset locations."""
        hw = HardwareSimulator()
        self.assertIn("hcm_center", PRESET_LOCATIONS)
        self.assertIn("hanoi_center", PRESET_LOCATIONS)
        loc = PRESET_LOCATIONS["hcm_center"]
        self.assertAlmostEqual(loc["lat"], 10.776889, places=4)

    def test_04_device_lock_concurrency(self):
        """Test device locking, conflict prevention, and release."""
        mgr = DeviceLockManager()
        serial = "emulator-5554"

        # Acquire lock
        acquired = mgr.acquire(serial, "Agent_Alpha", "Test_Task", 10)
        self.assertTrue(acquired)

        # Another agent tries to acquire
        conflict = mgr.acquire(serial, "Agent_Beta", "Other_Task", 10)
        self.assertFalse(conflict, "Second agent should have been blocked by lock")

        # First agent renews
        renewed = mgr.acquire(serial, "Agent_Alpha", "Updated_Task", 10)
        self.assertTrue(renewed)

        # First agent releases
        released = mgr.release(serial, "Agent_Alpha")
        self.assertTrue(released)

        # Second agent can now acquire
        now_acquired = mgr.acquire(serial, "Agent_Beta", "Other_Task", 10)
        self.assertTrue(now_acquired)
        mgr.release(serial, "Agent_Beta")

    def test_05_bug_reporter(self):
        """Test bug report generation and formatting."""
        reporter = BugReporter()
        report_file = reporter.generate_report(
            title="Unit Test Failure Sample",
            serial="emulator-5554",
            package_name="com.test.app",
            error_type="ASSERTION_ERROR",
            error_message="Button not clickable after 5s",
            step_history=[
                {"action": "tap", "target": "Login Button", "status": "success"},
                {"action": "tap", "target": "Submit Button", "status": "timeout"}
            ],
            stack_trace="java.lang.NullPointerException at com.test.app.MainActivity.onClick"
        )
        self.assertTrue(os.path.exists(report_file))
        content = Path(report_file).read_text(encoding="utf-8")
        self.assertIn("Unit Test Failure Sample", content)
        self.assertIn("NullPointerException", content)

        # Clean up test artifact
        try:
            os.remove(report_file)
            json_file = Path(report_file).with_suffix(".json")
            if json_file.exists():
                os.remove(json_file)
        except Exception:
            pass

    def test_06_mock_otp_service(self):
        """Test MockOTPService generation, retrieval, and verification."""
        service = MockOTPService()
        phone = "0941189263"
        code = service.generate_otp(phone, length=6)
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

        # Retrieve active
        retrieved = service.get_latest_otp(phone)
        self.assertEqual(retrieved, code)

        # Verify
        self.assertTrue(service.verify_otp(phone, code))
        # Once verified, cannot re-verify with same code
        self.assertFalse(service.verify_otp(phone, code))

    def test_07_planner_subagent(self):
        """Test PlannerSubagent plan decomposition and edge cases."""
        planner = PlannerSubagent()
        plan = planner.create_plan_from_goal("Dang nhap bang so 0941189263 va nhap OTP", "com.my.app")
        self.assertGreater(len(plan), 3)
        actions = [s["action"] for s in plan]
        self.assertIn("launch", actions)
        self.assertIn("mock_otp_flow", actions)

        # Edge cases
        edge_phones = planner.generate_edge_case_inputs("phone")
        self.assertIn("0941189263", edge_phones)
        self.assertIn("0000000000", edge_phones)

    def test_08_self_healing_matching(self):
        """Test fuzzy matching in SelfHealingSubagent."""
        healer = SelfHealingSubagent("emulator-5554")
        dummy_elements = [
            {"text": "Xác nhận đăng nhập", "bounds": {"center_x": 360, "center_y": 800}},
            {"content_desc": "Close button", "bounds": {"center_x": 700, "center_y": 100}},
        ]
        # Match with slight difference
        match = healer._fuzzy_find_element(dummy_elements, "Xác nhận")
        self.assertIsNotNone(match)
        self.assertEqual(match["text"], "Xác nhận đăng nhập")

    def test_09_auditor_recommendations(self):
        """Test AuditorSubagent code improvement rules."""
        auditor = AuditorSubagent("emulator-5554")
        fake_crash = "java.lang.NullPointerException: Attempt to invoke virtual method at com.app.User.getName(User.kt:42)"
        recs = auditor.generate_engineering_recommendations(fake_crash, [])
        self.assertTrue(any("NullPointerException" in r for r in recs))

    def test_10_memory_manager(self):
        """Test MemoryManager persistence, locators, and recall."""
        from core.memory_manager import MemoryManager
        mm = MemoryManager()
        # Remember and recall
        item = mm.remember("test_key", "test_val", tags=["unit_test", "core"])
        self.assertIsNotNone(item.get("id"))
        recalled = mm.recall(query="test_val", tags=["unit_test"])
        self.assertGreaterEqual(len(recalled), 1)

        # UI locator
        mm.save_locator("Screen_Login", "login_button", {"text": "Đăng nhập"}, [360, 1200])
        locs = mm.get_locators_for_screen("Screen_Login")
        self.assertEqual(len(locs), 1)
        self.assertEqual(locs[0]["element_role"], "login_button")

        # Summary
        summary = mm.get_summary()
        self.assertIn("knowledge_items_count", summary)

    def test_11_prompt_optimizer(self):
        """Test PromptOptimizerSubagent iterative refinement."""
        from agents.prompt_optimizer_subagent import PromptOptimizerSubagent
        opt = PromptOptimizerSubagent()
        feedback = {
            "scenario": "auth_test",
            "failures": [{"reason": "timeout waiting for otp"}],
            "healings": [{"type": "fuzzy_text"}],
            "avg_latency_ms": 300
        }
        res = opt.analyze_and_optimize("operator", "Click Login Button", feedback)
        self.assertEqual(res["status"], "OPTIMIZED")
        self.assertIn("Mock OTP Rule", res["optimized_prompt"])
        self.assertIn("Dynamic UI Rule", res["optimized_prompt"])

    def test_12_code_improver_patch_generation(self):
        """Test CodeImproverSubagent unified diff generation."""
        from agents.code_improver_subagent import CodeImproverSubagent
        improver = CodeImproverSubagent()
        defect = {
            "defect_id": "TEST_DEF_01",
            "defect_type": "NullPointerException",
            "title": "NPE in User.kt",
            "stack_trace": "java.lang.NullPointerException"
        }
        res = improver.analyze_defect_and_propose_patch(defect)
        self.assertEqual(res["status"], "PATCH_CREATED")
        self.assertTrue(os.path.exists(res["patch_file"]))
        self.assertIn("--- a/", Path(res["patch_file"]).read_text(encoding="utf-8"))

    def test_13_agents_orchestrator(self):
        """Test AgentsOrchestrator persona configuration."""
        from agents.agents_orchestrator import AgentsOrchestrator
        orch = AgentsOrchestrator()
        self.assertEqual(len(orch.persona_configs), 4)
        self.assertIn("emulator-5554", orch.persona_configs)
        self.assertIn("emulator-5556", orch.persona_configs)
        self.assertIn("emulator-5558", orch.persona_configs)
        self.assertIn("emulator-5560", orch.persona_configs)


if __name__ == "__main__":
    unittest.main()
