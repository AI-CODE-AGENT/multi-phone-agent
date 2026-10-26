"""
Unit tests for Subagents #61–#65 (`Recursive10xUIUXEvolutionSubagent` suite) and
`core/recursive_10x_ui_ux_evolution_engine.py`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agents.recursive_10x_ui_ux_evolution_subagent import (
    MicroInteractionAndEmptyStateSubagent,
    Recursive10xUIUXEvolutionCoordinatorSubagent,
    SemanticCTAHierarchyAndAntiRainbowSubagent,
    UIFinishGateReviewerSubagent,
    WCAGContrastAndTypographyScaleSubagent,
)


def test_engine_61_anti_rainbow_button_hierarchy_normalization() -> None:
    subagent = SemanticCTAHierarchyAndAntiRainbowSubagent()
    assert subagent.subagent_id == 61

    rainbow_buttons = [
        {"button_id": "btn_start", "label": "Start Farm", "bg_hex": "#22c55e", "role_hint": "primary"},
        {"button_id": "btn_sync", "label": "Sync ADB", "bg_hex": "#3b82f6", "role_hint": "secondary"},
        {"button_id": "btn_apk", "label": "Install APK", "bg_hex": "#a855f7", "role_hint": "secondary"},
        {"button_id": "btn_heal", "label": "Self-Heal", "bg_hex": "#f59e0b", "role_hint": "secondary"},
        {"button_id": "btn_stop", "label": "Stop All", "bg_hex": "#ef4444", "role_hint": "destructive"},
    ]

    before = subagent.detect_rainbow_overload(rainbow_buttons)
    assert before["rainbow_overload_detected"] is True
    assert before["distinct_saturated_count"] == 5

    result = subagent.normalize_button_hierarchy(rainbow_buttons, primary_button_id="btn_start")
    assert result["rainbow_overload_before"] is True
    assert result["rainbow_overload_after"] is False
    assert result["single_primary_cta_enforced"] is True
    assert result["no_rainbow_button_overload"] is True
    assert result["primary_cta_count"] == 1
    assert result["secondary_cta_count"] == 3
    assert result["destructive_cta_count"] == 1

    buttons_by_id = {b["button_id"]: b for b in result["normalized_buttons"]}
    assert buttons_by_id["btn_start"]["bg_hex"] == "#6366f1"
    assert buttons_by_id["btn_sync"]["bg_hex"] == "#1e2436"
    assert buttons_by_id["btn_sync"]["border_hex"] == "#2d354d"
    assert buttons_by_id["btn_sync"]["fg_hex"] == "#f3f4f6"
    assert buttons_by_id["btn_stop"]["bg_hex"] == "#1e2436"
    assert buttons_by_id["btn_stop"]["fg_hex"] == "#ef4444"


def test_engine_62_wcag_contrast_autofix_and_typography_scale() -> None:
    subagent = WCAGContrastAndTypographyScaleSubagent()
    assert subagent.subagent_id == 62

    low_contrast = subagent.contrast_ratio("#475569", "#181d2c")
    assert low_contrast < 4.5

    fixed_single = subagent.auto_fix_foreground_for_contrast("#475569", "#181d2c", target_ratio=4.5)
    assert fixed_single["was_modified"] is True
    assert fixed_single["contrast_after"] >= 4.5
    assert fixed_single["meets_target"] is True

    tokens = [
        {"name": "h1_title", "role": "h1", "fg_hex": "#64748b", "bg_hex": "#0b0d14", "font_size_px": 14},
        {"name": "telemetry_fps", "role": "telemetry", "fg_hex": "#475569", "bg_hex": "#121622", "font_size_px": 9},
        {"name": "body_label", "role": "body", "fg_hex": "#475569", "bg_hex": "#181d2c", "font_size_px": 10},
    ]
    audit = subagent.audit_and_fix_typography_tokens(tokens)
    assert audit["violations_before"] == 3
    assert audit["violations_after"] == 0
    assert audit["wcag_aa_100_percent"] is True
    assert audit["min_contrast_after"] >= 4.5

    by_name = {t["name"]: t for t in audit["tokens"]}
    assert by_name["h1_title"]["passes_wcag_aaa"] is True
    assert by_name["h1_title"]["contrast_after"] >= 7.0
    assert by_name["telemetry_fps"]["passes_wcag_aaa"] is True
    assert by_name["telemetry_fps"]["font_size_px_after"] >= 12
    assert by_name["body_label"]["passes_wcag_aa"] is True


def test_engine_63_empty_state_skeleton_and_shortcuts() -> None:
    subagent = MicroInteractionAndEmptyStateSubagent()
    assert subagent.subagent_id == 63

    skeleton = subagent.get_loading_skeleton_spec("device_matrix", rows=4)
    assert skeleton["state_type"] == "loading_skeleton"
    assert skeleton["grid_unit_px"] == 8
    assert len(skeleton["rows"]) == 4

    empty = subagent.get_empty_state_spec("device_matrix")
    assert empty["state_type"] == "empty_state"
    assert empty["has_recovery_cta"] is True
    assert empty["primary_cta_bg_hex"] == "#6366f1"
    assert "Ctrl+R" in empty["primary_cta_label"]

    badges = subagent.get_shortcut_badges()
    chords = {b["chord"] for b in badges}
    assert {"Ctrl+K", "Ctrl+R", "Ctrl+I", "Ctrl+E"}.issubset(chords)
    assert subagent.resolve_shortcut("ctrl+k") is not None

    t1 = subagent.enqueue_toast("APK Installed", "Vivo Y15s sideload succeeded", severity="success")
    assert t1["accent_hex"] == "#10b981"
    drained = subagent.drain_toasts()
    assert len(drained) == 1
    assert subagent.drain_toasts() == []


def test_engine_64_ui_finish_gate_hold_vs_pass() -> None:
    subagent = UIFinishGateReviewerSubagent()
    assert subagent.subagent_id == 64

    cluttered_ui = {
        "first_read_object_clear": False,
        "single_primary_cta_enforced": False,
        "no_rainbow_button_overload": False,
        "sidebar_ia_miller_compliant": False,
        "command_palette_ctrl_k_present": False,
        "grid_8pt_aligned": False,
        "wcag_aa_compliant": False,
        "states_covered": False,
    }
    hold_res = subagent.evaluate_finish_gate(cluttered_ui)
    assert hold_res["decision"] == "HOLD"
    assert hold_res["score"] < 94.0
    assert len(hold_res["critical_findings"]) == 8

    evolved_ui = {
        "first_read_object_clear": True,
        "single_primary_cta_enforced": True,
        "no_rainbow_button_overload": True,
        "sidebar_ia_miller_compliant": True,
        "command_palette_ctrl_k_present": True,
        "grid_8pt_aligned": True,
        "wcag_aa_compliant": True,
        "states_covered": True,
    }
    pass_res = subagent.evaluate_finish_gate(evolved_ui)
    assert pass_res["decision"] == "PASS"
    assert pass_res["score"] >= 94.0
    assert pass_res["all_criteria_passed"] is True
    assert pass_res["critical_findings"] == []


def test_engine_65_recursive_10x_ui_ux_evolution_loop_and_report() -> None:
    subagent = Recursive10xUIUXEvolutionCoordinatorSubagent(project_root=_PROJECT_ROOT)
    assert subagent.subagent_id == 65

    summary = subagent.run_10_ui_ux_iterations(write_report=True)
    assert summary["total_iterations"] == 10
    assert summary["initial_beauty_score"] < 60.0
    assert summary["final_beauty_score"] >= 96.0
    assert summary["initial_finish_gate_decision"] == "HOLD"
    assert summary["final_finish_gate_decision"] == "PASS"

    iterations = summary["iterations"]
    assert len(iterations) == 10

    # Verify monotonic improvement of beauty_score across all 10 loops
    prev_score = summary["initial_beauty_score"]
    input_prompts = []
    rewritten_prompts = []
    for idx, item in enumerate(iterations):
        curr_score = item["screenshot_and_measure"]["beauty_score"]
        assert curr_score > prev_score, f"Loop {idx + 1} did not improve beauty_score"
        prev_score = curr_score
        input_prompts.append(item["input_prompt"])
        rewritten_prompts.append(item["rewritten_next_loop_prompt"])
        if idx > 0:
            assert item["input_prompt"] == iterations[idx - 1]["rewritten_next_loop_prompt"]

    assert len(set(input_prompts)) == 10
    assert len(set(rewritten_prompts)) == 10

    report_path = Path(summary["report_path"])
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "RECURSIVE 10X UI/UX SELF-EVOLUTION REPORT" in content
    assert "Vòng Đệ Quy #10" in content
    assert "PASS" in content
