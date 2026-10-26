"""
Zero-Token GPU Geometric Contour & Orientation Visual Matcher Subagent (Subagent #43)
=====================================================================================
Wraps `GeometricContourAndOrientationEngine` (`NVIDIACudaPTXAccelerator` PTX `sm_86` Sobel
kernels + 2D FFT Edge Cross-Correlation + Hu/Radial Moments + PyTorch Orientation Conv Head)
to solve interactive geometric shape-contour drag puzzles and circular object orientation
CAPTCHAs on Android devices (`serial="10CF5L0TYL00312"`) with `tokens_used == 0`.
"""

import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager
from core.semantic_object_matcher_engine import GeometricContourAndOrientationEngine


class ZeroTokenSemanticMatcherSubagent:
    """
    Subagent #43: Zero-Token GPU Geometric Contour & Orientation Visual Matcher Subagent.
    Solves geometric shape contour matching and circular upright orientation detection
    entirely on the local NVIDIA GeForce RTX 3050 GPU with `tokens_used == 0`.
    """

    SUBAGENT_ID = 43
    SUBAGENT_NAME = "ZeroTokenSemanticMatcherSubagent"

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
        engine: Optional[GeometricContourAndOrientationEngine] = None,
    ) -> None:
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.engine = engine or GeometricContourAndOrientationEngine()
        self.history: List[Dict[str, Any]] = []

    def _infer_mode(
        self,
        mode: str,
        image_input: Optional[Union[str, Path, Image.Image, np.ndarray]],
    ) -> str:
        """Infer `'contour'` vs `'orientation'` when `mode == 'auto'`."""
        norm = (mode or "auto").strip().lower()
        if norm in ("contour", "shape", "puzzle", "contour_match"):
            return "contour"
        if norm in ("orientation", "rotate", "rotation", "upright"):
            return "orientation"

        if image_input is not None:
            try:
                rgb = self.engine._load_rgb_array(image_input)
                h, w, _ = rgb.shape
                # Nearly-square patches are circular orientation puzzles; wide canvases are contour drag puzzles
                if abs(w - h) <= int(0.18 * max(w, h)):
                    return "orientation"
                return "contour"
            except Exception:
                pass
        return "contour"

    def solve_contour_or_orientation(
        self,
        serial: str = "10CF5L0TYL00312",
        mode: str = "auto",
        image_input: Optional[Union[str, Path, Image.Image, np.ndarray]] = None,
        piece_bbox: Optional[Tuple[int, int, int, int]] = None,
        search_roi: Optional[Tuple[int, int, int, int]] = None,
        candidate_step_deg: int = 15,
    ) -> Dict[str, Any]:
        """
        Solve a geometric contour puzzle or upright orientation challenge on `serial`
        with `tokens_used == 0`.
        """
        resolved_mode = self._infer_mode(mode, image_input)

        if resolved_mode == "orientation":
            target_img = (
                image_input
                if image_input is not None
                else self.engine.generate_synthetic_rotated_object(rotation_deg=180.0)
            )
            engine_res = self.engine.estimate_upright_rotation_angle(
                target_img, candidate_step_deg=candidate_step_deg
            )
        else:
            target_img = (
                image_input
                if image_input is not None
                else self.engine.generate_synthetic_contour_puzzle(
                    target_pos=(220, 160), piece_pos=(480, 160)
                )
            )
            engine_res = self.engine.match_contour_piece_to_target(
                target_img, piece_bbox=piece_bbox, search_roi=search_roi
            )

        record: Dict[str, Any] = {
            "subagent": self.SUBAGENT_NAME,
            "subagent_id": self.SUBAGENT_ID,
            "serial": serial,
            "mode": resolved_mode,
            **engine_res,
            "tokens_used": 0,
        }
        self.history.append(record)
        return record

    def run_self_diagnostics(self) -> Dict[str, Any]:
        """
        Run deterministic end-to-end self-diagnostics verifying:
        1. Hu + Radial 23-D invariant descriptor extraction.
        2. Geometric contour puzzle matching within <= 6px error (`target_pos=(220, 160)`).
        3. Upright orientation angle recovery for both `0°` and `180°` rotated objects.
        4. Zero AI token consumption (`tokens_used == 0`).
        """
        t0 = time.perf_counter()
        telemetry = self.engine.get_gpu_telemetry()

        # 1. Contour puzzle self-test
        puzzle_img = self.engine.generate_synthetic_contour_puzzle(
            target_pos=(220, 160), piece_pos=(480, 160)
        )
        contour_res = self.engine.match_contour_piece_to_target(puzzle_img)
        tx, ty = contour_res["target_coords"]
        contour_err_px = math.hypot(tx - 220.0, ty - 160.0)

        # 2. Upright orientation self-test (0 deg and 180 deg)
        upright_img = self.engine.generate_synthetic_rotated_object(rotation_deg=0.0)
        rot180_img = self.engine.generate_synthetic_rotated_object(rotation_deg=180.0)
        res_0 = self.engine.estimate_upright_rotation_angle(upright_img, candidate_step_deg=15)
        res_180 = self.engine.estimate_upright_rotation_angle(rot180_img, candidate_step_deg=15)

        angle_0 = int(res_0["recommended_angle_deg"])
        angle_180 = int(res_180["recommended_angle_deg"])
        err_0 = min(abs(angle_0 - 0), abs(360 - angle_0))
        err_180 = abs(angle_180 - 180)

        passed = (
            contour_err_px <= 6.0
            and err_0 <= 15
            and err_180 <= 15
            and contour_res.get("tokens_used") == 0
            and res_0.get("tokens_used") == 0
            and res_180.get("tokens_used") == 0
        )

        total_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "subagent": f"{self.SUBAGENT_NAME} (#{self.SUBAGENT_ID})",
            "subagent_id": self.SUBAGENT_ID,
            "status": "SEMANTIC_MATCHER_READY" if passed else "DEGRADED",
            "passed": bool(passed),
            "gpu_telemetry": telemetry,
            "contour_benchmark": {
                **contour_res,
                "expected_target_coords": (220, 160),
                "euclidean_error_px": round(contour_err_px, 3),
            },
            "orientation_0deg_benchmark": res_0,
            "orientation_180deg_benchmark": res_180,
            "total_diagnostic_ms": total_ms,
            "tokens_used": 0,
        }


SemanticObjectMatcherSubagent = ZeroTokenSemanticMatcherSubagent

