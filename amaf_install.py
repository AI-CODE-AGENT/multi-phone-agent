"""
AMAF 1-Click Universal APK Installer CLI (`amaf_install.py`)
Usage:
    python amaf_install.py <apk_path> [--serial <serial>] [--grant-all] [--launch]

Features:
1. Reconfigures `sys.stdout` / `sys.stderr` to UTF-8 on Windows to support Vietnamese/CJK popup logs.
2. Auto-detects connected device serial if `--serial` is omitted (prioritizing physical device `10CF5L0TYL00312` or non-emulator `-d` hardware).
3. Extracts APK metadata (`package_name`, `permissions`, `launchable_activity`) via `MultiUserPackageEngine` if available (or pure-Python APK manifest inspection fallback).
4. Runs `AlwaysOnInstallDaemon` / `ADBWrapper.install_apk(..., auto_accept_oem_popups=True)` to install the APK while automatically ticking Vivo/Xiaomi/OPPO/Samsung unknown-app risk checkboxes and clicking confirm buttons.
5. Optionally grants runtime permissions (`--grant-all`) and launches the app (`--launch`), printing a structured JSON + human-readable report.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core.adb_wrapper import ADBWrapper
from core.always_on_install_daemon import AlwaysOnInstallDaemon

try:
    from core.multi_user_package_engine import MultiUserPackageEngine
except ImportError:
    MultiUserPackageEngine = None  # type: ignore

PREFERRED_PHYSICAL_SERIAL = "10CF5L0TYL00312"


def configure_windows_utf8_stdout() -> None:
    """Reconfigure sys.stdout and sys.stderr to UTF-8 on Windows."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser for `amaf_install.py`."""
    parser = argparse.ArgumentParser(
        prog="amaf_install",
        description="AMAF 1-Click Universal APK Installer with Always-On OEM Popup & Checkbox Guard",
    )
    parser.add_argument(
        "apk_path",
        help="Path to the .apk file to install",
    )
    parser.add_argument(
        "--serial",
        "-s",
        default=None,
        help="Target Android device serial (auto-detects connected device if omitted)",
    )
    parser.add_argument(
        "--grant-all",
        "-g",
        action="store_true",
        help="Grant all runtime permissions during and after installation",
    )
    parser.add_argument(
        "--launch",
        "-l",
        action="store_true",
        help="Automatically launch the installed application after installation",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=90,
        help="Installation timeout in seconds (default: 90)",
    )
    return parser


def parse_cli_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments for `amaf_install.py`."""
    parser = build_arg_parser()
    return parser.parse_args(argv)


def auto_detect_serial(adb: ADBWrapper, explicit_serial: Optional[str] = None) -> str:
    """
    Resolve target device serial:
    1. If `explicit_serial` is provided, return it directly.
    2. Query `adb.get_connected_devices()` for online (`status == 'device'`) devices.
    3. Prioritize `10CF5L0TYL00312` if connected, then physical devices (not starting with `emulator-`),
       then any connected device, or fall back to `10CF5L0TYL00312`.
    """
    if explicit_serial:
        return explicit_serial.strip()

    connected = [
        d for d in adb.get_connected_devices() if d.get("status") == "device"
    ]
    serials = [d["serial"] for d in connected if d.get("serial")]

    if PREFERRED_PHYSICAL_SERIAL in serials:
        return PREFERRED_PHYSICAL_SERIAL

    physical_serials = [
        s for s in serials if not s.startswith("emulator-") and ":" not in s
    ]
    if physical_serials:
        return physical_serials[0]

    if serials:
        return serials[0]

    return PREFERRED_PHYSICAL_SERIAL


def extract_apk_metadata(apk_path: str, adb: Optional[ADBWrapper] = None) -> Dict[str, Any]:
    """
    Extract APK metadata (`package_name`, `permissions`, `version_name`) using
    `MultiUserPackageEngine` if available, with graceful fallback.
    """
    metadata: Dict[str, Any] = {
        "package_name": None,
        "permissions": [],
        "extractor": "fallback",
    }

    if MultiUserPackageEngine is not None:
        try:
            engine = MultiUserPackageEngine()
            for method_name in ("extract_apk_metadata_pure_python", "extract_apk_metadata", "inspect_apk", "parse_apk_metadata"):
                if hasattr(engine, method_name):
                    res = getattr(engine, method_name)(apk_path)
                    if isinstance(res, dict):
                        metadata.update(res)
                        metadata["extractor"] = f"MultiUserPackageEngine.{method_name}"
                        break
        except Exception:
            pass

    return metadata


def run_amaf_install(
    apk_path: str,
    serial: Optional[str] = None,
    grant_all: bool = False,
    launch: bool = False,
    timeout_sec: int = 90,
    adb: Optional[ADBWrapper] = None,
) -> Dict[str, Any]:
    """
    Execute the complete 1-Click Universal APK Installation workflow and return a structured report.
    """
    adb_instance = adb or ADBWrapper()
    resolved_serial = auto_detect_serial(adb_instance, serial)
    abs_apk_path = str(Path(apk_path).resolve()) if os.path.exists(apk_path) else apk_path

    metadata = extract_apk_metadata(abs_apk_path, adb=adb_instance)
    package_name = metadata.get("package_name")
    permissions: List[str] = list(metadata.get("permissions") or [])

    daemon = AlwaysOnInstallDaemon(
        serial=resolved_serial,
        adb=adb_instance,
        poll_interval_sec=0.35,
    )

    extra_flags = ["-r", "-g"] if grant_all else ["-r"]
    install_res = daemon.install_apk_with_daemon(
        apk_path=abs_apk_path,
        extra_flags=extra_flags,
        timeout_sec=timeout_sec,
    )

    # Also invoke ADBWrapper.install_apk fallback if needed and file exists
    if not install_res.get("success") and os.path.exists(abs_apk_path):
        ok, msg = adb_instance.install_apk(
            resolved_serial,
            abs_apk_path,
            replace=True,
            auto_accept_oem_popups=True,
        )
        if ok:
            install_res["success"] = True
            install_res["output"] = msg

    permissions_granted: List[str] = []
    if grant_all and install_res.get("success") and package_name:
        for perm in permissions:
            if perm.startswith("android.permission."):
                out = adb_instance.shell(
                    resolved_serial,
                    f"pm grant --user 0 {package_name} {perm}",
                    timeout=10,
                )
                if "Exception" not in (out or "") and "Error" not in (out or ""):
                    permissions_granted.append(perm)

    launched = False
    if launch and install_res.get("success") and package_name:
        launched = adb_instance.launch_app(resolved_serial, package_name)

    report = {
        "status": "INSTALLED" if install_res.get("success") else "FAILED",
        "success": bool(install_res.get("success")),
        "serial": resolved_serial,
        "apk_path": abs_apk_path,
        "package_name": package_name,
        "permissions": permissions,
        "grant_all": grant_all,
        "permissions_granted": permissions_granted,
        "launch_requested": launch,
        "launched": launched,
        "popups_dismissed": install_res.get("popups_dismissed", 0),
        "checkboxes_ticked": install_res.get("checkboxes_ticked", 0),
        "elapsed_sec": install_res.get("elapsed_sec", 0.0),
        "output": install_res.get("output") or install_res.get("error", ""),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    return report


def format_human_report(report: Dict[str, Any]) -> str:
    """Format a concise human-readable installation summary."""
    lines = [
        "=" * 64,
        f"AMAF 1-Click Universal APK Installer — {report.get('status')}",
        "=" * 64,
        f"  Device Serial      : {report.get('serial')}",
        f"  APK Path           : {report.get('apk_path')}",
        f"  Package Name       : {report.get('package_name') or 'N/A'}",
        f"  Success            : {report.get('success')}",
        f"  Popups Dismissed   : {report.get('popups_dismissed')}",
        f"  Checkboxes Ticked  : {report.get('checkboxes_ticked')}",
        f"  Grant All Perms    : {report.get('grant_all')} ({len(report.get('permissions_granted', []))} granted)",
        f"  App Launched       : {report.get('launched')}",
        f"  Elapsed Time       : {report.get('elapsed_sec')}s",
        f"  ADB Output         : {report.get('output')}",
        "=" * 64,
    ]
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for `amaf_install.py` CLI."""
    configure_windows_utf8_stdout()
    args = parse_cli_args(argv)
    report = run_amaf_install(
        apk_path=args.apk_path,
        serial=args.serial,
        grant_all=args.grant_all,
        launch=args.launch,
        timeout_sec=args.timeout,
    )
    print(format_human_report(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
