"""
End-to-End Verification Suite for AMAF v14.0 (75 Subagents + 4-Layer Anti-Bot Stealth + 10x Causal Chain).
Verifies:
1. All Subagents #66-#75 are instantiated on SelfEvolutionEngine.
2. FarmDashboardApp exposes Tab 8 and all AMAF v14.0 handlers.
3. All 45 pairs (n, a) with n >= 1, a >= 1, n + a <= 10 satisfy the strict causal recurrence:
   Loop (n + a) only started after Loop (n + a - 1) completed, verified SHA-256 parent hash,
   and consumed the rewritten prompt from Loop (n + a - 1).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agents.self_evolution_engine import SelfEvolutionEngine
from gui.farm_dashboard import FarmDashboardApp


def test_self_evolution_engine_has_75_subagents() -> None:
    engine = SelfEvolutionEngine()
    required_v14_attrs = [
        "sigma_lognormal_kinematics",
        "patchright_stealth_cdp",
        "sensor_coherence_guard",
        "turnstile_waf_defense",
        "antibot_radar_telemetry",
        "mobile_header_filter_refiner",
        "cognitive_rhythm_pacer",
        "cross_layer_bot_correlator",
        "unified_ui_antibot_finish_gate",
        "causal_10x_antibot_ui_ux_coordinator",
    ]
    for attr in required_v14_attrs:
        assert hasattr(engine, attr), f"Missing v14 subagent attribute: {attr}"
        assert getattr(engine, attr) is not None


def test_farm_dashboard_exposes_v14_handlers() -> None:
    required_methods = [
        "_build_v14_antibot_and_causal_tab",
        "on_v14_sigma_lognormal_swipe",
        "on_v14_stealth_cdp_audit",
        "on_v14_sensor_recoil_audit",
        "on_v14_unified_finish_gate",
        "on_v14_run_10x_causal_evolution",
    ]
    for method_name in required_methods:
        assert hasattr(FarmDashboardApp, method_name), f"Missing {method_name} on FarmDashboardApp"


def test_v14_10x_causal_chain_n_plus_a_depends_on_n_plus_a_minus_1() -> None:
    engine = SelfEvolutionEngine()
    summary = engine.causal_10x_antibot_ui_ux_coordinator.execute(
        live_serial="10CF5L0TYL00312",
        write_report=True,
    )
    assert summary["total_iterations"] == 10
    assert summary["final_composite_score"] >= 98.0
    assert summary["final_bot_risk_pct"] <= 2.0
    assert summary["final_gate"] == "PASS"
    assert summary["causal_chain_verified"] is True
    assert summary["invariants"]["causal_chain_valid"] is True
    assert summary["invariants"]["total_na_pairs_verified"] == 45

    # Also verify the 10 live Vivo V2417A sequential JSON artifacts on disk if present
    artifact_dir = Path(r"C:\Users\Admin\.gemini\antigravity\brain\b1bc24df-05e3-49c2-a4dd-8d28d0b1b59b")
    loop_files = [artifact_dir / f"v14_loop_{i:02d}_result.json" for i in range(1, 11)]
    if all(f.exists() for f in loop_files):
        records = [json.loads(f.read_text(encoding="utf-8")) for f in loop_files]
        for n in range(1, 10):
            for a in range(1, 11 - n):
                k = n + a  # 1-based loop index (2..10)
                curr = records[k - 1]
                prev = records[k - 2]
                assert curr["started_at_ns"] > prev["completed_at_ns"], (
                    f"Loop {k} (n={n}, a={a}) started before Loop {k-1} completed!"
                )
                assert curr["parent_result_sha256"] == prev["result_sha256"]
                assert curr["input_prompt"] == prev["rewritten_prompt_for_next_loop"]
