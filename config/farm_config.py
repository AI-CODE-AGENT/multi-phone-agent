"""
Farm Configuration & Path Management
Central configuration for Ultra-Lightweight Android Multi-Agent Farm.
"""

import os
from pathlib import Path

# Base Directories
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Android SDK Paths
USER_PROFILE = Path(os.environ.get("USERPROFILE", "C:\\Users\\Admin"))
ANDROID_SDK_ROOT = USER_PROFILE / "AppData" / "Local" / "Android" / "Sdk"
ADB_PATH = ANDROID_SDK_ROOT / "platform-tools" / "adb.exe"
EMULATOR_PATH = ANDROID_SDK_ROOT / "emulator" / "emulator.exe"

# Storage on D: Drive (Massive 3.5TB free space)
AVD_STORAGE_DIR = Path("D:\\Android_AVD")
AVD_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
AVD_METADATA_DIR = USER_PROFILE / ".android" / "avd"
AVD_METADATA_DIR.mkdir(parents=True, exist_ok=True)

# System Image & ABI (Android 15 PlayStore with ARM64 native bridge)
DEFAULT_TARGET = "android-35"
DEFAULT_SYSDIR = "system-images/android-35/google_apis_playstore/x86_64/"
SYSTEM_IMAGE_PATH = ANDROID_SDK_ROOT / "system-images" / "android-35" / "google_apis_playstore" / "x86_64"

# Scrcpy & FFmpeg Discovery
SCRCPY_DEFAULT = USER_PROFILE / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages" / "Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe" / "scrcpy-win64-v5.0.1" / "scrcpy.exe"


def find_scrcpy() -> str:
    """Find scrcpy executable in PATH or WinGet package dir."""
    import shutil
    found = shutil.which("scrcpy")
    if found:
        return found
    if SCRCPY_DEFAULT.exists():
        return str(SCRCPY_DEFAULT)
    # Search WinGet dir
    winget_dir = USER_PROFILE / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    for p in winget_dir.glob("**/scrcpy.exe"):
        return str(p)
    return "scrcpy"


# Ultra-Lightweight Specs per Device
OPTIMIZED_SPECS = {
    "ram_mb": 1536,          # 1.5 GB RAM (sweet spot for Android 15 + PlayStore without OOM)
    "heap_size": 256,        # Dalvik heap 256MB
    "cores": 2,              # 2 vCPU cores per instance
    "width": 720,            # 720x1600 (HD+ modern 20:9 aspect ratio, 55% less VRAM/RAM than 1080p)
    "height": 1600,
    "density": 320,          # xhdpi density
    "gpu_mode": "host",      # Offload OpenGL/Vulkan directly to NVIDIA GeForce RTX 3050
    "camera_back": "virtualscene",
    "camera_front": "emulated",
    "gps": "yes",
    "battery": "yes",
    "fingerprint": "yes",
}

# 4 Default Farm Devices
DEFAULT_FARM_DEVICES = [
    {
        "id": 1,
        "name": "Pixel_Farm_1",
        "port": 5554,
        "serial": "emulator-5554",
        "description": "Customer Role / Primary Test Device"
    },
    {
        "id": 2,
        "name": "Pixel_Farm_2",
        "port": 5556,
        "serial": "emulator-5556",
        "description": "Merchant & Driver Role / Secondary Test Device"
    },
    {
        "id": 3,
        "name": "Pixel_Farm_3",
        "port": 5558,
        "serial": "emulator-5558",
        "description": "Admin & Backoffice Role / Stress Testing"
    },
    {
        "id": 4,
        "name": "Pixel_Farm_4",
        "port": 5560,
        "serial": "emulator-5560",
        "description": "Regression & Chaos / Edge Case Validator"
    },
]

# Headless Emulator Command Flags (Ultra-Low Overhead)
HEADLESS_FLAGS = [
    "-no-window",            # No desktop GUI window (0% host display GPU overhead)
    "-no-audio",             # No host audio server
    "-no-boot-anim",         # Skip boot animation (2-3x faster boot)
    "-gpu", "host",          # Hardware OpenGL/Vulkan rendering on RTX 3050
    "-no-snapshot-save",     # Don't spend CPU saving massive memory dumps on exit
    "-no-metrics",           # Disable Google telemetry reporting (eliminates background HTTP sync)
    "-no-passive-gps",       # Disable passive GPS sensor emulation (saves CPU)
    "-netfast",              # Accelerate network socket buffers
]

# Optional Real Phone Farm Configuration (AMAF 3.0 Hybrid Mode)
REAL_PHONE_FARM_CONFIG = {
    "enabled": True,                          # Enable optional real physical phone support
    "farm_mode": "HYBRID",                    # Options: "HYBRID" (AVDs + Real), "AVD_ONLY", "REAL_ONLY"
    "wireless_adb_default_port": 5555,        # Default TCP/IP port for Wireless ADB
    "auto_reconnect_wireless": True,          # Automatically reconnect known wireless ADB phones
    "max_safe_battery_temp_c": 42.0,          # Thermal guard threshold (°C) before cooling pause
    "min_safe_battery_level": 15,             # Minimum battery % warning threshold
    "dim_screen_on_farm": True,               # Lower brightness on real phones to reduce heat & burn-in
    "farm_brightness_level": 15,              # Safe low brightness (0-255) during automated farming
    "base_reference_resolution": (720, 1600), # Reference resolution for normalized coordinate scaling
}

REAL_DEVICES_REGISTRY_FILE = CONFIG_DIR / "real_devices_registry.json"

