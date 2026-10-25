"""
Human Touch Subagent (Subagent #17)
Wraps `HumanTouchEngine` and `MemoryManager` to execute biomechanical human-like gestures
(`tap`, `bezier_swipe`, `slider_drag`, `type_text`) and persist telemetry in agent memory.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.human_touch_engine import HumanTouchEngine
from core.memory_manager import MemoryManager
from core.real_device_manager import RealDeviceManager


class HumanTouchSubagent:
    """Subagent #17: Biomechanical Human Touch & Anti-Bot Gesture Executor."""

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        real_mgr: Optional[RealDeviceManager] = None,
        engine: Optional[HumanTouchEngine] = None,
        memory: Optional[MemoryManager] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.real_mgr = real_mgr or RealDeviceManager(self.adb)
        self.engine = engine or HumanTouchEngine(adb=self.adb, real_mgr=self.real_mgr)
        self.memory = memory or MemoryManager()

    def execute_human_action(
        self,
        serial: str,
        action_spec: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a biomechanical human touch action on `serial` according to `action_spec`.
        Supported action types:
        - `tap`: Gaussian-jittered tap with realistic finger dwell
        - `bezier_swipe`: Cubic Bézier curve swipe with minimum-jerk velocity profile
        - `slider_drag`: Slider puzzle CAPTCHA drag with natural arc & overshoot correction
        - `type_text`: Human burst typing with realistic inter-keystroke cadence
        """
        action_type = str(action_spec.get("action") or action_spec.get("type") or "tap").lower()
        start_ts = time.time()

        if action_type in ("tap", "human_tap"):
            res = self.engine.human_tap(
                serial=serial,
                x=float(action_spec.get("x", 0)),
                y=float(action_spec.get("y", 0)),
                bounds=action_spec.get("bounds"),
                dwell_ms=action_spec.get("dwell_ms"),
                is_normalized=bool(action_spec.get("is_normalized", False)),
            )
        elif action_type in ("bezier_swipe", "swipe", "human_bezier_swipe"):
            res = self.engine.human_bezier_swipe(
                serial=serial,
                start_x=int(action_spec.get("start_x", action_spec.get("x1", 360))),
                start_y=int(action_spec.get("start_y", action_spec.get("y1", 1200))),
                end_x=int(action_spec.get("end_x", action_spec.get("x2", 360))),
                end_y=int(action_spec.get("end_y", action_spec.get("y2", 400))),
                duration_ms=int(action_spec.get("duration_ms", 600)),
                steps=int(action_spec.get("steps", 12)),
                include_overshoot=bool(action_spec.get("include_overshoot", False)),
            )
        elif action_type in ("slider_drag", "human_slider_drag"):
            res = self.engine.human_slider_drag(
                serial=serial,
                start_x=int(action_spec.get("start_x", 100)),
                start_y=int(action_spec.get("start_y", 500)),
                distance_px=int(action_spec.get("distance_px", 300)),
                duration_ms=int(action_spec.get("duration_ms", 780)),
            )
        elif action_type in ("type_text", "type", "human_type_text"):
            res = self.engine.human_type_text(
                serial=serial,
                text=str(action_spec.get("text", "")),
                min_delay_ms=int(action_spec.get("min_delay_ms", 40)),
                max_delay_ms=int(action_spec.get("max_delay_ms", 120)),
            )
        else:
            res = {
                "status": "UNSUPPORTED_HUMAN_ACTION",
                "serial": serial,
                "action_type": action_type,
            }

        elapsed_ms = round((time.time() - start_ts) * 1000.0, 1)
        telemetry = {
            **res,
            "subagent": "HumanTouchSubagent#17",
            "action_type": action_type,
            "elapsed_ms": elapsed_ms,
        }

        self.memory.remember(
            key=f"human_touch_{serial}_{int(time.time() * 1000)}",
            value=telemetry,
            tags=["human_touch", action_type, serial],
            category="biomechanical_telemetry",
        )
        return telemetry


if __name__ == "__main__":
    sub = HumanTouchSubagent()
    print("HumanTouchSubagent (#17) initialized successfully.")
