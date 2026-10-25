"""
Unit & Integration Test Suite v2 for Android Multi-Agent Farm
Tests KanbanBoard, VisionPerception, SecurityAuditor, RegressionVerifier, and PipelineDirector.
"""

import os
import sys
import unittest
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.kanban_board import KanbanBoard, VALID_STATES
from core.memory_manager import MemoryManager
from agents.vision_perception_subagent import VisionPerceptionSubagent
from agents.security_auditor_subagent import SecurityAuditorSubagent
from agents.regression_verifier_subagent import RegressionVerifierSubagent
from agents.code_improver_subagent import CodeImproverSubagent


class TestAndroidFarmV2(unittest.TestCase):

    def test_01_kanban_board_lifecycle(self):
        """Test Kanban card creation, transitions, and summary counts."""
        kb = KanbanBoard()
        card = kb.create_card("Test Auth Flow", "Verify Mock OTP for 0941189263")
        card_id = card["card_id"]
        self.assertEqual(card["state"], "BACKLOG")

        # Transition through states
        self.assertTrue(kb.transition_state(card_id, "PLANNING", actor="Planner"))
        self.assertTrue(kb.transition_state(card_id, "DEV_IN_PROGRESS", actor="Operator"))
        self.assertTrue(kb.transition_state(card_id, "HEALING", actor="Healer"))
        
        # Verify healing incremented retries
        updated = kb.get_card(card_id)
        self.assertEqual(updated["retries"], 1)

        self.assertTrue(kb.transition_state(card_id, "PATCHED", actor="CodeImprover"))
        self.assertTrue(kb.transition_state(card_id, "REGRESSION_PASSED", actor="RegressionVerifier"))
        self.assertTrue(kb.transition_state(card_id, "DONE", actor="Director"))

        # Verify invalid state is rejected
        self.assertFalse(kb.transition_state(card_id, "NON_EXISTENT_STATE"))

        # Attach artifact
        kb.add_artifact(card_id, "test_report", "reports/test.md")
        card_with_art = kb.get_card(card_id)
        self.assertIn("test_report", card_with_art.get("artifacts", {}))

    def test_02_vision_perception_anchors(self):
        """Test spatial grounding and coordinate resolution."""
        vision = VisionPerceptionSubagent()
        top_menu = vision.resolve_visual_coordinates("emulator-5554", "top_right_menu")
        self.assertIsNotNone(top_menu)
        self.assertGreater(top_menu[0], 500)  # Near right edge of 720 width

        fab = vision.resolve_visual_coordinates("emulator-5554", "fab_action_button")
        self.assertIsNotNone(fab)
        self.assertGreater(fab[1], 1200)  # Near bottom edge of 1600 height

        confirm = vision.resolve_visual_coordinates("emulator-5554", "center_confirm")
        self.assertIsNotNone(confirm)

    def test_03_security_auditor_rules(self):
        """Test OWASP security auditor initialization and vulnerability structure."""
        sec = SecurityAuditorSubagent()
        self.assertIsNotNone(sec)
        # Test simulated parsing with dummy package
        res = sec.audit_package_security("emulator-5554", "com.nonexistent.fakeapp")
        self.assertIn("status", res)

    def test_04_regression_verifier_patch_syntax(self):
        """Test patch validation logic with valid and invalid patches."""
        reg = RegressionVerifierSubagent()
        temp_patch = Path("tests/temp_valid.patch")
        temp_patch.parent.mkdir(parents=True, exist_ok=True)

        # Valid unified diff
        temp_patch.write_text(
            "--- a/file.kt\n+++ b/file.kt\n@@ -1,2 +1,3 @@\n+newLine\n",
            encoding="utf-8"
        )
        is_valid, msg = reg.validate_patch_syntax(temp_patch)
        self.assertTrue(is_valid)

        # Invalid patch
        temp_patch.write_text("Just some text without diff markers", encoding="utf-8")
        is_invalid, msg2 = reg.validate_patch_syntax(temp_patch)
        self.assertFalse(is_invalid)

        if temp_patch.exists():
            temp_patch.unlink()

    def test_05_code_improver_and_regression_integration(self):
        """Test end-to-end patch generation followed by regression verification."""
        improver = CodeImproverSubagent()
        verifier = RegressionVerifierSubagent()

        defect = {
            "defect_id": "DEFECT_INTEGRATION_01",
            "defect_type": "TimeoutException",
            "title": "Network timeout in ApiClient.kt"
        }
        patch_info = improver.analyze_defect_and_propose_patch(defect)
        self.assertEqual(patch_info["status"], "PATCH_CREATED")

        patch_file = Path(patch_info["patch_file"])
        self.assertTrue(patch_file.exists())

        # Validate syntax
        valid, _ = verifier.validate_patch_syntax(patch_file)
        self.assertTrue(valid)


if __name__ == "__main__":
    unittest.main()
