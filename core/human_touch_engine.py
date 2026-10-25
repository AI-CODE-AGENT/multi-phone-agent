"""
Human Touch Biomechanics Engine for Android Multi-Agent Farm (AMAF 3.0)
Inspired by Google DeepMind `android_env`, `google-research/android_world`,
`sarperavci/human_mouse`, and Fitts's Law motor-control biomechanics.

Provides:
- Fitts's Law Gaussian micro-jitter within safe UI element bounds
- Cubic Bézier curve trajectory generation with ease-in/ease-out (minimum-jerk) velocity profile
- Realistic human overshoot & micro-correction settle points for slider CAPTCHAs
- Finger-dwell taps via micro-swipe touch pressure window (compatible with all OEM ROMs including Vivo OriginOS without root)
- Chained `input motionevent` gestures with automatic multi-segment Bézier `input swipe` fallback
- Human burst typing with natural inter-keystroke cadence
"""

import math
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.real_device_manager import RealDeviceManager


class HumanTouchEngine:
    """Biomechanical human touch and gesture synthesis engine for Android devices."""

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        real_mgr: Optional[RealDeviceManager] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.real_mgr = real_mgr or RealDeviceManager(self.adb)

    def apply_gaussian_jitter(
        self,
        x: int,
        y: int,
        bounds: Optional[Dict[str, int]] = None,
        sigma: float = 4.5,
    ) -> Tuple[int, int]:
        """
        Add human Gaussian micro-jitter (random.gauss(0, sigma)) around (x, y)
        and clamp safely within element `bounds` (with 4px inner margin) if provided,
        or default screen bounds.
        """
        dx = random.gauss(0, sigma)
        dy = random.gauss(0, sigma)
        jx = int(round(x + dx))
        jy = int(round(y + dy))

        if bounds:
            left = bounds.get("left", bounds.get("x1", 0))
            top = bounds.get("top", bounds.get("y1", 0))
            right = bounds.get("right", bounds.get("x2", max(jx, x + 20)))
            bottom = bounds.get("bottom", bounds.get("y2", max(jy, y + 20)))

            margin_x = 4 if (right - left) > 10 else 0
            margin_y = 4 if (bottom - top) > 10 else 0

            min_x = left + margin_x
            max_x = right - margin_x
            min_y = top + margin_y
            max_y = bottom - margin_y

            if min_x <= max_x:
                jx = max(min_x, min(max_x, jx))
            if min_y <= max_y:
                jy = max(min_y, min(max_y, jy))
        else:
            # Clamp to standard screen bounds (0..w, 0..h)
            w, h = 1440, 3200
            jx = max(0, min(w, jx))
            jy = max(0, min(h, jy))

        return int(jx), int(jy)

    def generate_bezier_trajectory(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        steps: int = 16,
        include_overshoot: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Generate a human-like Cubic Bézier trajectory from (start_x, start_y) to (end_x, end_y)
        with two randomized control points (cp1, cp2), minimum-jerk ease-in/ease-out velocity
        profile (t_eased = 3*t^2 - 2*t^3), and optional human overshoot + settle correction.
        """
        steps = max(4, int(steps))
        dx = float(end_x - start_x)
        dy = float(end_y - start_y)
        distance = math.hypot(dx, dy)

        # Perpendicular unit vector for subtle natural arc
        if distance > 1e-3:
            perp_x = -dy / distance
            perp_y = dx / distance
        else:
            perp_x, perp_y = 0.0, 1.0

        arc_scale = min(max(distance * 0.12, 4.0), 45.0)
        arc_dir = random.choice([-1.0, 1.0])
        offset1 = arc_dir * random.uniform(0.25, 0.85) * arc_scale
        offset2 = arc_dir * random.uniform(0.15, 0.65) * arc_scale

        cp1_x = start_x + dx * random.uniform(0.22, 0.36) + perp_x * offset1
        cp1_y = start_y + dy * random.uniform(0.22, 0.36) + perp_y * offset1
        cp2_x = start_x + dx * random.uniform(0.64, 0.80) + perp_x * offset2
        cp2_y = start_y + dy * random.uniform(0.64, 0.80) + perp_y * offset2

        trajectory: List[Dict[str, Any]] = []
        for i in range(steps):
            t = i / float(steps - 1)
            # Minimum-jerk ease-in / ease-out profile: denser at start and end
            t_eased = 3.0 * (t ** 2) - 2.0 * (t ** 3)
            u = 1.0 - t_eased

            bx = (
                (u ** 3) * start_x
                + 3.0 * (u ** 2) * t_eased * cp1_x
                + 3.0 * u * (t_eased ** 2) * cp2_x
                + (t_eased ** 3) * end_x
            )
            by = (
                (u ** 3) * start_y
                + 3.0 * (u ** 2) * t_eased * cp1_y
                + 3.0 * u * (t_eased ** 2) * cp2_y
                + (t_eased ** 3) * end_y
            )

            # Subtle physiological tremor on intermediate points
            if 0 < i < steps - 1:
                bx += random.gauss(0, 0.75)
                by += random.gauss(0, 0.75)

            # Velocity bell curve: slower at start/end (higher delay), faster at mid-cruise
            speed_factor = 6.0 * t * (1.0 - t)  # peaks at 1.5 when t=0.5
            base_delay = int(round(18 + (1.5 - speed_factor) * 14 + random.uniform(-2, 3)))
            delay_ms = max(8, base_delay)

            trajectory.append(
                {
                    "x": int(round(bx)),
                    "y": int(round(by)),
                    "delay_ms": delay_ms,
                }
            )

        if include_overshoot and distance > 40.0:
            sign_x = 1 if dx >= 0 else -1
            overshoot_x = int(end_x + sign_x * random.randint(3, 8))
            overshoot_y = int(end_y + random.randint(-2, 2))
            trajectory.append(
                {
                    "x": overshoot_x,
                    "y": overshoot_y,
                    "delay_ms": random.randint(28, 52),
                }
            )
            # Micro-correction settle point back to exact target
            trajectory.append(
                {
                    "x": int(end_x),
                    "y": int(end_y),
                    "delay_ms": random.randint(35, 65),
                }
            )

        return trajectory

    def human_tap(
        self,
        serial: str,
        x: float,
        y: float,
        bounds: Optional[Dict[str, int]] = None,
        dwell_ms: Optional[int] = None,
        is_normalized: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a human-like finger press with Gaussian micro-jitter and realistic dwell duration.
        Supports normalized [0.0..1.0] coordinates scaled via device resolution.
        Uses a micro-swipe dwell (`input swipe jx jy jx±1 jy±1 dwell`) to produce a true
        DOWN -> MOVE -> UP touch pressure window on all Android OEM ROMs without root.
        """
        target_x, target_y = x, y
        if is_normalized or (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and (x > 0 or y > 0)):
            w, h = self.real_mgr.get_device_resolution(serial)
            target_x = int(round(x * w))
            target_y = int(round(y * h))
        else:
            target_x = int(round(x))
            target_y = int(round(y))

        jx, jy = self.apply_gaussian_jitter(target_x, target_y, bounds=bounds)
        dwell = int(dwell_ms) if dwell_ms is not None else random.randint(55, 130)

        end_jx = jx + random.choice([-1, 0, 1])
        end_jy = jy + random.choice([-1, 0, 1])
        self.adb.shell(serial, f"input swipe {jx} {jy} {end_jx} {end_jy} {dwell}")

        return {
            "status": "HUMAN_TAP_OK",
            "serial": serial,
            "target": [int(target_x), int(target_y)],
            "actual_point": [jx, jy],
            "dwell_ms": dwell,
        }

    def human_bezier_swipe(
        self,
        serial: str,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 600,
        steps: int = 12,
        include_overshoot: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a human Cubic Bézier swipe along a minimum-jerk trajectory.
        First attempts a single chained `input motionevent DOWN ... MOVE ... UP` command;
        if unsupported by the OEM ROM, automatically falls back to multi-segment Bézier `input swipe`.
        """
        traj = self.generate_bezier_trajectory(
            start_x,
            start_y,
            end_x,
            end_y,
            steps=steps,
            include_overshoot=include_overshoot,
        )

        # Build single chained shell command using input motionevent
        cmd_parts = [f"input motionevent DOWN {traj[0]['x']} {traj[0]['y']}"]
        for pt in traj[1:-1]:
            cmd_parts.append(f"input motionevent MOVE {pt['x']} {pt['y']}")
        cmd_parts.append(f"input motionevent UP {traj[-1]['x']} {traj[-1]['y']}")
        chained_cmd = "; ".join(cmd_parts)

        out = self.adb.shell(serial, chained_cmd)
        out_lower = (out or "").lower()
        if (
            "error" in out_lower
            or "unknown command" in out_lower
            or "invalid" in out_lower
            or "exception" in out_lower
        ):
            # Fallback to multi-segment Bézier input swipe commands along trajectory
            seg_count = max(1, len(traj) - 1)
            seg_dur = max(15, int(round(duration_ms / seg_count)))
            swipe_cmds = []
            for idx in range(len(traj) - 1):
                p0 = traj[idx]
                p1 = traj[idx + 1]
                d_ms = p1.get("delay_ms") or seg_dur
                swipe_cmds.append(
                    f"input swipe {p0['x']} {p0['y']} {p1['x']} {p1['y']} {d_ms}"
                )
            self.adb.shell(serial, "; ".join(swipe_cmds))

        return {
            "status": "HUMAN_SWIPE_OK",
            "serial": serial,
            "points_count": len(traj),
            "include_overshoot": include_overshoot,
            "trajectory_sample": traj[:4] + traj[-2:],
        }

    def human_slider_drag(
        self,
        serial: str,
        start_x: int,
        start_y: int,
        distance_px: int,
        duration_ms: int = 780,
    ) -> Dict[str, Any]:
        """
        Specifically crafted for Slider Puzzle CAPTCHAs:
        Drags from (start_x, start_y) to (start_x + distance_px, start_y + random.randint(-3, 3))
        using a 18-step Cubic Bézier trajectory with human overshoot and micro-correction settle.
        """
        end_x = int(start_x + distance_px)
        end_y = int(start_y + random.randint(-3, 3))
        swipe_res = self.human_bezier_swipe(
            serial=serial,
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            duration_ms=duration_ms,
            steps=18,
            include_overshoot=True,
        )
        return {
            **swipe_res,
            "status": "HUMAN_SLIDER_DRAG_OK",
            "serial": serial,
            "start": [int(start_x), int(start_y)],
            "distance_px": int(distance_px),
            "end_x": end_x,
        }

    def human_type_text(
        self,
        serial: str,
        text: str,
        min_delay_ms: int = 40,
        max_delay_ms: int = 120,
    ) -> Dict[str, Any]:
        """
        Type text in human-like bursts/chunks (1-3 chars per burst) with natural
        inter-keystroke cadence.
        """
        if not text:
            return {
                "status": "HUMAN_TYPE_OK",
                "serial": serial,
                "text_length": 0,
                "chunks_typed": 0,
            }

        idx = 0
        chunks_count = 0
        n = len(text)
        while idx < n:
            chunk_len = random.randint(1, 3)
            chunk = text[idx : idx + chunk_len]
            self.adb.input_text(serial, chunk)
            chunks_count += 1
            idx += chunk_len
            if idx < n:
                delay_s = random.uniform(min_delay_ms, max_delay_ms) / 1000.0
                time.sleep(delay_s)

        return {
            "status": "HUMAN_TYPE_OK",
            "serial": serial,
            "text_length": len(text),
            "chunks_typed": chunks_count,
        }


if __name__ == "__main__":
    engine = HumanTouchEngine()
    sample_traj = engine.generate_bezier_trajectory(100, 500, 620, 505, steps=16, include_overshoot=True)
    print(f"Generated {len(sample_traj)} Bézier points. Sample:", sample_traj[:3], sample_traj[-2:])
