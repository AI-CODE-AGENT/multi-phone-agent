"""
Real Device Scout Subagent (Subagent #10)
Specializes in physical Android phone discovery, Wireless ADB over TCP/IP provisioning,
battery & thermal safety auditing, and zero-lag preparation of real phones before test execution.
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.real_device_manager import RealDeviceManager
from core.memory_manager import MemoryManager


class RealDeviceScoutSubagent:
    """Autonomous Scout & Health Guardian for Physical Android Phones."""

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        real_mgr: Optional[RealDeviceManager] = None,
        memory: Optional[MemoryManager] = None
    ):
        self.adb = adb or ADBWrapper()
        self.real_mgr = real_mgr or RealDeviceManager(self.adb)
        self.memory = memory or MemoryManager()

    def scout_and_prepare_fleet(self, auto_wireless: bool = True) -> Dict[str, Any]:
        """
        Scan for all physical phones, reconnect known wireless endpoints,
        apply thermal/battery guards, and record hardware profiles into memory.
        """
        start = time.time()
        reconnected = []
        if auto_wireless:
            reconnected = self.real_mgr.auto_reconnect_known_wireless()

        real_devices = self.real_mgr.discover_real_devices(include_unauthorized=True)
        prepared_devices = []
        overheated_warnings = []

        for dev in real_devices:
            serial = dev["serial"]
            if dev.get("status") == "device":
                guard_res = self.real_mgr.apply_real_phone_health_guard(serial)
                dev["health_guard"] = guard_res
                if dev.get("battery", {}).get("overheated"):
                    overheated_warnings.append(serial)
                self.memory.remember(
                    key=f"real_device_{serial}",
                    value={
                        "name": dev["name"],
                        "resolution": dev["resolution"],
                        "android_version": dev["android_version"],
                        "battery": dev["battery"]
                    },
                    tags=["real_device", "hardware_profile"],
                    category="fleet_topology"
                )
            prepared_devices.append(dev)

        return {
            "status": "SCOUT_COMPLETED",
            "duration_seconds": round(time.time() - start, 2),
            "farm_mode": self.real_mgr.get_farm_mode(),
            "real_devices_found": len(prepared_devices),
            "overheated_devices": overheated_warnings,
            "wireless_reconnections": reconnected,
            "devices": prepared_devices
        }


if __name__ == "__main__":
    scout = RealDeviceScoutSubagent()
    print(scout.scout_and_prepare_fleet())
