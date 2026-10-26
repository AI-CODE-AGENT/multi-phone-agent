import unittest
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp_bridge.android_farm_mcp_server import AndroidFarmMCPServer


class TestAndroidFarmMCPServer(unittest.TestCase):
    def setUp(self):
        self.server = AndroidFarmMCPServer()

    def test_registered_tools(self):
        tools = self.server.tools
        self.assertGreaterEqual(len(tools), 10)
        tool_names = [t["name"] for t in tools]
        self.assertIn("android_list_devices", tool_names)
        self.assertIn("android_lease_device", tool_names)
        self.assertIn("android_release_device", tool_names)
        self.assertIn("android_get_screen_state", tool_names)
        self.assertIn("android_tap_element", tool_names)
        self.assertIn("android_input_text", tool_names)
        self.assertIn("android_press_key", tool_names)
        self.assertIn("android_mock_otp", tool_names)
        self.assertIn("android_touch_fingerprint", tool_names)
        self.assertIn("android_set_gps", tool_names)
        self.assertIn("android_run_kanban_task", tool_names)
        self.assertIn("android_oem_popup_guard", tool_names)
        self.assertIn("android_universal_install_apk", tool_names)

    def test_mock_otp_tool_flow(self):
        # 1. Generate OTP
        gen_res = self.server.handle_tool_call("android_mock_otp", {
            "action": "generate",
            "phone_number": "0941189263"
        })
        self.assertTrue(gen_res["success"])
        code = gen_res["otp_code"]
        self.assertEqual(len(code), 6)

        # 2. Verify Valid OTP
        verify_res = self.server.handle_tool_call("android_mock_otp", {
            "action": "verify",
            "phone_number": "0941189263",
            "code": code
        })
        self.assertTrue(verify_res["success"])
        self.assertTrue(verify_res["verified"])

        # 3. Verify Invalid OTP
        invalid_res = self.server.handle_tool_call("android_mock_otp", {
            "action": "verify",
            "phone_number": "0941189263",
            "code": "000000"
        })
        self.assertFalse(invalid_res["verified"])

    def test_device_leasing_flow(self):
        # Lease
        lease_res = self.server.handle_tool_call("android_lease_device", {
            "serial": "emulator-5554",
            "agent_id": "TestAgent_01",
            "task_name": "Unit Testing"
        })
        self.assertTrue(lease_res["success"])

        # Release
        rel_res = self.server.handle_tool_call("android_release_device", {
            "serial": "emulator-5554",
            "agent_id": "TestAgent_01"
        })
        self.assertTrue(rel_res["success"])


if __name__ == "__main__":
    unittest.main()
