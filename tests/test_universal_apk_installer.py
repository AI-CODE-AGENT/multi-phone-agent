"""
Unit tests for UniversalAPKInstallerEngine and UniversalMultiStageInstallerSubagent (Subagent #46).
"""

import sys
import unicodedata
from pathlib import Path
from typing import List, Tuple

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.universal_apk_installer_subagent import UniversalMultiStageInstallerSubagent
from core.universal_apk_installer_engine import UniversalAPKInstallerEngine


class FakeMultiStageADB:
    """Mock ADB wrapper that sequences through multi-stage XML screens and records taps."""

    def __init__(self, xml_screens: List[str]):
        self.xml_screens = list(xml_screens)
        self.current_idx = 0
        self.taps: List[Tuple[int, int]] = []
        self.serial = "10ECBH26JJ000D2"

    def dump_ui_hierarchy(self, serial: str = "10ECBH26JJ000D2") -> str:
        if not self.xml_screens:
            return ""
        idx = min(self.current_idx, len(self.xml_screens) - 1)
        xml = self.xml_screens[idx]
        if self.current_idx < len(self.xml_screens) - 1:
            self.current_idx += 1
        return xml

    def tap(self, serial_or_x: int, x_or_y: int, y_opt: int = None) -> None:
        if y_opt is not None:
            self.taps.append((int(x_or_y), int(y_opt)))
        else:
            self.taps.append((int(serial_or_x), int(x_or_y)))


def test_vivo_originos_package_intercept_nfd_and_spatial_guard():
    """
    Scenario 1:
    Vivo OriginOS PackageInterceptActivity XML with NFD Vietnamese text,
    top toolbar 'Cài đặt' trap at y=236, unchecked 'deleted_file_state_cb',
    and bottom 'Tiếp tục cài đặt' (android:id/button1).
    """
    engine = UniversalAPKInstallerEngine()

    # Convert Vietnamese strings to decomposed NFD to verify NFC normalization
    nfd_top_title = unicodedata.normalize("NFD", "Cài đặt")
    nfd_cb_text = unicodedata.normalize("NFD", "Tôi đã hiểu kết quả phát hiện rủi ro")
    nfd_cancel = unicodedata.normalize("NFD", "Hủy")
    nfd_continue = unicodedata.normalize("NFD", "Tiếp tục cài đặt")

    xml_str = f"""<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
    <hierarchy rotation="0">
      <node index="0" package="com.android.packageinstaller" class="android.widget.FrameLayout" bounds="[0,0][1260,2800]">
        <!-- Top toolbar 'Cài đặt' trap at center_y = 236 (top 20% of 2800 is 560) -->
        <node index="1" text="{nfd_top_title}" resource-id="com.android.packageinstaller:id/toolbar_title"
              class="android.widget.TextView" clickable="true" bounds="[100,196][400,276]" />
        <!-- Unchecked Vivo risk checkbox -->
        <node index="2" text="{nfd_cb_text}" resource-id="com.android.packageinstaller:id/deleted_file_state_cb"
              class="android.widget.CheckBox" checkable="true" checked="false" clickable="true"
              bounds="[84,2380][1176,2480]" />
        <!-- Negative trap Cancel button -->
        <node index="3" text="{nfd_cancel}" resource-id="android:id/button2"
              class="android.widget.Button" clickable="true" bounds="[84,2520][600,2660]" />
        <!-- Primary bottom confirm button -->
        <node index="4" text="{nfd_continue}" resource-id="android:id/button1"
              class="android.widget.Button" clickable="true" bounds="[660,2520][1176,2660]" />
      </node>
    </hierarchy>
    """

    plan = engine.analyze_installer_hierarchy(xml_str, screen_width=1260, screen_height=2800)

    assert plan["stage"] == "checkbox_required"
    assert plan["checkbox_to_tick"] is not None
    assert plan["checkbox_to_tick"]["resource_id"] == "com.android.packageinstaller:id/deleted_file_state_cb"
    assert plan["checkbox_to_tick"]["center_y"] == 2430

    # Action button must be the bottom 'Tiếp tục cài đặt' button1, never the top y=236 'Cài đặt' or 'Hủy'
    assert plan["action_button"] is not None
    assert plan["action_button"]["resource_id"] == "android:id/button1"
    assert plan["action_button"]["center_x"] == 918
    assert plan["action_button"]["center_y"] == 2590

    # Verify both the top toolbar trap (y=236) and 'Hủy' were filtered into traps_filtered
    filtered_labels = [t["text"] for t in plan["traps_filtered"]]
    assert "Cài đặt" in filtered_labels
    assert "Hủy" in filtered_labels


def test_dark_pattern_v_appstore_and_expander_chi_tiet_khac():
    """
    Scenario 2:
    Dark-pattern dialog where 'Mở V-Appstore', 'Cài đặt an toàn', and 'Hủy' are prominent
    and 'Vẫn cài đặt' is hidden behind 'Chi tiết khác'.
    """
    engine = UniversalAPKInstallerEngine()

    xml_stage_1 = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
    <hierarchy rotation="0">
      <node index="0" package="com.vivo.secime" class="android.widget.FrameLayout" bounds="[0,0][1260,2800]">
        <node index="1" text="Mở V-Appstore" resource-id="com.vivo.secime:id/btn_recommend"
              class="android.widget.Button" clickable="true" bounds="[100,1900][1160,2040]" />
        <node index="2" text="Cài đặt an toàn" resource-id="com.vivo.secime:id/btn_safe_install"
              class="android.widget.Button" clickable="true" bounds="[100,2080][1160,2220]" />
        <node index="3" text="Hủy" resource-id="com.vivo.secime:id/btn_cancel"
              class="android.widget.Button" clickable="true" bounds="[100,2260][1160,2400]" />
        <node index="4" text="Chi tiết khác" resource-id="com.vivo.secime:id/tv_more_details"
              class="android.widget.TextView" clickable="true" bounds="[450,2480][810,2560]" />
      </node>
    </hierarchy>
    """

    plan_1 = engine.analyze_installer_hierarchy(xml_stage_1, screen_width=1260, screen_height=2800)
    assert plan_1["stage"] == "expander_required"
    assert plan_1["action_button"] is not None
    assert plan_1["action_button"]["text"] == "Chi tiết khác"
    assert plan_1["action_button"]["center_x"] == 630
    assert plan_1["action_button"]["center_y"] == 2520
    assert len(plan_1["traps_filtered"]) == 3

    # Once 'Chi tiết khác' is clicked, 'Vẫn cài đặt' becomes visible alongside 'Mở V-Appstore'
    xml_stage_2 = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
    <hierarchy rotation="0">
      <node index="0" package="com.vivo.secime" class="android.widget.FrameLayout" bounds="[0,0][1260,2800]">
        <node index="1" text="Mở V-Appstore" resource-id="com.vivo.secime:id/btn_recommend"
              class="android.widget.Button" clickable="true" bounds="[100,1900][1160,2040]" />
        <node index="2" text="Vẫn cài đặt" resource-id="com.vivo.secime:id/btn_install_anyway"
              class="android.widget.TextView" clickable="true" bounds="[420,2500][840,2600]" />
      </node>
    </hierarchy>
    """

    plan_2 = engine.analyze_installer_hierarchy(xml_stage_2, screen_width=1260, screen_height=2800)
    assert plan_2["stage"] == "confirm_ready"
    assert plan_2["action_button"] is not None
    assert plan_2["action_button"]["text"] == "Vẫn cài đặt"


def test_countdown_timer_detection():
    """
    Scenario 3:
    Countdown timer button 'Tiếp tục (5s)' detection and regex parser variants.
    """
    engine = UniversalAPKInstallerEngine()

    assert engine.detect_countdown_seconds("Tiếp tục (5s)") == 5
    assert engine.detect_countdown_seconds("Chấp nhận (10 giây)") == 10
    assert engine.detect_countdown_seconds("Install anyway [3s]") == 3
    assert engine.detect_countdown_seconds("Tiếp tục 7s") == 7
    assert engine.detect_countdown_seconds("Tiếp tục cài đặt") == 0

    xml_countdown = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
    <hierarchy rotation="0">
      <node index="0" package="com.miui.securitycenter" class="android.widget.FrameLayout" bounds="[0,0][1260,2800]">
        <node index="1" text="Từ chối" resource-id="com.miui.securitycenter:id/btn_deny"
              class="android.widget.Button" clickable="true" bounds="[80,2400][600,2560]" />
        <node index="2" text="Tiếp tục (5s)" resource-id="com.miui.securitycenter:id/btn_accept"
              class="android.widget.Button" clickable="true" bounds="[660,2400][1180,2560]" />
      </node>
    </hierarchy>
    """

    plan = engine.analyze_installer_hierarchy(xml_countdown, screen_width=1260, screen_height=2800)
    assert plan["stage"] == "countdown_waiting"
    assert plan["countdown_seconds"] == 5
    assert plan["action_button"] is not None
    assert plan["action_button"]["text"] == "Tiếp tục (5s)"
    assert len(plan["traps_filtered"]) == 1
    assert plan["traps_filtered"][0]["text"] == "Từ chối"


def test_post_install_completion_screen_done_vs_open():
    """
    Scenario 4:
    Post-install completion screen choosing 'Xong' ('Done') or 'Mở' ('Open').
    """
    engine = UniversalAPKInstallerEngine()

    xml_completed = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
    <hierarchy rotation="0">
      <node index="0" package="com.android.packageinstaller" class="android.widget.FrameLayout" bounds="[0,0][1260,2800]">
        <node index="1" text="Xong" resource-id="com.android.packageinstaller:id/done_button"
              class="android.widget.Button" clickable="true" bounds="[80,2480][600,2640]" />
        <node index="2" text="Mở" resource-id="com.android.packageinstaller:id/launch_button"
              class="android.widget.Button" clickable="true" bounds="[660,2480][1180,2640]" />
      </node>
    </hierarchy>
    """

    plan_done = engine.analyze_installer_hierarchy(
        xml_completed, screen_width=1260, screen_height=2800, prefer_done_over_open=True
    )
    assert plan_done["stage"] == "install_completed"
    assert plan_done["action_button"]["text"] == "Xong"
    assert plan_done["action_button"]["center_x"] == 340

    plan_open = engine.analyze_installer_hierarchy(
        xml_completed, screen_width=1260, screen_height=2800, prefer_done_over_open=False
    )
    assert plan_open["stage"] == "install_completed"
    assert plan_open["action_button"]["text"] == "Mở"
    assert plan_open["action_button"]["center_x"] == 920


def test_subagent_46_multi_stage_execution_pipeline():
    """
    End-to-end verification of Subagent #46 (UniversalMultiStageInstallerSubagent)
    across a 3-stage install flow:
      Stage 1 -> Expander 'Chi tiết khác'
      Stage 2 -> Risk checkbox + 'Tiếp tục cài đặt'
      Stage 3 -> Completion 'Xong'
    """
    xml_1 = """<hierarchy><node bounds="[0,0][1260,2800]">
      <node text="Mở V-Appstore" bounds="[100,1900][1160,2040]" />
      <node text="Chi tiết khác" bounds="[450,2480][810,2560]" />
    </node></hierarchy>"""

    xml_2 = """<hierarchy><node bounds="[0,0][1260,2800]">
      <node text="Tôi đã hiểu" resource-id="com.android.packageinstaller:id/deleted_file_state_cb"
            class="android.widget.CheckBox" checkable="true" checked="false" bounds="[84,2380][1176,2480]" />
      <node text="Tiếp tục cài đặt" resource-id="android:id/button1" bounds="[660,2520][1176,2660]" />
    </node></hierarchy>"""

    xml_3 = """<hierarchy><node bounds="[0,0][1260,2800]">
      <node text="Xong" bounds="[80,2480][600,2640]" />
      <node text="Mở" bounds="[660,2480][1180,2640]" />
    </node></hierarchy>"""

    fake_adb = FakeMultiStageADB([xml_1, xml_2, xml_3])
    subagent = UniversalMultiStageInstallerSubagent(adb_wrapper=fake_adb)

    res = subagent.install_apk_universal("nonexistent_mock_test.apk", timeout_sec=5.0)
    assert res["success"] is True
    assert res["subagent_id"] == 46
    assert len(res["steps"]) == 3
    assert res["steps"][0]["stage"] == "expander_required"
    assert res["steps"][1]["stage"] == "checkbox_required"
    assert res["steps"][2]["stage"] == "install_completed"

    status = subagent.get_status()
    assert status["subagent_id"] == 46
    assert status["checkboxes_ticked"] == 1
    assert status["traps_blocked"] >= 1
    assert status["zero_ai_tokens"] is True
