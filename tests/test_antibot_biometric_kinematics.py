"""
Unit Tests for Cluster 1 (Subagents #66 & #67):
  - `SigmaLognormalTouchKinematicsEngine` & `SigmaLognormalTouchKinematicsSubagent` (#66)
  - `PatchrightStealthCDPandWebViewEngine` & `PatchrightStealthCDPandWebViewSubagent` (#67)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.antibot_biometric_kinematics_subagent import (
    PatchrightStealthCDPandWebViewSubagent,
    SigmaLognormalTouchKinematicsSubagent,
)
from core.antibot_biometric_kinematics_engine import (
    PatchrightStealthCDPandWebViewEngine,
    SigmaLognormalTouchKinematicsEngine,
    TouchSample,
)


def test_subagent_66_fitts_gaussian_target_dispersion() -> None:
    subagent = SigmaLognormalTouchKinematicsSubagent()
    assert subagent.subagent_id == 66

    bounds = (200, 1500, 860, 1680)
    samples = [
        subagent.sample_fitts_gaussian_target(bounds=bounds, seed=100 + i)
        for i in range(25)
    ]

    xs = set()
    ys = set()
    for res in samples:
        tx, ty = res["tx"], res["ty"]
        assert bounds[0] + 4 <= tx <= bounds[2] - 4
        assert bounds[1] + 4 <= ty <= bounds[3] - 4
        assert res["id_bits"] > 0.0
        assert res["sigma_x"] == (bounds[2] - bounds[0]) / 6.0
        assert res["sigma_y"] == (bounds[3] - bounds[1]) / 6.0
        xs.add(tx)
        ys.add(ty)

    # Confirm non-constant realistic dispersion across seeds
    assert len(xs) > 10
    assert len(ys) > 10


def test_subagent_66_sigma_lognormal_swipe_vs_linear_bot_detection() -> None:
    subagent = SigmaLognormalTouchKinematicsSubagent()
    swipe = subagent.generate_sigma_lognormal_swipe(
        start=(630, 2200),
        end=(640, 620),
        duration_ms=360,
        steps=26,
        seed=42,
    )

    assert len(swipe["samples"]) == 26
    assert len(swipe["adb_motionevent_commands"]) == 26
    assert swipe["adb_motionevent_commands"][0].startswith("input motionevent DOWN")
    assert swipe["adb_motionevent_commands"][-1].startswith("input motionevent UP")
    assert 0.25 <= swipe["peak_velocity_ratio"] <= 0.50
    assert swipe["pressure_std"] > 0.12
    assert swipe["lateral_deviation_px"] >= 3.5

    human_audit = subagent.audit_trajectory_human_likeness(swipe["samples"])
    assert human_audit["is_bot_flagged"] is False
    assert human_audit["human_likeness_score"] >= 85.0
    assert human_audit["velocity_cv"] > 0.35
    assert human_audit["lateral_jitter_px"] >= 3.5

    # Construct a synthetic robotic linear constant-velocity, constant-pressure swipe
    bot_samples = []
    for i in range(24):
        u = i / 23.0
        bot_samples.append(
            TouchSample(
                x=630.0,
                y=2200.0 + u * (620.0 - 2200.0),
                t_ms=u * 340.0,
                pressure=1.0,
                touch_major=5.0,
                velocity_px_s=4647.06,
            )
        )

    bot_audit = subagent.audit_trajectory_human_likeness(bot_samples)
    assert bot_audit["is_bot_flagged"] is True
    assert bot_audit["human_likeness_score"] < 15.0
    assert bot_audit["pressure_std"] == 0.0
    assert bot_audit["lateral_jitter_px"] == 0.0

    exec_report = subagent.execute(seed=99)
    assert exec_report["status"] == "SIGMA_LOGNORMAL_KINEMATICS_SYNTHESIZED"
    assert exec_report["subagent_id"] == 66
    assert exec_report["tokens_used"] == 0
    assert exec_report["audit"]["is_bot_flagged"] is False


def test_subagent_67_stealth_isolated_world_command_zero_runtime_enable() -> None:
    subagent = PatchrightStealthCDPandWebViewSubagent()
    assert subagent.subagent_id == 67

    cmd_bundle = subagent.build_stealth_isolated_world_command(
        frame_id="FRAME_VIVO_01",
        expression="window.navigator.userAgent",
        world_name="amaf_stealth_world",
    )

    assert cmd_bundle["uses_runtime_enable"] is False
    assert "Runtime.enable" not in cmd_bundle["methods"]
    assert cmd_bundle["methods"] == [
        "Page.createIsolatedWorld",
        "Runtime.callFunctionOn",
    ]
    assert cmd_bundle["commands"][0]["params"]["frameId"] == "FRAME_VIVO_01"
    assert cmd_bundle["commands"][0]["params"]["worldName"] == "amaf_stealth_world"


def test_subagent_67_vivo_v2417a_webview_stealth_audit_and_remediation() -> None:
    subagent = PatchrightStealthCDPandWebViewSubagent()
    clean_profile = subagent.build_vivo_v2417a_hardware_profile(
        serial="10CF5L0TYL00312"
    )

    assert clean_profile["model"] == "V2417A"
    assert clean_profile["platform"] == "Linux aarch64"
    assert clean_profile["webgl_vendor"] == "Qualcomm"
    assert clean_profile["webgl_renderer"] == "Adreno (TM) 730"
    assert clean_profile["screen_width"] == 1260
    assert clean_profile["screen_height"] == 2800
    assert clean_profile["device_pixel_ratio"] == 2.8125
    assert clean_profile["navigator_webdriver"] is False
    assert clean_profile["runtime_enable_leaked"] is False
    assert clean_profile["cdc_artifacts_present"] is False

    clean_audit = subagent.audit_webview_stealth_posture(clean_profile)
    assert clean_audit["passed_vectors"] == 8
    assert clean_audit["total_vectors"] == 8
    assert clean_audit["stealth_score"] == 100.0
    assert clean_audit["leaks_detected"] == []

    # Test leaky bot profile detection & automatic remediation
    leaky_profile = dict(clean_profile)
    leaky_profile["runtime_enable_leaked"] = True
    leaky_profile["navigator_webdriver"] = True
    leaky_profile["cdc_artifacts_present"] = True
    leaky_profile["webgl_renderer"] = "SwiftShader"

    leaky_audit = subagent.audit_webview_stealth_posture(leaky_profile)
    assert leaky_audit["passed_vectors"] == 4
    assert leaky_audit["stealth_score"] == 50.0
    assert "no_runtime_enable_leak" in leaky_audit["leaks_detected"]
    assert "navigator_webdriver_false" in leaky_audit["leaks_detected"]
    assert "no_cdc_artifacts" in leaky_audit["leaks_detected"]
    assert "webgl_arm_coherent" in leaky_audit["leaks_detected"]

    remediated_audit = subagent.audit_webview_stealth_posture(
        leaky_audit["remediated_profile"]
    )
    assert remediated_audit["stealth_score"] == 100.0

    exec_report = subagent.execute(serial="10CF5L0TYL00312")
    assert exec_report["status"] == "STEALTH_CDP_AND_WEBVIEW_AUDITED"
    assert exec_report["subagent_id"] == 67
    assert exec_report["tokens_used"] == 0
    assert exec_report["audit"]["stealth_score"] == 100.0
