"""
Unit and Integration Test for Vivo OriginOS Unknown App APK Install & Auto-Checkbox Tick Guard.
Tests Subagent #18 (OEMPopupWatcher & OEMPopupGuardSubagent) on OriginOS PackageInterceptActivity.
"""

import sys
import unicodedata
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.adb_wrapper import ADBWrapper
from core.oem_popup_watcher import OEMPopupWatcher
from agents.oem_popup_guard_subagent import OEMPopupGuardSubagent


XML_VIVO_PACKAGE_INTERCEPT = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="GeminiCall AI" resource-id="com.android.packageinstaller:id/tv_app_name" class="android.widget.TextView" package="com.android.packageinstaller" clickable="false" bounds="[371,376][1176,461]" />
  <node index="1" text="Tôi đã hiểu kết quả phát hiện rủi ro của ứng dụng" resource-id="com.android.packageinstaller:id/deleted_file_state_cb" class="android.widget.CheckBox" package="com.android.packageinstaller" checkable="true" checked="false" clickable="true" enabled="true" bounds="[105,2418][1154,2481]" />
  <node index="2" text="" content-desc="Tiếp tục cài đặt" resource-id="android:id/button1" class="android.widget.Button" package="com.android.packageinstaller" checkable="false" checked="false" clickable="true" enabled="true" bounds="[168,2541][1092,2702]" />
</hierarchy>
"""


def test_vivo_unknown_app_checkbox_auto_ticked_and_continue_clicked():
    adb = ADBWrapper()
    watcher = OEMPopupWatcher(adb=adb)

    tapped_coords = []

    def fake_tap(serial, x, y):
        tapped_coords.append((x, y))
        return x, y

    watcher._human_micro_dwell_tap = fake_tap

    with patch.object(adb, "shell", return_value="mCurrentFocus=Window{123 u0 com.android.packageinstaller/com.android.packageinstaller.PackageInterceptActivity type=1 }"):
        with patch.object(adb, "dump_ui_hierarchy", return_value=XML_VIVO_PACKAGE_INTERCEPT):
            res = watcher.scan_and_dismiss_oem_popup("10CF5L0TYL00312")

    assert res["status"] == "POPUP_DISMISSED"
    assert res["checkbox_ticked"] is True
    normalized_info = unicodedata.normalize("NFC", res["checkbox_info"]).lower()
    assert "rủi ro" in normalized_info or "deleted_file_state_cb" in res["checkbox_info"]

    # Verify both checkbox and continue button were tapped in order!
    assert len(tapped_coords) == 2
    cb_tap, btn_tap = tapped_coords[0], tapped_coords[1]

    # Checkbox bounds [105, 2418][1154, 2481] -> tapped at ~150, 2449
    assert 105 <= cb_tap[0] <= 1154
    assert 2418 <= cb_tap[1] <= 2481

    # Button bounds [168, 2541][1092, 2702] -> center at 630, 2621
    assert 168 <= btn_tap[0] <= 1092
    assert 2541 <= btn_tap[1] <= 2702


def test_oem_popup_guard_subagent_persists_checkbox_telemetry():
    guard = OEMPopupGuardSubagent()
    tapped_coords = []
    guard.watcher._human_micro_dwell_tap = lambda s, x, y: (tapped_coords.append((x, y)), (x, y))[1]

    with patch.object(guard.adb, "shell", return_value="mCurrentFocus=Window{123 u0 com.android.packageinstaller/com.android.packageinstaller.PackageInterceptActivity type=1 }"):
        with patch.object(guard.adb, "dump_ui_hierarchy", return_value=XML_VIVO_PACKAGE_INTERCEPT):
            res = guard.guard_device("10CF5L0TYL00312")

    assert res["status"] == "POPUP_DISMISSED"
    assert res["checkbox_ticked"] is True
