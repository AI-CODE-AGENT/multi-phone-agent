"""
Action Macro Recorder & Self-Caching Replay Engine (AMAF 5.0 - Subagent #37 Core)
Inspired by:
- AirtestProject/Airtest (`Template(tpl_path, record_pos, resolution, threshold)` with resolution-aware template scaling & ROI priority search)
- AirtestProject/Poco (UI hierarchy node attribute selectors: `resource_id`, `text`, `content_desc`, `class_name`)
- Fitts's Law & Minimum-Jerk Cubic Bézier Biomechanics (`HumanTouchEngine`)

Provides a 0-AI-Token hybrid 3-stage deterministic coordinate resolution pipeline:
1. Stage 1 (Poco / XML Node Match): Exact UI hierarchy element center match (`strategy="poco_xml"`).
2. Stage 2 (Airtest Visual Template Match): Local ROI search near expected scaled position (<10ms) + full-screen NCC/SAD fallback with automatic cross-resolution template scaling (`strategy="visual_template"`).
3. Stage 3 (Relative Resolution Scaling Fallback): Normalized coordinate scaling across devices, e.g. Vivo V2314A `1260x2800` -> Emulator `1080x2400` (`strategy="relative_scale"`).
"""

import base64
import io
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.human_touch_engine import HumanTouchEngine
from core.real_device_manager import RealDeviceManager
from core.screenshot_perception_engine import ScreenshotPerceptionEngine


@dataclass
class VisualTemplate:
    """
    Airtest-inspired visual template descriptor (`Template(tpl_path, record_pos, resolution, threshold)`).
    Stores cropped template path (and optional inline base64 PNG), recorded position (`record_pos`),
    source screen `resolution` (width, height), and match `threshold` (default 0.80).
    """

    tpl_path: str = ""
    record_pos: Tuple[float, float] = (0.0, 0.0)
    resolution: Tuple[int, int] = (1260, 2800)
    threshold: float = 0.80
    tpl_base64: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tpl_path": str(self.tpl_path),
            "record_pos": [float(self.record_pos[0]), float(self.record_pos[1])],
            "resolution": [int(self.resolution[0]), int(self.resolution[1])],
            "threshold": float(self.threshold),
            "tpl_base64": self.tpl_base64,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VisualTemplate":
        rec_pos = data.get("record_pos", (0.0, 0.0))
        res = data.get("resolution", (1260, 2800))
        return cls(
            tpl_path=str(data.get("tpl_path", "")),
            record_pos=(float(rec_pos[0]), float(rec_pos[1])),
            resolution=(int(res[0]), int(res[1])),
            threshold=float(data.get("threshold", 0.80)),
            tpl_base64=data.get("tpl_base64"),
        )

    @staticmethod
    def _load_pil_image(source: Union[str, Path, bytes, np.ndarray, Image.Image]) -> Image.Image:
        if isinstance(source, Image.Image):
            return source.convert("RGB")
        if isinstance(source, np.ndarray):
            if source.ndim == 2:
                return Image.fromarray(source.astype(np.uint8), mode="L").convert("RGB")
            return Image.fromarray(source.astype(np.uint8)).convert("RGB")
        if isinstance(source, (bytes, bytearray)):
            return Image.open(io.BytesIO(source)).convert("RGB")
        path_str = str(source)
        if os.path.exists(path_str):
            return Image.open(path_str).convert("RGB")
        # Try base64 decoding if string is base64 data
        try:
            raw = base64.b64decode(path_str)
            return Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception as exc:
            raise FileNotFoundError(f"Cannot load image from source: {source}") from exc

    def _load_template_image(self) -> Optional[Image.Image]:
        if self.tpl_path and os.path.exists(str(self.tpl_path)):
            try:
                return Image.open(str(self.tpl_path)).convert("RGB")
            except Exception:
                pass
        if self.tpl_base64:
            try:
                raw = base64.b64decode(self.tpl_base64)
                return Image.open(io.BytesIO(raw)).convert("RGB")
            except Exception:
                pass
        return None

    def _expected_center_on_screen(self, target_w: int, target_h: int) -> Tuple[int, int]:
        """
        Compute expected (cx, cy) on target screen from `record_pos`.
        Supports both:
        - Normalized [0.0, 1.0] coordinates when `0.0 <= rx <= 1.0` and `0.0 <= ry <= 1.0`
          (or Airtest center-offset `[-0.5, 0.5]` when negative values or offset semantics are used).
        """
        rx, ry = float(self.record_pos[0]), float(self.record_pos[1])
        if rx < 0.0 or ry < 0.0:
            # Airtest-style offset from screen center: rx = (x - w/2) / w
            cx = int(round((rx + 0.5) * target_w))
            cy = int(round((ry + 0.5) * target_h))
        else:
            cx = int(round(rx * target_w))
            cy = int(round(ry * target_h))
        cx = max(0, min(target_w - 1, cx))
        cy = max(0, min(target_h - 1, cy))
        return cx, cy

    @staticmethod
    def _ncc_and_sad_match(region_gray: np.ndarray, tpl_gray: np.ndarray) -> Tuple[float, int, int]:
        """
        Ultra-fast 2D FFT Normalized Cross-Correlation (NCC) + Sum of Absolute Differences (SAD)
        similarity for <8ms execution across large screen ROIs.
        Returns `(confidence, best_top_y, best_left_x)`.
        """
        th, tw = tpl_gray.shape
        sh, sw = region_gray.shape
        if th > sh or tw > sw or th == 0 or tw == 0:
            return 0.0, 0, 0

        from scipy.signal import fftconvolve

        reg_f = region_gray.astype(np.float32)
        tpl_f = tpl_gray.astype(np.float32)
        tpl_mean = float(np.mean(tpl_f))
        tpl_zero = tpl_f - tpl_mean
        tpl_norm = float(np.sqrt(np.sum(tpl_zero ** 2)))

        if tpl_norm < 1e-5:
            # Uniform template: use integral table mean difference
            ones = np.ones((th, tw), dtype=np.float32) / float(th * tw)
            local_mean = fftconvolve(reg_f, ones, mode="valid")
            diff = np.abs(local_mean - tpl_mean)
            idx = int(np.argmin(diff))
            by, bx = divmod(idx, diff.shape[1])
            sad_sim = float(max(0.0, 1.0 - float(diff[by, bx]) / 255.0))
            return sad_sim, int(by), int(bx)

        # Cross-correlation via 2D FFT
        corr = fftconvolve(reg_f, tpl_zero[::-1, ::-1], mode="valid")

        # Local patch variance via integral images
        pad_s = np.pad(reg_f, ((1, 0), (1, 0)), mode="constant").cumsum(axis=0).cumsum(axis=1)
        pad_sq = np.pad(reg_f ** 2, ((1, 0), (1, 0)), mode="constant").cumsum(axis=0).cumsum(axis=1)

        n_pix = float(th * tw)
        sum_r = pad_s[th:, tw:] - pad_s[:-th, tw:] - pad_s[th:, :-tw] + pad_s[:-th, :-tw]
        sum_sq = pad_sq[th:, tw:] - pad_sq[:-th, tw:] - pad_sq[th:, :-tw] + pad_sq[:-th, :-tw]
        var_r = np.maximum(sum_sq - (sum_r ** 2) / n_pix, 0.0)
        denom = np.sqrt(np.maximum(var_r, 1.0)) * tpl_norm

        ncc_map = np.where(var_r > 1.0, corr / denom, 0.0)
        idx = int(np.argmax(ncc_map))
        by, bx = divmod(idx, ncc_map.shape[1])
        ncc_score = float(np.clip(ncc_map[by, bx], -1.0, 1.0))

        patch = reg_f[by : by + th, bx : bx + tw]
        sad_sim = float(max(0.0, 1.0 - float(np.mean(np.abs(patch - tpl_f))) / 255.0))
        if ncc_score > 0.0:
            combined = float(max(ncc_score, 0.85 * ncc_score + 0.15 * sad_sim))
        else:
            combined = float(ncc_score)
        return combined, int(by), int(bx)

    def match_on_screen(
        self,
        screen_image: Union[str, Path, bytes, np.ndarray, Image.Image],
        search_radius_ratio: float = 0.25,
    ) -> Dict[str, Any]:
        """
        Search for the visual template on `screen_image`.
        1. Automatically scales template if `screen_image` resolution differs from `self.resolution`.
        2. Searches local ROI around expected scaled position (`search_radius_ratio`, default 0.25) for <10ms speed.
        3. Falls back to full-screen pyramid + fine search if local ROI confidence < `self.threshold`.
        """
        t0 = time.perf_counter()
        tpl_img = self._load_template_image()
        if tpl_img is None:
            return {
                "matched": False,
                "confidence": 0.0,
                "x": 0,
                "y": 0,
                "center_x": 0,
                "center_y": 0,
                "search_mode": "missing_template",
                "elapsed_ms": 0.0,
            }

        scr_img = self._load_pil_image(screen_image)
        target_w, target_h = scr_img.size
        rec_w, rec_h = int(self.resolution[0]), int(self.resolution[1])

        orig_tw, orig_th = tpl_img.size
        scale_x = target_w / float(max(1, rec_w))
        scale_y = target_h / float(max(1, rec_h))

        resample_filter = getattr(getattr(Image, "Resampling", Image), "BILINEAR")
        if abs(scale_x - 1.0) > 1e-3 or abs(scale_y - 1.0) > 1e-3:
            scaled_tw = max(8, int(round(orig_tw * scale_x)))
            scaled_th = max(8, int(round(orig_th * scale_y)))
            tpl_scaled_img = tpl_img.resize((scaled_tw, scaled_th), resample=resample_filter)
        else:
            scaled_tw, scaled_th = orig_tw, orig_th
            tpl_scaled_img = tpl_img

        if scaled_tw > target_w or scaled_th > target_h:
            return {
                "matched": False,
                "confidence": 0.0,
                "x": 0,
                "y": 0,
                "center_x": 0,
                "center_y": 0,
                "search_mode": "template_larger_than_screen",
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            }

        scr_gray = np.asarray(scr_img.convert("L"), dtype=np.float32)
        tpl_gray = np.asarray(tpl_scaled_img.convert("L"), dtype=np.float32)

        exp_cx, exp_cy = self._expected_center_on_screen(target_w, target_h)
        radius_x = max(scaled_tw, int(round(target_w * float(search_radius_ratio))))
        radius_y = max(scaled_th, int(round(target_h * float(search_radius_ratio))))

        roi_x1 = max(0, exp_cx - radius_x - scaled_tw // 2)
        roi_y1 = max(0, exp_cy - radius_y - scaled_th // 2)
        roi_x2 = min(target_w, exp_cx + radius_x + scaled_tw // 2)
        roi_y2 = min(target_h, exp_cy + radius_y + scaled_th // 2)

        roi_gray = scr_gray[roi_y1:roi_y2, roi_x1:roi_x2]
        if roi_gray.shape[0] >= scaled_th and roi_gray.shape[1] >= scaled_tw:
            roi_score, local_y, local_x = self._ncc_and_sad_match(roi_gray, tpl_gray)
            if roi_score >= self.threshold:
                best_x1 = roi_x1 + local_x
                best_y1 = roi_y1 + local_y
                cx = int(best_x1 + scaled_tw // 2)
                cy = int(best_y1 + scaled_th // 2)
                return {
                    "matched": True,
                    "confidence": round(float(roi_score), 4),
                    "x": cx,
                    "y": cy,
                    "center_x": cx,
                    "center_y": cy,
                    "bounds": {
                        "x1": int(best_x1),
                        "y1": int(best_y1),
                        "x2": int(best_x1 + scaled_tw),
                        "y2": int(best_y1 + scaled_th),
                    },
                    "search_mode": "local_roi",
                    "scale_applied": [round(scale_x, 4), round(scale_y, 4)],
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                }

        # Stage 2B: Full-screen coarse-to-fine pyramid fallback
        min_dim = min(scaled_tw, scaled_th)
        pyr_scale = 1.0 if min_dim < 28 else (0.5 if min_dim < 64 else 0.25)
        if pyr_scale < 1.0:
            c_sw = max(8, int(round(target_w * pyr_scale)))
            c_sh = max(8, int(round(target_h * pyr_scale)))
            c_tw = max(4, int(round(scaled_tw * pyr_scale)))
            c_th = max(4, int(round(scaled_th * pyr_scale)))
            s_small = np.asarray(
                scr_img.convert("L").resize((c_sw, c_sh), resample=resample_filter),
                dtype=np.float32,
            )
            t_small = np.asarray(
                tpl_scaled_img.convert("L").resize((c_tw, c_th), resample=resample_filter),
                dtype=np.float32,
            )
            _, cy_small, cx_small = self._ncc_and_sad_match(s_small, t_small)
            approx_x = int(round(cx_small / pyr_scale))
            approx_y = int(round(cy_small / pyr_scale))
            margin = 20
            fx1 = max(0, approx_x - margin)
            fy1 = max(0, approx_y - margin)
            fx2 = min(target_w, approx_x + scaled_tw + margin)
            fy2 = min(target_h, approx_y + scaled_th + margin)
            fine_roi = scr_gray[fy1:fy2, fx1:fx2]
            full_score, ly, lx = self._ncc_and_sad_match(fine_roi, tpl_gray)
            best_x1 = fx1 + lx
            best_y1 = fy1 + ly
        else:
            full_score, best_y1, best_x1 = self._ncc_and_sad_match(scr_gray, tpl_gray)

        cx = int(best_x1 + scaled_tw // 2)
        cy = int(best_y1 + scaled_th // 2)
        matched = bool(full_score >= self.threshold)
        return {
            "matched": matched,
            "confidence": round(float(full_score), 4),
            "x": cx if matched else 0,
            "y": cy if matched else 0,
            "center_x": cx if matched else 0,
            "center_y": cy if matched else 0,
            "bounds": {
                "x1": int(best_x1),
                "y1": int(best_y1),
                "x2": int(best_x1 + scaled_tw),
                "y2": int(best_y1 + scaled_th),
            },
            "search_mode": "fullscreen_fallback",
            "scale_applied": [round(scale_x, 4), round(scale_y, 4)],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }


@dataclass
class MacroStep:
    """
    Represents a single deterministic macro action with Poco XML selector, Airtest VisualTemplate,
    and relative coordinate fallback.
    """

    step_id: int
    action_type: str  # "tap", "double_tap", "long_press", "swipe", "input_text", "keyevent", "wait"
    poco_selector: Dict[str, str] = field(default_factory=dict)
    visual_template: Optional[VisualTemplate] = None
    relative_coords: Tuple[float, ...] = (0.5, 0.5)
    recorded_resolution: Tuple[int, int] = (1260, 2800)
    text_payload: str = ""
    keycode: Optional[int] = None
    wait_after_sec: float = 0.25
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": int(self.step_id),
            "action_type": str(self.action_type),
            "poco_selector": dict(self.poco_selector or {}),
            "visual_template": self.visual_template.to_dict() if self.visual_template else None,
            "relative_coords": [round(float(c), 6) for c in self.relative_coords],
            "recorded_resolution": [int(self.recorded_resolution[0]), int(self.recorded_resolution[1])],
            "text_payload": str(self.text_payload or ""),
            "keycode": int(self.keycode) if self.keycode is not None else None,
            "wait_after_sec": float(self.wait_after_sec),
            "description": str(self.description or ""),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MacroStep":
        vt_raw = data.get("visual_template")
        vt = VisualTemplate.from_dict(vt_raw) if isinstance(vt_raw, dict) else (vt_raw if isinstance(vt_raw, VisualTemplate) else None)
        rel = tuple(float(c) for c in data.get("relative_coords", (0.5, 0.5)))
        res = data.get("recorded_resolution", (1260, 2800))
        return cls(
            step_id=int(data.get("step_id", 1)),
            action_type=str(data.get("action_type", "tap")),
            poco_selector=dict(data.get("poco_selector") or {}),
            visual_template=vt,
            relative_coords=rel,
            recorded_resolution=(int(res[0]), int(res[1])),
            text_payload=str(data.get("text_payload", "")),
            keycode=int(data["keycode"]) if data.get("keycode") is not None else None,
            wait_after_sec=float(data.get("wait_after_sec", 0.25)),
            description=str(data.get("description", "")),
        )


class MacroRecorderEngine:
    """
    Records UI interactions into JSON + cropped PNG template macros and replays them across
    heterogeneous device resolutions with 0 AI tokens using the 3-stage hybrid resolution pipeline.
    """

    SUPPORTED_ACTIONS = {
        "tap",
        "double_tap",
        "long_press",
        "swipe",
        "input_text",
        "keyevent",
        "wait",
    }

    def __init__(
        self,
        macros_dir: Optional[Union[str, Path]] = None,
        adb: Optional[ADBWrapper] = None,
        touch_engine: Optional[HumanTouchEngine] = None,
        real_mgr: Optional[RealDeviceManager] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.real_mgr = real_mgr or RealDeviceManager(self.adb)
        self.touch_engine = touch_engine or HumanTouchEngine(adb=self.adb, real_mgr=self.real_mgr)
        self.macros_dir = (
            Path(macros_dir)
            if macros_dir
            else (Path(__file__).resolve().parent.parent / "config" / "macros")
        )
        self.templates_dir = self.macros_dir / "templates"
        self.macros_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        self._active_macro_name: Optional[str] = None
        self._active_resolution: Tuple[int, int] = (1260, 2800)
        self._active_steps: List[MacroStep] = []
        self._macro_cache: Dict[str, Dict[str, Any]] = {}

        self._ensure_builtin_macros()

    def _ensure_builtin_macros(self) -> None:
        """
        Pre-populate built-in zero-token macros:
        1. `tiktok_switch_and_interact`: Swipe up to next short video, wait, double-tap to like, tap comment/bookmark.
        2. `vivo_dismiss_usb_install`: Auto-confirm Vivo OriginOS / FuntouchOS USB APK installation prompt.
        """
        builtins = {
            "tiktok_switch_and_interact": {
                "macro_name": "tiktok_switch_and_interact",
                "recorded_resolution": [1260, 2800],
                "tokens_used": 0,
                "description": "Zero-token TikTok/Douyin feed swipe, watch pause, double-tap heart like, and follow/profile check.",
                "steps": [
                    MacroStep(
                        step_id=1,
                        action_type="swipe",
                        poco_selector={"resource_id": "com.ss.android.ugc.trill:id/viewpager", "class_name": "androidx.viewpager.widget.ViewPager"},
                        visual_template=None,
                        relative_coords=(0.50, 0.78, 0.50, 0.22),
                        recorded_resolution=(1260, 2800),
                        wait_after_sec=0.35,
                        description="Bezier swipe up to next video in feed",
                    ).to_dict(),
                    MacroStep(
                        step_id=2,
                        action_type="wait",
                        poco_selector={},
                        visual_template=None,
                        relative_coords=(0.50, 0.50),
                        recorded_resolution=(1260, 2800),
                        wait_after_sec=0.50,
                        description="Natural viewing dwell on video content",
                    ).to_dict(),
                    MacroStep(
                        step_id=3,
                        action_type="double_tap",
                        poco_selector={"resource_id": "com.ss.android.ugc.trill:id/like_button", "content_desc": "Like video"},
                        visual_template=None,
                        relative_coords=(0.52, 0.48),
                        recorded_resolution=(1260, 2800),
                        wait_after_sec=0.25,
                        description="Double-tap center-right to trigger heart animation",
                    ).to_dict(),
                    MacroStep(
                        step_id=4,
                        action_type="tap",
                        poco_selector={"resource_id": "com.ss.android.ugc.trill:id/comment_button", "content_desc": "Read or add comments"},
                        visual_template=None,
                        relative_coords=(0.91, 0.64),
                        recorded_resolution=(1260, 2800),
                        wait_after_sec=0.20,
                        description="Tap right-rail interaction icon",
                    ).to_dict(),
                ],
            },
            "vivo_dismiss_usb_install": {
                "macro_name": "vivo_dismiss_usb_install",
                "recorded_resolution": [1260, 2800],
                "tokens_used": 0,
                "description": "Zero-token Vivo OriginOS / FuntouchOS USB APK installation consent bottom-sheet dismissal.",
                "steps": [
                    MacroStep(
                        step_id=1,
                        action_type="tap",
                        poco_selector={
                            "resource_id": "vivo:id/continue_button",
                            "text": "Tiếp tục cài đặt",
                            "content_desc": "Cho phép cài đặt qua USB",
                            "class_name": "android.widget.Button",
                        },
                        visual_template=None,
                        relative_coords=(0.50, 0.88),
                        recorded_resolution=(1260, 2800),
                        wait_after_sec=0.30,
                        description="Tap Vivo OriginOS 'Tiếp tục cài đặt' / 'Continue installing' bottom-sheet button",
                    ).to_dict(),
                    MacroStep(
                        step_id=2,
                        action_type="tap",
                        poco_selector={
                            "resource_id": "com.android.packageinstaller:id/ok_button",
                            "text": "Cài đặt",
                            "content_desc": "Install",
                            "class_name": "android.widget.Button",
                        },
                        visual_template=None,
                        relative_coords=(0.72, 0.90),
                        recorded_resolution=(1260, 2800),
                        wait_after_sec=0.20,
                        description="Tap secondary confirm install button if present",
                    ).to_dict(),
                ],
            },
        }

        for name, payload in builtins.items():
            json_path = self.macros_dir / f"{name}.json"
            if not json_path.exists():
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            self._macro_cache[name] = payload

    def start_recording(
        self,
        macro_name: str,
        resolution: Tuple[int, int] = (1260, 2800),
    ) -> Dict[str, Any]:
        """Begin recording a new macro for a given source screen resolution."""
        self._active_macro_name = str(macro_name).strip()
        self._active_resolution = (int(resolution[0]), int(resolution[1]))
        self._active_steps = []
        return {
            "status": "RECORDING_STARTED",
            "macro_name": self._active_macro_name,
            "recorded_resolution": list(self._active_resolution),
        }

    @staticmethod
    def _parse_bounds(bounds_str: str) -> Optional[Tuple[int, int, int, int]]:
        if not bounds_str or not bounds_str.startswith("["):
            return None
        try:
            clean = bounds_str.replace("][", ",").replace("[", "").replace("]", "")
            parts = [int(v) for v in clean.split(",")]
            if len(parts) == 4:
                return parts[0], parts[1], parts[2], parts[3]
        except Exception:
            pass
        return None

    @classmethod
    def extract_poco_selector_at_point(
        cls,
        xml_dump: Optional[str],
        x: int,
        y: int,
    ) -> Dict[str, str]:
        """
        Inspect `xml_dump` and find the tightest (smallest bounding-box area) UI node
        containing `(x, y)` that exposes identifying attributes (`resource-id`, `text`, `content-desc`, `class`).
        """
        if not xml_dump or not xml_dump.strip():
            return {}
        try:
            root = ET.fromstring(xml_dump)
        except Exception:
            return {}

        best_selector: Dict[str, str] = {}
        best_area = float("inf")

        for node in root.iter("node"):
            attrib = node.attrib
            parsed = cls._parse_bounds(attrib.get("bounds", ""))
            if not parsed:
                continue
            x1, y1, x2, y2 = parsed
            if x1 <= x <= x2 and y1 <= y <= y2:
                res_id = (attrib.get("resource-id") or "").strip()
                text = (attrib.get("text") or "").strip()
                desc = (attrib.get("content-desc") or "").strip()
                cls_name = (attrib.get("class") or "").strip()
                if not (res_id or text or desc or cls_name):
                    continue
                area = float(max(1, (x2 - x1) * (y2 - y1)))
                # Prefer nodes with specific identifiers (resource_id, text, content_desc) and tighter bounds
                has_strong_id = bool(res_id or text or desc)
                effective_area = area if has_strong_id else area * 100.0
                if effective_area <= best_area:
                    best_area = effective_area
                    best_selector = {
                        "resource_id": res_id,
                        "text": text,
                        "content_desc": desc,
                        "class_name": cls_name,
                    }
        return {k: v for k, v in best_selector.items() if v != ""}

    def _crop_template_around_point(
        self,
        screen_image: Union[str, Path, bytes, np.ndarray, Image.Image],
        x: int,
        y: int,
        macro_name: str,
        step_id: int,
        crop_size: int = 120,
        threshold: float = 0.80,
    ) -> VisualTemplate:
        """
        Crop a `120x120` region centered at `(x, y)` from `screen_image`, save it as PNG under
        `config/macros/templates/`, and construct a `VisualTemplate`.
        """
        img = VisualTemplate._load_pil_image(screen_image)
        w, h = img.size
        half = crop_size // 2

        cx1 = max(0, min(w - crop_size, int(x - half)))
        cy1 = max(0, min(h - crop_size, int(y - half)))
        cx2 = min(w, cx1 + crop_size)
        cy2 = min(h, cy1 + crop_size)

        cropped = img.crop((cx1, cy1, cx2, cy2))
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(macro_name))
        tpl_filename = f"{safe_name}_step_{step_id}_{int(x)}_{int(y)}.png"
        tpl_path = (self.templates_dir / tpl_filename).resolve()
        cropped.save(str(tpl_path), format="PNG")

        buf = io.BytesIO()
        cropped.save(buf, format="PNG")
        b64_str = base64.b64encode(buf.getvalue()).decode("ascii")

        rel_x = round(float(x) / float(max(1, w)), 6)
        rel_y = round(float(y) / float(max(1, h)), 6)

        return VisualTemplate(
            tpl_path=str(tpl_path),
            record_pos=(rel_x, rel_y),
            resolution=(w, h),
            threshold=float(threshold),
            tpl_base64=b64_str,
        )

    def record_step(
        self,
        action_type: str,
        x: int = 0,
        y: int = 0,
        screen_image: Optional[Union[str, Path, bytes, np.ndarray, Image.Image]] = None,
        xml_dump: Optional[str] = None,
        **kwargs: Any,
    ) -> MacroStep:
        """
        Record a single action step:
        - Automatically extracts the XML node at `(x, y)` if `xml_dump` is provided.
        - Crops a `120x120` visual template around `(x, y)` if `screen_image` is provided.
        - Calculates normalized `relative_coords = (x / width, y / height)` (and `x2/width, y2/height` for swipes).
        """
        act = str(action_type).lower().strip()
        if act not in self.SUPPORTED_ACTIONS:
            raise ValueError(f"Unsupported macro action_type '{act}'. Supported: {sorted(self.SUPPORTED_ACTIONS)}")

        macro_name = self._active_macro_name or "recorded_macro"
        rec_w, rec_h = self._active_resolution

        if screen_image is not None:
            try:
                pil_scr = VisualTemplate._load_pil_image(screen_image)
                rec_w, rec_h = pil_scr.size
                self._active_resolution = (rec_w, rec_h)
            except Exception:
                pass

        step_id = len(self._active_steps) + 1

        # 1. Extract Poco XML selector at (x, y)
        poco_selector = dict(kwargs.get("poco_selector") or {})
        if xml_dump and not poco_selector:
            poco_selector = self.extract_poco_selector_at_point(xml_dump, int(x), int(y))

        # 2. Crop 120x120 VisualTemplate around (x, y)
        visual_tpl: Optional[VisualTemplate] = kwargs.get("visual_template")
        if screen_image is not None and visual_tpl is None:
            crop_sz = int(kwargs.get("crop_size", 120))
            thresh = float(kwargs.get("threshold", 0.80))
            visual_tpl = self._crop_template_around_point(
                screen_image=screen_image,
                x=int(x),
                y=int(y),
                macro_name=macro_name,
                step_id=step_id,
                crop_size=crop_sz,
                threshold=thresh,
            )

        # 3. Calculate normalized relative coordinates
        rel_x = round(float(x) / float(max(1, rec_w)), 6)
        rel_y = round(float(y) / float(max(1, rec_h)), 6)

        if act == "swipe":
            end_x = int(kwargs.get("end_x", kwargs.get("x2", x)))
            end_y = int(kwargs.get("end_y", kwargs.get("y2", max(0, y - 600))))
            rel_x2 = round(float(end_x) / float(max(1, rec_w)), 6)
            rel_y2 = round(float(end_y) / float(max(1, rec_h)), 6)
            rel_coords: Tuple[float, ...] = (rel_x, rel_y, rel_x2, rel_y2)
        else:
            rel_coords = (rel_x, rel_y)

        step = MacroStep(
            step_id=step_id,
            action_type=act,
            poco_selector=poco_selector,
            visual_template=visual_tpl,
            relative_coords=rel_coords,
            recorded_resolution=(rec_w, rec_h),
            text_payload=str(kwargs.get("text_payload", kwargs.get("text", ""))),
            keycode=int(kwargs["keycode"]) if kwargs.get("keycode") is not None else None,
            wait_after_sec=float(kwargs.get("wait_after_sec", 0.25)),
            description=str(kwargs.get("description", f"{act} at ({x}, {y})")),
        )
        self._active_steps.append(step)
        return step

    def save_macro(self, macro_name: Optional[str] = None) -> str:
        """Save the currently recorded macro steps to `config/macros/<macro_name>.json` and return file path."""
        name = (macro_name or self._active_macro_name or "unnamed_macro").strip()
        payload = {
            "macro_name": name,
            "recorded_resolution": [int(self._active_resolution[0]), int(self._active_resolution[1])],
            "tokens_used": 0,
            "updated_at": time.time(),
            "steps": [s.to_dict() for s in self._active_steps],
        }
        out_path = (self.macros_dir / f"{name}.json").resolve()
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        self._macro_cache[name] = payload
        return str(out_path)

    def load_macro(self, macro_name: str) -> Dict[str, Any]:
        """Load a macro dictionary by name from disk (or memory cache)."""
        name = str(macro_name).strip()
        json_path = self.macros_dir / f"{name}.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._macro_cache[name] = data
            return data
        if name in self._macro_cache:
            return self._macro_cache[name]
        raise FileNotFoundError(f"Macro '{name}' not found in {self.macros_dir}")

    def list_macros(self) -> List[str]:
        """List all available macro names on disk."""
        names = {p.stem for p in self.macros_dir.glob("*.json")}
        names.update(self._macro_cache.keys())
        return sorted(names)

    @classmethod
    def _match_poco_selector_in_xml(
        cls,
        poco_selector: Dict[str, str],
        current_xml: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Match `poco_selector` (`resource_id`, `text`, `content_desc`, `class_name`) against `current_xml`.
        Returns center `(x, y)` and `bounds` if a matching node is found.
        """
        if not poco_selector or not current_xml or not current_xml.strip():
            return None

        req_res_id = (poco_selector.get("resource_id") or "").strip()
        req_text = (poco_selector.get("text") or "").strip()
        req_desc = (poco_selector.get("content_desc") or "").strip()
        req_class = (poco_selector.get("class_name") or "").strip()

        if not (req_res_id or req_text or req_desc):
            return None

        try:
            root = ET.fromstring(current_xml)
        except Exception:
            return None

        best_candidate: Optional[Dict[str, Any]] = None
        best_score = 0

        for node in root.iter("node"):
            attrib = node.attrib
            parsed = cls._parse_bounds(attrib.get("bounds", ""))
            if not parsed:
                continue
            x1, y1, x2, y2 = parsed
            node_res = (attrib.get("resource-id") or "").strip()
            node_text = (attrib.get("text") or "").strip()
            node_desc = (attrib.get("content-desc") or "").strip()
            node_class = (attrib.get("class") or "").strip()

            score = 0
            if req_res_id:
                if node_res == req_res_id:
                    score += 5
                elif req_res_id in node_res and node_res:
                    score += 3
                else:
                    continue

            if req_text:
                if node_text == req_text:
                    score += 4
                elif req_text.lower() == node_text.lower() and node_text:
                    score += 3
                elif not req_res_id:
                    continue

            if req_desc:
                if node_desc == req_desc:
                    score += 4
                elif req_desc.lower() == node_desc.lower() and node_desc:
                    score += 3
                elif not (req_res_id or req_text):
                    continue

            if req_class and node_class == req_class:
                score += 1

            if score > best_score:
                best_score = score
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                best_candidate = {
                    "x": int(cx),
                    "y": int(cy),
                    "bounds": {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "left": x1, "top": y1, "right": x2, "bottom": y2},
                    "score": score,
                }

        return best_candidate

    def resolve_step_coordinates(
        self,
        step: Union[MacroStep, Dict[str, Any]],
        target_resolution: Tuple[int, int],
        current_screen: Optional[Union[str, Path, bytes, np.ndarray, Image.Image]] = None,
        current_xml: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Hybrid 3-Stage Coordinate Resolution Strategy (0 AI Tokens):
        1. Stage 1 (Poco / XML Node Match): If `current_xml` is available and matches `poco_selector`,
           returns exact element center `(x, y)` with `strategy="poco_xml"`.
        2. Stage 2 (Airtest Visual Template Match): If `current_screen` and `visual_template` exist,
           matches visual template and returns `(x, y)` with `strategy="visual_template"`.
        3. Stage 3 (Relative Resolution Scaling Fallback): Scales `relative_coords` to `target_resolution`
           `(int(rel_x * target_w), int(rel_y * target_h))` with `strategy="relative_scale"`.
        """
        step_obj = step if isinstance(step, MacroStep) else MacroStep.from_dict(step)
        target_w, target_h = int(target_resolution[0]), int(target_resolution[1])

        # Stage 1: Poco / XML Node Match
        if current_xml and step_obj.poco_selector:
            xml_match = self._match_poco_selector_in_xml(step_obj.poco_selector, current_xml)
            if xml_match is not None:
                res: Dict[str, Any] = {
                    "x": int(xml_match["x"]),
                    "y": int(xml_match["y"]),
                    "bounds": xml_match.get("bounds"),
                    "strategy": "poco_xml",
                    "confidence": 1.0,
                    "tokens_used": 0,
                }
                if len(step_obj.relative_coords) >= 4:
                    res["end_x"] = int(round(step_obj.relative_coords[2] * target_w))
                    res["end_y"] = int(round(step_obj.relative_coords[3] * target_h))
                return res

        # Stage 2: Airtest Visual Template Match
        if current_screen is not None and step_obj.visual_template is not None:
            tpl_res = step_obj.visual_template.match_on_screen(current_screen)
            if tpl_res.get("matched"):
                res = {
                    "x": int(tpl_res["x"]),
                    "y": int(tpl_res["y"]),
                    "bounds": tpl_res.get("bounds"),
                    "strategy": "visual_template",
                    "confidence": float(tpl_res.get("confidence", 0.0)),
                    "search_mode": tpl_res.get("search_mode"),
                    "tokens_used": 0,
                }
                if len(step_obj.relative_coords) >= 4:
                    dx_rel = step_obj.relative_coords[2] - step_obj.relative_coords[0]
                    dy_rel = step_obj.relative_coords[3] - step_obj.relative_coords[1]
                    res["end_x"] = int(round(res["x"] + dx_rel * target_w))
                    res["end_y"] = int(round(res["y"] + dy_rel * target_h))
                return res

        # Stage 3: Relative Resolution Scaling Fallback
        rel = step_obj.relative_coords
        rel_x = float(rel[0]) if len(rel) >= 1 else 0.5
        rel_y = float(rel[1]) if len(rel) >= 2 else 0.5
        scaled_x = int(round(rel_x * target_w))
        scaled_y = int(round(rel_y * target_h))

        res = {
            "x": scaled_x,
            "y": scaled_y,
            "bounds": None,
            "strategy": "relative_scale",
            "confidence": 1.0,
            "tokens_used": 0,
        }
        if len(rel) >= 4:
            res["end_x"] = int(round(float(rel[2]) * target_w))
            res["end_y"] = int(round(float(rel[3]) * target_h))
        return res

    def replay_macro(
        self,
        macro_name: str,
        serial: Optional[str] = None,
        dry_run: bool = False,
        touch_engine: Optional[HumanTouchEngine] = None,
        target_resolution: Optional[Tuple[int, int]] = None,
        current_screen: Optional[Union[str, Path, bytes, np.ndarray, Image.Image]] = None,
        current_xml: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute all steps of `macro_name` sequentially using `HumanTouchEngine`
        (Fitts's Law taps & Cubic Bézier swipes) with `tokens_used: 0`.
        """
        macro_data = self.load_macro(macro_name)
        steps_raw = macro_data.get("steps", [])
        engine = touch_engine or self.touch_engine
        dev_serial = serial or "dry_run_device"

        if target_resolution is not None:
            res_w, res_h = int(target_resolution[0]), int(target_resolution[1])
        elif not dry_run and serial:
            try:
                res_w, res_h = self.real_mgr.get_device_resolution(serial)
            except Exception:
                rec_res = macro_data.get("recorded_resolution", [1260, 2800])
                res_w, res_h = int(rec_res[0]), int(rec_res[1])
        else:
            rec_res = macro_data.get("recorded_resolution", [1260, 2800])
            res_w, res_h = int(rec_res[0]), int(rec_res[1])

        executed_steps: List[Dict[str, Any]] = []
        t0 = time.perf_counter()

        for step_dict in steps_raw:
            step = step_dict if isinstance(step_dict, MacroStep) else MacroStep.from_dict(step_dict)
            resolved = self.resolve_step_coordinates(
                step=step,
                target_resolution=(res_w, res_h),
                current_screen=current_screen,
                current_xml=current_xml,
            )
            x, y = int(resolved["x"]), int(resolved["y"])
            bounds = resolved.get("bounds")
            act = step.action_type.lower()

            action_result: Dict[str, Any] = {"status": "DRY_RUN_OK" if dry_run else "EXECUTED"}

            if not dry_run:
                if act == "tap":
                    action_result = engine.human_tap(dev_serial, x, y, bounds=bounds)
                elif act == "double_tap":
                    r1 = engine.human_tap(dev_serial, x, y, bounds=bounds, dwell_ms=45)
                    time.sleep(0.06)
                    r2 = engine.human_tap(dev_serial, x, y, bounds=bounds, dwell_ms=50)
                    action_result = {"status": "HUMAN_DOUBLE_TAP_OK", "taps": [r1, r2]}
                elif act == "long_press":
                    action_result = engine.human_tap(dev_serial, x, y, bounds=bounds, dwell_ms=650)
                elif act == "swipe":
                    end_x = int(resolved.get("end_x", x))
                    end_y = int(resolved.get("end_y", max(0, y - 500)))
                    action_result = engine.human_bezier_swipe(
                        serial=dev_serial,
                        start_x=x,
                        start_y=y,
                        end_x=end_x,
                        end_y=end_y,
                        duration_ms=520,
                        steps=12,
                    )
                elif act == "input_text":
                    action_result = engine.human_type_text(dev_serial, step.text_payload)
                elif act == "keyevent":
                    kc = int(step.keycode if step.keycode is not None else 4)
                    self.adb.press_key(dev_serial, kc)
                    action_result = {"status": "KEYEVENT_OK", "keycode": kc}
                elif act == "wait":
                    time.sleep(max(0.0, float(step.wait_after_sec)))
                    action_result = {"status": "WAIT_OK", "waited_sec": float(step.wait_after_sec)}

                if act != "wait" and step.wait_after_sec > 0:
                    time.sleep(min(float(step.wait_after_sec), 2.0))

            executed_steps.append(
                {
                    "step_id": step.step_id,
                    "action_type": act,
                    "x": x,
                    "y": y,
                    "end_x": resolved.get("end_x"),
                    "end_y": resolved.get("end_y"),
                    "strategy": resolved["strategy"],
                    "confidence": resolved.get("confidence", 1.0),
                    "action_result": action_result,
                    "tokens_used": 0,
                }
            )

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "status": "MACRO_REPLAY_OK",
            "macro_name": macro_name,
            "serial": dev_serial,
            "dry_run": bool(dry_run),
            "target_resolution": [res_w, res_h],
            "steps_executed": len(executed_steps),
            "steps": executed_steps,
            "tokens_used": 0,
            "elapsed_ms": elapsed_ms,
        }


if __name__ == "__main__":
    rec = MacroRecorderEngine()
    print("Built-in macros ready:", rec.list_macros())
