"""
Cluster 1 (Subagents #66 & #67): Anti-Bot Biometric Touch Kinematics & Stealth WebView Engine
=============================================================================================
Implements zero-token mathematical models for:
  - Subagent #66 (`SigmaLognormalTouchKinematicsEngine`):
      * Fitts's Law index of difficulty & truncated Gaussian target dispersion
      * Plamondon's Kinematic Theory Sigma-Lognormal asymmetric velocity swipe profiles
      * Physiological 1/f lateral arc & micro-tremor synthesis + realistic finger pressure/size curves
      * Biometric trajectory human-likeness auditing (detecting linear constant-speed/pressure bots)
  - Subagent #67 (`PatchrightStealthCDPandWebViewEngine`):
      * `Runtime.enable`-free CDP isolated world command generation (`Page.createIsolatedWorld` + `Runtime.callFunctionOn`)
      * Coherent Vivo V2417A (Snapdragon 8+ Gen 1 / Adreno 730 / 1260x2800 @ 2.8125 DPR) WebView profile synthesis
      * 8-vector anti-bot posture auditing & automatic profile remediation
"""

from __future__ import annotations

import hashlib
import math
import random
import statistics
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


@dataclass
class TouchSample:
    """Single capacitive touch event sample along a kinematic stroke."""

    x: float
    y: float
    t_ms: float
    pressure: float
    touch_major: float
    velocity_px_s: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


class SigmaLognormalTouchKinematicsEngine:
    """
    Engine for Subagent #66:
    Synthesizes and audits human-like capacitive touch kinematics using Fitts's Law
    Gaussian dispersion and Plamondon's Sigma-Lognormal impulse velocity profiles.
    """

    def __init__(self, default_seed: int = 2026066) -> None:
        self.default_seed = default_seed

    def sample_fitts_gaussian_target(
        self,
        bounds: Tuple[int, int, int, int],
        seed: Optional[int] = None,
        origin: Tuple[int, int] = (630, 1400),
    ) -> Dict[str, Any]:
        """
        Given UI element bounds `(x1, y1, x2, y2)`, computes the center `(cx, cy)`,
        dimensions `(w, h)`, Fitts's Law Index of Difficulty (`id_bits`), and samples
        a humanized touch landing coordinate `(tx, ty)` using truncated 2D Gaussian
        dispersion (`sigma_x = max(2.0, w / 6.0)`, `sigma_y = max(2.0, h / 6.0)`)
        clamped strictly inside `[x1 + 4, x2 - 4]` and `[y1 + 4, y2 - 4]`.
        """
        x1, y1, x2, y2 = int(bounds[0]), int(bounds[1]), int(bounds[2]), int(bounds[3])
        if x2 < x1:
            x1, x2 = x2, x1
        if y2 < y1:
            y1, y2 = y2, y1

        w = max(1, x2 - x1)
        h = max(1, y2 - y1)
        cx = x1 + w / 2.0
        cy = y1 + h / 2.0

        sigma_x = max(2.0, w / 6.0)
        sigma_y = max(2.0, h / 6.0)

        rng = random.Random(self.default_seed if seed is None else seed)

        min_x = x1 + 4 if w > 8 else x1
        max_x = x2 - 4 if w > 8 else x2
        min_y = y1 + 4 if h > 8 else y1
        max_y = y2 - 4 if h > 8 else y2

        raw_x = rng.gauss(cx, sigma_x)
        raw_y = rng.gauss(cy, sigma_y)

        tx = int(round(max(min_x, min(max_x, raw_x))))
        ty = int(round(max(min_y, min(max_y, raw_y))))

        distance = math.hypot(cx - origin[0], cy - origin[1])
        id_bits = math.log2(2.0 * distance / max(w, 1) + 1.0)

        return {
            "bounds": (x1, y1, x2, y2),
            "center": (round(cx, 2), round(cy, 2)),
            "width": w,
            "height": h,
            "tx": tx,
            "ty": ty,
            "sigma_x": round(sigma_x, 4),
            "sigma_y": round(sigma_y, 4),
            "distance_px": round(distance, 2),
            "id_bits": round(id_bits, 4),
        }

    @staticmethod
    def _lognormal_density(u: float, mu: float = -0.78, sigma: float = 0.48) -> float:
        """
        Evaluates an asymmetric log-normal impulse density over normalized time u in (0, 1].
        With mu=-0.78, sigma=0.48, the mode exp(mu - sigma^2) is ~0.364 (36.4% of duration),
        falling squarely inside the physiological 33%..42% peak velocity window.
        """
        if u <= 1e-6:
            return 0.0
        z = (math.log(u) - mu) / sigma
        return (1.0 / (u * sigma * math.sqrt(2.0 * math.pi))) * math.exp(-0.5 * z * z)

    def generate_sigma_lognormal_swipe(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int],
        duration_ms: int = 340,
        steps: int = 24,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generates a human-like capacitive swipe trajectory of `TouchSample` points
        following Plamondon's Sigma-Lognormal velocity profile, physiological lateral
        curvature + micro-tremor, and realistic finger contact pressure/size curves.
        """
        steps = max(6, int(steps))
        duration_ms = max(40, int(duration_ms))
        rng = random.Random(self.default_seed if seed is None else seed)

        x0, y0 = float(start[0]), float(start[1])
        x1, y1 = float(end[0]), float(end[1])
        dx = x1 - x0
        dy = y1 - y0
        chord_len = max(1e-3, math.hypot(dx, dy))

        # Unit tangent and normal vectors
        ux, uy = dx / chord_len, dy / chord_len
        nx, ny = -uy, ux

        # Slight randomized lognormal shape parameters keeping mode in [0.33, 0.42]
        mu = -0.78 + rng.uniform(-0.04, 0.04)
        sigma = 0.47 + rng.uniform(-0.02, 0.02)

        # Integrate lognormal density across steps to get cumulative progress s(t) in [0, 1]
        u_grid = [i / (steps - 1) for i in range(steps)]
        densities = [self._lognormal_density(u, mu=mu, sigma=sigma) for u in u_grid]
        # Ensure endpoints start/end cleanly while preserving interior impulse peak
        densities[0] = 0.0
        densities[-1] = densities[-1] * 0.15

        cum_area = [0.0]
        for i in range(1, steps):
            dt_u = u_grid[i] - u_grid[i - 1]
            trap = 0.5 * (densities[i - 1] + densities[i]) * dt_u
            cum_area.append(cum_area[-1] + trap)

        total_area = max(1e-9, cum_area[-1])
        s_progress = [a / total_area for a in cum_area]
        s_progress[0] = 0.0
        s_progress[-1] = 1.0

        # Physiological lateral arc amplitude (6..14 px) + 1/f-like multi-sine micro-jitter (1.5..3.5 px)
        arc_sign = 1.0 if rng.random() >= 0.5 else -1.0
        arc_amp = arc_sign * rng.uniform(5.5, 11.5)
        phase1 = rng.uniform(0.0, 2.0 * math.pi)
        phase2 = rng.uniform(0.0, 2.0 * math.pi)
        phase3 = rng.uniform(0.0, 2.0 * math.pi)

        raw_coords: List[Tuple[float, float, float, float]] = []
        lateral_offsets: List[float] = []

        for i, u in enumerate(u_grid):
            s = s_progress[i]
            t_ms = round(u * duration_ms, 3)
            envelope = math.sin(math.pi * u)  # Vanishes strictly at u=0 and u=1

            # 1/f-like physiological tremor + smooth wrist arc
            tremor = (
                1.35 * math.sin(2.0 * math.pi * 2.0 * u + phase1)
                + 0.75 * math.sin(2.0 * math.pi * 5.0 * u + phase2)
                + 0.40 * math.sin(2.0 * math.pi * 9.0 * u + phase3)
            )
            lat_offset = envelope * (arc_amp * math.sin(math.pi * s) + tremor)
            if i == 0 or i == steps - 1:
                lat_offset = 0.0

            px = x0 + s * dx + lat_offset * nx
            py = y0 + s * dy + lat_offset * ny
            raw_coords.append((px, py, t_ms, u))
            lateral_offsets.append(abs(lat_offset))

        touch_samples: List[TouchSample] = []
        adb_commands: List[str] = []

        for i, (px, py, t_ms, u) in enumerate(raw_coords):
            # Compute instantaneous tangential velocity (px/s)
            if i == 0:
                dt_s = max(1e-4, (raw_coords[1][2] - raw_coords[0][2]) / 1000.0)
                dist = math.hypot(raw_coords[1][0] - px, raw_coords[1][1] - py)
                vel = dist / dt_s * 0.25
            elif i == steps - 1:
                dt_s = max(1e-4, (t_ms - raw_coords[i - 1][2]) / 1000.0)
                dist = math.hypot(px - raw_coords[i - 1][0], py - raw_coords[i - 1][1])
                vel = dist / dt_s
            else:
                dt_s = max(1e-4, (raw_coords[i + 1][2] - raw_coords[i - 1][2]) / 1000.0)
                dist = math.hypot(
                    raw_coords[i + 1][0] - raw_coords[i - 1][0],
                    raw_coords[i + 1][1] - raw_coords[i - 1][1],
                )
                vel = dist / dt_s

            # Realistic finger contact curve:
            # pressure: 0.22 -> 0.78 -> 0.19
            # touch_major: 4.5 -> 11.2 -> 4.2
            contact_bell = math.sin(math.pi * (u ** 0.82))
            baseline_p = 0.22 * (1.0 - u) + 0.19 * u
            pressure = baseline_p + (0.78 - 0.205) * contact_bell + rng.uniform(-0.008, 0.008) * contact_bell
            pressure = max(0.05, min(1.0, pressure))

            baseline_tm = 4.5 * (1.0 - u) + 4.2 * u
            touch_major = baseline_tm + (11.2 - 4.35) * contact_bell + rng.uniform(-0.08, 0.08) * contact_bell

            sample = TouchSample(
                x=round(px, 2),
                y=round(py, 2),
                t_ms=round(t_ms, 2),
                pressure=round(pressure, 4),
                touch_major=round(touch_major, 3),
                velocity_px_s=round(vel, 2),
            )
            touch_samples.append(sample)

            action = "DOWN" if i == 0 else ("UP" if i == steps - 1 else "MOVE")
            adb_commands.append(
                f"input motionevent {action} {sample.x:.1f} {sample.y:.1f}"
            )

        peak_idx = max(range(len(touch_samples)), key=lambda idx: touch_samples[idx].velocity_px_s)
        peak_velocity_ratio = round(peak_idx / max(1, steps - 1), 4)
        pressure_std = round(statistics.pstdev([s.pressure for s in touch_samples]), 4)
        lateral_deviation_px = round(max(lateral_offsets) if lateral_offsets else 0.0, 3)

        return {
            "samples": [s.to_dict() for s in touch_samples],
            "touch_samples": touch_samples,
            "peak_velocity_ratio": peak_velocity_ratio,
            "pressure_std": pressure_std,
            "lateral_deviation_px": lateral_deviation_px,
            "adb_motionevent_commands": adb_commands,
        }

    def audit_trajectory_human_likeness(
        self,
        samples: Sequence[Union[Dict[str, Any], TouchSample]],
    ) -> Dict[str, Any]:
        """
        Audits a sequence of touch samples to distinguish robotic linear ADB swipes
        (`constant velocity`, `zero lateral deviation`, `constant pressure = 1.0`)
        from organic Sigma-Lognormal human strokes.
        """
        norm: List[TouchSample] = []
        for item in samples:
            if isinstance(item, TouchSample):
                norm.append(item)
            else:
                norm.append(
                    TouchSample(
                        x=float(item.get("x", 0.0)),
                        y=float(item.get("y", 0.0)),
                        t_ms=float(item.get("t_ms", 0.0)),
                        pressure=float(item.get("pressure", 1.0)),
                        touch_major=float(item.get("touch_major", 5.0)),
                        velocity_px_s=float(item.get("velocity_px_s", 0.0)),
                    )
                )

        if len(norm) < 3:
            return {
                "velocity_cv": 0.0,
                "pressure_std": 0.0,
                "lateral_jitter_px": 0.0,
                "asymmetry_score": 0.0,
                "human_likeness_score": 0.0,
                "is_bot_flagged": True,
            }

        # Step speeds
        step_speeds: List[float] = []
        for i in range(1, len(norm)):
            dt_s = max(1e-4, (norm[i].t_ms - norm[i - 1].t_ms) / 1000.0)
            dist = math.hypot(norm[i].x - norm[i - 1].x, norm[i].y - norm[i - 1].y)
            step_speeds.append(dist / dt_s)

        mean_speed = statistics.fmean(step_speeds) if step_speeds else 0.0
        std_speed = statistics.pstdev(step_speeds) if len(step_speeds) > 1 else 0.0
        velocity_cv = std_speed / mean_speed if mean_speed > 1e-6 else 0.0

        pressures = [s.pressure for s in norm]
        pressure_std = statistics.pstdev(pressures) if len(pressures) > 1 else 0.0

        # Lateral deviation from chord connecting start to end
        x0, y0 = norm[0].x, norm[0].y
        x1, y1 = norm[-1].x, norm[-1].y
        dx, dy = x1 - x0, y1 - y0
        chord = math.hypot(dx, dy)
        if chord > 1e-6:
            perp_dists = [
                abs(dy * s.x - dx * s.y + x1 * y0 - y1 * x0) / chord for s in norm[1:-1]
            ]
            lateral_jitter_px = max(perp_dists) if perp_dists else 0.0
        else:
            lateral_jitter_px = 0.0

        # Asymmetry score: peak velocity should occur around 0.30..0.46 of stroke, and velocity CV > 0.25
        if velocity_cv < 0.08:
            asymmetry_score = 0.0
        else:
            peak_step = max(range(len(step_speeds)), key=lambda idx: step_speeds[idx])
            peak_pos = (peak_step + 0.5) / len(step_speeds)
            dist_from_ideal = abs(peak_pos - 0.37)
            asymmetry_score = max(0.0, min(1.0, 1.0 - dist_from_ideal / 0.35))

        # Score components (total 100):
        # 1. Velocity CV (0..30 pts): human strokes have bell/lognormal speed (CV ~ 0.45..0.95)
        vel_score = min(30.0, (velocity_cv / 0.45) * 30.0)
        # 2. Pressure variation (0..25 pts): human finger contact has std ~ 0.14..0.22
        press_score = min(25.0, (pressure_std / 0.14) * 25.0)
        # 3. Lateral curvature & tremor (0..25 pts): human strokes deviate >= 2.0 px from straight line
        lat_score = min(25.0, (lateral_jitter_px / 3.5) * 25.0)
        # 4. Log-normal asymmetry (0..20 pts)
        asym_pts = asymmetry_score * 20.0

        human_likeness_score = round(
            max(0.0, min(100.0, vel_score + press_score + lat_score + asym_pts)), 2
        )
        is_bot_flagged = bool(human_likeness_score < 65.0)

        return {
            "velocity_cv": round(velocity_cv, 4),
            "pressure_std": round(pressure_std, 4),
            "lateral_jitter_px": round(lateral_jitter_px, 4),
            "asymmetry_score": round(asymmetry_score, 4),
            "human_likeness_score": human_likeness_score,
            "is_bot_flagged": is_bot_flagged,
        }


class PatchrightStealthCDPandWebViewEngine:
    """
    Engine for Subagent #67:
    Synthesizes `Runtime.enable`-free CDP isolated world command sequences and
    audits/remediates Android WebView hardware profiles for Vivo V2417A.
    """

    VIVO_V2417A_CANONICAL: Dict[str, Any] = {
        "model": "V2417A",
        "platform": "Linux aarch64",
        "hardware_concurrency": 8,
        "device_memory_gb": 8,
        "webgl_vendor": "Qualcomm",
        "webgl_renderer": "Adreno (TM) 730",
        "screen_width": 1260,
        "screen_height": 2800,
        "device_pixel_ratio": 2.8125,
        "max_touch_points": 10,
        "navigator_webdriver": False,
        "runtime_enable_leaked": False,
        "cdc_artifacts_present": False,
        "locale": "en-US",
        "timezone": "Asia/Ho_Chi_Minh",
    }

    def build_stealth_isolated_world_command(
        self,
        frame_id: str,
        expression: str,
        world_name: str = "amaf_stealth_world",
    ) -> Dict[str, Any]:
        """
        Builds a `Runtime.enable`-free CDP command sequence using
        `Page.createIsolatedWorld` followed by `Runtime.callFunctionOn` on the
        resulting `executionContextId`, preventing Cloudflare/DataDome console scope leaks.
        """
        wrapped_fn = f"function() {{ return ({expression}); }}"
        commands = [
            {
                "id": 1,
                "method": "Page.createIsolatedWorld",
                "params": {
                    "frameId": frame_id,
                    "worldName": world_name,
                    "grantUniveralAccess": True,
                },
            },
            {
                "id": 2,
                "method": "Runtime.callFunctionOn",
                "params": {
                    "functionDeclaration": wrapped_fn,
                    "executionContextId": "$isolated_world_execution_context_id",
                    "returnByValue": True,
                    "awaitPromise": True,
                },
            },
        ]
        return {
            "frame_id": frame_id,
            "world_name": world_name,
            "expression": expression,
            "uses_runtime_enable": False,
            "commands": commands,
            "methods": [cmd["method"] for cmd in commands],
        }

    def build_vivo_v2417a_hardware_profile(
        self,
        serial: str = "10CF5L0TYL00312",
    ) -> Dict[str, Any]:
        """
        Generates a deterministic, internally consistent Android hardware & WebView
        fingerprint profile for Vivo V2417A bound to `serial`.
        """
        digest = hashlib.sha256(f"vivo_v2417a::{serial}".encode("utf-8")).hexdigest()
        canvas_noise_seed = int(digest[:8], 16)
        audio_noise_seed = int(digest[8:16], 16)

        profile = dict(self.VIVO_V2417A_CANONICAL)
        profile.update(
            {
                "serial": serial,
                "canvas_noise_seed": canvas_noise_seed,
                "audio_noise_seed": audio_noise_seed,
                "user_agent": (
                    "Mozilla/5.0 (Linux; Android 14; V2417A Build/UP1A.231005.007; wv) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
                    "Chrome/124.0.6367.82 Mobile Safari/537.36"
                ),
            }
        )
        return profile

    def audit_webview_stealth_posture(
        self,
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Audits 8 anti-bot vectors on an Android WebView profile and produces a
        remediated profile if any leaks or hardware inconsistencies are detected.
        """
        checks: Dict[str, bool] = {
            "no_runtime_enable_leak": not bool(profile.get("runtime_enable_leaked", True)),
            "navigator_webdriver_false": profile.get("navigator_webdriver") is False,
            "no_cdc_artifacts": not bool(profile.get("cdc_artifacts_present", True)),
            "webgl_arm_coherent": (
                profile.get("platform") == "Linux aarch64"
                and "Qualcomm" in str(profile.get("webgl_vendor", ""))
                and "Adreno" in str(profile.get("webgl_renderer", ""))
            ),
            "touch_points_valid": int(profile.get("max_touch_points", 0)) >= 5,
            "viewport_dpr_coherent": (
                int(profile.get("screen_width", 0)) == 1260
                and int(profile.get("screen_height", 0)) == 2800
                and abs(float(profile.get("device_pixel_ratio", 0.0)) - 2.8125) < 1e-3
            ),
            "audio_canvas_entropy_valid": (
                int(profile.get("canvas_noise_seed", 0)) > 0
                and int(profile.get("audio_noise_seed", 0)) > 0
                and profile.get("canvas_noise_seed") != profile.get("audio_noise_seed")
            ),
            "locale_timezone_coherent": (
                bool(profile.get("locale")) and bool(profile.get("timezone"))
            ),
        }

        leaks_detected = [name for name, passed in checks.items() if not passed]
        total_vectors = 8
        passed_vectors = sum(1 for passed in checks.values() if passed)
        stealth_score = round((passed_vectors / total_vectors) * 100.0, 2)

        serial = str(profile.get("serial", "10CF5L0TYL00312"))
        remediated_profile = self.build_vivo_v2417a_hardware_profile(serial=serial)

        return {
            "checks": checks,
            "passed_vectors": passed_vectors,
            "total_vectors": total_vectors,
            "stealth_score": stealth_score,
            "leaks_detected": leaks_detected,
            "remediated_profile": remediated_profile,
        }
