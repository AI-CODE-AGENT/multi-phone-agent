"""
Unit tests for Iteration #7:
- `core/always_on_install_daemon.py` (`AlwaysOnInstallDaemon`)
- `agents/always_on_install_daemon_subagent.py` (`AlwaysOnInstallDaemonAndCLISubagent`)
- `amaf_install.py` (1-Click Universal APK Installer CLI)
- `D:\\Project\\Tools\\amaf_install.bat`
"""

import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.always_on_install_daemon import AlwaysOnInstallDaemon
from agents.always_on_install_daemon_subagent import AlwaysOnInstallDaemonAndCLISubagent
import amaf_install


VIVO_RISK_DIALOG_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="Tôi đã hiểu kết quả phát hiện rủi ro của ứng dụng" resource-id="com.vivo.secime:id/cb_risk" class="android.widget.CheckBox" checkable="true" checked="false" clickable="true" enabled="true" bounds="[80,2380][1180,2480]" />
  <node index="1" text="Tiếp tục cài đặt" resource-id="com.vivo.secime:id/continue_button" class="android.widget.Button" checkable="false" checked="false" clickable="true" enabled="true" bounds="[120,2550][1140,2680]" />
</hierarchy>
"""


class FakeADB:
    """Mock ADBWrapper for deterministic zero-token testing."""

    def __init__(self, focus_window: str = "mCurrentFocus=Window{123 u0 com.android.launcher3/.Launcher}", xml: str = ""):
        self.focus_window = focus_window
        self.xml = xml
        self.shell_calls = []
        self.device_cmd_calls = []
        self.connected_devices = [
            {"serial": "emulator-5554", "status": "device", "model": "sdk_gphone64"},
            {"serial": "10CF5L0TYL00312", "status": "device", "model": "V2417A"},
        ]

    def shell(self, serial: str, command: str, timeout: int = 30) -> str:
        self.shell_calls.append((serial, command))
        if "dumpsys window" in command:
            return self.focus_window
        if "wm size" in command:
            return "Physical size: 1260x2800"
        return "OK"

    def dump_ui_hierarchy(self, serial: str) -> str:
        return self.xml

    def parse_ui_elements(self, xml_string: str):
        from core.adb_wrapper import ADBWrapper
        return ADBWrapper().parse_ui_elements(xml_string)

    def run_device_cmd(self, serial: str, args, timeout: int = 30):
        self.device_cmd_calls.append((serial, list(args)))
        if args and args[0] == "install":
            return 0, "Performing Streamed Install\nSuccess", ""
        return 0, "OK", ""

    def get_connected_devices(self):
        return self.connected_devices

    def launch_app(self, serial: str, package_name: str, activity_name=None) -> bool:
        self.shell_calls.append((serial, f"launch:{package_name}"))
        return True


def test_fast_path_window_filtering():
    """Verify that non-installer foreground windows skip full UIAutomator XML dumps."""
    adb = FakeADB(
        focus_window="mCurrentFocus=Window{111 u0 com.vivo.launcher/.Launcher}",
        xml=VIVO_RISK_DIALOG_XML,
    )
    daemon = AlwaysOnInstallDaemon(serial="10CF5L0TYL00312", adb=adb, poll_interval_sec=0.1)

    res = daemon.run_single_tick(force_full_scan=False)
    assert res["status"] == "FAST_PATH_SKIPPED"
    assert daemon.polls_completed == 1
    assert daemon.fast_path_skips == 1
    assert daemon.popups_dismissed == 0
    assert daemon.last_heartbeat_ts > 0


def test_single_tick_popup_and_checkbox_dismissal():
    """Verify that when foreground window matches packageinstaller/vivo.secime, risk checkbox is ticked and confirm button tapped."""
    adb = FakeADB(
        focus_window="mCurrentFocus=Window{222 u0 com.android.packageinstaller/.PackageInterceptActivity}",
        xml=VIVO_RISK_DIALOG_XML,
    )
    daemon = AlwaysOnInstallDaemon(serial="10CF5L0TYL00312", adb=adb, poll_interval_sec=0.1)

    res = daemon.run_single_tick(force_full_scan=False)
    assert res["status"] == "POPUP_DISMISSED"
    assert res["checkbox_ticked"] is True
    assert res["matched_label"] == "Tiếp tục cài đặt"
    assert daemon.popups_dismissed == 1
    assert daemon.checkboxes_ticked == 1
    assert len(daemon.events_log) == 1


def test_daemon_start_stop_lifecycle_and_heartbeat():
    """Verify background daemon thread starts, updates heartbeat, reports healthy status, and stops cleanly."""
    adb = FakeADB(
        focus_window="mCurrentFocus=Window{333 u0 com.vivo.secime/.SecurityPrompt}",
        xml=VIVO_RISK_DIALOG_XML,
    )
    daemon = AlwaysOnInstallDaemon(
        serial="10CF5L0TYL00312",
        adb=adb,
        poll_interval_sec=0.05,
        max_idle_timeout_sec=30.0,
    )

    start_res = daemon.start()
    assert start_res["status"] == "DAEMON_STARTED"

    dup_res = daemon.start()
    assert dup_res["status"] == "ALREADY_RUNNING"

    time.sleep(0.30)
    health = daemon.get_health_status()
    assert health["running"] is True
    assert health["healthy"] is True
    assert health["polls_completed"] >= 1
    assert health["popups_dismissed"] >= 1
    assert health["checkboxes_ticked"] >= 1

    stop_res = daemon.stop()
    assert stop_res["status"] == "DAEMON_STOPPED"
    assert daemon.get_health_status()["running"] is False


def test_install_apk_with_daemon_and_subagent():
    """Verify `install_apk_with_daemon` and `AlwaysOnInstallDaemonAndCLISubagent` wrapper."""
    scratch_dir = Path(__file__).resolve().parent.parent / "logs"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    dummy_apk = scratch_dir / "test_sample_app_50.apk"
    dummy_apk.write_bytes(b"PK\x03\x04dummy-apk-bytes")

    try:
        adb = FakeADB(
            focus_window="mCurrentFocus=Window{444 u0 com.google.android.packageinstaller/com.android.packageinstaller.InstallStaging}",
            xml=VIVO_RISK_DIALOG_XML,
        )
        mock_memory = MagicMock()
        subagent = AlwaysOnInstallDaemonAndCLISubagent(adb=adb, memory=mock_memory)

        res = subagent.install_apk(str(dummy_apk), serial="10CF5L0TYL00312", timeout_sec=15)
        assert res["success"] is True
        assert res["serial"] == "10CF5L0TYL00312"
        assert "Success" in res["output"]
        assert mock_memory.remember.called
    finally:
        if dummy_apk.exists():
            dummy_apk.unlink()


def test_amaf_install_cli_arg_parsing_and_execution():
    """Verify `amaf_install.py` CLI argument parsing, serial auto-detection, and batch file existence."""
    args = amaf_install.parse_cli_args(
        ["C:/temp/test.apk", "--serial", "10CF5L0TYL00312", "--grant-all", "--launch", "--timeout", "45"]
    )
    assert args.apk_path == "C:/temp/test.apk"
    assert args.serial == "10CF5L0TYL00312"
    assert args.grant_all is True
    assert args.launch is True
    assert args.timeout == 45

    adb = FakeADB()
    detected = amaf_install.auto_detect_serial(adb, explicit_serial=None)
    assert detected == "10CF5L0TYL00312"

    scratch_dir = Path(__file__).resolve().parent.parent / "logs"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    dummy_apk = scratch_dir / "test_cli_50.apk"
    dummy_apk.write_bytes(b"PK\x03\x04dummy-apk")

    try:
        report = amaf_install.run_amaf_install(
            apk_path=str(dummy_apk),
            serial=None,
            grant_all=True,
            launch=True,
            adb=adb,
        )
        assert report["status"] == "INSTALLED"
        assert report["success"] is True
        assert report["serial"] == "10CF5L0TYL00312"
    finally:
        if dummy_apk.exists():
            dummy_apk.unlink()

    bat_path = Path(r"D:\Project\Tools\amaf_install.bat")
    assert bat_path.exists()
    assert "amaf_install.py" in bat_path.read_text(encoding="utf-8")
