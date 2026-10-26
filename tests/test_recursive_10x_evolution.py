"""
Unit tests for Subagents #51–#55 (`Recursive10xEvolutionSubagent` suite) and
`core.recursive_10x_evolution_engine`.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.recursive_10x_evolution_subagent import (
    DroidBotStateTransitionGraphSubagent,
    GKDSelectorRuleEngineSubagent,
    MobileAgentTipsAndShortcutsMemorySubagent,
    Recursive10xEvolutionCoordinatorSubagent,
    UITarsSystem2ReflectionVerifierSubagent,
)
from core.recursive_10x_evolution_engine import (
    AgentShortcut,
    AgentTip,
    DroidBotStateTransitionGraph,
    GKDSelectorRuleEngine,
    MobileAgentTipsAndShortcutsMemory,
    Recursive10xEvolutionCoordinator,
    UIElementNode,
    UITarsSystem2ReflectionVerifier,
)


def test_gkd_selector_rule_engine_operators() -> None:
    """Verify GKDSelectorRuleEngine supports *=, !*= / !*, checked=false, and y>=500 in < 2ms."""
    engine = GKDSelectorRuleEngine()

    cb_node = UIElementNode(
        class_name="android.widget.CheckBox",
        resource_id="com.android.packageinstaller:id/deleted_file_state_cb",
        text="Tự động xóa gói cài đặt",
        checkable=True,
        checked=False,
        clickable=True,
        bounds=(80, 1800, 980, 1900),
    )
    assert engine.matches_element(
        'CheckBox[id*="deleted_file_state_cb"][checked=false]', cb_node
    )
    assert not engine.matches_element(
        'CheckBox[id*="deleted_file_state_cb"][checked=true]', cb_node
    )

    continue_btn = UIElementNode(
        class_name="android.widget.Button",
        resource_id="android:id/button1",
        text="Tiếp tục cài đặt",
        clickable=True,
        bounds=(540, 2100, 1000, 2240),
    )
    cancel_btn = UIElementNode(
        class_name="android.widget.Button",
        resource_id="android:id/button2",
        text="Hủy",
        clickable=True,
        bounds=(80, 2100, 500, 2240),
    )
    top_btn = UIElementNode(
        class_name="android.widget.Button",
        resource_id="android:id/button1",
        text="Tiếp tục",
        clickable=True,
        bounds=(540, 100, 1000, 200),
    )

    sel = 'Button[id="android:id/button1"][text*="Tiếp tục"][text!*="Hủy"][y>=500]'
    assert engine.matches_element(sel, continue_btn)
    assert not engine.matches_element(sel, cancel_btn)
    assert not engine.matches_element(sel, top_btn)

    # Also test `!*` shorthand operator
    assert engine.matches_element('Button[text!*"Hủy"][y>=500]', continue_btn)
    assert not engine.matches_element('Button[text!*"Hủy"][y>=500]', cancel_btn)

    subagent = GKDSelectorRuleEngineSubagent()
    eval_res = subagent.evaluate(
        [cb_node, cancel_btn, continue_btn],
        current_package="com.android.packageinstaller",
    )
    assert eval_res["matched"] is True
    assert eval_res["element"]["id"] == "android:id/button1"
    assert eval_res["elapsed_ms"] < 15.0


def test_mobile_agent_tips_and_shortcuts_memory() -> None:
    """Verify MobileAgentTipsAndShortcutsMemory evolution, JSON persistence, and state lookup."""
    mem_file = PROJECT_ROOT / "reports" / "_test_tips_shortcuts_memory.json"
    if mem_file.exists():
        mem_file.unlink()
    try:
        subagent = MobileAgentTipsAndShortcutsMemorySubagent(storage_path=mem_file)

        # Verify built-in shortcuts exist
        assert "vivo_originos_apk_intercept_bypass" in subagent.engine.shortcuts
        assert "manage_external_sources_toggle_and_back" in subagent.engine.shortcuts
        assert "vivo_user_666_pm_normalization" in subagent.engine.shortcuts

        # Evolve a new tip and shortcut
        new_tip = AgentTip(
            tip_id="tip_custom_miui_intercept",
            trigger_signature="miui_security_center",
            oem_scope="xiaomi_miui",
            lesson="Check 'I am aware of the risks' before clicking Continue on MIUI.",
            avoid_failure_mode="Disabled Continue button on MIUI.",
            recommended_selector='CheckBox[id*="risk"][checked=false]',
            iteration_learned=9,
        )
        subagent.evolve_tip(new_tip)

        new_sc = AgentShortcut(
            shortcut_id="miui_security_bypass",
            name="miui_security_bypass",
            trigger_signature="miui_security_center",
            steps=[{"step": 1, "action": "click", "selector": 'CheckBox[id*="risk"]'}],
            description="Bypasses MIUI risk checkbox.",
        )
        subagent.evolve_shortcut(new_sc)

        assert mem_file.exists()

        # Reload into a fresh instance and verify lookup
        reloaded = MobileAgentTipsAndShortcutsMemory(storage_path=mem_file)
        lookup = reloaded.retrieve_for_state("miui_security_center dialog")
        assert lookup["primary_tip"] is not None
        assert lookup["primary_tip"]["tip_id"] == "tip_custom_miui_intercept"
        assert lookup["primary_shortcut"] is not None
        assert lookup["primary_shortcut"]["shortcut_id"] == "miui_security_bypass"
    finally:
        if mem_file.exists():
            mem_file.unlink()


def test_uitars_system2_reflection_verifier() -> None:
    """Verify System-2 pre-action spatial/keyword trap rejection and post-action transition check."""
    subagent = UITarsSystem2ReflectionVerifierSubagent()

    # 1. Top 20% trap element (y=150 on 2400px screen)
    top_trap = {
        "class_name": "android.widget.TextView",
        "id": "com.android.packageinstaller:id/install_switch_entrance",
        "text": "Quản lý cài đặt",
        "bounds": [600, 100, 1000, 200],
    }
    pre_top = subagent.pre_action_reflect(top_trap, {"screen_height": 2400})
    assert pre_top["approved"] is False
    assert pre_top["spatial_ok"] is False

    # 2. Negative keyword trap ("Hủy")
    cancel_trap = {
        "class_name": "android.widget.Button",
        "id": "android:id/button2",
        "text": "Hủy cài đặt",
        "bounds": [80, 2100, 480, 2240],
    }
    pre_cancel = subagent.pre_action_reflect(cancel_trap, {"screen_height": 2400})
    assert pre_cancel["approved"] is False

    # 3. Valid bottom primary button
    valid_btn = {
        "class_name": "android.widget.Button",
        "id": "android:id/button1",
        "text": "Tiếp tục cài đặt",
        "enabled": True,
        "bounds": [540, 2100, 1000, 2240],
    }
    pre_valid = subagent.pre_action_reflect(valid_btn, {"screen_height": 2400})
    assert pre_valid["approved"] is True
    assert pre_valid["spatial_ok"] is True

    # 4. Post-action reflection: false-positive redirect vs stalled vs advanced
    post_fp = subagent.post_action_reflect(
        before_state_hash="PackageInterceptActivity::1111",
        after_state_hash="InstallSwitchActivity::2222",
        target_element=top_trap,
        after_activity="com.android.packageinstaller.InstallSwitchActivity",
    )
    assert post_fp["false_positive_redirect"] is True
    assert post_fp["recovery_action"] == "KEYCODE_BACK"

    post_stalled = subagent.post_action_reflect(
        before_state_hash="PackageInterceptActivity::1111",
        after_state_hash="PackageInterceptActivity::1111",
        target_element=valid_btn,
    )
    assert post_stalled["stalled"] is True

    post_advanced = subagent.post_action_reflect(
        before_state_hash="PackageInterceptActivity::1111",
        after_state_hash="InstallInstalling::3333",
        target_element=valid_btn,
        after_activity="com.android.packageinstaller.InstallInstalling",
    )
    assert post_advanced["advanced"] is True


def test_droidbot_state_transition_graph_loop_detection() -> None:
    """Verify DroidBot UTG detects bounce loops between PackageInterceptActivity and InstallSwitchActivity."""
    subagent = DroidBotStateTransitionGraphSubagent(loop_threshold=2)

    subagent.record_state("PackageInterceptActivity", "xml_v1", action_taken="init")
    assert subagent.detect_loop_trap()["loop_detected"] is False

    subagent.record_state("InstallSwitchActivity", "xml_v2", action_taken="click_header")
    subagent.record_state("PackageInterceptActivity", "xml_v1", action_taken="KEYCODE_BACK")
    subagent.record_state("InstallSwitchActivity", "xml_v2", action_taken="click_header")

    trap = subagent.detect_loop_trap()
    assert trap["loop_detected"] is True
    assert trap["loop_type"] == "bounce_loop"
    assert trap["escape_action"] == "KEYCODE_BACK"


def test_recursive_10x_evolution_coordinator_full_loop() -> None:
    """Verify Recursive10xEvolutionCoordinator runs all 10 iterations with 10/10 passed and generates report."""
    subagent = Recursive10xEvolutionCoordinatorSubagent(
        project_root=r"D:\Project\multi-phone-agent"
    )
    result = subagent.run_10_iterations(
        live_serial="10ECBH02JJ000D2",
        write_report=True,
    )

    assert result["total_iterations"] == 10
    assert result["passed_iterations"] == 10
    assert result["pass_rate"] == "10/10"
    assert result["all_passed"] is True
    assert len(result["iterations"]) == 10

    report_file = Path(result["report_path"])
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "Recursive 10x Self-Evolution Architecture Report" in content
    assert "10/10" in content
    assert "vivo_originos_apk_intercept_bypass" in content
    assert "manage_external_sources_toggle_and_back" in content
    assert "vivo_user_666_pm_normalization" in content
