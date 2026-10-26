"""
Subagent #42: Keyboard & Viewport Auto-Guard Subagent (AMAF v9.0)

Wraps `KeyboardAndViewportGuard` to protect physical touch interactions on Vivo V2417A
(`10CF5L0TYL00312`, OriginOS 6, `1260x2800`) against:
  1. Soft keyboard (`InputMethodManager`) occlusion (`y > 1680` when `mInputShown=true`).
  2. Desktop-layout horizontal/vertical WebView & Chrome overflow (`scrollWidth > innerWidth`).
  3. Android 15/16 background browser DevTools socket freezing (`@chrome_devtools_remote`).

Operates with 100% ZERO AI TOKENS at runtime (`tokens_used = 0`).
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.android_cdp_bridge import AndroidCDPBridge
from core.keyboard_viewport_guard import KeyboardAndViewportGuard
from core.memory_manager import MemoryManager


class KeyboardAndViewportGuardSubagent:
    """
    Subagent #42: Keyboard & Viewport Auto-Guard Engine.
    Ensures target touch coordinates are never swallowed by an open Android IME keyboard
    and off-screen DOM elements are scrolled into the center of the physical viewport.
    """

    SUBAGENT_ID = 42
    SUBAGENT_NAME = "KeyboardAndViewportGuardSubagent"

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
        cdp_bridge: Optional[AndroidCDPBridge] = None,
        guard: Optional[KeyboardAndViewportGuard] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory
        self.cdp_bridge = cdp_bridge or AndroidCDPBridge(adb=self.adb)
        self.guard = guard or KeyboardAndViewportGuard(
            adb=self.adb,
            cdp_bridge=self.cdp_bridge,
        )

    def guard_input_and_viewport(
        self,
        serial: str = "10CF5L0TYL00312",
        target_x: int = 400,
        target_y: int = 2200,
        dry_run: bool = False,
        selector: str = "button, input[type='submit']",
        screen_size: Tuple[int, int] = (1260, 2800),
        raw_dumpsys_override: Optional[str] = None,
        mock_eval_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        1. Detects soft keyboard (`InputMethodManager`) visibility and safe Y boundary.
        2. Evaluates whether `(target_x, target_y)` is occluded (`target_y > safe_visible_y_max`).
        3. Automatically dismisses the soft keyboard safely if occluded (or in `dry_run` mode).
        4. Normalizes the web viewport and scrolls the target DOM selector into the center
           of the screen via `@chrome_devtools_remote`.
        """
        if dry_run and raw_dumpsys_override is None:
            raw_dumpsys_sample = "mInputShown=true mVisibleFrame=[0,1680][1260,2800]"
        else:
            raw_dumpsys_sample = raw_dumpsys_override

        ime_state = self.guard.detect_ime_keyboard_state(
            serial=serial,
            raw_dumpsys_override=raw_dumpsys_sample,
            screen_size=screen_size,
        )
        compensation = self.guard.compensate_coordinates_for_ime(
            x=target_x,
            y=target_y,
            ime_state=ime_state,
            screen_size=screen_size,
        )

        dismiss_result: Optional[Dict[str, Any]] = None
        if compensation["occluded"] or ime_state.get("ime_visible", False):
            dismiss_result = self.guard.dismiss_soft_keyboard_safely(
                serial=serial,
                dry_run=dry_run,
                raw_dumpsys_override=raw_dumpsys_sample,
            )

        viewport_result = self.guard.normalize_web_viewport_and_scroll_to_element(
            serial=serial,
            selector=selector,
            cdp_bridge=self.cdp_bridge,
            dry_run=dry_run,
            screen_size=screen_size,
            mock_eval_result=mock_eval_result,
        )

        report = {
            "status": "INPUT_AND_VIEWPORT_GUARDED",
            "subagent_id": self.SUBAGENT_ID,
            "subagent_name": self.SUBAGENT_NAME,
            "serial": serial,
            "target_x": target_x,
            "target_y": target_y,
            "ime_state": ime_state,
            "compensation": compensation,
            "dismiss_result": dismiss_result,
            "viewport_result": viewport_result,
            "phys_x": viewport_result.get("phys_x", compensation["adjusted_x"]),
            "phys_y": viewport_result.get("phys_y", compensation["adjusted_y"]),
            "dry_run": dry_run,
            "tokens_used": 0,
            "timestamp": time.time(),
        }
        self._remember(serial, "guard_input_and_viewport", report)
        return report

    def _remember(self, serial: str, action: str, payload: Dict[str, Any]) -> None:
        if self.memory is None or not hasattr(self.memory, "remember"):
            return
        try:
            self.memory.remember(
                content=f"[Subagent #42 KeyboardAndViewportGuardSubagent] {action} on {serial} -> {payload.get('status')}",
                tags=["keyboard_viewport_guard", "ime", "viewport", serial],
                metadata=payload,
            )
        except TypeError:
            try:
                self.memory.remember(
                    key=f"kbd_viewport_guard_{serial}_{int(time.time() * 1000)}",
                    value=payload,
                    tags=["keyboard_viewport_guard", "ime", "viewport", serial],
                    category="keyboard_viewport_guard",
                )
            except Exception:
                pass
        except Exception:
            pass


KeyboardViewportGuardSubagent = KeyboardAndViewportGuardSubagent

