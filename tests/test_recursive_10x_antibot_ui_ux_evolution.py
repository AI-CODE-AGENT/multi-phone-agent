"""
Unit & Integration Tests for Subagents #71–#75:
Recursive 10x Anti-Bot & Mobile UI/UX Self-Evolution Suite (AMAF v14.0).
"""

from __future__ import annotations

from pathlib import Path

from agents.recursive_10x_antibot_ui_ux_evolution_subagent import (
    AdaptiveDwellAndRhythmPacerSubagent,
    CausalChain10xAntiBotUIUXCoordinatorSubagent,
    CrossLayerBotSignalCorrelatorSubagent,
    MobileAppHeaderAndFilterPillRefinerSubagent,
    UnifiedUIUXAndAntiBotFinishGateSubagent,
)


def test_subagent_71_mobile_header_filter_pills_and_card_badges() -> None:
    sub = MobileAppHeaderAndFilterPillRefinerSubagent()
    assert sub.subagent_id == 71

    # 1. Top Header Chips refinement (safe_top_inset_dp >= 16 on 8pt grid, max 1 primary CTA)
    raw_chips = [
        {"chip_id": "ready", "label": "Sẵn sàng", "role": "secondary"},
        {"chip_id": "trash", "label": "Thùng rác", "role": "secondary"},
        {"chip_id": "select", "label": "Chọn", "role": "primary"},
    ]
    header_res = sub.refine_top_header_chips(raw_chips, safe_top_inset_dp=11)
    assert header_res["safe_top_inset_dp"] >= 16
    assert header_res["safe_top_inset_dp"] % 8 == 0
    assert header_res["grid_8pt_compliant"] is True
    assert header_res["primary_cta_count"] == 1
    assert header_res["secondary_chip_count"] == 2
    assert header_res["min_contrast_ratio"] >= 4.5
    assert header_res["wcag_aa_compliant"] is True

    # 2. Filter Pills single-row horizontal scroll compaction (>=60% vertical space saved)
    raw_pills = [
        {"label": "Tất cả", "count": 4, "active": True},
        {"label": "Cuộc gọi 0", "count": 0, "active": False},
        {"label": "Ghi âm", "count": 4, "active": False},
        {"label": "Yêu thích 0", "count": 0, "active": False},
        {"label": "Có ghi chú 0", "count": 0, "active": False},
        {"label": "Hôm nay", "count": 4, "active": False},
        {"label": "Tuần này", "count": 4, "active": False},
    ]
    pills_res = sub.compact_filter_pills_to_single_scroll_row(raw_pills)
    assert pills_res["layout_mode"] == "single_row_horizontal_scroll"
    assert pills_res["row_count"] == 1
    assert pills_res["height_dp"] == 40
    assert pills_res["gap_dp"] == 8
    assert pills_res["hidden_zero_badge_count"] == 3
    assert pills_res["vertical_space_saved_pct"] >= 60.0
    assert pills_res["space_saving_target_met"] is True

    # 3. Recording Card micro-badge consolidation & WCAG AAA star contrast (>=7.0:1)
    raw_badges = ["WAV", "26-10", "14:11", "00:31", "980.4 KB"]
    card_res = sub.consolidate_recording_card_micro_badges(
        raw_badges,
        star_fg_hex="#334155",
        card_bg_hex="#0f172a",
    )
    assert card_res["subtitle"] == "26-10, 14:11 • 00:31 • WAV (980.4 KB)"
    assert card_res["semantic_badge_count"] <= 2
    assert card_res["max_two_badges_enforced"] is True
    assert card_res["star_contrast_ratio"] >= 7.0
    assert card_res["wcag_aaa_star_compliant"] is True

    full_exec = sub.execute()
    assert full_exec["all_mobile_clutter_resolved"] is True


def test_subagent_72_adaptive_cognitive_dwell_and_rhythm_pacer() -> None:
    sub = AdaptiveDwellAndRhythmPacerSubagent()
    assert sub.subagent_id == 72

    dwell_low = sub.compute_cognitive_dwell_ms(
        word_count=5,
        clickable_count=2,
        complexity_tier="low",
        seed=101,
    )
    dwell_high = sub.compute_cognitive_dwell_ms(
        word_count=30,
        clickable_count=10,
        complexity_tier="high",
        seed=101,
    )
    assert dwell_low["is_non_robotic"] is True
    assert dwell_high["is_non_robotic"] is True
    assert dwell_high["base_reading_ms"] > dwell_low["base_reading_ms"]
    assert dwell_high["hicks_choice_ms"] > dwell_low["hicks_choice_ms"]
    assert dwell_high["rhythm_entropy"] >= 2.1

    # Robotic fixed sleep(1.0) intervals -> cv < 0.08 -> is_robotic_clock = True
    robotic_audit = sub.audit_inter_action_intervals([1000.0, 1000.0, 1000.0, 1000.0, 1000.0])
    assert robotic_audit["cv"] < 0.08
    assert robotic_audit["is_robotic_clock"] is True
    assert robotic_audit["human_rhythm_verified"] is False

    # Organic human intervals -> cv >= 0.15 -> is_robotic_clock = False
    exec_res = sub.execute(word_count=16, clickable_count=6, seed=72)
    assert exec_res["schedule_audit"]["cv"] >= 0.15
    assert exec_res["schedule_audit"]["is_robotic_clock"] is False
    assert exec_res["schedule_audit"]["human_rhythm_verified"] is True


def test_subagent_73_cross_layer_bot_signal_correlator() -> None:
    sub = CrossLayerBotSignalCorrelatorSubagent()
    assert sub.subagent_id == 73

    weak_signals = {
        "touch_kinematics_score": 42.0,
        "cdp_webview_stealth_score": 38.0,
        "sensor_env_coherence_score": 51.0,
        "cognitive_rhythm_score": 45.0,
    }
    res = sub.correlate_and_remediate(weak_signals, auto_remediate=True, threshold=92.0)
    assert len(res["weak_layers_detected"]) == 4
    assert len(res["remediations_applied"]) == 4
    assert res["stealth_score_before"] < 50.0
    assert res["overall_stealth_score"] >= 95.0
    assert res["bot_detection_risk_pct"] <= 5.0
    assert res["all_layers_hardened"] is True


def test_subagent_74_unified_ui_ux_and_antibot_finish_gate() -> None:
    sub = UnifiedUIUXAndAntiBotFinishGateSubagent()
    assert sub.subagent_id == 74

    # Incomplete state -> HOLD
    hold_res = sub.evaluate_unified_finish_gate(
        {
            "single_primary_cta": True,
            "grid_8pt_compliant": True,
            "wcag_aa_contrast": False,
            "single_row_filter_ribbon": True,
            "command_palette_and_sidebar_ia": True,
            "sigma_lognormal_touch": True,
            "zero_runtime_enable_cdp": True,
            "sensor_touch_correlated": False,
            "pre_warm_entropy_active": True,
            "cognitive_rhythm_non_robotic": True,
            "composite_score": 80.0,
            "bot_detection_risk_pct": 18.0,
        }
    )
    assert hold_res["decision"] == "HOLD"
    assert hold_res["all_10_criteria_passed"] is False
    assert "wcag_aa_contrast" in hold_res["failed_criteria"]
    assert "sensor_touch_correlated" in hold_res["failed_criteria"]

    # Complete hardened state -> PASS
    pass_res = sub.execute()
    assert pass_res["decision"] == "PASS"
    assert pass_res["all_10_criteria_passed"] is True
    assert pass_res["passed_criteria_count"] == 10
    assert pass_res["composite_score"] >= 95.0
    assert pass_res["bot_detection_risk_pct"] <= 5.0


def test_subagent_75_causal_chain_10x_coordinator_and_na_recurrence() -> None:
    sub = CausalChain10xAntiBotUIUXCoordinatorSubagent(project_root=r"D:\Project\multi-phone-agent")
    assert sub.subagent_id == 75

    summary = sub.run_10_causal_iterations(live_serial="10CF5L0TYL00312", write_report=True)
    assert summary["total_iterations"] == 10
    assert summary["initial_composite_score"] == 44.0
    assert summary["final_composite_score"] == 100.0
    assert summary["initial_bot_risk_pct"] == 78.5
    assert summary["final_bot_risk_pct"] == 1.2
    assert summary["initial_gate"] == "HOLD"
    assert summary["final_gate"] == "PASS"
    assert summary["causal_chain_verified"] is True

    invariants = summary["invariants"]
    # For 10 iterations, pairs (n >= 1, a >= 1, n + a <= 10) = 9 + 8 + ... + 1 = 45 pairs
    assert invariants["total_na_pairs_verified"] == 45
    assert invariants["causal_chain_valid"] is True
    assert invariants["monotonic_score_improvement"] is True
    assert invariants["monotonic_risk_reduction"] is True
    assert invariants["violations"] == []

    # Explicitly verify Loop (n + a) only started after Loop (n + a - 1) completed for all n, a >= 1
    iterations = summary["iterations"]
    for n in range(1, 10):
        for a in range(1, 10 - n + 1):
            k = n + a
            prev_it = iterations[k - 2]  # Loop n + a - 1
            curr_it = iterations[k - 1]  # Loop n + a
            assert curr_it["iteration"] == k
            assert prev_it["iteration"] == k - 1
            assert curr_it["started_at_ns"] > prev_it["completed_at_ns"]
            assert curr_it["parent_sha256"] == prev_it["result_sha256"]
            assert curr_it["input_prompt"] == prev_it["rewritten_next_loop_prompt"]

    report_file = Path(summary["report_path"])
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "RECURSIVE 10X ANTI-BOT & UI/UX SELF-EVOLUTION REPORT" in content
    assert "10CF5L0TYL00312" in content
