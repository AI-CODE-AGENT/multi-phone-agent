"""
Unit Tests for Subagent #43: Zero-Token GPU Geometric Contour & Orientation Visual Matcher
==========================================================================================
Tests:
1. `compute_hu_and_radial_descriptors` translation/scale invariance & non-zero shape signature.
2. `match_contour_piece_to_target` on synthetic contour puzzle images, verifying `target_coords`
   matches `target_pos=(220, 160)` within `±6px` and `tokens_used == 0`.
3. `estimate_upright_rotation_angle` on synthetic upright (`0°`) and upside-down (`180°`) objects,
   verifying exact angle recovery (`180° ± 15°` and `0° ± 15°`) and `tokens_used == 0`.
4. `ZeroTokenSemanticMatcherSubagent` (`SUBAGENT_ID == 43`) `solve_contour_or_orientation`
   and `run_self_diagnostics()`.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.semantic_object_matcher_subagent import ZeroTokenSemanticMatcherSubagent
from core.semantic_object_matcher_engine import GeometricContourAndOrientationEngine


@pytest.fixture(scope="module")
def engine() -> GeometricContourAndOrientationEngine:
    return GeometricContourAndOrientationEngine()


@pytest.fixture(scope="module")
def subagent(engine: GeometricContourAndOrientationEngine) -> ZeroTokenSemanticMatcherSubagent:
    return ZeroTokenSemanticMatcherSubagent(engine=engine)


def test_hu_and_radial_descriptors_translation_invariance(
    engine: GeometricContourAndOrientationEngine,
) -> None:
    """Verify `compute_hu_and_radial_descriptors` produces 23-D translation-invariant vectors."""
    mask_a = np.zeros((120, 120), dtype=np.float32)
    mask_a[20:55, 25:65] = 1.0
    mask_a[55:80, 15:75] = 1.0

    mask_b = np.zeros((120, 120), dtype=np.float32)
    mask_b[35:70, 40:80] = 1.0
    mask_b[70:95, 30:90] = 1.0

    desc_a = engine.compute_hu_and_radial_descriptors(mask_a)
    desc_b = engine.compute_hu_and_radial_descriptors(mask_b)

    assert isinstance(desc_a, np.ndarray)
    assert desc_a.shape == (23,)
    assert np.allclose(desc_a, desc_b, atol=1e-4)


def test_match_contour_piece_to_target_default_and_shifted(
    engine: GeometricContourAndOrientationEngine,
) -> None:
    """
    Verify `match_contour_piece_to_target` locates `target_pos=(220, 160)` within ±6px
    with `tokens_used == 0` and `gpu_accelerated == True`.
    """
    puzzle_img = engine.generate_synthetic_contour_puzzle(
        target_pos=(220, 160), piece_pos=(480, 160)
    )
    res = engine.match_contour_piece_to_target(puzzle_img)

    assert res["status"] == "CONTOUR_MATCHED"
    assert res["tokens_used"] == 0
    assert res["gpu_accelerated"] is True
    sx, sy = res["start_coords"]
    tx, ty = res["target_coords"]

    assert abs(sx - 480) <= 6
    assert abs(sy - 160) <= 6
    assert abs(tx - 220) <= 6
    assert abs(ty - 160) <= 6
    assert res["confidence"] >= 0.70

    # Also test a second target coordinate (190, 130)
    puzzle_img_2 = engine.generate_synthetic_contour_puzzle(
        target_pos=(190, 130), piece_pos=(490, 180)
    )
    res_2 = engine.match_contour_piece_to_target(puzzle_img_2)
    tx2, ty2 = res_2["target_coords"]
    assert abs(tx2 - 190) <= 6
    assert abs(ty2 - 130) <= 6
    assert res_2["tokens_used"] == 0


def test_estimate_upright_rotation_angle_0_and_180_deg(
    engine: GeometricContourAndOrientationEngine,
) -> None:
    """
    Verify `estimate_upright_rotation_angle` recovers `0°` for an upright object
    and `180° ± 15°` for an upside-down (`180°`) object with `tokens_used == 0`.
    """
    img_upright = engine.generate_synthetic_rotated_object(rotation_deg=0.0)
    res_0 = engine.estimate_upright_rotation_angle(img_upright, candidate_step_deg=15)

    assert res_0["status"] == "ORIENTATION_SOLVED"
    assert res_0["tokens_used"] == 0
    assert res_0["gpu_accelerated"] is True
    angle_0 = int(res_0["recommended_angle_deg"])
    err_0 = min(abs(angle_0 - 0), abs(360 - angle_0))
    assert err_0 <= 15
    assert res_0["taps_needed_36deg"] == 0

    img_180 = engine.generate_synthetic_rotated_object(rotation_deg=180.0)
    res_180 = engine.estimate_upright_rotation_angle(img_180, candidate_step_deg=15)

    assert res_180["status"] == "ORIENTATION_SOLVED"
    assert res_180["tokens_used"] == 0
    assert res_180["gpu_accelerated"] is True
    angle_180 = int(res_180["recommended_angle_deg"])
    assert abs(angle_180 - 180) <= 15
    assert res_180["taps_needed_36deg"] == 5
    assert res_180["symmetry_score"] >= 0.85


def test_subagent_43_solve_and_self_diagnostics(
    subagent: ZeroTokenSemanticMatcherSubagent,
) -> None:
    """
    Verify `ZeroTokenSemanticMatcherSubagent` (#43) `solve_contour_or_orientation`
    in both `contour` and `orientation` modes, plus `run_self_diagnostics()`.
    """
    assert subagent.SUBAGENT_ID == 43
    assert subagent.SUBAGENT_NAME == "ZeroTokenSemanticMatcherSubagent"

    res_contour = subagent.solve_contour_or_orientation(
        serial="10CF5L0TYL00312", mode="contour"
    )
    assert res_contour["status"] == "CONTOUR_MATCHED"
    assert res_contour["subagent_id"] == 43
    assert res_contour["tokens_used"] == 0
    tx, ty = res_contour["target_coords"]
    assert math.hypot(tx - 220, ty - 160) <= 6.0

    res_orient = subagent.solve_contour_or_orientation(
        serial="10CF5L0TYL00312", mode="orientation"
    )
    assert res_orient["status"] == "ORIENTATION_SOLVED"
    assert abs(int(res_orient["recommended_angle_deg"]) - 180) <= 15
    assert res_orient["tokens_used"] == 0

    diag = subagent.run_self_diagnostics()
    assert diag["passed"] is True
    assert diag["status"] == "SEMANTIC_MATCHER_READY"
    assert diag["subagent_id"] == 43
    assert diag["tokens_used"] == 0
