"""
Unit tests for Proposal 5 (Subagent #40: Hybrid 3-Tier CAPTCHA Defense Bridge)
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.hybrid_captcha_defense_bridge import HybridCaptchaDefenseBridge
from agents.hybrid_captcha_fallback_subagent import HybridCaptchaFallbackSubagent


def test_tier1_checkbox_and_slider_zero_token():
    bridge = HybridCaptchaDefenseBridge()

    # 1. Checkbox
    res_cb = bridge.solve_captcha_3tier({"type": "checkbox", "screen_size": (1260, 2800)})
    assert res_cb["status"] == "SOLVED"
    assert res_cb["tier_used"] == 1
    assert res_cb["tokens_used"] == 0
    assert res_cb["cost_usd"] == 0.0
    assert res_cb["target_coords"] == (204, 1612)

    # 2. Synthetic slider image with dark gap at x=320..360
    img = Image.new("RGB", (600, 300), (220, 220, 220))
    draw = ImageDraw.Draw(img)
    draw.rectangle([320, 90, 370, 160], fill=(25, 25, 25))
    res_sl = bridge.solve_captcha_3tier({"type": "slider", "image": img, "slider_start": (100, 250)})
    assert res_sl["status"] == "SOLVED"
    assert res_sl["tier_used"] == 1
    assert res_sl["tokens_used"] == 0
    assert 300 <= res_sl["drag_distance_px"] <= 380


def test_tier2_local_audio_stft_ctc_decoder_zero_token():
    bridge = HybridCaptchaDefenseBridge()
    wav_bytes = bridge.synthesize_spoken_digits_wav("4829")
    res_audio = bridge.solve_captcha_3tier({
        "type": "audio",
        "audio_wav_bytes": wav_bytes,
    })
    assert res_audio["status"] == "SOLVED"
    assert res_audio["tier_used"] == 2
    assert res_audio["tokens_used"] == 0
    assert res_audio["transcription"] == "4829"
    assert res_audio["segments_detected"] == 4


def test_tier3_external_api_schema_and_escalation():
    bridge = HybridCaptchaDefenseBridge(confidence_threshold=0.75)

    # Automatic escalation from low_confidence Tier 1 -> Tier 2
    res_esc = bridge.solve_captcha_3tier({"type": "low_confidence", "expected_digits": "9163"})
    assert res_esc["status"] == "SOLVED"
    assert res_esc["tier_used"] == 2
    assert res_esc["transcription"] == "9163"
    assert res_esc["tokens_used"] == 0

    # Explicit Tier 3 token bridge formatting across 2captcha, capsolver, anticaptcha
    for provider in ("2captcha", "capsolver", "anticaptcha"):
        res_t3 = bridge.solve_captcha_3tier({
            "type": "token_api",
            "provider": provider,
            "websiteURL": "https://2captcha.com/demo",
            "force_tier": 3,
        })
        assert res_t3["status"] == "SOLVED"
        assert res_t3["tier_used"] == 3
        assert res_t3["provider"] == provider
        assert "SANDBOX_VERIFIED" in res_t3["solution"]["token"]


def test_subagent_40_self_audit():
    sub = HybridCaptchaFallbackSubagent()
    audit = sub.run_3tier_self_audit("10CF5L0TYL00312")
    assert audit["status"] == "HYBRID_3TIER_READY"
    assert audit["subagent_id"] == 40
    assert audit["tier2_audio_decoded"] == "5924"
    assert audit["telemetry"]["total_ai_tokens_used"] == 0
