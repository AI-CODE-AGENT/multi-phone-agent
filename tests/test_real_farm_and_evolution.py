"""
Comprehensive Unit & Integration Tests for AMAF 3.0:
- Optional Real Phone Farm Management (USB & Wireless TCP/IP, Battery & Thermal Guard, Farm Modes)
- Group Control Synchronized Broadcaster (Normalized Cross-Resolution Coordinate Scaling)
- 12-Subagent Ecosystem (RealDeviceScout, GroupSync, ExperienceMiner)
- Self-Evolution Engine Loop (Ideation -> Plan -> Sync -> Execute -> Patch -> Evolve)
- MCP Server 2.0 (All 18 Tools)
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.adb_wrapper import ADBWrapper
from core.real_device_manager import RealDeviceManager
from core.group_control_broadcaster import GroupControlBroadcaster
from core.hardware_simulator import HardwareSimulator
from core.memory_manager import MemoryManager
from agents.real_device_scout_subagent import RealDeviceScoutSubagent
from agents.group_sync_subagent import GroupSyncSubagent
from agents.experience_miner_subagent import ExperienceMinerSubagent
from agents.self_evolution_engine import SelfEvolutionEngine
from mcp_bridge.android_farm_mcp_server import AndroidFarmMCPServer


class FakeHybridADB(ADBWrapper):
    """Fake ADB simulating 2 Emulators (720x1600) + 2 Real Phones (Samsung 1080x2400 USB & Xiaomi 1440x3200 Wi-Fi)."""

    def __init__(self):
        super().__init__()
        self.taps = []
        self.swipes = []
        self.shells = []

    def get_connected_devices(self):
        return [
            {"serial": "emulator-5554", "status": "device", "model": "sdk_gphone64_x86_64"},
            {"serial": "emulator-5556", "status": "device", "model": "sdk_gphone64_x86_64"},
            {"serial": "R58M99AABB", "status": "device", "model": "SM_S928B"},
            {"serial": "192.168.1.88:5555", "status": "device", "model": "23116PN5BC"},
        ]

    def shell(self, serial: str, command: str, timeout: int = 30) -> str:
        self.shells.append((serial, command))
        if "wm size" in command:
            if serial == "R58M99AABB":
                return "Physical size: 1080x2400"
            elif serial == "192.168.1.88:5555":
                return "Physical size: 1440x3200"
            return "Physical size: 720x1600"
        if "dumpsys battery" in command and not command.startswith("dumpsys battery "):
            if serial == "R58M99AABB":
                return "  AC powered: false\n  USB powered: true\n  level: 86\n  temperature: 365\n  voltage: 4180"
            elif serial == "192.168.1.88:5555":
                return "  AC powered: true\n  USB powered: false\n  level: 92\n  temperature: 435\n  voltage: 4300"
            return "  USB powered: true\n  level: 100\n  temperature: 250\n  voltage: 4200"
        if "ro.product.manufacturer" in command:
            return "Samsung" if serial == "R58M99AABB" else "Xiaomi"
        if "ro.product.model" in command:
            return "Galaxy S24 Ultra" if serial == "R58M99AABB" else "Xiaomi 14 Pro"
        if "ro.build.version.release" in command:
            return "15"
        if "ro.build.version.sdk" in command:
            return "35"
        if "ip -f inet addr show wlan0" in command:
            return "    inet 192.168.1.77/24 brd 192.168.1.255 scope global wlan0"
        return "OK"

    def run_command(self, args, timeout=30):
        if args and args[0] == "connect":
            return 0, f"connected to {args[1]}", ""
        if args and args[0] == "disconnect":
            return 0, f"disconnected {args[1]}", ""
        return 0, "OK", ""

    def run_device_cmd(self, serial, args, timeout=30):
        return 0, "OK", ""

    def tap(self, serial: str, x: int, y: int):
        self.taps.append((serial, x, y))

    def swipe(self, serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300):
        self.swipes.append((serial, x1, y1, x2, y2, duration_ms))


class TestAMAFv3RealFarmAndEvolution(unittest.TestCase):
    def setUp(self):
        self.fake_adb = FakeHybridADB()
        self.real_mgr = RealDeviceManager(self.fake_adb)
        self.real_mgr.set_farm_mode("HYBRID")
        self.broadcaster = GroupControlBroadcaster(self.fake_adb, self.real_mgr)
        self.memory = MemoryManager()

    def test_01_real_device_discovery_and_battery_thermal_guard(self):
        real_devs = self.real_mgr.discover_real_devices()
        self.assertEqual(len(real_devs), 2)

        s24 = next(d for d in real_devs if d["serial"] == "R58M99AABB")
        self.assertEqual(s24["connection_type"], "usb_cable")
        self.assertEqual(s24["resolution"], "1080x2400")
        self.assertEqual(s24["battery"]["level"], 86)
        self.assertAlmostEqual(s24["battery"]["temperature_c"], 36.5)
        self.assertFalse(s24["battery"]["overheated"])

        xiaomi = next(d for d in real_devs if d["serial"] == "192.168.1.88:5555")
        self.assertEqual(xiaomi["connection_type"], "wireless_tcp")
        self.assertEqual(xiaomi["resolution"], "1440x3200")
        self.assertAlmostEqual(xiaomi["battery"]["temperature_c"], 43.5)
        self.assertTrue(xiaomi["battery"]["overheated"])

        # Apply thermal guard to overheated Xiaomi -> should trigger cooling unplug
        guard = self.real_mgr.apply_real_phone_health_guard("192.168.1.88:5555")
        self.assertIn("cooling_unplug", guard["thermal_action"])

    def test_02_optional_farm_modes_switching(self):
        # 1. AVD_ONLY mode disables real phone discovery
        self.real_mgr.set_farm_mode("AVD_ONLY")
        self.assertEqual(len(self.real_mgr.discover_real_devices()), 0)

        # 2. REAL_ONLY mode returns only physical phones in active pool
        self.real_mgr.set_farm_mode("REAL_ONLY")
        active_real = self.real_mgr.get_all_active_farm_devices()
        self.assertTrue(all(d["is_real_device"] for d in active_real))
        self.assertEqual(len(active_real), 2)

        # 3. Restore HYBRID mode
        self.real_mgr.set_farm_mode("HYBRID")
        active_hybrid = self.real_mgr.get_all_active_farm_devices()
        self.assertEqual(len(active_hybrid), 6)  # 4 AVD slots + 2 connected Real Phones

    def test_03_wireless_adb_provisioning(self):
        ok, msg = self.real_mgr.enable_wireless_adb("R58M99AABB", 5555)
        self.assertTrue(ok)
        self.assertIn("192.168.1.77:5555", msg)

    def test_04_real_device_zero_cost_otp_and_hardware_fallback(self):
        hw = HardwareSimulator(self.fake_adb)
        ok_otp, msg_otp = hw.send_sms_otp("R58M99AABB", "0941189263", "Ma OTP: 654321")
        self.assertTrue(ok_otp)
        self.assertIn("RealPhone 0-VND OTP broadcast", msg_otp)

        ok_fp, msg_fp = hw.touch_fingerprint("R58M99AABB")
        self.assertTrue(ok_fp)
        self.assertIn("Real device biometric", msg_fp)

        ok_gps, msg_gps = hw.set_gps_location("R58M99AABB", 10.7951, 106.7219)
        self.assertTrue(ok_gps)
        self.assertIn("RealPhone GPS Broadcast", msg_gps)

    def test_05_group_control_normalized_resolution_scaling(self):
        # Broadcast center tap (0.5, 0.5) across 720x1600 AVD, 1080x2400 Samsung, and 1440x3200 Xiaomi
        res = self.broadcaster.broadcast_tap(0.5, 0.5, group_filter="ALL", is_normalized=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["targets_count"], 4)
        self.assertEqual(res["results"]["emulator-5554"]["scaled_coords"], [360, 800])
        self.assertEqual(res["results"]["R58M99AABB"]["scaled_coords"], [540, 1200])
        self.assertEqual(res["results"]["192.168.1.88:5555"]["scaled_coords"], [720, 1600])

    def test_06_experience_miner_and_group_sync_subagents(self):
        miner = ExperienceMinerSubagent(self.memory)
        goal = "Verify OTP login flow on hybrid farm"
        plan = [{"action": "tap", "milestone": "Confirm OTP"}]
        traj = [{"status": "healed_success", "detail": "Recovered: fuzzy match at (360, 800)"}]
        mined = miner.mine_trajectory(goal, "com.android.settings", plan, traj, 1.25, (720, 1600))
        self.assertEqual(mined["status"], "MACRO_MINED")

        cached = miner.lookup_macro_for_goal(goal, "com.android.settings")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["steps"][0]["normalized_coords"], [0.5, 0.5])

        sync_sub = GroupSyncSubagent(self.fake_adb, self.broadcaster, self.memory)
        sync_res = sync_sub.run_synchronized_macro(
            steps=[{"action": "tap", "x": 0.5, "y": 0.5, "normalized": True}],
            group_filter="REAL_ONLY"
        )
        self.assertEqual(sync_res["status"], "SYNC_COMPLETED")
        self.assertEqual(sync_res["targets_count"], 2)

    def test_07_self_evolution_engine_12_subagents_loop(self):
        engine = SelfEvolutionEngine(self.fake_adb, self.memory)
        res = engine.run_evolution_loop(iterations=1, package_name="com.android.settings")
        self.assertEqual(res["status"], "EVOLUTION_COMPLETED")
        self.assertEqual(res["cycles_executed"], 1)
        self.assertTrue(Path(res["report_path"]).exists())

    def test_08_mcp_server_v2_all_18_tools(self):
        mcp = AndroidFarmMCPServer()
        mcp.adb = self.fake_adb
        mcp.real_mgr = self.real_mgr
        mcp.broadcaster = self.broadcaster
        mcp.bridge.adb = self.fake_adb
        mcp.bridge.real_mgr = self.real_mgr

        self.assertGreaterEqual(len(mcp.tools), 18)

        r_disc = mcp.handle_tool_call("android_discover_real_devices", {"set_farm_mode": "HYBRID"})
        self.assertTrue(r_disc["success"])
        self.assertEqual(r_disc["real_devices_count"], 2)

        r_bcast = mcp.handle_tool_call("android_group_broadcast", {
            "action": "tap",
            "group_filter": "REAL_ONLY",
            "x": 0.5,
            "y": 0.5
        })
        self.assertTrue(r_bcast["success"])
        self.assertEqual(r_bcast["targets_count"], 2)

        r_macros = mcp.handle_tool_call("android_mine_experience_macros", {})
        self.assertTrue(r_macros["success"])


if __name__ == "__main__":
    unittest.main()
