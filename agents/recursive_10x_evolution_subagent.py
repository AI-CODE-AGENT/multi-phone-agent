"""
Subagents #51–#55: Recursive 10x Self-Evolution Subagent Suite.

Exports:
- #51: GKDSelectorRuleEngineSubagent
- #52: MobileAgentTipsAndShortcutsMemorySubagent
- #53: UITarsSystem2ReflectionVerifierSubagent
- #54: DroidBotStateTransitionGraphSubagent
- #55: Recursive10xEvolutionCoordinatorSubagent
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.recursive_10x_evolution_engine import (
    AgentShortcut,
    AgentTip,
    DroidBotStateTransitionGraph,
    GKDRule,
    GKDSelectorRuleEngine,
    MobileAgentTipsAndShortcutsMemory,
    Recursive10xEvolutionCoordinator,
    UIElementNode,
    UITarsSystem2ReflectionVerifier,
)


class GKDSelectorRuleEngineSubagent:
    """
    Subagent #51: CSS-like Accessibility Selector Engine Subagent (`gkd-kit/gkd`).
    Evaluates priority-ordered GKD selectors in < 2ms with zero AI tokens.
    """

    subagent_id: int = 51
    name: str = "GKDSelectorRuleEngineSubagent"

    def __init__(self, rules: list[GKDRule] | None = None) -> None:
        self.engine = GKDSelectorRuleEngine(rules=rules)

    def matches_element(self, selector: str, element: UIElementNode | dict[str, Any]) -> bool:
        return self.engine.matches_element(selector, element)

    def query_first(
        self,
        selector: str,
        elements: list[UIElementNode | dict[str, Any]],
    ) -> UIElementNode | None:
        return self.engine.query_first(selector, elements)

    def query_all(
        self,
        selector: str,
        elements: list[UIElementNode | dict[str, Any]],
    ) -> list[UIElementNode]:
        return self.engine.query_all(selector, elements)

    def evaluate(
        self,
        elements: list[UIElementNode | dict[str, Any]],
        current_package: str = "*",
    ) -> dict[str, Any]:
        return self.engine.evaluate_rules(elements, current_package=current_package)


class MobileAgentTipsAndShortcutsMemorySubagent:
    """
    Subagent #52: Self-Evolving Tips & Shortcuts Memory Subagent (`X-PLUG/MobileAgent`).
    Stores and retrieves declarative `Tips` and multi-step `Shortcuts`.
    """

    subagent_id: int = 52
    name: str = "MobileAgentTipsAndShortcutsMemorySubagent"

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self.engine = MobileAgentTipsAndShortcutsMemory(storage_path=storage_path)

    def evolve_tip(self, tip: AgentTip) -> AgentTip:
        return self.engine.evolve_tip(tip)

    def evolve_shortcut(self, shortcut: AgentShortcut) -> AgentShortcut:
        return self.engine.evolve_shortcut(shortcut)

    def retrieve(self, ui_state_context: str | dict[str, Any]) -> dict[str, Any]:
        return self.engine.retrieve_for_state(ui_state_context)

    def save(self, path: str | Path | None = None) -> Path:
        return self.engine.save(path)

    def load(self, path: str | Path | None = None) -> None:
        self.engine.load(path)


class UITarsSystem2ReflectionVerifierSubagent:
    """
    Subagent #53: System-2 Pre/Post-Action Reflection Verifier Subagent (`ByteDance/UI-TARS`).
    Blocks spatial top-zone traps (`y < 20%`), negative trap keywords, and detects redirect stalls.
    """

    subagent_id: int = 53
    name: str = "UITarsSystem2ReflectionVerifierSubagent"

    def __init__(self) -> None:
        self.engine = UITarsSystem2ReflectionVerifier()

    def pre_action_reflect(
        self,
        target_element: UIElementNode | dict[str, Any],
        screen_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.engine.pre_action_reflect(target_element, screen_context)

    def post_action_reflect(
        self,
        before_state_hash: str,
        after_state_hash: str,
        target_element: UIElementNode | dict[str, Any] | None = None,
        after_activity: str = "",
    ) -> dict[str, Any]:
        return self.engine.post_action_reflect(
            before_state_hash=before_state_hash,
            after_state_hash=after_state_hash,
            target_element=target_element,
            after_activity=after_activity,
        )


class DroidBotStateTransitionGraphSubagent:
    """
    Subagent #54: Directed UI Transition Graph (`UTG`) Subagent (`honeynet/droidbot`).
    Tracks visited `activity::element_hash` states and breaks loop traps.
    """

    subagent_id: int = 54
    name: str = "DroidBotStateTransitionGraphSubagent"

    def __init__(self, loop_threshold: int = 2) -> None:
        self.engine = DroidBotStateTransitionGraph(loop_threshold=loop_threshold)

    def record_state(
        self,
        activity: str,
        elements: list[UIElementNode | dict[str, Any]] | str = "",
        action_taken: str = "init",
    ) -> str:
        return self.engine.record_state(activity, elements, action_taken=action_taken)

    def detect_loop_trap(self) -> dict[str, Any]:
        return self.engine.detect_loop_trap()


class Recursive10xEvolutionCoordinatorSubagent:
    """
    Subagent #55: 10-Iteration Recursive Self-Evolution Coordinator Subagent.
    Executes the full 10-iteration evolution loop and generates `RECURSIVE_10X_EVOLUTION_REPORT.md`.
    """

    subagent_id: int = 55
    name: str = "Recursive10xEvolutionCoordinatorSubagent"

    def __init__(self, project_root: str | Path = r"D:\Project\multi-phone-agent") -> None:
        self.coordinator = Recursive10xEvolutionCoordinator(project_root=project_root)

    def run_10_iterations(
        self,
        live_serial: str | None = None,
        write_report: bool = True,
    ) -> dict[str, Any]:
        return self.coordinator.run_10_iterations(
            live_serial=live_serial,
            write_report=write_report,
        )


__all__ = [
    "GKDSelectorRuleEngineSubagent",
    "MobileAgentTipsAndShortcutsMemorySubagent",
    "UITarsSystem2ReflectionVerifierSubagent",
    "DroidBotStateTransitionGraphSubagent",
    "Recursive10xEvolutionCoordinatorSubagent",
]
