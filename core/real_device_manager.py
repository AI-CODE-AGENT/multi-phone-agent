"""
Real Device Manager for Android Multi-Agent Farm (AMAF 3.0)
Provides optional physical Android phone farm management:
- USB & Wireless ADB over TCP/IP auto-discovery and provisioning
- Hardware profiling (Manufacturer, Model, Android Version, ABI, Resolution, Density)
- Real-time Battery & Thermal Guard (prevents battery swelling and thermal throttling)
- Screen dimming & wake-lock power optimization for 24/7 phone racks
- Persistent registry of known physical devices
"""

import json
import os
import re
import sys
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.farm_config import (
    REAL_PHONE_FARM_CONFIG,
    REAL_DEVICES_REGISTRY_FILE,
    DEFAULT_FARM_DEVICES,
)
from core.adb_wrapper import ADBWrapper


class RealDeviceManager:
    """Manages physical Android phones (USB & Wireless TCP/IP) alongside virtual AVDs."""

    def __init__(self, adb: Optional[ADBWrapper] = None, registry_file: Optional[Path] = None):
        self.adb = adb or ADBWrapper()
        self.registry_file = registry_file or REAL_DEVICES_REGISTRY_FILE
        self._lock = threading.Lock()
        self.config = dict(REAL_PHONE_FARM_CONFIG)
        self._resolution_cache: Dict[str, Tuple[int, int]] = {}
        self._ensure_registry()

    def _ensure_registry(self):
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_file.exists():
            default_reg = {
                "enabled": self.config.get("enabled", True),
                "farm_mode": self.config.get("farm_mode", "HYBRID"),
                "known_devices": {},
                "wireless_endpoints": [],
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(default_reg, f, indent=2, ensure_ascii=False)

    def _read_registry(self) -> Dict[str, Any]:
        with self._lock:
            try:
                if self.registry_file.exists():
                    with open(self.registry_file, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception:
                pass
            return {
                "enabled": True,
                "farm_mode": "HYBRID",
                "known_devices": {},
                "wireless_endpoints": []
            }

    def _write_registry(self, data: Dict[str, Any]):
        with self._lock:
            data["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            tmp = self.registry_file.with_suffix(".tmp")
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                if tmp.exists():
                    os.replace(tmp, self.registry_file)
            except Exception:
                pass

    @staticmethod
    def is_real_device(serial: str) -> bool:
        """Return True if the serial belongs to a physical phone (USB or IP:Port) rather than an AVD."""
        if not serial:
            return False
        return not serial.startswith("emulator-")

    def set_farm_mode(self, mode: str, enabled: Optional[bool] = None) -> Dict[str, Any]:
        """
        Switch farm mode dynamically:
        - 'HYBRID': Both Headless AVDs and Physical Real Phones
        - 'AVD_ONLY': Virtual Emulators only
        - 'REAL_ONLY': Physical Real Phones only
        """
        valid_modes = ("HYBRID", "AVD_ONLY", "REAL_ONLY")
        clean_mode = mode.upper() if mode.upper() in valid_modes else "HYBRID"
        self.config["farm_mode"] = clean_mode
        if enabled is not None:
            self.config["enabled"] = bool(enabled)
        elif clean_mode == "AVD_ONLY":
            self.config["enabled"] = False
        else:
            self.config["enabled"] = True

        reg = self._read_registry()
        reg["farm_mode"] = clean_mode
        reg["enabled"] = self.config["enabled"]
        self._write_registry(reg)
        return {
            "farm_mode": clean_mode,
            "real_phone_farm_enabled": self.config["enabled"]
        }

    def get_farm_mode(self) -> Dict[str, Any]:
        reg = self._read_registry()
        return {
            "farm_mode": reg.get("farm_mode", self.config.get("farm_mode", "HYBRID")),
            "real_phone_farm_enabled": reg.get("enabled", self.config.get("enabled", True))
        }

    def get_device_resolution(self, serial: str) -> Tuple[int, int]:
        """Query physical or override screen resolution (width, height) with caching."""
        if serial in self._resolution_cache:
            return self._resolution_cache[serial]

        out = self.adb.shell(serial, "wm size", timeout=5)
        width, height = self.config.get("base_reference_resolution", (720, 1600))
        if out and "ERROR" not in out:
            # Prefer Override size if set, otherwise Physical size
            m_over = re.search(r"Override size:\s*(\d+)x(\d+)", out)
            m_phys = re.search(r"Physical size:\s*(\d+)x(\d+)", out)
            match = m_over or m_phys
            if match:
                width, height = int(match.group(1)), int(match.group(2))
                self._resolution_cache[serial] = (width, height)
        return width, height

    def get_battery_and_thermal_info(self, serial: str) -> Dict[str, Any]:
        """Parse `dumpsys battery` to monitor battery %, temperature (°C), voltage (mV), and charging state."""
        out = self.adb.shell(serial, "dumpsys battery", timeout=5)
        info = {
            "level": 100,
            "temperature_c": 28.0,
            "voltage_mv": 4200,
            "status": "charging",
            "plugged": "usb",
            "overheated": False,
            "low_battery": False
        }
        if not out or "ERROR" in out:
            return info

        for line in out.splitlines():
            line = line.strip()
            if line.startswith("level:"):
                try:
                    info["level"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("temperature:"):
                try:
                    # Android reports tenths of a degree Celsius (e.g. 345 -> 34.5 C)
                    raw_temp = int(line.split(":", 1)[1].strip())
                    info["temperature_c"] = round(raw_temp / 10.0, 1)
                except ValueError:
                    pass
            elif line.startswith("voltage:"):
                try:
                    info["voltage_mv"] = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("AC powered:") and "true" in line.lower():
                info["plugged"] = "ac"
            elif line.startswith("USB powered:") and "true" in line.lower():
                info["plugged"] = "usb"
            elif line.startswith("Wireless powered:") and "true" in line.lower():
                info["plugged"] = "wireless"

        max_temp = self.config.get("max_safe_battery_temp_c", 42.0)
        min_bat = self.config.get("min_safe_battery_level", 15)
        info["overheated"] = info["temperature_c"] >= max_temp
        info["low_battery"] = info["level"] <= min_bat
        return info

    def inspect_real_device(self, serial: str, status: str = "device") -> Dict[str, Any]:
        """Build a complete hardware & health profile for a physical Android device."""
        connection_type = "wireless_tcp" if ":" in serial else "usb_cable"
        if status != "device":
            return {
                "serial": serial,
                "name": f"RealPhone ({serial})",
                "is_real_device": True,
                "connection_type": connection_type,
                "status": status,
                "is_running": False,
                "boot_completed": False,
                "manufacturer": "Unknown",
                "model": status.upper(),
                "android_version": "--",
                "sdk_int": "--",
                "resolution": "720x1600",
                "width": 720,
                "height": 1600,
                "battery": {"level": 0, "temperature_c": 0.0, "overheated": False},
                "wifi_ip": serial.split(":")[0] if ":" in serial else None
            }

        if not hasattr(self, "_hw_meta_cache"):
            self._hw_meta_cache = {}
        if serial in self._hw_meta_cache:
            brand, model, release, sdk, abi = self._hw_meta_cache[serial]
        else:
            batch_out = self.adb.shell(
                serial,
                "getprop ro.product.manufacturer; getprop ro.product.model; getprop ro.build.version.release; getprop ro.build.version.sdk; getprop ro.product.cpu.abi",
                timeout=3
            )
            lines = [ln.strip() for ln in (batch_out or "").splitlines() if ln.strip() and "ERROR" not in ln]
            brand = lines[0] if len(lines) > 0 else "Android"
            model = lines[1] if len(lines) > 1 else "Phone"
            release = lines[2] if len(lines) > 2 else "14"
            sdk = lines[3] if len(lines) > 3 else "34"
            abi = lines[4] if len(lines) > 4 else "arm64-v8a"
            if len(lines) >= 2:
                self._hw_meta_cache[serial] = (brand, model, release, sdk, abi)
        width, height = self.get_device_resolution(serial)
        battery = self.get_battery_and_thermal_info(serial)
        if not hasattr(self, "_wifi_ip_cache"):
            self._wifi_ip_cache = {}
        wifi_ip = self._wifi_ip_cache.get(serial) or self.get_device_wifi_ip(serial)
        if wifi_ip:
            self._wifi_ip_cache[serial] = wifi_ip

        profile = {
            "serial": serial,
            "name": f"{brand.capitalize()} {model}",
            "is_real_device": True,
            "connection_type": connection_type,
            "status": status,
            "adb_status": status,
            "is_running": True,
            "boot_completed": True,
            "manufacturer": brand,
            "model": model,
            "android_version": release,
            "sdk_int": sdk,
            "abi": abi,
            "width": width,
            "height": height,
            "resolution": f"{width}x{height}",
            "battery": battery,
            "wifi_ip": wifi_ip,
            "description": f"Real {brand.capitalize()} {model} (Android {release} | {connection_type.upper()})"
        }

        # Persist to known devices registry
        reg = self._read_registry()
        reg.setdefault("known_devices", {})[serial] = {
            "name": profile["name"],
            "manufacturer": brand,
            "model": model,
            "android_version": release,
            "resolution": profile["resolution"],
            "wifi_ip": wifi_ip,
            "last_seen": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self._write_registry(reg)
        return profile

    def discover_real_devices(self, include_unauthorized: bool = True) -> List[Dict[str, Any]]:
        """Discover all connected physical phones via USB or Wireless ADB."""
        if not self.config.get("enabled", True) and self.config.get("farm_mode") == "AVD_ONLY":
            return []

        raw_devs = self.adb.get_connected_devices()
        real_list = []
        for d in raw_devs:
            serial = d["serial"]
            status = d["status"]
            if self.is_real_device(serial):
                if status == "device" or include_unauthorized:
                    real_list.append(self.inspect_real_device(serial, status))
        return real_list

    def get_all_active_farm_devices(self) -> List[Dict[str, Any]]:
        """
        Return unified list of devices according to active farm_mode:
        - 'HYBRID': 4 Virtual AVDs + Any Connected Real Phones
        - 'AVD_ONLY': 4 Virtual AVDs only
        - 'REAL_ONLY': Connected Real Phones only
        """
        mode_info = self.get_farm_mode()
        farm_mode = mode_info["farm_mode"]
        raw_connected = {d["serial"]: d["status"] for d in self.adb.get_connected_devices()}
        unified: List[Dict[str, Any]] = []

        if farm_mode in ("HYBRID", "AVD_ONLY"):
            for item in DEFAULT_FARM_DEVICES:
                s = item["serial"]
                status = raw_connected.get(s, "offline")
                is_online = status == "device"
                w, h = (720, 1600)
                if is_online:
                    w, h = self.get_device_resolution(s)
                unified.append({
                    "id": item["id"],
                    "serial": s,
                    "name": item["name"],
                    "port": item["port"],
                    "is_real_device": False,
                    "connection_type": "emulator",
                    "status": status,
                    "is_running": is_online,
                    "width": w,
                    "height": h,
                    "resolution": f"{w}x{h}",
                    "description": item["description"]
                })

        if farm_mode in ("HYBRID", "REAL_ONLY") and mode_info["real_phone_farm_enabled"]:
            real_devs = self.discover_real_devices(include_unauthorized=True)
            for idx, rdev in enumerate(real_devs, start=len(unified) + 1):
                rdev["id"] = idx
                unified.append(rdev)

        return unified

    def get_device_wifi_ip(self, serial: str) -> Optional[str]:
        """Extract the local Wi-Fi IPv4 address (wlan0) of a connected Android phone."""
        if ":" in serial:
            return serial.split(":")[0]
        out = self.adb.shell(serial, "ip -f inet addr show wlan0", timeout=4)
        m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", out or "")
        if m:
            return m.group(1)
        out2 = self.adb.shell(serial, "ip route", timeout=4)
        m2 = re.search(r"src\s+(\d+\.\d+\.\d+\.\d+)", out2 or "")
        if m2:
            return m2.group(1)
        return None

    def enable_wireless_adb(self, usb_serial: str, port: int = 5555) -> Tuple[bool, str]:
        """
        Switch a USB-connected real phone to Wireless ADB over TCP/IP and connect to it.
        """
        ip = self.get_device_wifi_ip(usb_serial)
        code, out, err = self.adb.run_device_cmd(usb_serial, ["tcpip", str(port)], timeout=10)
        if code != 0:
            return False, f"Failed to enable tcpip on {usb_serial}: {err or out}"

        time.sleep(1.2)
        if not ip:
            return True, f"Enabled TCP/IP port {port} on {usb_serial}, but could not detect wlan0 IP automatically."

        return self.connect_wireless_device(ip, port)

    def connect_wireless_device(self, ip_address: str, port: int = 5555) -> Tuple[bool, str]:
        """Connect to a physical Android device over Wi-Fi (`adb connect <ip>:<port>`)."""
        endpoint = f"{ip_address.strip()}:{port}" if ":" not in ip_address else ip_address.strip()
        code, out, err = self.adb.run_command(["connect", endpoint], timeout=10)
        combined = f"{out} {err}".strip()
        success = code == 0 and ("connected to" in combined.lower() or "already connected" in combined.lower())

        if success:
            reg = self._read_registry()
            endpoints = reg.setdefault("wireless_endpoints", [])
            if endpoint not in endpoints:
                endpoints.append(endpoint)
            self._write_registry(reg)

        return success, combined

    def disconnect_wireless_device(self, endpoint: str) -> Tuple[bool, str]:
        """Disconnect a wireless ADB endpoint."""
        code, out, err = self.adb.run_command(["disconnect", endpoint.strip()], timeout=8)
        return code == 0, (out or err).strip()

    def auto_reconnect_known_wireless(self) -> List[Dict[str, Any]]:
        """Attempt to reconnect all previously registered Wireless ADB endpoints."""
        reg = self._read_registry()
        endpoints = reg.get("wireless_endpoints", [])
        results = []
        for ep in endpoints:
            ok, msg = self.connect_wireless_device(ep)
            results.append({"endpoint": ep, "reconnected": ok, "message": msg})
        return results

    def apply_real_phone_health_guard(self, serial: str) -> Dict[str, Any]:
        """
        Apply battery & thermal protection and zero-lag settings for a physical farm phone:
        1. Disable window/transition animations for 2x faster UI response.
        2. Keep screen awake while plugged in (`svc power stayon usb`).
        3. Dim screen brightness to minimum safe level (15/255) to prevent OLED burn-in & overheating.
        4. If battery temperature exceeds threshold (42°C), simulate battery unplug (`dumpsys battery unplug`)
           to stop charging heat generation while keeping USB data active.
        """
        actions_taken = []
        self.adb.optimize_system_animations(serial)
        actions_taken.append("animations_disabled")

        self.adb.shell(serial, "svc power stayon true", timeout=4)
        actions_taken.append("stay_awake_enabled")

        if self.config.get("dim_screen_on_farm", True):
            brightness = self.config.get("farm_brightness_level", 15)
            self.adb.shell(serial, "settings put system screen_brightness_mode 0", timeout=4)
            self.adb.shell(serial, f"settings put system screen_brightness {brightness}", timeout=4)
            actions_taken.append(f"brightness_dimmed_to_{brightness}")

        battery = self.get_battery_and_thermal_info(serial)
        thermal_action = "normal"
        if battery.get("overheated"):
            # Stop charging heat via dumpsys battery unplug
            self.adb.shell(serial, "dumpsys battery unplug", timeout=4)
            thermal_action = f"cooling_unplug_triggered_at_{battery['temperature_c']}C"
            actions_taken.append(thermal_action)
        elif battery.get("level", 100) < 80:
            # Ensure normal charging state is restored
            self.adb.shell(serial, "dumpsys battery reset", timeout=4)
            thermal_action = "charging_normal"

        return {
            "serial": serial,
            "battery": battery,
            "thermal_action": thermal_action,
            "actions_taken": actions_taken
        }


if __name__ == "__main__":
    mgr = RealDeviceManager()
    print("Farm Mode:", mgr.get_farm_mode())
    print("Active Hybrid Devices:", len(mgr.get_all_active_farm_devices()))
