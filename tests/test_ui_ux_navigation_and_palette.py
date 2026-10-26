"""
Comprehensive Unit Tests for Subagents #58, #59 & #60:
- `SidebarNavigationAndIAEngine` / `SidebarNavigationAndIASubagent` (#58)
- `CommandPaletteAndProgressiveDisclosureEngine` / `CommandPaletteAndProgressiveDisclosureSubagent` (#59)
- `BentoDeviceCardAndSparklineEngine` / `BentoDeviceCardAndSparklineSubagent` (#60)
"""

from __future__ import annotations

import pytest

from agents.ui_ux_navigation_and_palette_subagent import (
    BentoDeviceCardAndSparklineSubagent,
    CommandPaletteAndProgressiveDisclosureSubagent,
    SidebarNavigationAndIASubagent,
)
from core.ui_ux_navigation_and_palette_engine import (
    BentoDeviceCardAndSparklineEngine,
    CommandPaletteAndProgressiveDisclosureEngine,
    SidebarNavigationAndIAEngine,
)


# ==============================================================================
# 1. Tests for Engine #58 & Subagent #58 (5-Workspace Left Sidebar IA)
# ==============================================================================


def test_sidebar_5_workspaces_and_complete_65_subagent_mapping() -> None:
    subagent = SidebarNavigationAndIASubagent()
    workspaces = subagent.get_sidebar_workspaces()

    assert len(workspaces) == 5
    ws_ids = [w["workspace_id"] for w in workspaces]
    assert ws_ids == [
        "fleet_overview",
        "automation_evolution",
        "security_captcha_lab",
        "gpu_stream_diagnostics",
        "apk_installer_memory",
    ]

    ws_titles = {w["workspace_id"]: w["title"] for w in workspaces}
    assert ws_titles["fleet_overview"] == "📱 Fleet & Real Phones"
    assert ws_titles["automation_evolution"] == "🤖 AI Loops & 10x Evolution"
    assert ws_titles["security_captcha_lab"] == "🔐 Security, 2FA & CAPTCHA"
    assert ws_titles["gpu_stream_diagnostics"] == "⚡ GPU, Stream & Diagnostics"
    assert ws_titles["apk_installer_memory"] == "📦 APK Installer & Memory"

    audit = subagent.audit_information_architecture()
    assert audit["complete_65_coverage"] is True
    assert audit["total_mapped_subagents"] == 65
    assert audit["missing_subagents"] == []
    assert audit["duplicate_subagents"] == []
    assert audit["millers_law_compliant"] is True
    assert audit["cognitive_load_reduction_pct"] > 60.0
    assert audit["hicks_law_target_met"] is True


def test_sidebar_subagent_routing_and_lookup() -> None:
    subagent = SidebarNavigationAndIASubagent()

    # Check canonical subagent placements specified in architecture
    assert subagent.find_subagent_workspace(46)["workspace_id"] == "apk_installer_memory"
    assert subagent.find_subagent_workspace(48)["workspace_id"] == "apk_installer_memory"
    assert subagent.find_subagent_workspace(26)["workspace_id"] == "security_captcha_lab"
    assert subagent.find_subagent_workspace(40)["workspace_id"] == "security_captcha_lab"
    assert subagent.find_subagent_workspace(36)["workspace_id"] == "gpu_stream_diagnostics"
    assert subagent.find_subagent_workspace(41)["workspace_id"] == "gpu_stream_diagnostics"
    assert subagent.find_subagent_workspace(55)["workspace_id"] == "automation_evolution"
    assert subagent.find_subagent_workspace(58)["workspace_id"] == "automation_evolution"
    assert subagent.find_subagent_workspace(60)["workspace_id"] == "automation_evolution"

    routed = subagent.route_to_workspace("apk_installer_memory")
    assert routed["is_active"] is True
    assert routed["workspace_id"] == "apk_installer_memory"

    with pytest.raises(KeyError):
        subagent.route_to_workspace("non_existent_workspace")

    with pytest.raises(ValueError):
        subagent.find_subagent_workspace(999)


# ==============================================================================
# 2. Tests for Engine #59 & Subagent #59 (Ctrl+K Command Palette & Fuzzy Search)
# ==============================================================================


@pytest.mark.parametrize(
    "query,expected_subagent_or_keyword",
    [
        ("#46", 46),
        ("vivo", 48),
        ("ui ux", 58),
        ("captcha", 40),
        ("10x", 55),
        ("cai dat apk", 46),
        ("2fa", 26),
        ("tiktok", 16),
    ],
)
def test_command_palette_fuzzy_search_queries(
    query: str,
    expected_subagent_or_keyword: int,
) -> None:
    palette = CommandPaletteAndProgressiveDisclosureSubagent()
    telemetry = palette.get_palette_telemetry()
    assert telemetry["total_indexed_commands"] >= 95  # 65 subagents + 32 quick actions

    results = palette.search(query, limit=8)
    assert 1 <= len(results) <= 8

    # Verify top results match the query domain or target subagent
    found_subagents = {r["subagent_id"] for r in results if r["subagent_id"] is not None}
    combined_text = " ".join(
        (r["title"] + " " + " ".join(r["keywords"])).lower() for r in results
    )
    assert (expected_subagent_or_keyword in found_subagents) or (
        query.replace("#", "").lower() in combined_text
    )


def test_command_palette_exact_subagent_tag_ranks_first() -> None:
    engine = CommandPaletteAndProgressiveDisclosureEngine()
    res_46 = engine.search_commands("#46", limit=5)
    assert res_46[0]["subagent_id"] == 46
    assert "APK Installer" in res_46[0]["title"]

    res_65 = engine.search_commands("#65", limit=5)
    assert res_65[0]["subagent_id"] == 65


# ==============================================================================
# 3. Tests for Progressive Disclosure Toolbar Splitter (#59)
# ==============================================================================


def test_progressive_disclosure_splits_9_button_cluttered_bar() -> None:
    palette = CommandPaletteAndProgressiveDisclosureSubagent()
    cluttered_9_buttons = [
        {"id": "btn_1", "label": "Start All Phones", "is_primary": True},
        {"id": "btn_2", "label": "Mirror Scrcpy Wall"},
        {"id": "btn_3", "label": "Install APK"},
        {"id": "btn_4", "label": "Group Broadcast"},
        {"id": "btn_5", "label": "Clean Cache"},
        {"id": "btn_6", "label": "Rotate Screen"},
        {"id": "btn_7", "label": "Spoof IMEI"},
        {"id": "btn_8", "label": "Reboot ADB"},
        {"id": "btn_9", "label": "Export Defect Logs"},
    ]

    disclosed = palette.split_cluttered_toolbar(
        cluttered_9_buttons,
        max_visible_primary=1,
        max_visible_secondary=3,
    )

    assert len(disclosed["primary_cta"]) == 1
    assert disclosed["primary_cta"][0]["id"] == "btn_1"
    assert len(disclosed["secondary_buttons"]) == 3
    assert [b["id"] for b in disclosed["secondary_buttons"]] == ["btn_2", "btn_3", "btn_4"]
    assert len(disclosed["overflow_drawer_items"]) == 5
    assert disclosed["visible_button_count"] == 4
    assert disclosed["overflow_count"] == 5
    assert disclosed["is_clutter_free"] is True
    assert disclosed["command_palette_shortcut"] == "Ctrl+K"


# ==============================================================================
# 4. Tests for Engine #60 & Subagent #60 (Bento Device Card & Sparklines)
# ==============================================================================


def test_bento_device_card_vivo_physical_and_avd_models() -> None:
    subagent = BentoDeviceCardAndSparklineSubagent()

    vivo_card = subagent.render_device_card(
        {
            "serial": "10AC94123X000T5",
            "model": "Vivo V2417A",
            "is_physical": True,
            "status": "online",
            "cpu_history": [10, 20, 35, 50, 65, 80, 65, 50],
            "fps_history": [59, 60, 60, 60, 58, 60, 60, 60],
            "ram_pct": 54.5,
            "battery_pct": 96,
        }
    )

    assert vivo_card["first_read_title"] == "Vivo V2417A (Physical)"
    assert vivo_card["is_physical"] is True
    assert vivo_card["status_pill"]["text"] == "ONLINE • READY"
    assert vivo_card["status_pill"]["color"] == "#10b981"
    assert vivo_card["primary_action"]["label"] == "Mirror Scrcpy"
    assert len(vivo_card["secondary_icon_actions"]) == 3
    assert len(vivo_card["sparkline_unicode"]) == 8
    assert "," in vivo_card["sparkline_svg_points"]
    assert vivo_card["rainbow_button_clutter_eliminated"] is True

    offline_avd_card = subagent.render_device_card(
        {
            "serial": "emulator-5554",
            "model": "Pixel 6 AVD #1",
            "is_physical": False,
            "status": "offline",
            "cpu_history": [0, 0, 0, 0, 0, 0, 0, 0],
        }
    )

    assert offline_avd_card["first_read_title"] == "Pixel 6 AVD #1"
    assert offline_avd_card["is_physical"] is False
    assert offline_avd_card["status_pill"]["text"] == "OFFLINE • STOPPED"
    assert offline_avd_card["primary_action"]["label"] == "Start Headless"


def test_sparkline_unicode_and_svg_generation() -> None:
    engine = BentoDeviceCardAndSparklineEngine()
    rising = [10, 20, 30, 40, 50, 60, 50, 40]
    uni = engine.render_unicode_sparkline(rising)
    assert len(uni) == 8
    assert uni[0] == "▁"
    assert uni[5] == "█"

    svg_pts = engine.render_svg_sparkline_points(rising, width=120, height=28)
    coords = svg_pts.split(" ")
    assert len(coords) == 8
    for pt in coords:
        x_str, y_str = pt.split(",")
        assert 0.0 <= float(x_str) <= 120.0
        assert 0.0 <= float(y_str) <= 28.0
