"""
Unit tests for SideloadSourceGuardEngine and SideloadSourceAndPermissionSubagent (Subagent #47).
Iteration #4 of the 10x Recursive Evolution Plan.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.sideload_source_guard_subagent import SideloadSourceAndPermissionSubagent
from core.sideload_source_guard_engine import SideloadSourceGuardEngine


VIETNAMESE_SIDELOAD_XML_UNCHECKED = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="Cài đặt ứng dụng không xác định" resource-id="android:id/title" class="android.widget.TextView" package="com.android.settings" checkable="false" checked="false" clickable="false" bounds="[72,140][900,210]" />
  <node index="1" text="Cho phép từ nguồn này" resource-id="android:id/title" class="android.widget.TextView" package="com.android.settings" checkable="false" checked="false" clickable="false" bounds="[72,420][780,490]" />
  <node index="2" text="" resource-id="android:id/switch_widget" class="android.widget.Switch" package="com.android.settings" checkable="true" checked="false" clickable="true" bounds="[880,415][1020,495]" />
</hierarchy>
"""

VIETNAMESE_SIDELOAD_XML_CHECKED = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="Cài đặt ứng dụng không xác định" resource-id="android:id/title" class="android.widget.TextView" package="com.android.settings" checkable="false" checked="false" clickable="false" bounds="[72,140][900,210]" />
  <node index="1" text="Cho phép từ nguồn này" resource-id="android:id/title" class="android.widget.TextView" package="com.android.settings" checkable="false" checked="false" clickable="false" bounds="[72,420][780,490]" />
  <node index="2" text="" resource-id="android:id/switch_widget" class="android.widget.Switch" package="com.android.settings" checkable="true" checked="true" clickable="true" bounds="[880,415][1020,495]" />
</hierarchy>
"""


class MockADBWrapper:
    """Mock ADB wrapper recording shell commands, taps, keyevents, and returning canned XML."""

    def __init__(self, xml_to_return: str = "") -> None:
        self.xml_to_return = xml_to_return
        self.commands: list[str] = []
        self.taps: list[tuple[int, int]] = []
        self.keyevents: list[int] = []

    def dump_xml(self) -> str:
        return self.xml_to_return

    def shell(self, cmd: str) -> str:
        self.commands.append(cmd)
        if cmd.startswith("input tap "):
            parts = cmd.split()
            self.taps.append((int(parts[2]), int(parts[3])))
        elif cmd.startswith("input keyevent "):
            parts = cmd.split()
            self.keyevents.append(int(parts[2]))
        return "Success"


def test_analyze_sideload_settings_xml_unchecked_and_checked() -> None:
    engine = SideloadSourceGuardEngine(tap_settle_delay_s=0.0)

    # 1. Unchecked Vietnamese "Cho phép từ nguồn này" screen
    res_unchecked = engine.analyze_sideload_settings_xml(VIETNAMESE_SIDELOAD_XML_UNCHECKED)
    assert res_unchecked["is_sideload_screen"] is True
    assert res_unchecked["is_enabled"] is False
    assert res_unchecked["needs_back_navigation"] is False
    assert res_unchecked["toggle_target"] is not None
    assert res_unchecked["toggle_target"]["resource_id"] == "android:id/switch_widget"
    assert res_unchecked["toggle_target"]["x"] == 950
    assert res_unchecked["toggle_target"]["y"] == 455

    # 2. Checked Vietnamese "Cho phép từ nguồn này" screen
    res_checked = engine.analyze_sideload_settings_xml(VIETNAMESE_SIDELOAD_XML_CHECKED)
    assert res_checked["is_sideload_screen"] is True
    assert res_checked["is_enabled"] is True
    assert res_checked["needs_back_navigation"] is True
    assert res_checked["toggle_target"] is not None
    assert res_checked["toggle_target"]["checked"] is True


def test_handle_sideload_settings_screen_taps_and_navigates_back() -> None:
    engine = SideloadSourceGuardEngine(tap_settle_delay_s=0.0)
    mock_adb = MockADBWrapper(xml_to_return=VIETNAMESE_SIDELOAD_XML_UNCHECKED)

    result = engine.handle_sideload_settings_screen(mock_adb)
    assert result["handled"] is True
    assert result["tapped"] is True
    assert result["tap_coords"] == (950, 455)
    assert result["back_sent"] is True
    assert mock_adb.taps == [(950, 455)]
    assert mock_adb.keyevents == [4]
    assert "input tap 950 455" in mock_adb.commands
    assert "input keyevent 4" in mock_adb.commands


def test_pre_authorize_sideload_sources_and_auto_grant_runtime_permissions() -> None:
    mock_adb = MockADBWrapper()
    subagent = SideloadSourceAndPermissionSubagent(adb_wrapper=mock_adb, tap_settle_delay_s=0.0)

    # 1. Pre-authorize default sideload sources
    pre_auth = subagent.ensure_sideload_ready()
    assert pre_auth["status"] == "ok"
    assert len(pre_auth["packages"]) == 6
    for pkg in SideloadSourceGuardEngine.DEFAULT_SIDELOAD_SOURCES:
        expected_cmd = f"appops set --user 0 {pkg} REQUEST_INSTALL_PACKAGES allow"
        assert expected_cmd in pre_auth["commands"]
        assert expected_cmd in mock_adb.commands

    # 2. Auto-grant runtime permissions and special appops with --user 0
    mock_adb.commands.clear()
    perms = [
        "android.permission.CAMERA",
        "android.permission.READ_EXTERNAL_STORAGE",
    ]
    grant_res = subagent.grant_all_package_permissions(
        package_name="com.example.testapp",
        permissions=perms,
        include_special_appops=True,
    )
    assert grant_res["status"] == "ok"
    assert "pm grant --user 0 com.example.testapp android.permission.CAMERA" in mock_adb.commands
    assert "pm grant --user 0 com.example.testapp android.permission.READ_EXTERNAL_STORAGE" in mock_adb.commands
    assert "appops set --user 0 com.example.testapp SYSTEM_ALERT_WINDOW allow" in mock_adb.commands
    assert "appops set --user 0 com.example.testapp MANAGE_EXTERNAL_STORAGE allow" in mock_adb.commands

    status = subagent.get_status()
    assert status["subagent_id"] == 47
    assert status["stats"]["pre_authorizations_run"] == 1
    assert status["stats"]["runtime_grants_run"] == 1
