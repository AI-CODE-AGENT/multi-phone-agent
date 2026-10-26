"""
Pytest Suite for AMAF v15.0:
- Multi-Screen Responsive Viewport Matrix Engine (5 Screen Profiles + XML/DOM Critic + Auto-Fix Patches)
- Synchronized Multi-Device Normalized [0..1] Action Mirror
- Zero-Human Autonomous QA Tester Engine (6-Stage End-to-End QA + Reproducible Bug Tickets)
- 10-Loop Strict Causal Responsive & Autonomous QA Evolution (Loop n+1 learns from Loop n)
- Subagents #76 - #85 & MCP Server v15.0.0 (50 On-Demand MCP Tools + Vision-LLM Image Blocks)
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.adb_wrapper import ADBWrapper
from core.multi_screen_responsive_engine import (
    SCREEN_PROFILES,
    SCREEN_SUITES,
    ResponsiveLayoutAnalyzer,
    MultiScreenResponsiveEngine,
)
from core.autonomous_qa_tester_engine import (
    AutonomousQATesterEngine,
    Causal10xResponsiveQAEvolver,
)
from agents.multi_screen_responsive_subagent import (
    MultiScreenViewportMatrixSubagent,
    ResponsiveDOMAndXMLCriticSubagent,
    SynchronizedMultiDeviceMirrorSubagent,
    VisualMultiScreenGridComposerSubagent,
    AutoFixLayoutPatchSynthesizerSubagent,
)
from agents.autonomous_qa_tester_subagent import (
    AutonomousTestPlanGeneratorSubagent,
    BoundaryAndMonkeyFuzzTesterSubagent,
    ZeroHumanQASignOffOracleSubagent,
    MCPVisionAndTestRunnerBridgeSubagent,
    Causal10xResponsiveQACoordinatorSubagent,
)
from mcp_bridge.android_farm_mcp_server import AndroidFarmMCPServer


SAMPLE_DEFECTIVE_XML = """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="com.app:id/root" class="android.widget.FrameLayout" bounds="[0,0][720,1280]">
    <node index="0" text="Header Banner" resource-id="com.app:id/header_banner" class="android.widget.TextView" clickable="false" bounds="[16,40][820,110]" />
    <node index="1" text="Primary CTA..." resource-id="com.app:id/btn_primary" class="android.widget.Button" clickable="true" bounds="[20,200][300,260]" />
    <node index="2" text="Secondary Action" resource-id="com.app:id/btn_secondary" class="android.widget.Button" clickable="true" bounds="[180,220][420,280]" />
    <node index="3" text="Tiny Icon" resource-id="com.app:id/btn_tiny" class="android.widget.ImageButton" clickable="true" bounds="[20,340][50,370]" />
  </node>
</hierarchy>"""


def test_screen_profiles_and_suites_catalog():
    assert len(SCREEN_PROFILES) == 5
    for key in ["compact_phone", "standard_phone", "vivo_v2417a", "foldable_inner", "tablet_10in"]:
        assert key in SCREEN_PROFILES
        prof = SCREEN_PROFILES[key]
        assert prof.width > 0 and prof.height > 0 and prof.density_dpi > 0
        assert prof.dp_width > 0 and prof.dp_height > 0
        assert prof.min_touch_px >= 32
    assert SCREEN_SUITES["full_5_screens"] == [
        "compact_phone",
        "standard_phone",
        "vivo_v2417a",
        "foldable_inner",
        "tablet_10in",
    ]


def test_responsive_layout_analyzer_detects_all_defect_classes_and_synthesizes_autofixes():
    analyzer = ResponsiveLayoutAnalyzer()
    audit = analyzer.analyze_xml_for_profile(SAMPLE_DEFECTIVE_XML, "compact_phone")
    assert audit["profile_id"] == "compact_phone"
    assert audit["node_count"] >= 4
    finding_codes = {f["code"] for f in audit["findings"]}
    assert "OFFSCREEN_CLIPPED_VIEW" in finding_codes
    assert "SIBLING_VIEW_OVERLAP" in finding_codes
    assert "TEXT_TRUNCATION_ELLIPSIS" in finding_codes
    assert "TOUCH_TARGET_TOO_SMALL" in finding_codes
    assert len(audit["auto_fixes"]) >= 4
    for patch in audit["auto_fixes"]:
        assert "android_xml" in patch
        assert "jetpack_compose" in patch
        assert "webview_css" in patch


def test_multi_screen_responsive_engine_5_screen_sweep_and_comparison_grid():
    out_dir = ROOT_DIR / "artifacts" / "test_v15_responsive"
    adb = ADBWrapper()
    engine = MultiScreenResponsiveEngine(adb)
    res = engine.run_multi_screen_responsive_audit(
        serial="10CF5L0TYL00312",
        suite="full_5_screens",
        apply_hardware_wm=False,
        capture_screenshots=True,
        output_dir=str(out_dir),
        xml_override=SAMPLE_DEFECTIVE_XML,
    )
    assert res["screens_tested"] == 5
    assert 0 <= res["responsive_score"] <= 100
    assert res["comparison_grid_path"] is not None
    assert Path(res["comparison_grid_path"]).exists()
    assert len(res["findings"]) >= 4
    assert len(res["auto_fixes"]) >= 4


def test_synchronized_multi_screen_normalized_action_mirror():
    adb = ADBWrapper()
    engine = MultiScreenResponsiveEngine(adb)
    res = engine.sync_multi_screen_action(
        serials=["10CF5L0TYL00312", "emulator-5554"],
        action_type="tap",
        norm_x=0.5,
        norm_y=0.25,
        dry_run=True,
    )
    assert res["total_targets"] == 2
    assert res["synced_count"] == 2
    assert len(res["results"]) == 2
    for item in res["results"]:
        assert item["mapped_point"]["x"] > 0
        assert item["mapped_point"]["y"] > 0


def test_autonomous_qa_tester_engine_6_stage_zero_human_audit():
    out_dir = ROOT_DIR / "artifacts" / "test_v15_qa"
    adb = ADBWrapper()
    qa_engine = AutonomousQATesterEngine(adb)
    report = qa_engine.run_full_autonomous_qa_session(
        serial="10CF5L0TYL00312",
        package_name="com.android.settings",
        suite="default_3",
        apply_hardware_wm=False,
        capture_screenshots=False,
        xml_override=SAMPLE_DEFECTIVE_XML,
        output_dir=str(out_dir),
    )
    assert report["test_plan"]["total_test_cases"] == 6
    assert report["boundary_fuzzing"]["fuzz_cases_count"] == 5
    assert 0 <= report["qa_readiness_score"] <= 100
    assert report["verdict"] in ("PASS_PRODUCTION_READY", "NEEDS_POLISH", "BLOCK_RELEASE")
    assert report["bug_tickets_count"] >= 4
    assert Path(report["report_json_path"]).exists()


def test_causal_10x_responsive_qa_evolver_strict_n_plus_1_dependency():
    adb = ADBWrapper()
    evolver = Causal10xResponsiveQAEvolver(adb)
    res = evolver.run_10_causal_loops(
        serial="10CF5L0TYL00312",
        package_name="com.android.settings",
        xml_override=SAMPLE_DEFECTIVE_XML,
    )
    assert res["loops_completed"] == 10
    assert res["causal_chain_valid"] is True
    assert res["final_calibrated_qa_score"] >= res["initial_qa_score"]
    loops = res["loops"]
    for idx in range(1, 10):
        prev_loop = loops[idx - 1]
        curr_loop = loops[idx]
        assert curr_loop["input_lesson_from_previous_loop"] == prev_loop["learned_lesson"]
        assert curr_loop["started_at"] > prev_loop["completed_at"]


def test_subagents_76_to_85_and_mcp_server_v15_tools():
    s76 = MultiScreenViewportMatrixSubagent()
    s77 = ResponsiveDOMAndXMLCriticSubagent()
    s78 = SynchronizedMultiDeviceMirrorSubagent()
    s79 = AutonomousTestPlanGeneratorSubagent()
    s80 = BoundaryAndMonkeyFuzzTesterSubagent()
    s81 = VisualMultiScreenGridComposerSubagent()
    s82 = AutoFixLayoutPatchSynthesizerSubagent()
    s83 = ZeroHumanQASignOffOracleSubagent()
    s84 = MCPVisionAndTestRunnerBridgeSubagent()
    s85 = Causal10xResponsiveQACoordinatorSubagent()

    assert s76.subagent_id == 76
    assert s77.subagent_id == 77
    assert s78.subagent_id == 78
    assert s79.subagent_id == 79
    assert s80.subagent_id == 80
    assert s81.subagent_id == 81
    assert s82.subagent_id == 82
    assert s83.subagent_id == 83
    assert s84.subagent_id == 84
    assert s85.subagent_id == 85

    critic_res = s77.execute(SAMPLE_DEFECTIVE_XML, profile_id="compact_phone")
    assert critic_res["defect_count"] >= 4
    patch_res = s82.execute(SAMPLE_DEFECTIVE_XML, profile_id="compact_phone")
    assert patch_res["auto_fix_count"] >= 4

    mcp = AndroidFarmMCPServer()
    tools = mcp.list_tools()
    tool_names = {t["name"] for t in tools}
    assert len(tools) == 50
    assert "android_test_multi_screen_responsive" in tool_names
    assert "android_run_autonomous_qa_tester" in tool_names
    assert "android_sync_multi_screen_action" in tool_names
    assert "android_run_10x_responsive_qa_evolution" in tool_names

    call_res = mcp.call_tool(
        "android_sync_multi_screen_action",
        {
            "serials": ["10CF5L0TYL00312"],
            "action_type": "tap",
            "norm_x": 0.5,
            "norm_y": 0.5,
            "dry_run": True,
        },
    )
    assert call_res["total_targets"] == 1
