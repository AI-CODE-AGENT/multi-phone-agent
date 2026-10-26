"""
Unit & Hardware Integration Tests for Proposal 1 (Subagent #36):
Local Zero-Token GPU Vision & Neural OCR Engine (`core/local_gpu_vision_ocr_engine.py`
and `agents/local_gpu_vision_subagent.py`).
Tests:
1. `NVIDIACudaPTXAccelerator` on the local NVIDIA GeForce RTX 3050 GPU (`get_gpu_telemetry`,
   `gpu_sobel_gradient_sm86`, and `gpu_sad_template_scan_sm86` PTX `sm_86` execution).
2. `solve_ocr_captcha` on synthetic and real-style CAPTCHA images (`E8W9`, `TNTDW`, `7K4M`, `2026`),
   verifying exact character recognition and `tokens_used == 0`.
3. `locate_slider_gap_gpu` on synthetic slider puzzle images.
4. `match_template_gpu` finding an embedded button template inside a 1260x2800 screen.
5. `classify_grid_3x3_zero_token` on 3x3 CAPTCHA grid images.
6. `LocalGPUVisionSubagent` (`audit_gpu_status`, `solve_screen_captcha_zero_token`, `run_self_diagnostics`).
"""

import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.local_gpu_vision_subagent import LocalGPUVisionSubagent
from core.local_gpu_vision_ocr_engine import (
    CRNNCTCModel,
    LocalGPUVisionOCREngine,
    NVIDIACudaPTXAccelerator,
    ZeroTokenNeuralOCREngine,
)
from core.universal_captcha_cv_engine import UniversalCaptchaCVEngine


@pytest.fixture(scope="module")
def gpu_engine() -> LocalGPUVisionOCREngine:
    return LocalGPUVisionOCREngine()


@pytest.fixture(scope="module")
def gpu_subagent(gpu_engine: LocalGPUVisionOCREngine) -> LocalGPUVisionSubagent:
    return LocalGPUVisionSubagent(engine=gpu_engine)


@pytest.fixture(scope="module")
def scratch_dir() -> Path:
    d = Path(__file__).resolve().parent.parent / "logs" / "test_gpu_vision_tmp"
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_nvidia_cuda_ptx_accelerator_telemetry_and_kernels(gpu_engine: LocalGPUVisionOCREngine) -> None:
    """Verify RTX 3050 telemetry and real PTX `sm_86` kernel execution (`sobel` + `sad`)."""
    accel: NVIDIACudaPTXAccelerator = gpu_engine.accelerator
    telemetry = accel.get_gpu_telemetry()

    assert telemetry["zero_token_mode"] is True
    assert isinstance(telemetry["gpu_name"], str) and len(telemetry["gpu_name"]) > 0
    if telemetry["cuda_driver_active"]:
        assert "RTX 3050" in telemetry["gpu_name"] or "NVIDIA" in telemetry["gpu_name"]
        assert telemetry["compute_capability"] == "sm_86"
        assert telemetry["vram_total_mb"] >= 4000
        assert telemetry["vram_free_mb"] > 0

    # Test 1D/2D PTX Sobel kernel
    test_img = np.zeros((64, 64), dtype=np.float32)
    test_img[:, 32:] = 200.0
    grad = accel.gpu_sobel_gradient_sm86(test_img)
    assert grad.shape == (64, 64)
    # Sharp vertical step edge at column 31->32 must produce peak gradient ~200
    assert float(np.max(grad[:, 31])) >= 195.0
    assert float(np.mean(grad[:, 5])) == 0.0

    # Test PTX SAD kernel
    patch_a = np.full((32, 32), 150.0, dtype=np.float32)
    patch_b = np.full((32, 32), 90.0, dtype=np.float32)
    sad = accel.gpu_sad_template_scan_sm86(patch_a, patch_b)
    assert sad.shape == (32, 32)
    assert np.allclose(sad, 60.0, atol=1e-3)


@pytest.mark.parametrize("target_code", ["E8W9", "TNTDW", "7K4M", "2026"])
def test_solve_ocr_captcha_zero_token(
    gpu_engine: LocalGPUVisionOCREngine,
    scratch_dir: Path,
    target_code: str,
) -> None:
    """Verify `solve_ocr_captcha` decodes alphanumeric CAPTCHA strings with `tokens_used == 0`."""
    img_path = str(scratch_dir / f"captcha_{target_code}.png")
    gpu_engine.ocr_engine.generate_synthetic_ocr_captcha_image(
        text=target_code,
        save_path=img_path,
        add_noise=True,
    )
    res = gpu_engine.solve_ocr_captcha(img_path)

    assert res["tokens_used"] == 0
    assert res["engine"] == "gpu_ptx_crnn_zero_token"
    assert res["text"] == target_code
    assert res["confidence"] >= 0.70
    assert res["latency_ms"] >= 0.0


def test_locate_slider_gap_gpu_ptx(
    gpu_engine: LocalGPUVisionOCREngine,
    scratch_dir: Path,
) -> None:
    """Verify `locate_slider_gap_gpu` accurately finds the jigsaw cavity on synthetic slider images."""
    cv_gen = UniversalCaptchaCVEngine()
    slider_path = str(scratch_dir / "slider_gap_355.png")
    cv_gen.generate_synthetic_slider_puzzle_image(
        save_path=slider_path,
        width=520,
        height=260,
        gap_x=355,
        gap_y=110,
        piece_size=54,
    )

    res = gpu_engine.locate_slider_gap_gpu(slider_path, piece_start_x=45, piece_size=54)
    assert res["tokens_used"] == 0
    assert res["engine"] == "gpu_ptx_sobel_sm86"
    assert abs(res["gap_x"] - 355) <= 15
    assert abs(res["gap_y"] - 110) <= 20
    assert abs(res["drag_distance"] - (res["gap_x"] - 45)) <= 1


def test_match_template_gpu_on_1260x2800_screen(
    gpu_engine: LocalGPUVisionOCREngine,
) -> None:
    """Verify `match_template_gpu` locates an embedded button inside a 1260x2800 mobile screen."""
    screen_w, screen_h = 1260, 2800
    screen = Image.new("RGB", (screen_w, screen_h), (24, 28, 36))
    s_draw = ImageDraw.Draw(screen)

    # Draw background UI bars
    for y in range(200, 2400, 300):
        s_draw.rectangle([80, y, 1180, y + 90], fill=(42, 48, 60))

    # Create distinct button template (160x64)
    btn_w, btn_h = 160, 64
    template = Image.new("RGB", (btn_w, btn_h), (235, 85, 45))
    t_draw = ImageDraw.Draw(template)
    t_draw.rectangle([4, 4, btn_w - 5, btn_h - 5], outline=(255, 245, 200), width=3)
    t_draw.ellipse([20, 14, 56, 50], fill=(255, 255, 255), outline=(20, 20, 20), width=2)
    t_draw.rectangle([72, 22, 140, 42], fill=(255, 250, 240))

    # Embed button at top-left (740, 1820) -> center (820, 1852)
    embed_x, embed_y = 740, 1820
    screen.paste(template, (embed_x, embed_y))

    res = gpu_engine.match_template_gpu(screen, template, threshold=0.8)
    expected_cx = embed_x + btn_w // 2
    expected_cy = embed_y + btn_h // 2

    assert res["tokens_used"] == 0
    assert res["matched"] is True
    assert res["score"] >= 0.85
    assert abs(res["x"] - expected_cx) <= 8
    assert abs(res["y"] - expected_cy) <= 8


def test_classify_grid_3x3_zero_token(
    gpu_engine: LocalGPUVisionOCREngine,
    scratch_dir: Path,
) -> None:
    """Verify `classify_grid_3x3_zero_token` identifies all target tiles in a 3x3 CAPTCHA grid."""
    expected_cells = [0, 4, 8]
    grid_path = str(scratch_dir / "grid_3x3.png")
    gpu_engine.generate_synthetic_grid_3x3_image(
        target_label="traffic_light",
        matching_indices=expected_cells,
        save_path=grid_path,
        size=360,
    )

    res = gpu_engine.classify_grid_3x3_zero_token(grid_path, target_label="traffic_light")
    assert res["tokens_used"] == 0
    assert res["matching_indices"] == expected_cells
    assert len(res["matching_coordinates"]) == 3
    # Cell 0 center in 360x360 is (60, 60), Cell 4 is (180, 180), Cell 8 is (300, 300)
    assert res["matching_coordinates"][0] == (60, 60)
    assert res["matching_coordinates"][1] == (180, 180)
    assert res["matching_coordinates"][2] == (300, 300)


def test_local_gpu_vision_subagent_end_to_end(
    gpu_subagent: LocalGPUVisionSubagent,
    scratch_dir: Path,
) -> None:
    """Verify Subagent #36 wrapper methods (`audit_gpu_status`, `solve_screen_captcha_zero_token`, `run_self_diagnostics`)."""
    status = gpu_subagent.audit_gpu_status()
    assert status["tokens_used"] == 0
    assert status["telemetry"]["zero_token_mode"] is True

    ocr_file = str(scratch_dir / "subagent_ocr.png")
    gpu_subagent.engine.ocr_engine.generate_synthetic_ocr_captcha_image("TNTDW", save_path=ocr_file)
    solve_res = gpu_subagent.solve_screen_captcha_zero_token(
        serial="emulator-5554",
        screenshot_path=ocr_file,
        mode="ocr",
    )
    assert solve_res["tokens_used"] == 0
    assert solve_res["result"]["text"] == "TNTDW"

    diag = gpu_subagent.run_self_diagnostics()
    assert diag["passed"] is True
    assert diag["tokens_used"] == 0
