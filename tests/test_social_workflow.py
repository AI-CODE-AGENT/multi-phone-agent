"""
Unit & Integration Tests for Proposal 4: Multi-App Social & Trust-Building Workflow Engine
(Subagent #39: `SocialWorkflowSubagent` and `SocialWorkflowEngine`).

Tests:
1. Proportional resolution scaling of TikTok workflow coordinates across `1260x2800`
   (Vivo V2417A `10CF5L0TYL00312`) and `1080x2400`.
2. Full execution of `run_tiktok_account_switch_and_engage` in `dry_run=True` mode
   verifying all 6 steps and `tokens_used == 0`.
3. Full execution of `run_full_11_website_captcha_patrol` in `dry_run=True` mode
   verifying all 11+ benchmark URLs are processed with `tokens_used == 0`.
4. `SocialWorkflowSubagent` (Subagent #39) orchestration and mocked ADB command execution.
"""

import sys
from pathlib import Path
from typing import Any, List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.social_workflow_subagent import SocialWorkflowSubagent
from core.social_workflow_engine import SocialWorkflowEngine


class DummyADB:
    """Mock ADBWrapper that records all shell and text commands without hardware delay."""

    def __init__(self, width: int = 1260, height: int = 2800):
        self.width = width
        self.height = height
        self.commands: List[str] = []
        self.typed_texts: List[str] = []

    def shell(self, serial: str, cmd: str, timeout: int = 10) -> str:
        self.commands.append(cmd)
        if cmd.strip() == "wm size":
            return f"Physical size: {self.width}x{self.height}"
        return "OK"

    def input_text(self, serial: str, text: str) -> str:
        self.typed_texts.append(text)
        return "OK"


def test_tiktok_coordinate_scaling_1260x2800_and_1080x2400():
    """
    Verify exact Vivo V2417A `1260x2800` calibrated points and proportional scaling
    to `1080x2400`.
    """
    coords_1260 = SocialWorkflowEngine.get_tiktok_coordinates_for_resolution(1260, 2800)
    assert coords_1260["profile_tab"] == (1134, 2688)
    assert coords_1260["target_account_row"] == (450, 2400)
    assert coords_1260["top_right_search"] == (1160, 240)
    assert coords_1260["top_video_result"] == (300, 1400)
    assert coords_1260["comment_bar"] == (400, 2700)
    assert coords_1260["pink_send_button"] == (1125, 1700)

    coords_1080 = SocialWorkflowEngine.get_tiktok_coordinates_for_resolution(1080, 2400)
    # 1080 / 1260 = 6/7, 2400 / 2800 = 6/7
    assert coords_1080["profile_tab"] == (
        round(1134 * 1080 / 1260),
        round(2688 * 2400 / 2800),
    )
    assert coords_1080["profile_tab"] == (972, 2304)
    assert coords_1080["target_account_row"] == (
        round(450 * 1080 / 1260),
        round(2400 * 2400 / 2800),
    )
    assert coords_1080["top_right_search"] == (
        round(1160 * 1080 / 1260),
        round(240 * 2400 / 2800),
    )
    assert coords_1080["top_video_result"] == (
        round(300 * 1080 / 1260),
        round(1400 * 2400 / 2800),
    )
    assert coords_1080["comment_bar"] == (
        round(400 * 1080 / 1260),
        round(2700 * 2400 / 2800),
    )
    assert coords_1080["pink_send_button"] == (
        round(1125 * 1080 / 1260),
        round(1700 * 2400 / 2800),
    )


def test_run_tiktok_account_switch_and_engage_dry_run():
    """
    Verify full 6-step execution of `run_tiktok_account_switch_and_engage` in
    `dry_run=True` mode with `tokens_used == 0`.
    """
    engine = SocialWorkflowEngine(adb=DummyADB(1260, 2800))
    res = engine.run_tiktok_account_switch_and_engage(
        serial="10CF5L0TYL00312",
        target_account="nht.tn472",
        search_query="tra dang",
        comment_text="dinh quaa",
        dry_run=True,
    )

    assert res["status"] == "TIKTOK_WORKFLOW_COMPLETED"
    assert res["serial"] == "10CF5L0TYL00312"
    assert res["package"] == "com.ss.android.ugc.trill"
    assert res["resolution"] == "1260x2800"
    assert res["steps_completed"] == 6
    assert res["steps_total"] == 6
    assert res["tokens_used"] == 0

    steps = res["steps_trace"]
    assert len(steps) == 6
    for idx, step_info in enumerate(steps, start=1):
        assert step_info["step"] == idx
        assert step_info["status"] == "COMPLETED"
        assert step_info["tokens_used"] == 0
        assert "timestamp" in step_info

    # Verify step details match specification
    assert steps[0]["package"] == "com.ss.android.ugc.trill"
    assert steps[1]["profile_tab_coords"] == [1134, 2688]
    assert steps[1]["target_account"] == "nht.tn472"
    assert steps[1]["target_account_calibrated_coords"] == [450, 2400]
    assert steps[2]["search_icon_coords"] == [1160, 240]
    assert steps[2]["search_query"] == "tra dang"
    assert steps[2]["enter_keyevent"] == 66
    assert steps[3]["video_result_coords"] == [300, 1400]
    assert 1.5 <= steps[3]["simulated_watch_seconds"] <= 3.0
    assert steps[4]["heart_state_verified"] is True
    assert steps[5]["comment_bar_coords"] == [400, 2700]
    assert steps[5]["comment_text"] == "dinh quaa"
    assert steps[5]["pink_send_button_coords"] == [1125, 1700]
    assert steps[5]["dismiss_keyboard_keyevent"] == 4
    assert steps[5]["exit_home_keyevent"] == 3


def test_run_full_11_website_captcha_patrol_dry_run():
    """
    Verify `run_full_11_website_captcha_patrol` in `dry_run=True` mode processes all
    11+ required benchmark URLs with `tokens_used == 0`.
    """
    engine = SocialWorkflowEngine(adb=DummyADB(1260, 2800))
    res = engine.run_full_11_website_captcha_patrol(
        serial="10CF5L0TYL00312",
        dry_run=True,
    )

    assert res["status"] == "CAPTCHA_PATROL_COMPLETED"
    assert res["tokens_used"] == 0
    assert res["websites_total"] >= 11
    assert res["websites_solved"] == res["websites_total"]

    required_11_urls = [
        "https://2captcha.com/demo/recaptcha-v2",
        "https://2captcha.com/demo/geetest",
        "https://2captcha.com/demo/cloudflare-turnstile",
        "https://2captcha.com/demo/rotate",
        "https://anti-captcha.com/demo",
        "https://capsolver.com/demo",
        "https://www.google.com/recaptcha/api2/demo",
        "https://accounts.hcaptcha.com/demo",
        "https://www.geetest.com/en/demo",
        "https://captcha.com/demos/features/captcha-demo.aspx",
        "https://bot.sannysoft.com",
    ]
    patrolled_urls = [item["url"] for item in res["results"]]
    for expected_url in required_11_urls:
        assert expected_url in patrolled_urls

    for item in res["results"]:
        assert item["solved"] is True
        assert item["tokens_used"] == 0
        assert any("am start -a android.intent.action.VIEW -d" in act for act in item["actions"])


def test_social_workflow_subagent_39_and_mocked_live_execution():
    """
    Verify `SocialWorkflowSubagent` (Subagent #39) orchestrates both workflows and
    executes ADB commands when `dry_run=False` against a mocked ADB wrapper.
    """
    dummy_adb = DummyADB(1080, 2400)
    subagent = SocialWorkflowSubagent(adb=dummy_adb)

    combined = subagent.execute_combined_social_and_captcha_workflow(
        serial="10CF5L0TYL00312",
        dry_run=True,
    )
    assert combined["status"] == "COMBINED_SOCIAL_AND_CAPTCHA_COMPLETED"
    assert combined["subagent_id"] == 39
    assert combined["tokens_used"] == 0
    assert combined["tiktok_workflow"]["steps_completed"] == 6
    assert combined["captcha_patrol"]["websites_total"] >= 11

    # Also verify non-dry-run path against DummyADB for 2 sample URLs
    patrol_live = subagent.run_full_11_website_captcha_patrol(
        serial="emulator-5554",
        websites=[
            "https://2captcha.com/demo/geetest",
            "https://captcha.com/demos/features/captcha-demo.aspx",
        ],
        dry_run=False,
    )
    assert patrol_live["websites_solved"] == 2
    assert patrol_live["tokens_used"] == 0
    assert any("input keyevent 4" in cmd for cmd in dummy_adb.commands)


def test_tiktok_live_mocked_execution_and_xml_grounding():
    """
    Verify `run_tiktok_account_switch_and_engage` in `dry_run=False` mode with mocked
    ADB commands and XML target account resolution, confirming `keyevent 66`, `keyevent 4`,
    and `keyevent 3` are issued with `tokens_used == 0`.
    """
    dummy_adb = DummyADB(1260, 2800)
    engine = SocialWorkflowEngine(adb=dummy_adb)
    res = engine.run_tiktok_account_switch_and_engage(
        serial="10CF5L0TYL00312",
        target_account="nht.tn472",
        search_query="tra dang",
        comment_text="dinh quaa",
        dry_run=False,
    )
    assert res["status"] == "TIKTOK_WORKFLOW_COMPLETED"
    assert res["steps_completed"] == 6
    assert res["tokens_used"] == 0
    assert any("com.ss.android.ugc.trill" in cmd for cmd in dummy_adb.commands)
    assert any("input keyevent 66" in cmd for cmd in dummy_adb.commands)
    assert any("input keyevent 4" in cmd for cmd in dummy_adb.commands)
    assert any("input keyevent 3" in cmd for cmd in dummy_adb.commands)
    assert "".join(dummy_adb.typed_texts) == "tra dangdinh quaa"

