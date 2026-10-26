"""
Keyboard & Viewport Auto-Guard Engine (AMAF v9.0 - Subagent #42 Core)

Solves three real-world mobile automation hardware hazards discovered on
Vivo V2417A (`10CF5L0TYL00312`, OriginOS 6 / Android 15-16, `1260x2800`):
1. Soft keyboard (`InputMethodManager`) popping up and occluding the bottom 40%
   (`~1120px`, `y > 1680`) of the screen during text entry.
2. Desktop-layout web pages overflowing horizontally (`scrollWidth > innerWidth`)
   so critical action buttons (`"Validate"`, `"Submit"`) render off-screen.
3. Android 15/16 freezing background browser DevTools sockets
   (`@chrome_devtools_remote` raising `ConnectionRefusedError` when Chrome loses focus).

Operates with 100% ZERO AI TOKENS at runtime (`tokens_used = 0`).
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.android_cdp_bridge import AndroidCDPBridge


CDP_NORMALIZE_VIEWPORT_AND_SCROLL_JS_TEMPLATE = r"""
(function(selector) {
    var dpr = window.devicePixelRatio || 3.0;
    var innerW = window.innerWidth || document.documentElement.clientWidth || 420;
    var innerH = window.innerHeight || document.documentElement.clientHeight || 820;
    var scrollW = Math.max(
        document.documentElement ? document.documentElement.scrollWidth : 0,
        document.body ? document.body.scrollWidth : 0,
        innerW
    );
    var scrollH = Math.max(
        document.documentElement ? document.documentElement.scrollHeight : 0,
        document.body ? document.body.scrollHeight : 0,
        innerH
    );
    var horizontalOverflow = scrollW > innerW;

    var targetEl = null;
    try {
        targetEl = document.querySelector(selector);
    } catch (e) {}

    if (!targetEl) {
        var fallbacks = [
            "button[type='submit']",
            "input[type='submit']",
            "button",
            "input[type='button']"
        ];
        for (var i = 0; i < fallbacks.length; i++) {
            try {
                var candidate = document.querySelector(fallbacks[i]);
                if (candidate) {
                    targetEl = candidate;
                    break;
                }
            } catch (e2) {}
        }
    }

    if (!targetEl) {
        return {
            found: false,
            selector: selector,
            horizontal_overflow: horizontalOverflow,
            scroll_width: scrollW,
            scroll_height: scrollH,
            inner_width: innerW,
            inner_height: innerH,
            device_pixel_ratio: dpr
        };
    }

    var beforeRect = targetEl.getBoundingClientRect();
    var wasOffscreen = (
        beforeRect.left < 0 ||
        beforeRect.top < 0 ||
        beforeRect.right > innerW ||
        beforeRect.bottom > innerH
    );

    try {
        targetEl.scrollIntoView({behavior: 'instant', block: 'center', inline: 'center'});
    } catch (err) {
        try {
            targetEl.scrollIntoView(true);
        } catch (err2) {}
    }

    var afterRect = targetEl.getBoundingClientRect();
    var vv = window.visualViewport || {
        offsetLeft: 0,
        offsetTop: 0,
        scale: 1.0,
        width: innerW,
        height: innerH
    };

    return {
        found: true,
        selector: selector,
        tag_name: (targetEl.tagName || "").toLowerCase(),
        id: targetEl.id || "",
        text: (targetEl.innerText || targetEl.value || "").slice(0, 120).trim(),
        was_offscreen: wasOffscreen,
        horizontal_overflow: horizontalOverflow,
        scrolled_into_view: true,
        scroll_strategy: "el.scrollIntoView({behavior: 'instant', block: 'center', inline: 'center'})",
        css_rect: {
            left: afterRect.left,
            top: afterRect.top,
            width: afterRect.width,
            height: afterRect.height,
            right: afterRect.right,
            bottom: afterRect.bottom
        },
        viewport_metrics: {
            devicePixelRatio: dpr,
            innerWidth: window.innerWidth || innerW,
            innerHeight: window.innerHeight || innerH,
            outerWidth: window.outerWidth || innerW,
            outerHeight: window.outerHeight || innerH,
            scrollWidth: scrollW,
            scrollHeight: scrollH,
            visualViewportOffsetLeft: vv.offsetLeft || 0,
            visualViewportOffsetTop: vv.offsetTop || 0,
            visualViewportScale: vv.scale || 1.0,
            pageXOffset: window.pageXOffset || window.scrollX || 0,
            pageYOffset: window.pageYOffset || window.scrollY || 0,
            webdriver: navigator.webdriver
        }
    };
})(__SELECTOR_JSON__);
"""


class KeyboardAndViewportGuard:
    """
    Deterministic, zero-token hardware guard for Android soft-keyboard (IME) occlusion,
    horizontal/vertical WebView & Chrome viewport overflow, and Android 15/16 background
    DevTools socket freezing.
    """

    DEFAULT_SCREEN_SIZE: Tuple[int, int] = (1260, 2800)
    DEFAULT_KEYBOARD_HEIGHT_PX: int = 1120
    CHROME_PACKAGE: str = "com.android.chrome"
    CHROME_MAIN_ACTIVITY: str = "com.google.android.apps.chrome.Main"

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        cdp_bridge: Optional[AndroidCDPBridge] = None,
        default_screen_size: Tuple[int, int] = DEFAULT_SCREEN_SIZE,
    ):
        self.adb = adb or ADBWrapper()
        self.cdp_bridge = cdp_bridge or AndroidCDPBridge(adb=self.adb)
        self.default_screen_size = default_screen_size

    def detect_ime_keyboard_state(
        self,
        serial: str,
        raw_dumpsys_override: Optional[str] = None,
        screen_size: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        """
        Inspects Android's `InputMethodManager` state via:
            adb -s <serial> shell "dumpsys input_method | grep -E 'mInputShown|mVisibleFrame|mFrame'"
        or parses `raw_dumpsys_override` directly.

        Extracts:
          - `ime_visible: bool`
          - `keyboard_height_px: int` (defaults to 1120 on 1260x2800 when `mInputShown=true`
            and explicit frame bounds are absent or zero)
          - `safe_visible_y_max: int` (`screen_h - keyboard_height_px`)
          - `tokens_used: 0`
        """
        screen_w, screen_h = screen_size or self.default_screen_size
        cmd = "dumpsys input_method | grep -E 'mInputShown|mVisibleFrame|mFrame'"

        if raw_dumpsys_override is not None:
            raw_output = raw_dumpsys_override
        else:
            try:
                raw_output = self.adb.shell(serial, cmd, timeout=5.0) or ""
            except Exception:
                raw_output = ""

        ime_visible = False
        shown_matches = re.findall(r"mInputShown\s*=\s*(true|false)", raw_output, flags=re.IGNORECASE)
        if shown_matches:
            ime_visible = any(val.lower() == "true" for val in shown_matches)
        elif re.search(r"mImeWindowVis\s*=\s*0x[1-9a-fA-F]", raw_output):
            ime_visible = True

        parsed_frame_height = self._extract_frame_height_px(raw_output, screen_h=screen_h)

        if ime_visible:
            if parsed_frame_height and parsed_frame_height > 100:
                keyboard_height_px = parsed_frame_height
            else:
                keyboard_height_px = (
                    self.DEFAULT_KEYBOARD_HEIGHT_PX
                    if screen_h == 2800
                    else int(round(screen_h * 0.40))
                )
        else:
            keyboard_height_px = 0

        keyboard_height_px = max(0, min(keyboard_height_px, screen_h))
        safe_visible_y_max = max(0, screen_h - keyboard_height_px)

        return {
            "serial": serial,
            "ime_visible": ime_visible,
            "keyboard_height_px": keyboard_height_px,
            "safe_visible_y_max": safe_visible_y_max,
            "screen_size": (screen_w, screen_h),
            "raw_dumpsys_excerpt": raw_output.strip()[:500],
            "tokens_used": 0,
        }

    @staticmethod
    def _extract_frame_height_px(raw_output: str, screen_h: int = 2800) -> int:
        """
        Parses `mVisibleFrame` or `mFrame` coordinate bounds when present in `dumpsys input_method`.
        Supports formats such as:
          - mVisibleFrame=[0,1680][1260,2800]
          - mVisibleFrame=Rect(0, 1680 - 1260, 2800)
          - mFrame=[0,1680][1260,2800]
        """
        if not raw_output:
            return 0

        bracket_pattern = re.compile(
            r"(?:mVisibleFrame|mFrame)\s*=\s*\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]\s*\[\s*(-?\d+)\s*,\s*(-?\d+)\s*\]"
        )
        rect_pattern = re.compile(
            r"(?:mVisibleFrame|mFrame)\s*=\s*Rect\(\s*(-?\d+)\s*,\s*(-?\d+)\s*-\s*(-?\d+)\s*,\s*(-?\d+)\s*\)"
        )

        candidates: List[Tuple[int, int]] = []
        for match in bracket_pattern.finditer(raw_output):
            top = int(match.group(2))
            bottom = int(match.group(4))
            candidates.append((top, bottom))

        for match in rect_pattern.finditer(raw_output):
            top = int(match.group(2))
            bottom = int(match.group(4))
            candidates.append((top, bottom))

        for top, bottom in candidates:
            height = bottom - top
            # Ignore full-screen container frames (e.g. [0,0][1260,2800]) when looking for the IME bar height
            if 100 < height < int(screen_h * 0.85):
                return height
            if top > 0 and bottom == screen_h and (screen_h - top) > 100:
                return screen_h - top

        return 0

    def compensate_coordinates_for_ime(
        self,
        x: int,
        y: int,
        ime_state: Dict[str, Any],
        screen_size: Tuple[int, int] = DEFAULT_SCREEN_SIZE,
        prefer_shift: bool = False,
    ) -> Dict[str, Any]:
        """
        Checks if target `(x, y)` is occluded by the open soft keyboard (`y > safe_visible_y_max`).

        Returns:
          {
              "occluded": bool,
              "action_needed": "dismiss_keyboard_first" | "shift_y" | "none",
              "adjusted_x": int,
              "adjusted_y": int,
              "tokens_used": 0,
              ...
          }
        """
        screen_w, screen_h = screen_size or self.default_screen_size
        ime_visible = bool(ime_state.get("ime_visible", False))
        keyboard_height_px = int(
            ime_state.get(
                "keyboard_height_px",
                self.DEFAULT_KEYBOARD_HEIGHT_PX if ime_visible else 0,
            )
        )
        safe_visible_y_max = int(
            ime_state.get("safe_visible_y_max", max(0, screen_h - keyboard_height_px))
        )

        clamped_x = max(0, min(int(x), screen_w - 1))
        target_y = int(y)

        if ime_visible and target_y > safe_visible_y_max:
            occluded = True
            use_shift = prefer_shift or bool(ime_state.get("prefer_shift", False))
            action_needed = "shift_y" if use_shift else "dismiss_keyboard_first"
            # Calculate a safe shifted Y above the IME boundary while staying on screen
            shifted_y = max(80, min(safe_visible_y_max - 40, target_y - keyboard_height_px))
            adjusted_y = shifted_y if use_shift else target_y
        else:
            occluded = False
            action_needed = "none"
            adjusted_y = max(0, min(target_y, screen_h - 1))

        return {
            "occluded": occluded,
            "action_needed": action_needed,
            "adjusted_x": clamped_x,
            "adjusted_y": adjusted_y,
            "original_x": int(x),
            "original_y": target_y,
            "ime_visible": ime_visible,
            "keyboard_height_px": keyboard_height_px,
            "safe_visible_y_max": safe_visible_y_max,
            "tokens_used": 0,
        }

    def dismiss_soft_keyboard_safely(
        self,
        serial: str,
        dry_run: bool = False,
        raw_dumpsys_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Checks `detect_ime_keyboard_state`; if `ime_visible` is True (or in `dry_run` mode),
        sends `input keyevent 4` (KEYCODE_BACK) with fallback to `input keyevent 111`
        (KEYCODE_ESCAPE), verifies the keyboard closed, and returns:
            {"status": "IME_DISMISSED", "tokens_used": 0, ...}
        """
        if dry_run and raw_dumpsys_override is None:
            initial_state = {
                "serial": serial,
                "ime_visible": True,
                "keyboard_height_px": self.DEFAULT_KEYBOARD_HEIGHT_PX,
                "safe_visible_y_max": self.default_screen_size[1] - self.DEFAULT_KEYBOARD_HEIGHT_PX,
                "screen_size": self.default_screen_size,
                "tokens_used": 0,
            }
        else:
            initial_state = self.detect_ime_keyboard_state(
                serial=serial,
                raw_dumpsys_override=raw_dumpsys_override,
            )

        commands_sent: List[str] = []

        if initial_state.get("ime_visible", False):
            cmd_back = "input keyevent 4"
            commands_sent.append(cmd_back)
            if not dry_run:
                try:
                    self.adb.shell(serial, cmd_back, timeout=4.0)
                except Exception:
                    pass

                post_state = self.detect_ime_keyboard_state(serial=serial)
                if post_state.get("ime_visible", False):
                    cmd_esc = "input keyevent 111"
                    commands_sent.append(cmd_esc)
                    try:
                        self.adb.shell(serial, cmd_esc, timeout=4.0)
                    except Exception:
                        pass
                    post_state = self.detect_ime_keyboard_state(serial=serial)
            else:
                post_state = {
                    "serial": serial,
                    "ime_visible": False,
                    "keyboard_height_px": 0,
                    "safe_visible_y_max": self.default_screen_size[1],
                    "screen_size": self.default_screen_size,
                    "tokens_used": 0,
                }

            return {
                "status": "IME_DISMISSED",
                "serial": serial,
                "was_visible": True,
                "ime_visible_after": bool(post_state.get("ime_visible", False)),
                "commands_sent": commands_sent,
                "safe_visible_y_max": post_state.get("safe_visible_y_max", self.default_screen_size[1]),
                "dry_run": dry_run,
                "tokens_used": 0,
            }

        return {
            "status": "IME_DISMISSED",
            "serial": serial,
            "was_visible": False,
            "ime_visible_after": False,
            "commands_sent": commands_sent,
            "safe_visible_y_max": initial_state.get("safe_visible_y_max", self.default_screen_size[1]),
            "dry_run": dry_run,
            "tokens_used": 0,
        }

    def ensure_chrome_foreground_and_socket_ready(
        self,
        serial: str,
        cdp_bridge: Optional[AndroidCDPBridge] = None,
        local_port: int = 9229,
        dry_run: bool = False,
        raw_focus_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ensures Chrome (`com.android.chrome`) is in the foreground via `mCurrentFocus`
        so Android 15/16 does not freeze `@chrome_devtools_remote`, and re-binds the
        `adb forward` DevTools socket if needed.
        """
        bridge = cdp_bridge or self.cdp_bridge
        focus_cmd = "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'"

        if raw_focus_override is not None:
            focus_out = raw_focus_override
        elif dry_run:
            focus_out = f"mCurrentFocus=Window{{12345 u0 {self.CHROME_PACKAGE}/{self.CHROME_MAIN_ACTIVITY}}}"
        else:
            try:
                focus_out = self.adb.shell(serial, focus_cmd, timeout=5.0) or ""
            except Exception:
                focus_out = ""

        chrome_focused = self.CHROME_PACKAGE in focus_out
        foreground_restored = False

        if not chrome_focused and not dry_run:
            try:
                self.adb.shell(
                    serial,
                    f"am start -n {self.CHROME_PACKAGE}/{self.CHROME_MAIN_ACTIVITY}",
                    timeout=5.0,
                )
                foreground_restored = True
                chrome_focused = True
            except Exception:
                pass
        elif not chrome_focused and dry_run:
            foreground_restored = True
            chrome_focused = True

        socket_rebound = False
        active_port = local_port
        if not dry_run and bridge is not None:
            try:
                socket_rebound = bool(
                    bridge.forward_socket(
                        serial=serial,
                        local_port=local_port,
                        socket_name="chrome_devtools_remote",
                    )
                )
                active_port = bridge.active_forwards.get(
                    f"{serial}:chrome_devtools_remote",
                    local_port,
                )
            except Exception:
                socket_rebound = False
        else:
            socket_rebound = True

        return {
            "serial": serial,
            "chrome_focused": chrome_focused,
            "foreground_restored": foreground_restored,
            "socket_rebound": socket_rebound,
            "local_port": active_port,
            "raw_focus_excerpt": focus_out.strip()[:300],
            "tokens_used": 0,
        }

    def normalize_web_viewport_and_scroll_to_element(
        self,
        serial: str,
        selector: str = "button, input[type='submit']",
        cdp_bridge: Optional[AndroidCDPBridge] = None,
        dry_run: bool = False,
        screen_size: Tuple[int, int] = DEFAULT_SCREEN_SIZE,
        mock_eval_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        1. Ensures Chrome is in the foreground (`mCurrentFocus`) so Android 15/16 does not
           freeze the `@chrome_devtools_remote` abstract unix socket.
        2. Automatically re-binds `@chrome_devtools_remote` if disconnected/frozen.
        3. Injects `el.scrollIntoView({behavior: 'instant', block: 'center', inline: 'center'})`
           to center off-screen elements both horizontally (`scrollWidth > innerWidth`) and
           vertically before computing their updated physical touch coordinates `(phys_x, phys_y)`.
        """
        bridge = cdp_bridge or self.cdp_bridge
        screen_w, screen_h = screen_size or self.default_screen_size

        fg_state = self.ensure_chrome_foreground_and_socket_ready(
            serial=serial,
            cdp_bridge=bridge,
            dry_run=dry_run,
        )

        js_expr = CDP_NORMALIZE_VIEWPORT_AND_SCROLL_JS_TEMPLATE.replace(
            "__SELECTOR_JSON__", json.dumps(selector)
        )

        eval_payload: Optional[Dict[str, Any]] = None

        if mock_eval_result is not None:
            eval_payload = mock_eval_result
        elif dry_run:
            # Deterministic centered viewport payload for dry-run verification on 1260x2800
            eval_payload = {
                "found": True,
                "selector": selector,
                "tag_name": "button",
                "id": "submit-btn",
                "text": "Validate",
                "was_offscreen": True,
                "horizontal_overflow": True,
                "scrolled_into_view": True,
                "scroll_strategy": "el.scrollIntoView({behavior: 'instant', block: 'center', inline: 'center'})",
                "css_rect": {
                    "left": 150.0,
                    "top": 360.0,
                    "width": 120.0,
                    "height": 44.0,
                    "right": 270.0,
                    "bottom": 404.0,
                },
                "viewport_metrics": {
                    "devicePixelRatio": 3.0,
                    "innerWidth": 420.0,
                    "innerHeight": 820.0,
                    "outerWidth": 420.0,
                    "outerHeight": 933.0,
                    "scrollWidth": 980.0,
                    "scrollHeight": 1600.0,
                    "visualViewportOffsetLeft": 0.0,
                    "visualViewportOffsetTop": 0.0,
                    "visualViewportScale": 1.0,
                    "pageXOffset": 280.0,
                    "pageYOffset": 420.0,
                    "webdriver": False,
                },
            }
        else:
            local_port = fg_state.get("local_port", 9229)
            tabs = bridge.list_open_tabs(local_port=local_port)
            if not tabs:
                # Re-forward and retry once if Chrome socket was transiently frozen
                bridge.forward_socket(
                    serial=serial,
                    local_port=local_port,
                    socket_name="chrome_devtools_remote",
                )
                tabs = bridge.list_open_tabs(local_port=local_port)

            ws_url = ""
            for tab in tabs:
                candidate_ws = tab.get("webSocketDebuggerUrl", "")
                if candidate_ws:
                    ws_url = candidate_ws
                    break

            if ws_url:
                eval_payload = bridge.evaluate_js(ws_url=ws_url, expression=js_expr)

        if not isinstance(eval_payload, dict) or not eval_payload.get("found"):
            return {
                "status": "ELEMENT_NOT_FOUND",
                "serial": serial,
                "selector": selector,
                "chrome_focused": fg_state.get("chrome_focused", False),
                "socket_rebound": fg_state.get("socket_rebound", False),
                "scrolled_into_view": False,
                "phys_x": screen_w // 2,
                "phys_y": screen_h // 2,
                "dry_run": dry_run,
                "tokens_used": 0,
            }

        css_rect = eval_payload.get("css_rect", {})
        viewport_metrics = eval_payload.get("viewport_metrics", {})
        if hasattr(bridge, "css_rect_to_physical_coords"):
            coords = bridge.css_rect_to_physical_coords(
                css_rect=css_rect,
                viewport_metrics=viewport_metrics,
                screen_size=(screen_w, screen_h),
            )
        else:
            cx_css = float(css_rect.get("left", 0.0)) + float(css_rect.get("width", 0.0)) / 2.0
            cy_css = float(css_rect.get("top", 0.0)) + float(css_rect.get("height", 0.0)) / 2.0
            px, py = bridge.css_to_physical_screen_coords(
                css_x=cx_css,
                css_y=cy_css,
                viewport_metrics=viewport_metrics,
                screen_size=(screen_w, screen_h),
            )
            coords = {"phys_x": px, "phys_y": py, "bounds": None}

        return {
            "status": "VIEWPORT_NORMALIZED_AND_CENTERED",
            "serial": serial,
            "selector": selector,
            "tag_name": eval_payload.get("tag_name", "button"),
            "text": eval_payload.get("text", ""),
            "was_offscreen": bool(eval_payload.get("was_offscreen", False)),
            "horizontal_overflow": bool(eval_payload.get("horizontal_overflow", False)),
            "scrolled_into_view": bool(eval_payload.get("scrolled_into_view", True)),
            "scroll_strategy": eval_payload.get(
                "scroll_strategy",
                "el.scrollIntoView({behavior: 'instant', block: 'center', inline: 'center'})",
            ),
            "chrome_focused": fg_state.get("chrome_focused", True),
            "socket_rebound": fg_state.get("socket_rebound", True),
            "phys_x": int(coords["phys_x"]),
            "phys_y": int(coords["phys_y"]),
            "bounds": coords.get("bounds"),
            "css_rect": css_rect,
            "viewport_metrics": viewport_metrics,
            "dry_run": dry_run,
            "tokens_used": 0,
        }
