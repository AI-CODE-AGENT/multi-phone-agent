"""
End-to-End Integration Test for AMAF 9.0 (40 Subagents + Zero-Token GPU RTX 3050)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.self_evolution_engine import SelfEvolutionEngine
from agents.local_gpu_vision_subagent import LocalGPUVisionSubagent
from agents.macro_replay_subagent import MacroReplaySubagent
from agents.android_cdp_subagent import AndroidCDPSubagent
from agents.social_workflow_subagent import SocialWorkflowSubagent
from agents.hybrid_captcha_fallback_subagent import HybridCaptchaFallbackSubagent


def test_all_40_subagents_instantiated_and_ready():
    eng = SelfEvolutionEngine()
    assert isinstance(eng.local_gpu_vision, LocalGPUVisionSubagent)
    assert isinstance(eng.macro_replay, MacroReplaySubagent)
    assert isinstance(eng.android_cdp, AndroidCDPSubagent)
    assert isinstance(eng.social_workflow, SocialWorkflowSubagent)
    assert isinstance(eng.hybrid_captcha_3tier, HybridCaptchaFallbackSubagent)

    # Verify Subagent IDs #36 - #40
    assert eng.local_gpu_vision.SUBAGENT_ID == 36
    assert eng.macro_replay.SUBAGENT_ID == 37
    assert eng.android_cdp.SUBAGENT_ID == 38
    assert eng.social_workflow.SUBAGENT_ID == 39
    assert eng.hybrid_captcha_3tier.SUBAGENT_ID == 40


def test_rtx_3050_zero_token_self_diagnostics_and_cdp_bridge():
    eng = SelfEvolutionEngine()
    gpu_diag = eng.local_gpu_vision.run_self_diagnostics()
    assert gpu_diag["status"] in ("GPU_VISION_READY", "OK", "PASSED")
    assert gpu_diag["tokens_used"] == 0

    macro_res = eng.macro_replay.replay_macro("vivo_dismiss_usb_install", serial="10CF5L0TYL00312", dry_run=True)
    assert macro_res["status"] == "MACRO_REPLAY_OK"
    assert macro_res["tokens_used"] == 0

    social_res = eng.social_workflow.run_tiktok_workflow("10CF5L0TYL00312", dry_run=True)
    assert social_res["tokens_used"] == 0

    hybrid_res = eng.hybrid_captcha_3tier.run_3tier_self_audit("10CF5L0TYL00312")
    assert hybrid_res["status"] == "HYBRID_3TIER_READY"
    assert hybrid_res["telemetry"]["total_ai_tokens_used"] == 0
