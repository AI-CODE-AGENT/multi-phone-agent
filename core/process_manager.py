"""
Process Manager for Android Multi-Agent Farm
Starts, stops, monitors, and tracks headless Android emulator processes.
"""

import subprocess
import os
import sys
import time
import psutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.farm_config import (
    EMULATOR_PATH,
    HEADLESS_FLAGS,
    DEFAULT_FARM_DEVICES
)
from core.adb_wrapper import ADBWrapper
from core.real_device_manager import RealDeviceManager


class ProcessManager:
    def __init__(self, adb: Optional[ADBWrapper] = None, real_mgr: Optional[RealDeviceManager] = None):
        self.adb = adb or ADBWrapper()
        self.real_mgr = real_mgr or RealDeviceManager(self.adb)
        self.emulator_path = str(EMULATOR_PATH)
        self._running_pids: Dict[str, int] = {}  # serial -> PID

    def is_port_in_use(self, port: int) -> bool:
        """Check if an ADB or console port is currently listening."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def start_instance(
        self,
        avd_name: str,
        port: int,
        headless: bool = True,
        extra_flags: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        Start an Android Virtual Device in background.
        Default: Headless mode (-no-window -no-audio -no-boot-anim -gpu host).
        """
        serial = f"emulator-{port}"

        # Check if already running in ADB
        connected = [d["serial"] for d in self.adb.get_connected_devices()]
        if serial in connected:
            return True, f"Device {serial} ({avd_name}) is already running."

        cmd = [self.emulator_path, "-avd", avd_name, "-port", str(port)]
        if headless:
            cmd.extend(HEADLESS_FLAGS)

        # Quickboot from golden_ready snapshot if available
        snapshot_dir = Path("D:/Android_AVD") / f"{avd_name}.avd" / "snapshots" / "golden_ready"
        if snapshot_dir.exists() and (not extra_flags or "-snapshot" not in extra_flags):
            cmd.extend(["-snapshot", "golden_ready"])

        if extra_flags:
            cmd.extend(extra_flags)

        try:
            # Run detached without console window so it outlives calling CLI script
            if os.name == "nt":
                flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                flags = 0

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags
            )
            # Give a brief moment for launcher to spawn qemu-system-x86_64
            time.sleep(1.0)
            metrics = self.get_instance_metrics(serial)
            actual_pid = metrics.get("pid") or proc.pid
            self._running_pids[serial] = actual_pid
            return True, f"Started {avd_name} on {serial} (PID: {actual_pid})"
        except Exception as e:
            return False, f"Failed to start {avd_name}: {e}"

    def stop_instance(self, serial: str, timeout: int = 15) -> Tuple[bool, str]:
        """
        Gracefully stop an emulator instance via 'adb emu kill',
        falling back to killing its process if unresponsive.
        """
        # 1. Attempt clean shutdown via ADB console
        code, out, _ = self.adb.run_device_cmd(serial, ["emu", "kill"], timeout=5)

        # 2. Wait for process to exit or check PID
        start = time.time()
        while time.time() - start < timeout:
            connected = [d["serial"] for d in self.adb.get_connected_devices()]
            if serial not in connected:
                self._running_pids.pop(serial, None)
                return True, f"Device {serial} stopped gracefully."
            time.sleep(1.0)

        # 3. Fallback kill via PID
        pid = self._running_pids.get(serial)
        if pid and psutil.pid_exists(pid):
            try:
                p = psutil.Process(pid)
                p.kill()
                self._running_pids.pop(serial, None)
                return True, f"Device {serial} force-killed (PID: {pid})."
            except Exception as e:
                return False, f"Error killing PID {pid}: {e}"

        # 4. Fallback search qemu processes by port in cmdline
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = p.info.get('cmdline') or []
                if "qemu-system" in p.info.get('name', '').lower() and str(serial) in " ".join(cmdline):
                    p.kill()
                    return True, f"Killed qemu process for {serial} (PID: {p.pid})"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return True, f"Device {serial} shutdown complete."

    def start_farm(self, count: int = 4, headless: bool = True) -> List[Dict[str, Any]]:
        """Start N farm devices in background."""
        results = []
        for item in DEFAULT_FARM_DEVICES[:count]:
            success, msg = self.start_instance(item["name"], item["port"], headless=headless)
            results.append({
                "name": item["name"],
                "serial": item["serial"],
                "port": item["port"],
                "success": success,
                "message": msg
            })
        return results

    def stop_farm(self) -> List[Dict[str, Any]]:
        """Stop all running farm devices."""
        results = []
        for item in DEFAULT_FARM_DEVICES:
            serial = item["serial"]
            success, msg = self.stop_instance(serial)
            results.append({
                "name": item["name"],
                "serial": serial,
                "success": success,
                "message": msg
            })
        return results

    def _scan_and_cache_all_pids(self):
        """Single-pass process scan to populate running PIDs for all devices (with 8s cooldown)."""
        now = time.time()
        if (now - getattr(self, "_last_pid_scan_ts", 0.0)) < 8.0:
            return
        self._last_pid_scan_ts = now
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = p.info.get('name', '').lower()
                if "qemu-system" in name or "emulator" in name:
                    cmdline = " ".join(p.info.get('cmdline') or [])
                    for item in DEFAULT_FARM_DEVICES:
                        serial = item["serial"]
                        port_str = str(item["port"])
                        if (port_str in cmdline or serial in cmdline) and serial not in self._running_pids:
                            self._running_pids[serial] = p.pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def get_instance_metrics(self, serial: str) -> Dict[str, Any]:
        """Fetch memory and CPU usage of the emulator process with high-speed direct PID caching."""
        # 1. Fast path: check cached PID
        pid = self._running_pids.get(serial)
        if not pid or not psutil.pid_exists(pid):
            self._scan_and_cache_all_pids()
            pid = self._running_pids.get(serial)

        if pid and psutil.pid_exists(pid):
            try:
                p = psutil.Process(pid)
                mem = p.memory_info().rss / (1024 * 1024)
                return {
                    "pid": pid,
                    "ram_mb": round(mem, 1),
                    "cpu_pct": round(p.cpu_percent(interval=None), 1)
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self._running_pids.pop(serial, None)

        return {"pid": None, "ram_mb": 0.0, "cpu_pct": 0.0}

    def get_farm_state(self) -> List[Dict[str, Any]]:
        """Return comprehensive live status for all 4 farm devices with cached ADB lookup."""
        now = time.time()
        if not hasattr(self, "_last_adb_time") or (now - getattr(self, "_last_adb_time", 0)) > 3.0:
            self._cached_adb_devices = {d["serial"]: d["status"] for d in self.adb.get_connected_devices()}
            self._last_adb_time = now

        connected_devs = getattr(self, "_cached_adb_devices", {})
        results = []

        for item in DEFAULT_FARM_DEVICES:
            serial = item["serial"]
            name = item["name"]
            is_connected = serial in connected_devs
            adb_status = connected_devs.get(serial, "offline")
            boot_done = is_connected and adb_status == "device"
            metrics = self.get_instance_metrics(serial) if is_connected else {"pid": None, "ram_mb": 0.0, "cpu_pct": 0.0}

            results.append({
                "id": item["id"],
                "name": name,
                "port": item["port"],
                "serial": serial,
                "description": item["description"],
                "is_running": is_connected,
                "adb_status": adb_status,
                "boot_completed": boot_done,
                "pid": metrics.get("pid"),
                "ram_mb": metrics.get("ram_mb", 0.0),
                "cpu_pct": metrics.get("cpu_pct", 0.0)
            })

        return results

    def get_hybrid_farm_state(self) -> List[Dict[str, Any]]:
        """
        Return comprehensive live status for both the 4 Headless AVDs
        and any connected Physical Real Phones (when enabled).
        """
        mode_info = self.real_mgr.get_farm_mode()
        farm_mode = mode_info.get("farm_mode", "HYBRID")
        results: List[Dict[str, Any]] = []

        if farm_mode in ("HYBRID", "AVD_ONLY"):
            avd_states = self.get_farm_state()
            for st in avd_states:
                st["is_real_device"] = False
                st["connection_type"] = "emulator"
                results.append(st)

        if farm_mode in ("HYBRID", "REAL_ONLY") and mode_info.get("real_phone_farm_enabled", True):
            real_devs = self.real_mgr.discover_real_devices(include_unauthorized=True)
            for idx, rdev in enumerate(real_devs, start=len(results) + 1):
                rdev["id"] = idx
                rdev["port"] = int(rdev["serial"].split(":")[1]) if ":" in rdev["serial"] else 0
                rdev["pid"] = None
                rdev["ram_mb"] = 0.0
                rdev["cpu_pct"] = 0.0
                results.append(rdev)

        return results


if __name__ == "__main__":
    pm = ProcessManager()
    print("Farm Status:")
    for s in pm.get_farm_state():
        print(f" - {s['name']} ({s['serial']}): {'ONLINE' if s['is_running'] else 'OFFLINE'}")
