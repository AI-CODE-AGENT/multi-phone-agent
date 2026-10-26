"""
End-to-End Integration Test for AMAF 10.0 (45 Subagents + Persistent ADB Stream + IME/Viewport Guard + Semantic GPU + Account Vault + Visual DAG)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.self_evolution_engine import SelfEvolutionEngine
from agents.persistent_adb_stream_subagent import PersistentADBStreamSubagent
from agents.keyboard_viewport_guard_subagent import KeyboardAndViewportGuardSubagent
from agents.semantic_object_matcher_subagent import ZeroTokenSemanticMatcherSubagent
from agents.account_vault_proxy_subagent import MultiAccountVaultAndProxySubagent
from agents.visual_flow_dag_subagent import VisualFlowBuilderAndLiveMonitorSubagent
from gui.farm_dashboard import FarmDashboardApp


def test_all_45_subagents_instantiated_in_self_evolution_engine():
    eng = SelfEvolutionEngine()
    assert isinstance(eng.persistent_stream, PersistentADBStreamSubagent)
    assert isinstance(eng.kbd_viewport_guard, KeyboardAndViewportGuardSubagent)
    assert isinstance(eng.semantic_matcher, ZeroTokenSemanticMatcherSubagent)
    assert isinstance(eng.account_vault, MultiAccountVaultAndProxySubagent)
    assert isinstance(eng.visual_flow_dag, VisualFlowBuilderAndLiveMonitorSubagent)

    assert eng.persistent_stream.SUBAGENT_ID == 41
    assert eng.kbd_viewport_guard.SUBAGENT_ID == 42
    assert eng.semantic_matcher.SUBAGENT_ID == 43
    assert eng.account_vault.SUBAGENT_ID == 44
    assert eng.visual_flow_dag.SUBAGENT_ID == 45


def test_amaf_v10_subagents_41_to_45_zero_token_execution():
    eng = SelfEvolutionEngine()
    serial = "10CF5L0TYL00312"

    # #41 Persistent ADB Stream & Zero-Flash RAM Frame Streamer
    res41 = eng.persistent_stream.run_stream_benchmark(serial)
    assert res41["status"] == "BENCHMARK_OK"
    assert res41["flash_writes"] == 0
    assert res41["tokens_used"] == 0

    # #42 Keyboard & Viewport Auto-Guard
    res42 = eng.kbd_viewport_guard.guard_input_and_viewport(serial, target_x=400, target_y=2200, dry_run=True)
    assert res42["status"] == "INPUT_AND_VIEWPORT_GUARDED"
    assert res42["tokens_used"] == 0

    # #43 Zero-Token GPU Geometric Contour & Upright Orientation Matcher
    res43 = eng.semantic_matcher.run_self_diagnostics()
    assert res43["status"] == "SEMANTIC_MATCHER_READY"
    assert res43["passed"] is True
    assert res43["tokens_used"] == 0

    # #44 Multi-Account Vault & Proxy Isolation
    res44 = eng.account_vault.run_vault_and_proxy_audit(serial, dry_run=True)
    assert res44["status"] == "VAULT_AND_PROXY_AUDITED"
    assert res44["accounts_count"] >= 2
    assert res44["tokens_used"] == 0

    # #45 Visual Flow DAG & Live Screen Preview Monitor
    res45 = eng.visual_flow_dag.execute_dag("tiktok_smart_switch_and_engage_dag", serial=serial, dry_run=True)
    assert res45["status"] == "DAG_COMPLETED"
    assert res45["tokens_used"] == 0
    preview = eng.visual_flow_dag.render_annotated_preview_frame(
        touch_points=[(630, 1400)],
        boxes=[{"bbox": (200, 300, 800, 600), "label": "TARGET"}],
        preview_size=(320, 700),
    )
    assert preview.size == (320, 700)


def test_farm_dashboard_v10_handlers_present():
    assert hasattr(FarmDashboardApp, "_build_v10_stream_vault_dag_tab")
    assert hasattr(FarmDashboardApp, "on_v10_stream_benchmark")
    assert hasattr(FarmDashboardApp, "on_v10_kbd_viewport_guard")
    assert hasattr(FarmDashboardApp, "on_v10_semantic_matcher")
    assert hasattr(FarmDashboardApp, "on_v10_account_vault")
    assert hasattr(FarmDashboardApp, "on_v10_visual_dag")
