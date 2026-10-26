"""
Unit & Integration Tests for AMAF v17.0:
- Dual-Theme Light Mode (★) & Dark Mode (●) Semantic Token System (Subagent #96)
- Visual Balance & Anti-Clutter Geometry Critic (Subagent #97)
- Tabless Sidebar & Breadcrumb Router (Subagent #98)
- Collapsible Device Telemetry Strip & Drawer (Subagent #99)
- Anti-Rainbow 2x3 Uniform Button Grid Normalizer (Subagent #100)
- Website & Desktop Template Benchmark Catalog (Subagent #101)
- DrawSI MCP Dual-Theme Artboard Sync (Subagent #102)
- Side-by-Side Light & Dark Visual Evidence Composer (Subagent #103)
- Universal Dual-Theme Finish Gate Oracle (Subagent #104)
- 10-Loop Strict Causal Dual-Theme & Layout Balance Evolution (Subagent #105)
- On-Demand MCP Server Tools #56-#60 (Total 60 MCP Tools)
"""

import os
from pathlib import Path

from core.dual_theme_and_layout_balance_engine import (
    ANTI_CLUTTER_LAYOUT_RULES,
    DUAL_THEME_PALETTES,
    WEBSITE_TEMPLATE_INTERFACE_CATALOG,
    DualThemeAndLayoutBalanceEngine,
)
from agents.dual_theme_and_balanced_layout_subagent import (
    AdaptiveDeviceStripAndDrawerSubagent,
    AntiRainbowGridButtonNormalizerSubagent,
    Causal10xDualThemeAndLayoutEvolverSubagent,
    DrawSIDualThemeArtboardSyncSubagent,
    DualThemeBalancedOrchestrator,
    DualThemeLightDarkTokenSubagent,
    DualThemeSideBySideEvidenceComposerSubagent,
    TablessSidebarAndBreadcrumbRouterSubagent,
    UniversalDualThemeFinishGateOracleSubagent,
    VisualBalanceAndWhitespaceCriticSubagent,
    WebsiteTemplateGalleryBenchmarkSubagent,
)
from mcp_bridge.android_farm_mcp_server import AndroidFarmMCPServer


def test_dual_theme_palettes_wcag_aaa():
    assert "LIGHT" in DUAL_THEME_PALETTES
    assert "DARK" in DUAL_THEME_PALETTES
    light = DUAL_THEME_PALETTES["LIGHT"]
    dark = DUAL_THEME_PALETTES["DARK"]

    assert light["BG_CANVAS"].lower() == "#f8fafc"
    assert light["BG_CHROME"].lower() == "#ffffff"
    assert light["ACCENT_PRIMARY"].lower() == "#4f46e5"
    assert light["wcag_primary_contrast"] >= 15.0

    assert dark["BG_CANVAS"].lower() == "#09090b"
    assert dark["BG_PANEL"].lower() == "#121217"
    assert dark["ACCENT_PRIMARY"].lower() == "#6366f1"
    assert dark["wcag_primary_contrast"] >= 15.0


def test_website_template_catalog_and_anti_clutter_rules():
    assert len(WEBSITE_TEMPLATE_INTERFACE_CATALOG) >= 12
    assert len(ANTI_CLUTTER_LAYOUT_RULES) == 6
    rule_ids = [r["rule_id"] for r in ANTI_CLUTTER_LAYOUT_RULES]
    assert rule_ids == ["ACL-01", "ACL-02", "ACL-03", "ACL-04", "ACL-05", "ACL-06"]


def test_subagents_96_to_104_execution():
    engine = DualThemeAndLayoutBalanceEngine()

    s96 = DualThemeLightDarkTokenSubagent(engine)
    r96_l = s96.execute("LIGHT")
    r96_d = s96.execute("DARK")
    assert r96_l["subagent_id"] == 96
    assert r96_l["active_mode"] == "LIGHT"
    assert r96_d["active_mode"] == "DARK"
    assert r96_l["wcag_aaa_verified"] is True

    s97 = VisualBalanceAndWhitespaceCriticSubagent(engine)
    r97 = s97.execute("LIGHT")
    assert r97["subagent_id"] == 97
    assert r97["visual_balance_score"] >= 99.0
    assert r97["truncated_widgets_count"] == 0
    assert r97["rainbow_buttons_count"] == 0

    s98 = TablessSidebarAndBreadcrumbRouterSubagent()
    r98 = s98.execute(active_tab_index=9, theme_mode="LIGHT")
    assert r98["subagent_id"] == 98
    assert r98["duplicate_horizontal_tabs_removed"] is True

    s99 = AdaptiveDeviceStripAndDrawerSubagent()
    r99 = s99.execute(drawer_expanded=False)
    assert r99["subagent_id"] == 99
    assert r99["vertical_stage_freed_px"] == 174

    s100 = AntiRainbowGridButtonNormalizerSubagent()
    r100 = s100.execute("LIGHT")
    assert r100["subagent_id"] == 100
    assert r100["rainbow_buttons_remaining"] == 0
    assert r100["grid_columns"] == 3

    s101 = WebsiteTemplateGalleryBenchmarkSubagent(engine)
    r101 = s101.execute()
    assert r101["subagent_id"] == 101
    assert r101["total_templates_benchmarked"] >= 12

    s102 = DrawSIDualThemeArtboardSyncSubagent()
    r102 = s102.execute()
    assert r102["subagent_id"] == 102
    assert len(r102["artboards_synced"]) == 2

    s104 = UniversalDualThemeFinishGateOracleSubagent(engine)
    r104 = s104.execute()
    assert r104["subagent_id"] == 104
    assert r104["overall_finish_gate_score"] >= 99.0
    assert r104["verdict"] == "PASS"


def test_subagent_105_strict_10_loop_causal_chain():
    s105 = Causal10xDualThemeAndLayoutEvolverSubagent()
    res = s105.execute(serial="10CF5L0TYL00312", loops=10)
    assert res["subagent_id"] == 105
    assert res["total_loops_executed"] == 10
    assert res["strict_causal_chain_verified"] is True
    assert res["final_score"] > res["initial_score"]
    ledger = res["loops"]
    assert len(ledger) == 10
    for i in range(1, len(ledger)):
        prev_l = ledger[i - 1]
        curr_l = ledger[i]
        assert curr_l["started_at"] > prev_l["completed_at"]
        assert curr_l["input_state_hash"] == prev_l["output_state_hash"]


def test_mcp_server_60_tools_and_v17_handlers():
    server = AndroidFarmMCPServer()
    tools = server.list_tools()
    assert len(tools) == 60
    tool_names = {t["name"] for t in tools}
    expected_v17_tools = {
        "android_switch_and_audit_dual_theme",
        "android_audit_visual_balance_and_clutter",
        "android_benchmark_website_ui_templates",
        "android_render_dual_theme_evidence_posters",
        "android_run_10x_dual_theme_causal_evolution",
    }
    assert expected_v17_tools.issubset(tool_names)

    r56 = server.call_tool("android_switch_and_audit_dual_theme", {"theme_mode": "LIGHT"})
    assert r56["active_mode"] == "LIGHT"

    r57 = server.call_tool("android_audit_visual_balance_and_clutter", {"theme_mode": "DARK"})
    assert r57["visual_balance_score"] >= 99.0

    r58 = server.call_tool("android_benchmark_website_ui_templates", {})
    assert r58["total_templates_benchmarked"] >= 12

    r60 = server.call_tool("android_run_10x_dual_theme_causal_evolution", {"serial": "10CF5L0TYL00312", "loops": 10})
    assert r60["strict_causal_chain_verified"] is True
    assert r60["total_loops_executed"] == 10
