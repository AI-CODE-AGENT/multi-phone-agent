"""
AVD Cloner & Farm Initializer
Provisions ultra-lightweight Android Virtual Devices on D: drive
"""

import sys
from pathlib import Path
from typing import Dict, List, Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.farm_config import (
    AVD_STORAGE_DIR,
    AVD_METADATA_DIR,
    DEFAULT_TARGET,
    DEFAULT_SYSDIR,
    OPTIMIZED_SPECS,
    DEFAULT_FARM_DEVICES
)


def generate_config_ini(specs: Dict[str, Any]) -> str:
    """Generate the config.ini content for an ultra-lightweight AVD."""
    return f"""abi.type = x86_64
avd.ini.encoding = UTF-8
hw.accelerometer = yes
hw.audioInput = yes
hw.battery = {specs.get("battery", "yes")}
hw.camera.back = {specs.get("camera_back", "virtualscene")}
hw.camera.front = {specs.get("camera_front", "emulated")}
hw.cpu.arch = x86_64
hw.cpu.ncore = {specs.get("cores", 2)}
hw.dPad = no
hw.device.hash2 = MD5:524f72cfa530864e452e60b260f52557
hw.device.manufacturer = Google
hw.device.name = pixel
hw.gps = {specs.get("gps", "yes")}
hw.gpu.enabled = yes
hw.gpu.mode = {specs.get("gpu_mode", "host")}
hw.initialOrientation = Portrait
hw.keyboard = yes
hw.lcd.density = {specs.get("density", 320)}
hw.lcd.height = {specs.get("height", 1600)}
hw.lcd.width = {specs.get("width", 720)}
hw.mainKeys = no
hw.ramSize = {specs.get("ram_mb", 1536)}
hw.sdCard = yes
hw.sensors.orientation = yes
hw.sensors.proximity = yes
hw.trackBall = no
image.sysdir.1 = {DEFAULT_SYSDIR}
tag.display = Google Play
tag.id = google_apis_playstore
vm.heapSize = {specs.get("heap_size", 256)}
disk.dataPartition.size = 6442450944
fastboot.forceColdBoot = no
"""


def generate_metadata_ini(avd_name: str) -> str:
    """Generate the <avd_name>.ini content placed in ~/.android/avd."""
    avd_path = AVD_STORAGE_DIR / f"{avd_name}.avd"
    return f"""avd.ini.encoding=UTF-8
path={str(avd_path)}
path.rel=avd\\{avd_name}.avd
target={DEFAULT_TARGET}
"""


def provision_avd(avd_name: str, custom_specs: Dict[str, Any] = None) -> bool:
    """
    Provision a single AVD on D:\\Android_AVD with metadata in ~/.android/avd.
    Returns True if successfully created or updated.
    """
    specs = OPTIMIZED_SPECS.copy()
    if custom_specs:
        specs.update(custom_specs)

    # 1. Ensure target directory on D: drive exists
    avd_dir = AVD_STORAGE_DIR / f"{avd_name}.avd"
    avd_dir.mkdir(parents=True, exist_ok=True)

    # 2. Write config.ini in D:\Android_AVD\<avd_name>.avd\config.ini
    config_file = avd_dir / "config.ini"
    config_content = generate_config_ini(specs)
    config_file.write_text(config_content, encoding="utf-8")

    # 3. Write metadata file in C:\Users\<user>\.android\avd\<avd_name>.ini
    meta_file = AVD_METADATA_DIR / f"{avd_name}.ini"
    meta_content = generate_metadata_ini(avd_name)
    meta_file.write_text(meta_content, encoding="utf-8")

    return True


def setup_farm(count: int = 4) -> List[Dict[str, Any]]:
    """
    Setup the farm of N virtual devices.
    Default count = 4 (Pixel_Farm_1 to Pixel_Farm_4).
    """
    created = []
    for item in DEFAULT_FARM_DEVICES[:count]:
        name = item["name"]
        provision_avd(name)
        created.append({
            "name": name,
            "port": item["port"],
            "serial": item["serial"],
            "path": str(AVD_STORAGE_DIR / f"{name}.avd"),
            "status": "ready"
        })
    return created


def get_farm_status() -> List[Dict[str, Any]]:
    """Check provision status of all configured farm devices."""
    results = []
    for item in DEFAULT_FARM_DEVICES:
        name = item["name"]
        avd_dir = AVD_STORAGE_DIR / f"{name}.avd"
        meta_file = AVD_METADATA_DIR / f"{name}.ini"
        config_file = avd_dir / "config.ini"

        is_provisioned = meta_file.exists() and config_file.exists()
        results.append({
            "name": name,
            "port": item["port"],
            "serial": item["serial"],
            "description": item["description"],
            "provisioned": is_provisioned,
            "dir_exists": avd_dir.exists(),
            "path": str(avd_dir)
        })
    return results


if __name__ == "__main__":
    print(f"Setting up 4 Ultra-Light AVDs on {AVD_STORAGE_DIR}...")
    farm = setup_farm(4)
    print("Provisioned devices:")
    for d in farm:
        print(f" - {d['name']} -> {d['serial']} at {d['path']}")
