"""
Unit tests for Subagents #68, #69 & #70:
- AndroidEnvironmentAndSensorCoherenceSubagent (#68)
- TurnstileAndWAFInvisibleDefenseSubagent (#69)
- AntiBotRadarAndUIUXTelemetrySubagent (#70)
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agents.antibot_fingerprint_and_ui_radar_subagent import (
    AndroidEnvironmentAndSensorCoherenceSubagent,
    AntiBotRadarAndUIUXTelemetrySubagent,
    TurnstileAndWAFInvisibleDefenseSubagent,
)


def test_subagent_68_sensor_touch_micro_correlation_and_env_audit() -> None:
    sub = AndroidEnvironmentAndSensorCoherenceSubagent()
    assert sub.subagent_id == 68

    recoil = sub.generate_sensor_touch_micro_correlation(touch_timestamp_ms=1500.0, tap_force=0.75, seed=42)
    assert 15.0 <= recoil["lag_ms"] <= 40.0
    assert recoil["is_flatline"] is False
    assert recoil["coherence_valid"] is True
    assert len(recoil["damping_samples"]) == 5

    clean_audit = sub.audit_android_environment_signals()
    assert clean_audit["coherence_score"] == 100.0
    assert clean_audit["anomalies"] == []

    leaky_audit = sub.audit_android_environment_signals(
        {"ro_debuggable": "1", "sensor_jitter_std": 0.0, "touch_sensor_lag_ms": 0.0}
    )
    assert leaky_audit["coherence_score"] < 70.0
    assert "ro_debuggable_safe" in leaky_audit["anomalies"]
    assert leaky_audit["remediation_plan"]["ro_debuggable"] == "0"


def test_subagent_69_pre_warm_entropy_and_challenge_triage() -> None:
    sub = TurnstileAndWAFInvisibleDefenseSubagent()
    assert sub.subagent_id == 69

    warm = sub.generate_pre_warm_entropy_sequence(viewport=(1260, 2800), seed=99)
    assert warm["entropy_ready"] is True
    assert len(warm["events"]) == 4
    assert warm["h2_settings_order"] == "1:65536;2:0;4:6291456;6:262144"

    inv = sub.triage_waf_challenge({"widget_mode": "invisible"})
    assert inv["classification"] == "invisible_pass"

    pow_mode = sub.triage_waf_challenge({"widget_mode": "non-interactive", "pow_in_progress": True})
    assert pow_mode["classification"] == "non_interactive_pow_wait"

    inter = sub.triage_waf_challenge({"widget_mode": "interactive", "has_interactive_checkbox": True})
    assert inter["classification"] == "interactive_sigma_lognormal_click"


def test_subagent_70_radar_bento_card_and_comparison_visuals() -> None:
    sub = AntiBotRadarAndUIUXTelemetrySubagent()
    assert sub.subagent_id == 70

    card = sub.build_radar_bento_card_spec(
        serial="10CF5L0TYL00312",
        ui_beauty_score=98.5,
        stealth_score=99.2,
        bot_risk_pct=1.2,
    )
    assert card["grid_8pt_compliant"] is True
    assert card["primary_cta_count"] == 1
    assert card["primary_cta"]["bg_hex"] == "#6366f1"
    assert card["wcag_contrast_ratio"] >= 7.0
    assert len(card["badges"]) <= card["max_visible_badges"]

    out_dir = _PROJECT_ROOT / "artifacts" / "antibot_ui_ux_comparison"
    visuals = sub.render_antibot_and_ui_ux_comparison_visuals(out_dir)
    assert visuals["before_exists"] is True
    assert visuals["after_exists"] is True
