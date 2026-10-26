"""
End-to-End Integration Tests for AMAF v13.0 (65 Subagents Total):
- Verifies SelfEvolutionEngine wires all 65 subagents (#1-#65)
- Verifies FarmDashboardApp exposes all AMAF v13.0 UI/UX Design System, Ctrl+K Palette & Vivo Screenshot Critic handlers
- Verifies 10-iteration sequential UI/UX evolution loop achieves PASS on the UI Finish-Gate Reviewer
"""

from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager
from core.kanban_board import KanbanBoard
from agents.self_evolution_engine import SelfEvolutionEngine
from gui.farm_dashboard import FarmDashboardApp


def test_self_evolution_engine_has_65_subagents():
    adb = ADBWrapper()
    memory = MemoryManager()
    kanban = KanbanBoard()
    engine = SelfEvolutionEngine(adb, memory, kanban)

    # Check Subagents #56-#65 attributes exist on SelfEvolutionEngine
    assert hasattr(engine, "ui_screenshot_critic")
    assert hasattr(engine, "design_token_8pt")
    assert hasattr(engine, "sidebar_ia")
    assert hasattr(engine, "command_palette")
    assert hasattr(engine, "bento_device_card")
    assert hasattr(engine, "semantic_cta_anti_rainbow")
    assert hasattr(engine, "wcag_typography")
    assert hasattr(engine, "micro_interaction_empty")
    assert hasattr(engine, "ui_finish_gate")
    assert hasattr(engine, "recursive_10x_ui_ux_coordinator")

    # Verify sidebar IA covers all 65 subagents across 5 Miller's Law workspaces
    ia_cov = engine.sidebar_ia.audit_information_architecture()
    assert ia_cov["complete_65_coverage"] is True
    assert ia_cov["total_mapped_subagents"] == 65
    assert ia_cov["millers_law_compliant"] is True


def test_farm_dashboard_exposes_v13_handlers():
    required_methods = [
        "_build_v13_ui_ux_and_critic_tab",
        "on_v13_ctrl_k_search",
        "on_v13_screenshot_critique",
        "on_v13_bento_sparkline",
        "on_v13_finish_gate_audit",
        "on_v13_run_10x_ui_ux_evolution",
    ]
    for method_name in required_methods:
        assert hasattr(FarmDashboardApp, method_name), f"Missing {method_name} on FarmDashboardApp"


def test_v13_10x_sequential_ui_ux_coordinator_e2e():
    adb = ADBWrapper()
    memory = MemoryManager()
    kanban = KanbanBoard()
    engine = SelfEvolutionEngine(adb, memory, kanban)

    res = engine.recursive_10x_ui_ux_coordinator.execute(live_serial="10CF5L0TYL00312", write_report=False)
    assert res["total_iterations"] == 10
    assert res["final_beauty_score"] >= 96.0
    assert res["final_finish_gate_decision"] == "PASS"
    assert len(res["iterations"]) == 10
    # Verify sequential prompt rewriting across all 10 loops
    for idx, item in enumerate(res["iterations"], start=1):
        assert item["iteration"] == idx
        assert len(item["rewritten_next_loop_prompt"]) > 40
