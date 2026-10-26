"""
Unit & Integration Tests for AMAF v16.0:
- 25-OS Cross-Platform Responsive Matrix (Windows 11, macOS, ChromeOS, Ubuntu, Linux Mint, Fedora, Manjaro,
  Elementary OS, Zorin OS, iOS 18, iPadOS 18, Android 15, Vivo OriginOS 5, HarmonyOS 4.2, HarmonyOS NEXT,
  GrapheneOS, LineageOS 21, Ubuntu Touch, Sailfish OS 4.6, KaiOS 3.1, LG webOS 24 TV, Hisense VIDAA U7 TV)
- LRUD D-Pad Spatial Navigation Focus Graph Reachability (KaiOS, LG webOS TV, Hisense VIDAA OS TV)
- 6-Framework Auto-Fix Patch Synthesizer (Android XML, Compose Multiplatform, SwiftUI, HarmonyOS ArkTS, Web/Desktop CSS, TV/KaiOS D-Pad)
- 25-OS Visual Matrix Poster Generation & MCP Vision Payload
- Strict 10-Loop Causal Evolution (`Loop n+a+1` strictly starts and rewrites prompt after `Loop n+a` completes)
- Subagents #86-#95 & 55 On-Demand MCP Tools
"""

from pathlib import Path
from PIL import Image

from core.cross_platform_os_matrix_engine import (
    CROSS_PLATFORM_OS_CATALOG,
    CROSS_PLATFORM_SUITES,
    UI_UX_DESIGN_REFERENCE_CATALOG,
    MOBBIN_AND_TAURI_DESKTOP_UX_RULES,
    CrossPlatformOSMatrixEngine,
    Causal10xCrossPlatformQAEvolver,
)
from agents.cross_platform_os_matrix_subagent import (
    DesktopOSViewportMatrixSubagent,
    AppleiOSAndiPadOSViewportSubagent,
    HarmonyOSAndOriginOSContinuitySubagent,
    AlternativeAndPrivacyMobileOSSubagent,
    KaiOSAndSmartTV10FootUISubagent,
    UniversalSafeAreaAndWindowChromeSubagent,
    CrossPlatform6FrameworkPatchSubagent,
    Visual25OSMatrixPosterComposerSubagent,
    UniversalZeroHumanCrossPlatformQAOracleSubagent,
    Causal10xCrossPlatformPromptEvolverSubagent,
)
from mcp_bridge.android_farm_mcp_server import AndroidFarmMCPServer


SAMPLE_CROSS_PLATFORM_DEFECT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="android:id/content" class="android.widget.FrameLayout" bounds="[0,0][1260,2800]">
    <node index="1" text="Header overlapping Notch / Dynamic Island / Pulley..." resource-id="com.app:id/header_title" class="android.widget.TextView" clickable="true" focusable="true" bounds="[10,12][1250,55]" />
    <node index="2" text="Horizontal Overflow Card..." resource-id="com.app:id/overflow_banner" class="android.widget.TextView" clickable="false" bounds="[40,300][1420,440]" />
    <node index="3" text="Tiny Button" resource-id="com.app:id/tiny_btn" class="android.widget.Button" clickable="true" focusable="true" bounds="[60,600][78,618]" />
    <node index="4" text="Bottom Action Bar Overlapping Gesture/Dock/Softkey" resource-id="com.app:id/bottom_cta" class="android.widget.Button" clickable="true" focusable="true" bounds="[20,2775][1240,2798]" />
  </node>
</hierarchy>
"""


class FakeV16ADB:
    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        self.adb_path = "adb"

    def capture_screenshot(self, serial: str, out_path: str) -> str:
        img = Image.new("RGB", (630, 1400), (24, 30, 48))
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path)
        return out_path

    def take_screenshot(self, serial: str, out_path: str) -> str:
        return self.capture_screenshot(serial, out_path)

    def dump_ui_hierarchy(self, serial: str, out_path: str = "") -> str:
        return SAMPLE_CROSS_PLATFORM_DEFECT_XML

    def dump_ui_xml(self, serial: str, out_path: str = "") -> str:
        return SAMPLE_CROSS_PLATFORM_DEFECT_XML


def _get_test_out_dir(sub: str) -> Path:
    d = Path(__file__).resolve().parent.parent / "artifacts" / "pytest_v16" / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


def test_25_os_catalog_completeness():
    assert len(CROSS_PLATFORM_OS_CATALOG) == 25
    required_os_keys = {
        "windows_11_laptop",
        "windows_4k_workstation",
        "macos_macbook_pro_16",
        "macos_imac_24",
        "chromeos_pixelbook",
        "linux_ubuntu_gnome",
        "linux_mint_cinnamon",
        "linux_fedora_workstation",
        "linux_manjaro_kde",
        "linux_elementary_pantheon",
        "linux_zorin_os",
        "ios_iphone_16_pro_max",
        "ios_iphone_se_3",
        "ipados_ipad_pro_13",
        "android_15_pixel_9_pro",
        "originos_vivo_v2417a",
        "harmonyos_4_mate_60",
        "harmonyos_next_mate_xt",
        "grapheneos_pixel_hardened",
        "lineageos_21_aosp",
        "ubuntu_touch_lomiri",
        "sailfish_os_silica",
        "kaios_3_smart_feature",
        "tv_lg_webos_4k",
        "tv_hisense_vidaa_os",
    }
    assert required_os_keys == set(CROSS_PLATFORM_OS_CATALOG.keys())
    assert len(CROSS_PLATFORM_SUITES["full_25_os_matrix"]) == 25


def test_25_os_xml_analysis_and_dpad_spatial_navigation():
    out_dir = _get_test_out_dir("xml_dpad")
    adb = FakeV16ADB(out_dir)
    engine = CrossPlatformOSMatrixEngine(adb=adb)

    # 1. Check iOS 18 Dynamic Island & Home Indicator safe-area detection
    ios_audit = engine.analyze_xml_for_os_profile(
        SAMPLE_CROSS_PLATFORM_DEFECT_XML,
        CROSS_PLATFORM_OS_CATALOG["ios_iphone_16_pro_max"],
    )
    defect_codes_ios = {f["code"] for f in ios_audit["findings"]}
    assert "SAFE_AREA_INSET_COLLISION" in defect_codes_ios
    assert "OFFSCREEN_CLIPPED_VIEW" in defect_codes_ios

    # 2. Check HarmonyOS NEXT ArkUI breakpoint & tri-fold validation
    harmony_audit = engine.analyze_xml_for_os_profile(
        SAMPLE_CROSS_PLATFORM_DEFECT_XML,
        CROSS_PLATFORM_OS_CATALOG["harmonyos_next_mate_xt"],
    )
    assert harmony_audit["arkui_breakpoint"] in ("md", "lg", "xl")

    # 3. Check Smart TV (LG webOS 24) & KaiOS 3.1 LRUD D-Pad Spatial Navigation graph
    webos_audit = engine.analyze_xml_for_os_profile(
        SAMPLE_CROSS_PLATFORM_DEFECT_XML,
        CROSS_PLATFORM_OS_CATALOG["tv_lg_webos_4k"],
    )
    assert webos_audit["dpad_spatial_navigation"]["applicable"] is True
    assert webos_audit["dpad_spatial_navigation"]["interactive_nodes"] >= 3
    assert "reachability_pct" in webos_audit["dpad_spatial_navigation"]


def test_6_framework_patch_synthesis_and_25os_poster():
    out_dir = _get_test_out_dir("poster_patch")
    adb = FakeV16ADB(out_dir)
    engine = CrossPlatformOSMatrixEngine(adb=adb)

    patches = engine.synthesize_6_framework_patch(
        "SAFE_AREA_INSET_COLLISION",
        CROSS_PLATFORM_OS_CATALOG["ios_iphone_16_pro_max"],
        "header_title",
    )
    for fw in (
        "android_xml",
        "compose_multiplatform",
        "apple_swiftui",
        "harmonyos_arkts",
        "web_desktop_css",
        "tv_kaios_dpad_focus",
        "tauri_shadcn_ui",
        "electron_react_ts",
    ):
        assert fw in patches
        assert len(patches[fw]) > 30

    assert len(UI_UX_DESIGN_REFERENCE_CATALOG) >= 25
    for ref_key in (
        "figma_community",
        "sketch_app_sources",
        "dribbble_and_behance",
        "tauri_ui_shadcn",
        "electron_react_boilerplate",
        "collect_ui",
        "mobbin_desktop_web",
        "refero_design",
        "pageflows",
        "component_gallery",
        "apple_hig_macos_ios_ipados",
        "microsoft_fluent_2",
        "gnome_libadwaita_hig",
        "kde_kirigami_hig",
        "harmonyos_next_design",
    ):
        assert ref_key in UI_UX_DESIGN_REFERENCE_CATALOG
    assert len(MOBBIN_AND_TAURI_DESKTOP_UX_RULES) == 12

    matrix_res = engine.run_25_os_cross_platform_audit(
        serial="10CF5L0TYL00312",
        suite="full_25_os_matrix",
        xml_override=SAMPLE_CROSS_PLATFORM_DEFECT_XML,
        output_dir=str(out_dir),
    )
    assert matrix_res["os_profiles_tested"] == 25
    assert Path(matrix_res["poster_path"]).exists()
    assert len(matrix_res["mcp_images"]) >= 1


def test_strict_10_loop_causal_evolution_n_plus_a_plus_1():
    out_dir = _get_test_out_dir("causal_10x")
    adb = FakeV16ADB(out_dir)
    evolver = Causal10xCrossPlatformQAEvolver(adb=adb)

    summary = evolver.run_10_causal_loops(
        serial="10CF5L0TYL00312",
        xml_override=SAMPLE_CROSS_PLATFORM_DEFECT_XML,
        artifact_dir=str(out_dir),
    )
    assert summary["loops_completed"] == 10
    assert summary["causal_chain_valid"] is True
    assert summary["final_calibrated_qa_score"] > summary["initial_qa_score"]
    assert summary["final_calibrated_qa_score"] >= 98.0

    ledger = summary["loops"]
    # Verify for every loop n and constant a >= 0 that Loop (n+a+1) starts strictly after Loop (n+a) completes
    # and rewrites its prompt from Loop (n+a)'s output state hash and learned lesson
    for idx in range(len(ledger) - 1):
        prev_loop = ledger[idx]
        next_loop = ledger[idx + 1]
        assert next_loop["started_at"] > prev_loop["completed_at"]
        assert next_loop["input_state_hash"] == prev_loop["output_state_hash"]
        assert next_loop["input_lesson_from_prev_loop"] == prev_loop["learned_lesson"]
        assert prev_loop["output_state_hash"] in next_loop["rewritten_prompt"]
        assert Path(next_loop["screenshot_path"]).exists()


def test_subagents_86_to_95_and_55_mcp_tools():
    out_dir = _get_test_out_dir("subagents_mcp")
    adb = FakeV16ADB(out_dir)
    subagents = [
        DesktopOSViewportMatrixSubagent(adb=adb),
        AppleiOSAndiPadOSViewportSubagent(adb=adb),
        HarmonyOSAndOriginOSContinuitySubagent(adb=adb),
        AlternativeAndPrivacyMobileOSSubagent(adb=adb),
        KaiOSAndSmartTV10FootUISubagent(adb=adb),
        UniversalSafeAreaAndWindowChromeSubagent(adb=adb),
        CrossPlatform6FrameworkPatchSubagent(adb=adb),
        Visual25OSMatrixPosterComposerSubagent(adb=adb),
        UniversalZeroHumanCrossPlatformQAOracleSubagent(adb=adb),
        Causal10xCrossPlatformPromptEvolverSubagent(adb=adb),
    ]
    assert [s.subagent_id for s in subagents] == list(range(86, 96))

    r92 = subagents[6].execute()
    assert r92["frameworks_count"] == 6

    mcp = AndroidFarmMCPServer()
    tools = mcp.list_tools()
    tool_names = {t["name"] for t in tools}
    assert len(tools) >= 55
    for expected_tool in (
        "android_list_cross_platform_os_profiles",
        "android_test_cross_platform_25os_matrix",
        "android_audit_tv_and_kaios_spatial_navigation",
        "android_generate_cross_platform_autofix_patches",
        "android_run_10x_cross_platform_causal_evolution",
    ):
        assert expected_tool in tool_names

    catalog_res = mcp.call_tool("android_list_cross_platform_os_profiles", {})
    assert catalog_res["total_os_profiles"] == 25
