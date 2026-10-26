"""
Subagents #58, #59 & #60: UI/UX Information Architecture, Command Palette & Bento Cards.

Exports:
- `SidebarNavigationAndIASubagent` (Subagent #58)
- `CommandPaletteAndProgressiveDisclosureSubagent` (Subagent #59)
- `BentoDeviceCardAndSparklineSubagent` (Subagent #60)

Zero AI tokens at runtime; deterministic, unit-tested UI/UX architecture subagents.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.ui_ux_navigation_and_palette_engine import (
    BentoDeviceCardAndSparklineEngine,
    CommandPaletteAndProgressiveDisclosureEngine,
    SidebarNavigationAndIAEngine,
)


class SidebarNavigationAndIASubagent:
    """
    Subagent #58: Information Architecture & Left Sidebar Router.

    Replaces 8+ cramped horizontal tabs with 5 Miller's-Law-compliant Left Sidebar
    Workspaces grouping all 65 Subagents and reducing Hick's Law decision time by > 60%.
    """

    SUBAGENT_ID = 58
    SUBAGENT_NAME = "SidebarNavigationAndIASubagent"

    def __init__(self, engine: Optional[SidebarNavigationAndIAEngine] = None) -> None:
        self.engine = engine or SidebarNavigationAndIAEngine()

    def get_sidebar_workspaces(self) -> List[Dict[str, Any]]:
        """Return all 5 Miller's-Law Left Sidebar Workspaces."""
        return self.engine.list_workspaces()

    def route_to_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Switch active sidebar workspace and return updated workspace view-model."""
        return self.engine.select_workspace(workspace_id)

    def find_subagent_workspace(self, subagent_id: int) -> Dict[str, Any]:
        """Return which of the 5 Sidebar Workspaces contains `subagent_id` (1..65)."""
        return self.engine.locate_subagent_workspace(subagent_id)

    def audit_information_architecture(self) -> Dict[str, Any]:
        """Run full IA verification (65-subagent coverage + Hick's Law reduction > 60%)."""
        coverage = self.engine.verify_complete_65_subagent_coverage()
        reduction_pct = self.engine.cognitive_load_reduction_pct()
        return {
            "subagent_id": self.SUBAGENT_ID,
            "subagent_name": self.SUBAGENT_NAME,
            "zero_token_runtime": True,
            "cognitive_load_reduction_pct": reduction_pct,
            "hicks_law_target_met": reduction_pct > 60.0,
            **coverage,
        }


class CommandPaletteAndProgressiveDisclosureSubagent:
    """
    Subagent #59: Raycast/Linear `Ctrl+K` Fuzzy Command Palette & Progressive Disclosure.

    Indexes all 65 Subagents and 30+ quick actions with English/Vietnamese aliases and
    splits cluttered toolbars into `1 Primary CTA` + `<= 3 Secondary` + `Overflow Drawer`.
    """

    SUBAGENT_ID = 59
    SUBAGENT_NAME = "CommandPaletteAndProgressiveDisclosureSubagent"

    def __init__(
        self,
        engine: Optional[CommandPaletteAndProgressiveDisclosureEngine] = None,
    ) -> None:
        self.engine = engine or CommandPaletteAndProgressiveDisclosureEngine()

    def search(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Execute zero-token fuzzy command search (`Ctrl+K` / `⌘K`)."""
        return self.engine.search_commands(query=query, limit=limit)

    def split_cluttered_toolbar(
        self,
        toolbar_actions: List[Dict[str, Any]],
        max_visible_primary: int = 1,
        max_visible_secondary: int = 3,
    ) -> Dict[str, Any]:
        """Enforce Progressive Disclosure on any toolbar."""
        return self.engine.enforce_progressive_disclosure(
            toolbar_actions=toolbar_actions,
            max_visible_primary=max_visible_primary,
            max_visible_secondary=max_visible_secondary,
        )

    def get_palette_telemetry(self) -> Dict[str, Any]:
        """Return Command Palette index statistics."""
        return {
            "subagent_id": self.SUBAGENT_ID,
            "subagent_name": self.SUBAGENT_NAME,
            "shortcut": self.engine.SHORTCUT_TRIGGER,
            "total_indexed_commands": self.engine.total_indexed_commands,
            "indexed_subagents": 65,
            "zero_token_runtime": True,
        }


class BentoDeviceCardAndSparklineSubagent:
    """
    Subagent #60: Bento Device Card & Telemetry Sparkline Renderer.

    Formats clean Bento Device Card view-models (`Vivo V2417A (Physical)`, `Pixel 6 AVD #1`)
    with semantic status pills, single primary CTA, compact icon secondary buttons,
    and Unicode/SVG telemetry sparklines.
    """

    SUBAGENT_ID = 60
    SUBAGENT_NAME = "BentoDeviceCardAndSparklineSubagent"

    def __init__(
        self,
        engine: Optional[BentoDeviceCardAndSparklineEngine] = None,
    ) -> None:
        self.engine = engine or BentoDeviceCardAndSparklineEngine()

    def render_device_card(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build a Bento Device Card view-model for a single phone or emulator."""
        return self.engine.build_bento_device_card_model(device_info)

    def render_fleet_bento_grid(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build Bento Device Card view-models for an entire fleet of devices."""
        return [self.engine.build_bento_device_card_model(d) for d in devices]

    def render_sparkline(self, values: List[float]) -> Dict[str, str]:
        """Render both Unicode and SVG polyline sparklines for telemetry series."""
        return {
            "unicode": self.engine.render_unicode_sparkline(values),
            "svg_points": self.engine.render_svg_sparkline_points(values),
        }
