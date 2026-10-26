"""
Subagents #61–#65: Recursive 10x UI/UX Self-Evolution Subagent Suite.

Exports:
- #61: SemanticCTAHierarchyAndAntiRainbowSubagent
- #62: WCAGContrastAndTypographyScaleSubagent
- #63: MicroInteractionAndEmptyStateSubagent
- #64: UIFinishGateReviewerSubagent
- #65: Recursive10xUIUXEvolutionCoordinatorSubagent
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from core.recursive_10x_ui_ux_evolution_engine import (
    MicroInteractionAndEmptyStateEngine,
    Recursive10xUIUXEvolutionCoordinator,
    SemanticCTAHierarchyAndAntiRainbowEngine,
    UIButtonSpec,
    UIFinishGateReviewerEngine,
    WCAGContrastAndTypographyScaleEngine,
)


class SemanticCTAHierarchyAndAntiRainbowSubagent:
    """
    Subagent #61: Detects and auto-fixes "Rainbow Button Overload" by converting
    multi-colored button rows into a strict 3-tier visual hierarchy:
    - Tier 1 (`Primary CTA`): Accent Indigo (`#6366f1`) — max 1 per panel.
    - Tier 2 (`Secondary Action`): Neutral Surface (`#1e2436`) with `#2d354d` border.
    - Tier 3 (`Destructive / Guard Action`): Muted `#ef4444` text badge on dark surface.
    """

    subagent_id: int = 61
    name: str = "SemanticCTAHierarchyAndAntiRainbowSubagent"

    def __init__(self) -> None:
        self.engine = SemanticCTAHierarchyAndAntiRainbowEngine()

    def detect_rainbow_overload(self, buttons: list[UIButtonSpec | dict[str, Any]]) -> dict[str, Any]:
        return self.engine.detect_rainbow_overload(buttons)

    def normalize_button_hierarchy(
        self,
        buttons: list[UIButtonSpec | dict[str, Any]],
        primary_button_id: str | None = None,
    ) -> dict[str, Any]:
        return self.engine.normalize_button_hierarchy(
            buttons=buttons,
            primary_button_id=primary_button_id,
        )


class WCAGContrastAndTypographyScaleSubagent:
    """
    Subagent #62: Audits and auto-fixes font sizes, line heights, and foreground/background
    hex pairs so 100% of text meets WCAG 2.1 AA (`>= 4.5:1`) and primary headings/telemetry
    meet WCAG AAA (`>= 7.0:1`).
    """

    subagent_id: int = 62
    name: str = "WCAGContrastAndTypographyScaleSubagent"

    def __init__(self) -> None:
        self.engine = WCAGContrastAndTypographyScaleEngine()

    def contrast_ratio(
        self,
        fg_color: str | tuple[int, int, int],
        bg_color: str | tuple[int, int, int],
    ) -> float:
        return self.engine.contrast_ratio(fg_color, bg_color)

    def auto_fix_foreground_for_contrast(
        self,
        fg_hex: str,
        bg_hex: str,
        target_ratio: float = 4.5,
    ) -> dict[str, Any]:
        return self.engine.auto_fix_foreground_for_contrast(
            fg_hex=fg_hex,
            bg_hex=bg_hex,
            target_ratio=target_ratio,
        )

    def audit_and_fix_typography_tokens(self, tokens: list[dict[str, Any]]) -> dict[str, Any]:
        return self.engine.audit_and_fix_typography_tokens(tokens)


class MicroInteractionAndEmptyStateSubagent:
    """
    Subagent #63: Provides structured Loading Skeletons, informative Empty States
    with a 1-click recovery CTA, Toast Notification queues, and keyboard shortcut
    badges (`Ctrl+K`, `Ctrl+R`, `Ctrl+I`, `Ctrl+E`).
    """

    subagent_id: int = 63
    name: str = "MicroInteractionAndEmptyStateSubagent"

    def __init__(self) -> None:
        self.engine = MicroInteractionAndEmptyStateEngine()

    def get_loading_skeleton_spec(self, view_name: str, rows: int = 4) -> dict[str, Any]:
        return self.engine.get_loading_skeleton_spec(view_name=view_name, rows=rows)

    def get_empty_state_spec(self, context_key: str = "device_matrix") -> dict[str, Any]:
        return self.engine.get_empty_state_spec(context_key=context_key)

    def enqueue_toast(
        self,
        title: str,
        message: str,
        severity: str = "info",
        duration_ms: int = 3200,
    ) -> dict[str, Any]:
        return self.engine.enqueue_toast(
            title=title,
            message=message,
            severity=severity,
            duration_ms=duration_ms,
        )

    def drain_toasts(self) -> list[dict[str, Any]]:
        return self.engine.drain_toasts()

    def get_shortcut_badges(self) -> list[dict[str, str]]:
        return self.engine.get_shortcut_badges()

    def resolve_shortcut(self, chord: str) -> dict[str, str] | None:
        return self.engine.resolve_shortcut(chord)


class UIFinishGateReviewerSubagent:
    """
    Subagent #64: Evaluates the 8-point UI Finish-Gate Reviewer Contract and returns
    `decision`: `"HOLD"` if any critical finding remains, or `"PASS"` when all criteria
    are satisfied (`score >= 94/100`).
    """

    subagent_id: int = 64
    name: str = "UIFinishGateReviewerSubagent"

    def __init__(self) -> None:
        self.engine = UIFinishGateReviewerEngine()

    def evaluate_finish_gate(self, ui_snapshot: dict[str, Any]) -> dict[str, Any]:
        return self.engine.evaluate_finish_gate(ui_snapshot)

    def execute(self, ui_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
        snap = ui_snapshot or {
            "primary_cta_count": 1,
            "saturated_button_colors": 1,
            "workspace_tab_count": 5,
            "min_contrast_ratio": 7.35,
            "has_command_palette_ctrl_k": True,
            "grid_8pt_compliance_pct": 100.0,
            "has_bento_sparkline_cards": True,
            "has_empty_state_and_skeleton": True,
        }
        return self.engine.evaluate_finish_gate(snap)


class Recursive10xUIUXEvolutionCoordinatorSubagent:
    """
    Subagent #65: Executes the 10-Iteration Recursive UI/UX Self-Evolution Loop,
    dynamically rewriting the prompt for Loop `i+1` from Loop `i`'s telemetry and
    generating `RECURSIVE_10X_UI_UX_EVOLUTION_REPORT.md`.
    """

    subagent_id: int = 65
    name: str = "Recursive10xUIUXEvolutionCoordinatorSubagent"

    def __init__(self, project_root: str | Path = r"D:\Project\multi-phone-agent") -> None:
        self.coordinator = Recursive10xUIUXEvolutionCoordinator(project_root=project_root)

    def run_10_ui_ux_iterations(self, write_report: bool = True) -> dict[str, Any]:
        return self.coordinator.run_10_ui_ux_iterations(write_report=write_report)

    def execute(self, live_serial: str = "10CF5L0TYL00312", write_report: bool = True) -> dict[str, Any]:
        return self.coordinator.run_10_ui_ux_iterations(write_report=write_report)


__all__ = [
    "SemanticCTAHierarchyAndAntiRainbowSubagent",
    "WCAGContrastAndTypographyScaleSubagent",
    "MicroInteractionAndEmptyStateSubagent",
    "UIFinishGateReviewerSubagent",
    "Recursive10xUIUXEvolutionCoordinatorSubagent",
]
