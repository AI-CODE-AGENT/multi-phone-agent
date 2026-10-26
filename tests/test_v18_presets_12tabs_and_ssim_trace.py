"""
Unit & Integration Tests for AMAF v18.0:
- 8 Curated Website & Desktop UI Template Presets in both Light & Dark modes (`16 palettes`)
- Subagent #106: All12TabsDualThemeHarmonyAuditorSubagent
- Subagent #107: WebsiteTemplatePresetLiveSwitcherSubagent
- Subagent #108: VisualRegressionPixelDiffAndSSIMSubagent
- Subagent #109: InteractiveTraceTimelineAndReplaySubagent
- Subagent #110: SelfHealingLocatorAndLayoutAutoPatcherSubagent
- Subagent #111: MultiTabVisualGalleryComposerSubagent
- Subagent #112: DrawSI8PresetAnd12TabArtboardSyncSubagent
- Subagent #113: OpenCodeBrowserLiveVerifierAndTraceBridgeSubagent
- Subagent #114: UniversalV18FinishGateOracleSubagent
- Subagent #115: Causal10xV18PresetAndQATraceEvolverSubagent
- MCP Server Tools #61-#65 (Total 65 MCP Tools)
"""

from core.visual_regression_and_template_preset_engine import (
    ALL_12_STUDIO_TABS_SPEC,
    TEMPLATE_PRESET_PALETTES,
    VisualRegressionAndTemplatePresetEngine,
)
from agents.all_tabs_preset_and_qa_trace_subagent import (
    All12TabsDualThemeHarmonyAuditorSubagent,
    Causal10xV18PresetAndQATraceEvolverSubagent,
    DrawSI8PresetAnd12TabArtboardSyncSubagent,
    InteractiveTraceTimelineAndReplaySubagent,
    MultiTabVisualGalleryComposerSubagent,
    OpenCodeBrowserLiveVerifierAndTraceBridgeSubagent,
    SelfHealingLocatorAndLayoutAutoPatcherSubagent,
    UniversalV18FinishGateOracleSubagent,
    VisualRegressionPixelDiffAndSSIMSubagent,
    WebsiteTemplatePresetLiveSwitcherSubagent,
)
from mcp_bridge.android_farm_mcp_server import AndroidFarmMCPServer


def test_8_website_template_presets_light_and_dark_wcag_aaa():
    assert len(TEMPLATE_PRESET_PALETTES) == 8
    for preset_id, pdata in TEMPLATE_PRESET_PALETTES.items():
        assert "LIGHT" in pdata
        assert "DARK" in pdata
        assert pdata["LIGHT"]["wcag_primary_contrast"] >= 15.0
        assert pdata["DARK"]["wcag_primary_contrast"] >= 15.0


def test_subagents_106_to_114_execution():
    engine = VisualRegressionAndTemplatePresetEngine()

    s106 = All12TabsDualThemeHarmonyAuditorSubagent(engine)
    r106 = s106.execute("shadcn_zinc_daylight", "LIGHT")
    assert r106["subagent_id"] == 106
    assert r106["total_tabs_audited"] == 12
    assert r106["all_tabs_zero_clipping"] is True
    assert r106["overall_12_tab_harmony_score"] >= 99.0

    s107 = WebsiteTemplatePresetLiveSwitcherSubagent(engine)
    r107 = s107.execute("stripe_daylight_night", "DARK")
    assert r107["subagent_id"] == 107
    assert r107["preset_id"] == "stripe_daylight_night"
    assert r107["active_mode"] == "DARK"
    assert r107["total_presets_available"] == 8

    s108 = VisualRegressionPixelDiffAndSSIMSubagent(engine)
    r108 = s108.execute()
    assert r108["subagent_id"] == 108
    assert r108["layout_structural_ssim"] >= 0.99
    assert r108["widget_bounds_drift_px"] == 0.0

    s109 = InteractiveTraceTimelineAndReplaySubagent(engine)
    r109 = s109.execute(serial="10CF5L0TYL00312")
    assert r109["subagent_id"] == 109
    assert r109["total_steps"] == 6
    assert r109["replay_ready"] is True

    s110 = SelfHealingLocatorAndLayoutAutoPatcherSubagent(engine)
    r110 = s110.execute()
    assert r110["subagent_id"] == 110
    assert r110["self_healing_success_rate_pct"] >= 99.0
    assert len(r110["fallback_tiers"]) == 5

    s112 = DrawSI8PresetAnd12TabArtboardSyncSubagent()
    r112 = s112.execute()
    assert r112["subagent_id"] == 112
    assert len(r112["artboards_synced"]) == 7

    s113 = OpenCodeBrowserLiveVerifierAndTraceBridgeSubagent()
    r113 = s113.execute()
    assert r113["subagent_id"] == 113
    assert r113["dom_overflow_x"] is False

    s114 = UniversalV18FinishGateOracleSubagent(engine)
    r114 = s114.execute()
    assert r114["subagent_id"] == 114
    assert r114["total_subagents"] == 115
    assert r114["total_mcp_tools"] == 65
    assert r114["verdict"] == "PASS"


def test_subagent_115_strict_10_loop_causal_chain():
    s115 = Causal10xV18PresetAndQATraceEvolverSubagent()
    res = s115.execute(serial="10CF5L0TYL00312", loops=10)
    assert res["subagent_id"] == 115
    assert res["total_loops_executed"] == 10
    assert res["strict_causal_chain_verified"] is True
    assert res["final_score"] > res["initial_score"]
    loops = res["loops"]
    assert len(loops) == 10
    for i in range(1, len(loops)):
        assert loops[i]["started_at"] > loops[i - 1]["completed_at"]
        assert loops[i]["input_state_hash"] == loops[i - 1]["output_state_hash"]


def test_mcp_server_65_tools_and_v18_handlers():
    server = AndroidFarmMCPServer()
    tools = server.list_tools()
    assert len(tools) >= 65
    tool_names = {t["name"] for t in tools}
    expected_v18_tools = {
        "android_audit_all_12_tabs_dual_theme_harmony",
        "android_switch_website_template_design_preset",
        "android_run_visual_regression_ssim_and_pixel_diff",
        "android_record_and_replay_interactive_qa_trace",
        "android_run_10x_causal_v18_preset_and_qa_loop",
    }
    assert expected_v18_tools.issubset(tool_names)

    r61 = server.call_tool("android_audit_all_12_tabs_dual_theme_harmony", {"preset_id": "linear_obsidian_paper", "mode": "LIGHT"})
    assert r61["total_tabs_audited"] == 12

    r62 = server.call_tool("android_switch_website_template_design_preset", {"preset_id": "supabase_emerald_studio", "mode": "DARK"})
    assert r62["preset_id"] == "supabase_emerald_studio"

    r63 = server.call_tool("android_run_visual_regression_ssim_and_pixel_diff", {})
    assert r63["layout_structural_ssim"] >= 0.99

    r64 = server.call_tool("android_record_and_replay_interactive_qa_trace", {"serial": "10CF5L0TYL00312"})
    assert r64["total_steps"] == 6
    assert r64["self_healing"]["verdict"] == "PASS"

    r65 = server.call_tool("android_run_10x_causal_v18_preset_and_qa_loop", {"serial": "10CF5L0TYL00312", "loops": 10})
    assert r65["strict_causal_chain_verified"] is True
    assert r65["total_loops_executed"] == 10
