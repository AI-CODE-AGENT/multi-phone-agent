"""
Unit Tests for Proposal 2: Subagent #37 (Action Macro Recorder & Self-Caching Replay Engine)
Tests:
1. Recording steps with XML hierarchy attribute extraction + 120x120 screen image template cropping.
2. Saving and loading macros from disk + built-in zero-token macros (`tiktok_switch_and_interact`, `vivo_dismiss_usb_install`).
3. Hybrid 3-Stage Resolution Strategy (0 AI Tokens):
   - Stage 1: Poco XML node match (`strategy="poco_xml"`).
   - Stage 2: Airtest Visual Template match when button shifts position by 80px (`strategy="visual_template"`), plus cross-resolution template scaling.
   - Stage 3: Relative coordinate scaling across Vivo `1260x2800` -> Emulator `1080x2400` (`strategy="relative_scale"`).
4. Full macro replay in `dry_run=True` mode and mocked `HumanTouchEngine` mode confirming `tokens_used == 0`.
"""

import os
import shutil
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.macro_replay_subagent import MacroReplaySubagent
from core.macro_recorder_engine import MacroRecorderEngine, MacroStep, VisualTemplate


@pytest.fixture
def tmp_path():
    """Provide a clean temporary directory under scratch/ to avoid Windows Temp permission locks."""
    base = Path(__file__).resolve().parent.parent / "scratch" / f"test_macros_{uuid.uuid4().hex[:8]}"
    base.mkdir(parents=True, exist_ok=True)
    yield base
    shutil.rmtree(base, ignore_errors=True)


def _create_screen_with_button(
    width: int = 1260,
    height: int = 2800,
    btn_center_x: int = 630,
    btn_center_y: int = 1400,
    btn_w: int = 100,
    btn_h: int = 80,
) -> Image.Image:
    """Create a synthetic screen with a distinctive patterned button centered at (btn_center_x, btn_center_y)."""
    img = Image.new("RGB", (width, height), color=(240, 242, 245))
    draw = ImageDraw.Draw(img)

    x1 = btn_center_x - btn_w // 2
    y1 = btn_center_y - btn_h // 2
    x2 = btn_center_x + btn_w // 2
    y2 = btn_center_y + btn_h // 2

    # Outer button frame
    draw.rectangle([x1, y1, x2, y2], fill=(20, 30, 180), outline=(10, 15, 90), width=4)
    # Distinctive inner crosshair & concentric boxes for unambiguous NCC peak
    draw.rectangle([x1 + 14, y1 + 12, x2 - 14, y2 - 12], fill=(250, 200, 30), outline=(255, 255, 255), width=3)
    draw.line([btn_center_x - 30, btn_center_y, btn_center_x + 30, btn_center_y], fill=(15, 20, 25), width=5)
    draw.line([btn_center_x, btn_center_y - 24, btn_center_x, btn_center_y + 24], fill=(15, 20, 25), width=5)
    draw.ellipse([btn_center_x - 10, btn_center_y - 10, btn_center_x + 10, btn_center_y + 10], fill=(220, 38, 38))
    return img


SAMPLE_XML_VIVO = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout" bounds="[0,0][1260,2800]">
    <node index="1" text="Tiếp tục cài đặt" resource-id="vivo:id/continue_button" class="android.widget.Button" content-desc="Cho phép cài đặt qua USB" clickable="true" bounds="[330,2380][930,2540]" />
    <node index="2" text="Submit Action" resource-id="com.app:id/btn_submit" class="android.widget.Button" content-desc="Submit Form" clickable="true" bounds="[580,1360][680,1440]" />
  </node>
</hierarchy>
"""


def test_record_step_extracts_xml_and_crops_120x120_template(tmp_path: Path):
    engine = MacroRecorderEngine(macros_dir=tmp_path)
    engine.start_recording("login_flow", resolution=(1260, 2800))

    screen_img = _create_screen_with_button(1260, 2800, btn_center_x=630, btn_center_y=1400)
    step = engine.record_step(
        action_type="tap",
        x=630,
        y=1400,
        screen_image=screen_img,
        xml_dump=SAMPLE_XML_VIVO,
    )

    assert step.step_id == 1
    assert step.action_type == "tap"
    assert step.poco_selector["resource_id"] == "com.app:id/btn_submit"
    assert step.poco_selector["text"] == "Submit Action"
    assert step.poco_selector["content_desc"] == "Submit Form"
    assert step.poco_selector["class_name"] == "android.widget.Button"

    assert step.visual_template is not None
    assert os.path.exists(step.visual_template.tpl_path)
    with Image.open(step.visual_template.tpl_path) as cropped_tpl:
        assert cropped_tpl.size == (120, 120)

    assert pytest.approx(step.relative_coords[0], rel=1e-4) == 630 / 1260.0
    assert pytest.approx(step.relative_coords[1], rel=1e-4) == 1400 / 2800.0


def test_save_and_load_macro_plus_builtin_macros(tmp_path: Path):
    engine = MacroRecorderEngine(macros_dir=tmp_path)
    builtins = engine.list_macros()
    assert "tiktok_switch_and_interact" in builtins
    assert "vivo_dismiss_usb_install" in builtins

    tiktok_macro = engine.load_macro("tiktok_switch_and_interact")
    assert tiktok_macro["tokens_used"] == 0
    assert len(tiktok_macro["steps"]) >= 3

    vivo_macro = engine.load_macro("vivo_dismiss_usb_install")
    assert vivo_macro["tokens_used"] == 0
    assert vivo_macro["steps"][0]["poco_selector"]["text"] == "Tiếp tục cài đặt"

    engine.start_recording("custom_checkout", resolution=(1260, 2800))
    engine.record_step("tap", x=630, y=2460, xml_dump=SAMPLE_XML_VIVO)
    engine.record_step("swipe", x=630, y=2000, end_x=630, y2=600)
    saved_path = engine.save_macro("custom_checkout")

    assert os.path.exists(saved_path)
    loaded = engine.load_macro("custom_checkout")
    assert loaded["macro_name"] == "custom_checkout"
    assert loaded["recorded_resolution"] == [1260, 2800]
    assert len(loaded["steps"]) == 2
    assert loaded["steps"][1]["action_type"] == "swipe"
    assert len(loaded["steps"][1]["relative_coords"]) == 4


def test_hybrid_3_stage_resolution_poco_visual_shifted_80px_and_relative_scaling(tmp_path: Path):
    engine = MacroRecorderEngine(macros_dir=tmp_path)
    engine.start_recording("hybrid_test", resolution=(1260, 2800))

    # Record at (630, 1400) on 1260x2800
    orig_screen = _create_screen_with_button(1260, 2800, btn_center_x=630, btn_center_y=1400)
    step = engine.record_step(
        action_type="tap",
        x=630,
        y=1400,
        screen_image=orig_screen,
        xml_dump=SAMPLE_XML_VIVO,
    )

    # --- STAGE 1: Poco XML Match (element moved in XML to [700,1500][800,1600] -> center (750, 1550)) ---
    shifted_xml = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
    <hierarchy rotation="0">
      <node index="0" text="Submit Action" resource-id="com.app:id/btn_submit" class="android.widget.Button" content-desc="Submit Form" bounds="[700,1500][800,1600]" />
    </hierarchy>
    """
    res_stage1 = engine.resolve_step_coordinates(
        step=step,
        target_resolution=(1260, 2800),
        current_screen=orig_screen,
        current_xml=shifted_xml,
    )
    assert res_stage1["strategy"] == "poco_xml"
    assert (res_stage1["x"], res_stage1["y"]) == (750, 1550)
    assert res_stage1["tokens_used"] == 0

    # --- STAGE 2: Visual Template Match when XML is unavailable and button shifted by +80px in X and -80px in Y ---
    shifted_x = 630 + 80  # 710
    shifted_y = 1400 - 80  # 1320
    shifted_screen = _create_screen_with_button(1260, 2800, btn_center_x=shifted_x, btn_center_y=shifted_y)

    res_stage2 = engine.resolve_step_coordinates(
        step=step,
        target_resolution=(1260, 2800),
        current_screen=shifted_screen,
        current_xml=None,
    )
    assert res_stage2["strategy"] == "visual_template"
    assert res_stage2["confidence"] >= 0.80
    assert abs(res_stage2["x"] - shifted_x) <= 2
    assert abs(res_stage2["y"] - shifted_y) <= 2
    assert res_stage2["tokens_used"] == 0

    # --- STAGE 3: Relative Resolution Scaling Fallback (Vivo 1260x2800 -> Emulator 1080x2400) ---
    res_stage3 = engine.resolve_step_coordinates(
        step=step,
        target_resolution=(1080, 2400),
        current_screen=None,
        current_xml=None,
    )
    assert res_stage3["strategy"] == "relative_scale"
    assert res_stage3["x"] == int(round((630 / 1260.0) * 1080))  # 540
    assert res_stage3["y"] == int(round((1400 / 2800.0) * 2400))  # 1200
    assert res_stage3["tokens_used"] == 0


def test_subagent_37_dry_run_and_mock_touch_replay_zero_tokens(tmp_path: Path):
    subagent = MacroReplaySubagent(macros_dir=tmp_path)

    # 1. Dry-run replay of built-in macro across Emulator resolution (1080x2400)
    dry_res = subagent.replay_macro(
        macro_name="tiktok_switch_and_interact",
        serial="emulator-5554",
        dry_run=True,
        target_resolution=(1080, 2400),
    )
    assert dry_res["status"] == "MACRO_REPLAY_OK"
    assert dry_res["tokens_used"] == 0
    assert dry_res["subagent_id"] == 37
    assert dry_res["steps_executed"] == 4
    assert all(s["tokens_used"] == 0 for s in dry_res["steps"])

    # Verify swipe coordinates scaled properly to 1080x2400
    swipe_step = dry_res["steps"][0]
    assert swipe_step["action_type"] == "swipe"
    assert swipe_step["x"] == int(round(0.50 * 1080))
    assert swipe_step["y"] == int(round(0.78 * 2400))
    assert swipe_step["end_y"] == int(round(0.22 * 2400))

    # 2. Live execution path with mocked HumanTouchEngine
    mock_touch = MagicMock()
    mock_touch.human_tap.return_value = {"status": "HUMAN_TAP_OK"}
    mock_touch.human_bezier_swipe.return_value = {"status": "HUMAN_SWIPE_OK"}

    live_res = subagent.replay_macro(
        macro_name="vivo_dismiss_usb_install",
        serial="10AC9C1285000CS",
        dry_run=False,
        touch_engine=mock_touch,
        target_resolution=(1260, 2800),
        current_xml=SAMPLE_XML_VIVO,
    )
    assert live_res["status"] == "MACRO_REPLAY_OK"
    assert live_res["tokens_used"] == 0
    assert live_res["steps"][0]["strategy"] == "poco_xml"
    assert (live_res["steps"][0]["x"], live_res["steps"][0]["y"]) == (630, 2460)
    assert mock_touch.human_tap.call_count == 2
