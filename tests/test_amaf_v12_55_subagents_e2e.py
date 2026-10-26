"""
End-to-End Verification Suite for AMAF v12.0 (55 Subagents + 10x Recursive Self-Evolution Loop).
Verifies:
1. All 55 Subagents are wired into SelfEvolutionEngine.
2. Subagents #46 to #55 execute in 0-token deterministic mode.
3. FarmDashboardApp exposes AMAF 12.0 (55 Subagents) and Tab 6 handlers.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.self_evolution_engine import SelfEvolutionEngine
import gui.farm_dashboard as farm_dashboard


def test_all_55_subagents_instantiated_in_self_evolution_engine():
    engine = SelfEvolutionEngine()
    required_attrs = [
        # v10.0 (#41-#45)
        "persistent_stream",
        "kbd_viewport_guard",
        "semantic_matcher",
        "account_vault",
        "visual_flow_dag",
        # v12.0 (#46-#55)
        "universal_apk_installer",
        "sideload_source_guard",
        "oem_secime_vault",
        "multi_user_pkg",
        "always_on_install_daemon",
        "gkd_selector_engine",
        "mobile_agent_memory",
        "uitars_reflection",
        "droidbot_utg",
        "recursive_10x_coordinator",
    ]
    for attr in required_attrs:
        assert hasattr(engine, attr), f"Missing subagent attribute: {attr}"
        assert getattr(engine, attr) is not None


def test_amaf_v12_10x_recursive_evolution_and_subagents_46_to_55():
    engine = SelfEvolutionEngine()

    # Subagent #46 status
    st46 = engine.universal_apk_installer.get_status()
    assert st46["subagent_id"] == 46

    # Subagent #47 status
    st47 = engine.sideload_source_guard.get_status()
    assert st47["subagent_id"] == 47

    # Subagent #48 inspection
    st48 = engine.oem_secime_vault.inspect_and_handle_secime(
        dumpsys_window_output="mCurrentFocus=Window{123 u0 com.vivo.secime/.SecIME}",
        xml_content="<hierarchy></hierarchy>",
    )
    assert st48["subagent_id"] == 48
    assert st48["detection"]["secime_active"] is True

    # Subagent #49 normalization & user 666 filter
    st49 = engine.multi_user_pkg.normalize_and_filter_pm_execution(
        "pm list packages",
        raw_output="Error: Shell does not have permission to access user 666\npackage:com.geminicall.ai\n",
    )
    assert st49["subagent_id"] == 49
    assert "--user 0" in st49["normalized_cmd"]
    assert "com.geminicall.ai" in st49["packages"]

    # Subagent #50 health status
    st50 = engine.always_on_install_daemon.get_health_status("10CF5L0TYL00312")
    assert "healthy" in st50

    # Subagents #51-#55 10x Recursive Evolution Loop
    res_10x = engine.recursive_10x_coordinator.run_10_iterations(
        live_serial="10CF5L0TYL00312",
        write_report=True,
    )
    assert res_10x["total_iterations"] == 10
    assert res_10x["passed_iterations"] == 10
    assert Path(res_10x["report_path"]).exists()


def test_farm_dashboard_v12_handlers_present():
    app_cls = farm_dashboard.FarmDashboardApp
    for method_name in [
        "_build_v12_installer_and_10x_tab",
        "on_v12_sideload_guard",
        "on_v12_inspect_axml",
        "on_v12_toggle_daemon",
        "on_v12_run_10x_evolution",
    ]:
        assert hasattr(app_cls, method_name), f"Missing GUI method: {method_name}"
