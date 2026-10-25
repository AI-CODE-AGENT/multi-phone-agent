"""
ARTEMIS & External Agent Bridge
Provides compatibility bindings between Android Farm and ARTEMIS / Cursor / Kilo Code / OpenCode.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.farm_config import DEFAULT_FARM_DEVICES
from core.adb_wrapper import ADBWrapper
from core.hardware_simulator import HardwareSimulator
from core.real_device_manager import RealDeviceManager
from agents.device_lock_manager import DeviceLockManager


class ArtemisBridge:
    """Bridge for integrating Android Multi-Agent Farm with ARTEMIS MCP Server."""

    def __init__(self):
        self.adb = ADBWrapper()
        self.hardware = HardwareSimulator(self.adb)
        self.real_mgr = RealDeviceManager(self.adb)
        self.lock_mgr = DeviceLockManager()

    def get_available_devices_for_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        List connected devices (both Virtual AVDs and Physical Real Phones)
        that are free to be leased by an agent.
        """
        connected = {d["serial"]: d["status"] for d in self.adb.get_connected_devices() if d["status"] == "device"}
        active_locks = self.lock_mgr.list_active_locks()
        available = []

        # 1. Standard 4 Farm Emulators
        for dev in DEFAULT_FARM_DEVICES:
            serial = dev["serial"]
            if serial in connected:
                lock = active_locks.get(serial)
                is_free = lock is None or lock.get("agent_id") == agent_id
                available.append({
                    "serial": serial,
                    "name": dev["name"],
                    "port": dev["port"],
                    "is_real_device": False,
                    "connection_type": "emulator",
                    "description": dev["description"],
                    "is_free": is_free,
                    "locked_by": lock.get("agent_id") if lock else None,
                    "task": lock.get("task_name") if lock else None
                })

        # 2. Optional Real Physical Phones (USB or Wireless TCP/IP)
        mode_info = self.real_mgr.get_farm_mode()
        if mode_info.get("real_phone_farm_enabled", True) and mode_info.get("farm_mode") in ("HYBRID", "REAL_ONLY"):
            for rdev in self.real_mgr.discover_real_devices(include_unauthorized=False):
                serial = rdev["serial"]
                lock = active_locks.get(serial)
                is_free = lock is None or lock.get("agent_id") == agent_id
                available.append({
                    "serial": serial,
                    "name": rdev["name"],
                    "port": int(serial.split(":")[1]) if ":" in serial else 0,
                    "is_real_device": True,
                    "connection_type": rdev["connection_type"],
                    "resolution": rdev["resolution"],
                    "battery": rdev["battery"],
                    "description": rdev["description"],
                    "is_free": is_free,
                    "locked_by": lock.get("agent_id") if lock else None,
                    "task": lock.get("task_name") if lock else None
                })
        return available

    def lease_device(self, serial: str, agent_id: str, task_name: str, lease_seconds: int = 300) -> bool:
        """Lease a device for ARTEMIS task execution."""
        return self.lock_mgr.acquire(serial, agent_id, task_name, lease_seconds)

    def release_device(self, serial: str, agent_id: str) -> bool:
        """Release leased device."""
        return self.lock_mgr.release(serial, agent_id)

    def trigger_biometric(self, serial: str) -> bool:
        """Helper for agent to satisfy BiometricPrompt during testing."""
        ok, _ = self.hardware.touch_fingerprint(serial)
        return ok

    def deliver_otp(self, serial: str, otp_code: str, sender: str = "+84901234567") -> bool:
        """Helper for agent to deliver OTP SMS directly to target device."""
        ok, _ = self.hardware.send_sms_otp(serial, sender, f"Ma OTP xac thuc: {otp_code}")
        return ok

    def spoof_location(self, serial: str, lat: float, lng: float) -> bool:
        """Helper for agent to spoof GPS coordinates."""
        ok, _ = self.hardware.set_gps_location(serial, lat, lng)
        return ok


if __name__ == "__main__":
    bridge = ArtemisBridge()
    print("Available devices for ARTEMIS:")
    for d in bridge.get_available_devices_for_agent("Artemis_Main"):
        print(f" - {d['name']} ({d['serial']}): {'FREE' if d['is_free'] else 'BUSY'}")
