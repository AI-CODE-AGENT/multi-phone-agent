"""
Unit tests for Engine #56 / Subagent #56 (`VisualScreenshotClutterCriticSubagent`)
and Engine #57 / Subagent #57 (`DesignTokenAnd8PtGridSubagent`).
"""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.ui_ux_design_system_subagent import (
    DesignTokenAnd8PtGridSubagent,
    VisualScreenshotClutterCriticSubagent,
)
from core.ui_ux_design_system_engine import (
    DesignTokenAnd8PtGridEngine,
    VisualScreenshotClutterCriticEngine,
)


def test_design_tokens_and_8pt_grid_snapping():
    """Verify canonical Linear/Raycast/Geist tokens and 8pt spatial grid snapping."""
    subagent = DesignTokenAnd8PtGridSubagent()

    # Check surface elevation tokens
    assert subagent.CANVAS_BG == "#0b0d14"
    assert subagent.SIDEBAR_BG == "#10131d"
    assert subagent.CARD_SURFACE == "#151926"
    assert subagent.ELEVATED_SURFACE == "#1e2436"
    assert subagent.HAIRLINE_BORDER == "#262d42"

    # Check semantic accent tokens
    assert subagent.PRIMARY_ACCENT == "#6366f1"
    assert subagent.SECONDARY_SURFACE_BTN == "#1e2436"
    assert subagent.STATUS_HEALTHY == "#10b981"
    assert subagent.STATUS_WARNING == "#f59e0b"
    assert subagent.STATUS_DANGER == "#ef4444"
    assert subagent.TEXT_PRIMARY == "#f3f4f6"
    assert subagent.TEXT_SECONDARY == "#9ca3af"
    assert subagent.TEXT_MUTED == "#6b7280"

    # Check 8pt spacing scale
    assert (
        subagent.SPACE_1,
        subagent.SPACE_2,
        subagent.SPACE_3,
        subagent.SPACE_4,
        subagent.SPACE_6,
        subagent.SPACE_8,
    ) == (4, 8, 12, 16, 24, 32)

    # Check typography scale
    assert subagent.FONT_DISPLAY == ("Segoe UI", 15, "bold")
    assert subagent.FONT_SECTION == ("Segoe UI", 11, "bold")
    assert subagent.FONT_BODY == ("Segoe UI", 10)
    assert subagent.FONT_CAPTION == ("Segoe UI", 9)
    assert subagent.FONT_MONO == ("Consolas", 9)

    # Check 8pt snapping math
    assert subagent.snap_to_8pt_grid(0) == 0
    assert subagent.snap_to_8pt_grid(3) == 8
    assert subagent.snap_to_8pt_grid(7) == 8
    assert subagent.snap_to_8pt_grid(13) == 16
    assert subagent.snap_to_8pt_grid(23) == 24
    assert subagent.snap_to_8pt_grid(31) == 32
    assert subagent.snap_to_8pt_grid(5, allow_half_step=True) == 4


def test_wcag_contrast_ratio_and_token_compliance():
    """Verify WCAG 2.1 contrast calculation and widget tree token compliance auditing."""
    subagent = DesignTokenAnd8PtGridSubagent()

    # Pure white on pure black = 21.0
    assert subagent.compute_wcag_contrast_ratio("#ffffff", "#000000") == 21.0

    # Primary text (#f3f4f6) on Canvas BG (#0b0d14) passes WCAG AAA (>= 7.0)
    primary_contrast = subagent.compute_wcag_contrast_ratio(
        subagent.TEXT_PRIMARY, subagent.CANVAS_BG
    )
    assert primary_contrast >= 15.0

    # Secondary text (#9ca3af) on Card Surface (#151926) passes WCAG AA (>= 4.5)
    secondary_contrast = subagent.compute_wcag_contrast_ratio(
        subagent.TEXT_SECONDARY, subagent.CARD_SURFACE
    )
    assert secondary_contrast >= 6.0

    # Compliant widget tree
    clean_tree = [
        {
            "id": "kpi_card_1",
            "bg": subagent.CARD_SURFACE,
            "fg": subagent.TEXT_PRIMARY,
            "padding": subagent.SPACE_6,
            "gap": subagent.SPACE_4,
        },
        {
            "id": "primary_cta",
            "bg": subagent.PRIMARY_ACCENT,
            "fg": subagent.TEXT_PRIMARY,
            "padding_x": subagent.SPACE_4,
            "padding_y": subagent.SPACE_2,
            "min_contrast": 4.0,
        },
    ]
    clean_report = subagent.audit_token_compliance(clean_tree)
    assert clean_report["compliant"] is True
    assert clean_report["compliance_score"] == 100.0
    assert clean_report["grid_alignment_ratio"] == 1.0

    # Non-compliant rainbow/off-grid widget tree
    messy_tree = [
        {
            "id": "neon_yellow_btn",
            "bg": "#eab308",
            "fg": "#ffffff",
            "padding": 5,
            "gap": 3,
        }
    ]
    messy_report = subagent.audit_token_compliance(messy_tree)
    assert messy_report["compliant"] is False
    assert len(messy_report["token_violations"]) >= 1
    assert len(messy_report["grid_violations"]) == 2
    assert len(messy_report["contrast_violations"]) == 1


def test_visual_clutter_critic_penalizes_v12_and_rewards_v13():
    """
    Verify VisualScreenshotClutterCriticSubagent penalizes the cluttered Rainbow +
    8+ Horizontal Tabs layout (score < 65) and rewards the Linear/Raycast Sidebar +
    Bento Grid + Single Primary CTA layout (score >= 94, grade starting with 'A+').
    """
    critic = VisualScreenshotClutterCriticSubagent()

    v12_spec = VisualScreenshotClutterCriticEngine.default_v12_cluttered_spec()
    v12_result = critic.critique(v12_spec)

    assert v12_result["rainbow_button_overload_count"] == 7
    assert v12_result["hicks_law_choice_overload"] > 7
    assert v12_result["whitespace_ratio"] < 0.25
    assert v12_result["overall_beauty_and_logic_score"] < 65
    assert v12_result["grade"] == "C (Cluttered)"
    assert len(v12_result["critique_findings"]) >= 4
    assert len(v12_result["auto_fix_recommendations"]) >= 4

    v13_spec = VisualScreenshotClutterCriticEngine.default_v13_linear_bento_spec()
    v13_result = critic.critique(v13_spec)

    assert v13_result["rainbow_button_overload_count"] == 1
    assert v13_result["hicks_law_choice_overload"] == 5
    assert v13_result["whitespace_ratio"] >= 0.25
    assert v13_result["grid_8pt_alignment_score"] == 100.0
    assert v13_result["wcag_contrast_score"] == 100.0
    assert v13_result["visual_hierarchy_score"] == 100.0
    assert v13_result["overall_beauty_and_logic_score"] >= 94
    assert v13_result["grade"].startswith("A+")


def test_render_before_and_after_ui_comparison_screenshots():
    """
    Verify `render_before_and_after_ui_comparison` creates `ui_before_v12_cluttered.png`
    and `ui_after_v13_linear_bento.png` at 1340x880 resolution and scores them accurately.
    """
    output_dir = Path(__file__).resolve().parent.parent / "artifacts" / "ui_ux_comparison"
    critic = VisualScreenshotClutterCriticSubagent()
    comparison = critic.render_before_and_after_ui_comparison(output_dir)

    before_path = Path(comparison["before_image_path"])
    after_path = Path(comparison["after_image_path"])

    assert before_path.name == "ui_before_v12_cluttered.png"
    assert after_path.name == "ui_after_v13_linear_bento.png"
    assert before_path.exists() and before_path.stat().st_size > 10_000
    assert after_path.exists() and after_path.stat().st_size > 10_000

    with Image.open(before_path) as img_before:
        assert img_before.size == (1340, 880)
    with Image.open(after_path) as img_after:
        assert img_after.size == (1340, 880)

    before_score = comparison["before_audit"]["overall_beauty_and_logic_score"]
    after_score = comparison["after_audit"]["overall_beauty_and_logic_score"]

    assert before_score < 65
    assert comparison["before_audit"]["grade"] == "C (Cluttered)"
    assert after_score >= 96
    assert comparison["after_audit"]["grade"] == "A+ (Linear/Raycast Grade)"
    assert comparison["score_delta"] >= 35
