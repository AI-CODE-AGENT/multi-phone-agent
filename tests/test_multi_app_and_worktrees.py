"""
Comprehensive Unit & Integration Tests for AMAF 4.0 Multi-App Automation & 16-Subagent Worktrees:
- MultiAppAutomationManager (Packages, Permissions, State Snapshots, Deep Links, Declarative Flows)
- CrossAppNotetakerSubagent (#13) (OTP, Order ID, Deep Link, Price & Notification Bridging)
- ActionReflectorSubagent (#14) (UI Structural Hash, Permission/ANR Detection, Transition Reflection)
- MultiAppCrawlerSubagent (#15) (DroidBot/Fastbot UI State-Graph Exploration)
- WorktreeCoordinatorSubagent (#16) (Git Worktree Topology Audit)
- SelfEvolutionEngine (16 Subagents Closed-Loop)
- AndroidFarmMCPServer (All 24 Tools)
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.adb_wrapper import ADBWrapper
from core.real_device_manager import RealDeviceManager
from core.group_control_broadcaster import GroupControlBroadcaster
from core.multi_app_manager import MultiAppAutomationManager
from core.memory_manager import MemoryManager
from agents.cross_app_notetaker_subagent import CrossAppNotetakerSubagent
from agents.action_reflector_subagent import ActionReflectorSubagent
from agents.multi_app_crawler_subagent import MultiAppCrawlerSubagent
from agents.worktree_coordinator_subagent import WorktreeCoordinatorSubagent
from agents.self_evolution_engine import SelfEvolutionEngine
from mcp_bridge.android_farm_mcp_server import AndroidFarmMCPServer


SAMPLE_XML_SCREEN_1 = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="Order #ORD-99281A Confirmed" resource-id="com.shop.app:id/order_title" class="android.widget.TextView" package="com.shop.app" content-desc="" clickable="false" enabled="true" bounds="[40,120][680,200]" />
  <node index="1" text="Your verification code is 482910" resource-id="com.shop.app:id/otp_msg" class="android.widget.TextView" package="com.shop.app" content-desc="" clickable="false" enabled="true" bounds="[40,220][680,300]" />
  <node index="2" text="Total: $149.99" resource-id="com.shop.app:id/price" class="android.widget.TextView" package="com.shop.app" content-desc="" clickable="false" enabled="true" bounds="[40,320][680,400]" />
  <node index="3" text="Pay Now https://pay.example.com/checkout/99281" resource-id="com.shop.app:id/pay_btn" class="android.widget.Button" package="com.shop.app" content-desc="Pay Button" clickable="true" enabled="true" bounds="[100,500][620,620]" />
</hierarchy>
"""

SAMPLE_XML_SCREEN_2 = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="Payment Completed" resource-id="com.wallet.app:id/done_title" class="android.widget.TextView" package="com.wallet.app" content-desc="" clickable="false" enabled="true" bounds="[40,120][680,200]" />
  <node index="1" text="Receipt Details" resource-id="com.wallet.app:id/receipt_btn" class="android.widget.Button" package="com.wallet.app" content-desc="Receipt" clickable="true" enabled="true" bounds="[100,400][620,520]" />
</hierarchy>
"""

SAMPLE_XML_PERMISSION_DIALOG = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="Allow ShopApp to send you notifications?" resource-id="com.android.permissioncontroller:id/permission_message" class="android.widget.TextView" package="com.android.permissioncontroller" clickable="false" bounds="[60,600][660,700]" />
  <node index="1" text="Allow" resource-id="com.android.permissioncontroller:id/permission_allow_button" class="android.widget.Button" package="com.android.permissioncontroller" clickable="true" bounds="[100,750][620,830]" />
</hierarchy>
"""


class FakeMultiAppADB(ADBWrapper):
    """Fake ADB for Multi-App testing across virtual AVD + physical phone."""

    def __init__(self):
        super().__init__()
        self.xml_queue = [SAMPLE_XML_SCREEN_1, SAMPLE_XML_SCREEN_2]
        self.current_xml = SAMPLE_XML_SCREEN_1

    def get_connected_devices(self):
        return [
            {"serial": "emulator-5554", "status": "device", "model": "sdk_gphone64_x86_64"},
            {"serial": "10CF5L0TYL00312", "status": "device", "model": "Pixel_8_Pro"},
        ]

    def dump_ui_hierarchy(self, serial: str) -> str:
        if self.xml_queue:
            self.current_xml = self.xml_queue.pop(0)
            self.xml_queue.append(self.current_xml)
        return self.current_xml

    def shell(self, serial: str, command: str, timeout: int = 30) -> str:
        if command.startswith("pm list packages"):
            return "package:com.shop.app\npackage:com.wallet.app\npackage:com.android.settings\n"
        if "resolve-activity" in command:
            return "priority=0 preferredOrder=0 match=0x108000\ncom.shop.app/.MainActivity"
        if command.startswith("pm clear"):
            return "Success"
        if "am start -W" in command:
            return "Status: ok\nLaunchState: COLD\nActivity: com.shop.app/.CheckoutActivity\nTotalTime: 185\nWaitTime: 192\nComplete"
        if "dumpsys notification" in command:
            return (
                "  NotificationRecord(0x123: pkg=com.shop.app)\n"
                "    extras={\n"
                "      android.title=String (ShopApp OTP)\n"
                "      android.text=String (Your OTP code is 839201)\n"
                "    }\n"
            )
        if "cmd clipboard get-text" in command:
            return "Copied OTP 839201 from https://shop.example.com/verify"
        if "wm size" in command:
            return "Physical size: 1080x2400" if serial == "10CF5L0TYL00312" else "Physical size: 720x1600"
        if "dumpsys window" in command or "dumpsys activity" in command:
            return "mCurrentFocus=Window{123 u0 com.shop.app/com.shop.app.MainActivity}"
        if "dumpsys package" in command:
            return "versionName=4.2.0\nversionCode=42"
        if "dumpsys battery" in command:
            return "  USB powered: true\n  level: 90\n  temperature: 330\n  voltage: 4150"
        return "OK"

    def tap(self, serial: str, x: int, y: int):
        return True

    def input_text(self, serial: str, text: str):
        return True


class TestAMAFv4MultiAppAndWorktrees(unittest.TestCase):
    def setUp(self):
        self.fake_adb = FakeMultiAppADB()
        self.real_mgr = RealDeviceManager(self.fake_adb)
        self.real_mgr.set_farm_mode("HYBRID")
        self.broadcaster = GroupControlBroadcaster(self.fake_adb, self.real_mgr)
        self.multi_app = MultiAppAutomationManager(self.fake_adb, self.real_mgr, self.broadcaster)
        self.memory = MemoryManager()

    def test_01_multi_app_manager_packages_permissions_state_and_deeplinks(self):
        apps = self.multi_app.list_installed_apps("10CF5L0TYL00312")
        self.assertEqual(apps["apps_count"], 3)
        self.assertIn("com.shop.app", apps["packages"])

        act = self.multi_app.resolve_launcher_activity("10CF5L0TYL00312", "com.shop.app")
        self.assertEqual(act, "com.shop.app/.MainActivity")

        perms = self.multi_app.grant_all_runtime_permissions("10CF5L0TYL00312", "com.shop.app")
        self.assertEqual(perms["status"], "PERMISSIONS_GRANTED")
        self.assertGreaterEqual(perms["granted_count"], 5)

        clr = self.multi_app.clear_app_data("10CF5L0TYL00312", "com.shop.app")
        self.assertTrue(clr["success"])

        snap = self.multi_app.snapshot_app_state("10CF5L0TYL00312", "com.shop.app", label="pre_checkout")
        self.assertEqual(snap["status"], "SNAPSHOT_SAVED")

        rest = self.multi_app.restore_app_state("10CF5L0TYL00312", "com.shop.app", label="pre_checkout")
        self.assertEqual(rest["status"], "STATE_RESTORED")

        dl = self.multi_app.open_deep_link("10CF5L0TYL00312", "https://pay.example.com/checkout/99281", "com.shop.app")
        self.assertEqual(dl["status"], "DEEPLINK_OPENED")
        self.assertEqual(dl["launch_time_ms"], 185)

        notifs = self.multi_app.get_active_notifications("10CF5L0TYL00312")
        self.assertGreaterEqual(notifs["notifications_count"], 1)

    def test_02_declarative_multi_app_flow_execution(self):
        flow_res = self.multi_app.run_declarative_multi_app_flow(
            flow_steps=[
                {"action": "launchApp", "package": "com.shop.app", "clearState": True, "grantPermissions": True},
                {"action": "injectMockOtp", "phone": "0941189263", "service": "ShopCheckout"},
                {"action": "extractNote", "key": "order_ref", "value": "ORD-99281A"},
                {"action": "openLink", "uri": "https://pay.example.com/checkout/99281", "package": "com.wallet.app"},
                {"action": "inputText", "text": "$NOTE:last_otp"},
                {"action": "tapOn", "x": 0.5, "y": 0.5},
                {"action": "assertVisible", "text": "Payment"},
                {"action": "switchApp", "package": "com.shop.app"}
            ],
            serials=["emulator-5554", "10CF5L0TYL00312"]
        )
        self.assertEqual(flow_res["status"], "FLOW_COMPLETED")
        self.assertEqual(flow_res["steps_executed"], 8)
        self.assertIn("last_otp", flow_res["shared_notes"])
        self.assertEqual(flow_res["shared_notes"]["order_ref"], "ORD-99281A")

    def test_03_cross_app_notetaker_subagent_13(self):
        notetaker = CrossAppNotetakerSubagent(self.fake_adb, self.memory)
        self.fake_adb.xml_queue = [SAMPLE_XML_SCREEN_1]
        screen_res = notetaker.extract_notes_from_screen("10CF5L0TYL00312", source_app="com.shop.app")
        self.assertGreaterEqual(screen_res["extracted_count"], 3)
        self.assertEqual(notetaker.get_note("otp_code"), "482910")
        self.assertIn("ORD-99281A", notetaker.get_note("order_id"))

        resolved = notetaker.resolve_template("Verify order $NOTE:order_id with OTP ${NOTE:otp_code}")
        self.assertIn("482910", resolved)
        self.assertIn("ORD-99281A", resolved)

        clip_res = notetaker.extract_from_notifications_and_clipboard("10CF5L0TYL00312")
        self.assertEqual(notetaker.get_note("otp_code"), "839201")
        self.assertTrue(len(clip_res) > 0)

    def test_04_action_reflector_subagent_14(self):
        reflector = ActionReflectorSubagent(self.fake_adb, self.memory)
        sig1 = reflector.compute_ui_signature(SAMPLE_XML_SCREEN_1, foreground_app="com.shop.app")
        sig2 = reflector.compute_ui_signature(SAMPLE_XML_SCREEN_2, foreground_app="com.shop.app")
        sig_perm = reflector.compute_ui_signature(SAMPLE_XML_PERMISSION_DIALOG, foreground_app="com.android.permissioncontroller")

        # 1. Progress verified when UI hash changes
        r_prog = reflector.reflect_on_action("10CF5L0TYL00312", {"action": "tap"}, sig1, sig2, expected_package="com.shop.app")
        self.assertEqual(r_prog["outcome"], "PROGRESS_VERIFIED")

        # 2. Stuck when UI hash identical after tap
        r_stuck = reflector.reflect_on_action("10CF5L0TYL00312", {"action": "tap"}, sig1, sig1, expected_package="com.shop.app")
        self.assertEqual(r_stuck["outcome"], "NO_CHANGE_STUCK")

        # 3. Permission dialog blocked
        r_perm = reflector.reflect_on_action("10CF5L0TYL00312", {"action": "tap"}, sig1, sig_perm, expected_package="com.shop.app")
        self.assertEqual(r_perm["outcome"], "PERMISSION_DIALOG_BLOCKED")

    def test_05_multi_app_crawler_subagent_15(self):
        crawler = MultiAppCrawlerSubagent(self.fake_adb, self.memory)
        nodes = crawler.extract_interactive_nodes(SAMPLE_XML_SCREEN_1)
        self.assertGreaterEqual(len(nodes), 1)

        crawl_res = crawler.crawl_application("10CF5L0TYL00312", "com.shop.app", max_steps=2, run_monkey_burst=True)
        self.assertEqual(crawl_res["status"], "CRAWL_COMPLETED")
        self.assertGreaterEqual(crawl_res["unique_states_discovered"], 1)

        multi_res = crawler.crawl_multiple_apps("10CF5L0TYL00312", ["com.shop.app", "com.wallet.app"], steps_per_app=2)
        self.assertEqual(len(multi_res["apps_crawled"]), 2)

    def test_06_worktree_coordinator_subagent_16_and_16_subagent_evolution(self):
        coord = WorktreeCoordinatorSubagent(memory=self.memory)
        audit = coord.audit_worktree_topology()
        self.assertEqual(audit["status"], "WORKTREE_TOPOLOGY_AUDITED")
        self.assertGreaterEqual(audit["total_worktrees"], 1)

        engine = SelfEvolutionEngine(self.fake_adb, self.memory)
        evo_res = engine.run_evolution_loop(iterations=1, package_name="com.shop.app")
        self.assertEqual(evo_res["status"], "EVOLUTION_COMPLETED")
        self.assertEqual(evo_res["subagents_count"], 16)

    def test_07_mcp_server_all_24_tools(self):
        mcp = AndroidFarmMCPServer()
        mcp.adb = self.fake_adb
        mcp.real_mgr = self.real_mgr
        mcp.broadcaster = self.broadcaster
        mcp.multi_app_mgr = self.multi_app
        mcp.crawler = MultiAppCrawlerSubagent(self.fake_adb, self.memory)

        self.assertEqual(len(mcp.tools), 24)

        r_apps = mcp.handle_tool_call("android_list_installed_apps", {"serial": "10CF5L0TYL00312"})
        self.assertTrue(r_apps["success"])
        self.assertIn("com.shop.app", r_apps["packages"])

        r_state = mcp.handle_tool_call("android_app_state_control", {
            "action": "grant_permissions",
            "serial": "10CF5L0TYL00312",
            "package_name": "com.shop.app"
        })
        self.assertTrue(r_state["success"])

        r_dl = mcp.handle_tool_call("android_open_deep_link", {
            "serial": "10CF5L0TYL00312",
            "uri": "https://pay.example.com/checkout/99281"
        })
        self.assertTrue(r_dl["success"])

        r_flow = mcp.handle_tool_call("android_run_multi_app_flow", {
            "steps": [{"action": "launchApp", "package": "com.shop.app"}],
            "serials": ["10CF5L0TYL00312"]
        })
        self.assertTrue(r_flow["success"])

        r_crawl = mcp.handle_tool_call("android_crawl_app_graph", {
            "serial": "10CF5L0TYL00312",
            "package_name": "com.shop.app",
            "max_steps": 2
        })
        self.assertTrue(r_crawl["success"])


if __name__ == "__main__":
    unittest.main()
