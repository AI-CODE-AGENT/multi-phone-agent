"""
Unit tests for Feature #42 (Subagent #42: Keyboard & Viewport Auto-Guard Engine)
in `core/keyboard_viewport_guard.py` and `agents/keyboard_viewport_guard_subagent.py`.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.keyboard_viewport_guard_subagent import KeyboardAndViewportGuardSubagent
from core.keyboard_viewport_guard import KeyboardAndViewportGuard


class FakeADB:
    """Deterministic mock ADB wrapper for testing IME & Chrome focus commands."""

    def __init__(self, responses: List[str] = None):
        self.responses = list(responses or [])
        self.commands: List[str] = []

    def shell(self, serial: str, cmd: str, timeout: float = 5.0) -> str:
        self.commands.append(cmd)
        if self.responses:
            return self.responses.pop(0)
        return ""


class FakeCDPBridge:
    """Deterministic mock CDP bridge for testing background socket recovery and JS evaluation."""

    def __init__(self):
        self.active_forwards: Dict[str, int] = {}
        self.forward_calls: List[Dict[str, Any]] = []
        self.evaluated_expressions: List[str] = []

    def forward_socket(
        self,
        serial: str,
        local_port: int = 9229,
        socket_name: str = "chrome_devtools_remote",
    ) -> bool:
        self.forward_calls.append(
            {"serial": serial, "local_port": local_port, "socket_name": socket_name}
        )
        self.active_forwards[f"{serial}:{socket_name}"] = local_port
        return True

    def list_open_tabs(self, local_port: int = 9229, mock_tabs_response=None):
        return [
            {
                "id": "TAB_1",
                "title": "Desktop Overflow Form",
                "url": "https://example.com/form",
                "webSocketDebuggerUrl": f"ws://127.0.0.1:{local_port}/devtools/page/TAB_1",
            }
        ]

    def evaluate_js(self, ws_url: str, expression: str, timeout: float = 5.0) -> Dict[str, Any]:
        self.evaluated_expressions.append(expression)
        return {
            "found": True,
            "selector": "button, input[type='submit']",
            "tag_name": "button",
            "id": "validate-btn",
            "text": "Validate",
            "was_offscreen": True,
            "horizontal_overflow": True,
            "scrolled_into_view": True,
            "scroll_strategy": "el.scrollIntoView({behavior: 'instant', block: 'center', inline: 'center'})",
            "css_rect": {
                "left": 150.0,
                "top": 350.0,
                "width": 120.0,
                "height": 48.0,
                "right": 270.0,
                "bottom": 398.0,
            },
            "viewport_metrics": {
                "devicePixelRatio": 3.0,
                "innerWidth": 420.0,
                "innerHeight": 820.0,
                "outerWidth": 420.0,
                "outerHeight": 933.0,
                "scrollWidth": 1024.0,
                "scrollHeight": 1800.0,
                "visualViewportOffsetLeft": 0.0,
                "visualViewportOffsetTop": 0.0,
                "visualViewportScale": 1.0,
                "pageXOffset": 310.0,
                "pageYOffset": 240.0,
                "webdriver": False,
            },
        }

    def css_rect_to_physical_coords(
        self,
        css_rect: Dict[str, float],
        viewport_metrics: Dict[str, Any],
        screen_size=(1260, 2800),
    ) -> Dict[str, Any]:
        dpr = float(viewport_metrics.get("devicePixelRatio", 3.0))
        cx = (float(css_rect.get("left", 0.0)) + float(css_rect.get("width", 0.0)) / 2.0) * dpr
        cy = (float(css_rect.get("top", 0.0)) + float(css_rect.get("height", 0.0)) / 2.0) * dpr + 340
        return {
            "phys_x": int(round(cx)),
            "phys_y": int(round(cy)),
            "bounds": (
                int(round(float(css_rect.get("left", 0.0)) * dpr)),
                int(round(float(css_rect.get("top", 0.0)) * dpr + 340)),
                int(round(float(css_rect.get("right", 0.0)) * dpr)),
                int(round(float(css_rect.get("bottom", 0.0)) * dpr + 340)),
            ),
        }


def test_detect_ime_keyboard_state_shown_and_hidden():
    guard = KeyboardAndViewportGuard(adb=FakeADB())

    # 1. mInputShown=true without explicit frame bounds -> defaults to 1120px on 1260x2800
    raw_shown_default = "  mInputShown=true mIsInputViewShown=true"
    state_shown = guard.detect_ime_keyboard_state(
        serial="10CF5L0TYL00312",
        raw_dumpsys_override=raw_shown_default,
    )
    assert state_shown["ime_visible"] is True
    assert state_shown["keyboard_height_px"] == 1120
    assert state_shown["safe_visible_y_max"] == 1680
    assert state_shown["tokens_used"] == 0

    # 2. mInputShown=true with explicit mVisibleFrame bounds
    raw_shown_frame = "  mInputShown=true\n  mVisibleFrame=[0,1700][1260,2800]"
    state_framed = guard.detect_ime_keyboard_state(
        serial="10CF5L0TYL00312",
        raw_dumpsys_override=raw_shown_frame,
    )
    assert state_framed["ime_visible"] is True
    assert state_framed["keyboard_height_px"] == 1100
    assert state_framed["safe_visible_y_max"] == 1700
    assert state_framed["tokens_used"] == 0

    # 3. mInputShown=false -> keyboard_height_px == 0, safe_visible_y_max == 2800
    raw_hidden = "  mInputShown=false mIsInputViewShown=false mVisibleFrame=[0,2800][1260,2800]"
    state_hidden = guard.detect_ime_keyboard_state(
        serial="10CF5L0TYL00312",
        raw_dumpsys_override=raw_hidden,
    )
    assert state_hidden["ime_visible"] is False
    assert state_hidden["keyboard_height_px"] == 0
    assert state_hidden["safe_visible_y_max"] == 2800
    assert state_hidden["tokens_used"] == 0


def test_compensate_coordinates_for_ime_occlusion_on_1260x2800():
    guard = KeyboardAndViewportGuard(adb=FakeADB())
    ime_open_state = guard.detect_ime_keyboard_state(
        serial="10CF5L0TYL00312",
        raw_dumpsys_override="mInputShown=true",
    )
    assert ime_open_state["safe_visible_y_max"] == 1680

    # Target at y=2200 is occluded by the open soft keyboard (2200 > 1680)
    res_occluded = guard.compensate_coordinates_for_ime(
        x=400,
        y=2200,
        ime_state=ime_open_state,
        screen_size=(1260, 2800),
    )
    assert res_occluded["occluded"] is True
    assert res_occluded["action_needed"] == "dismiss_keyboard_first"
    assert res_occluded["adjusted_x"] == 400
    assert res_occluded["safe_visible_y_max"] == 1680
    assert res_occluded["tokens_used"] == 0

    # Shift mode returns action_needed="shift_y" and shifts Y above 1680
    res_shifted = guard.compensate_coordinates_for_ime(
        x=400,
        y=2200,
        ime_state=ime_open_state,
        screen_size=(1260, 2800),
        prefer_shift=True,
    )
    assert res_shifted["occluded"] is True
    assert res_shifted["action_needed"] == "shift_y"
    assert res_shifted["adjusted_y"] <= 1680
    assert res_shifted["tokens_used"] == 0

    # Target at y=1100 is above the keyboard (1100 <= 1680) -> not occluded
    res_safe = guard.compensate_coordinates_for_ime(
        x=400,
        y=1100,
        ime_state=ime_open_state,
        screen_size=(1260, 2800),
    )
    assert res_safe["occluded"] is False
    assert res_safe["action_needed"] == "none"
    assert res_safe["adjusted_x"] == 400
    assert res_safe["adjusted_y"] == 1100
    assert res_safe["tokens_used"] == 0


def test_dismiss_soft_keyboard_safely_and_viewport_centering():
    # Simulate IME initially open, then closed after `input keyevent 4`
    fake_adb = FakeADB(
        responses=[
            "mInputShown=true mVisibleFrame=[0,1680][1260,2800]",
            "",  # output of input keyevent 4
            "mInputShown=false",
            # Responses for normalize_web_viewport_and_scroll_to_element:
            "mCurrentFocus=Window{111 u0 com.vivo.launcher/com.vivo.launcher.Main}",
            "Starting: Intent { cmp=com.android.chrome/com.google.android.apps.chrome.Main }",
        ]
    )
    fake_cdp = FakeCDPBridge()
    guard = KeyboardAndViewportGuard(adb=fake_adb, cdp_bridge=fake_cdp)

    dismiss_res = guard.dismiss_soft_keyboard_safely(serial="10CF5L0TYL00312", dry_run=False)
    assert dismiss_res["status"] == "IME_DISMISSED"
    assert dismiss_res["was_visible"] is True
    assert dismiss_res["ime_visible_after"] is False
    assert "input keyevent 4" in dismiss_res["commands_sent"]
    assert dismiss_res["tokens_used"] == 0

    viewport_res = guard.normalize_web_viewport_and_scroll_to_element(
        serial="10CF5L0TYL00312",
        selector="button, input[type='submit']",
        cdp_bridge=fake_cdp,
        dry_run=False,
    )
    assert viewport_res["status"] == "VIEWPORT_NORMALIZED_AND_CENTERED"
    assert viewport_res["chrome_focused"] is True
    assert viewport_res["socket_rebound"] is True
    assert viewport_res["scrolled_into_view"] is True
    assert viewport_res["phys_x"] == 630
    assert viewport_res["phys_y"] == 1462
    assert viewport_res["tokens_used"] == 0
    assert any(
        "scrollIntoView({behavior: 'instant', block: 'center', inline: 'center'})" in expr
        for expr in fake_cdp.evaluated_expressions
    )


def test_subagent_42_guard_input_and_viewport_dry_run():
    subagent = KeyboardAndViewportGuardSubagent(adb=FakeADB(), cdp_bridge=FakeCDPBridge())
    assert subagent.SUBAGENT_ID == 42
    assert subagent.SUBAGENT_NAME == "KeyboardAndViewportGuardSubagent"

    report = subagent.guard_input_and_viewport(
        serial="10CF5L0TYL00312",
        target_x=400,
        target_y=2200,
        dry_run=True,
    )
    assert report["status"] == "INPUT_AND_VIEWPORT_GUARDED"
    assert report["subagent_id"] == 42
    assert report["subagent_name"] == "KeyboardAndViewportGuardSubagent"
    assert report["ime_state"]["ime_visible"] is True
    assert report["ime_state"]["safe_visible_y_max"] == 1680
    assert report["compensation"]["occluded"] is True
    assert report["dismiss_result"]["status"] == "IME_DISMISSED"
    assert report["viewport_result"]["status"] == "VIEWPORT_NORMALIZED_AND_CENTERED"
    assert report["phys_x"] > 0
    assert report["phys_y"] > 0
    assert report["tokens_used"] == 0
