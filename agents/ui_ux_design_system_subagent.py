"""
Subagents #56 & #57:
- VisualScreenshotClutterCriticSubagent (#56): UI/UX Screenshot Clutter & Cognitive Load Analyzer.
- DesignTokenAnd8PtGridSubagent (#57): Linear/Raycast/Geist Design Token & 8-Point Spatial Grid System.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.ui_ux_design_system_engine import (
    DesignTokenAnd8PtGridEngine,
    VisualScreenshotClutterCriticEngine,
)


class DesignTokenAnd8PtGridSubagent:
    """
    Subagent #57: Enforces canonical dark-mode design tokens (Linear / Raycast /
    Vercel Geist / Catppuccin Mocha Refined), 8-point spatial grid snapping,
    and WCAG 2.1 AA/AAA contrast compliance.
    """

    SUBAGENT_ID: int = 57
    SUBAGENT_NAME: str = "DesignTokenAnd8PtGridSubagent"

    # Expose canonical tokens directly on the Subagent class as well
    CANVAS_BG: str = DesignTokenAnd8PtGridEngine.CANVAS_BG
    SIDEBAR_BG: str = DesignTokenAnd8PtGridEngine.SIDEBAR_BG
    CARD_SURFACE: str = DesignTokenAnd8PtGridEngine.CARD_SURFACE
    ELEVATED_SURFACE: str = DesignTokenAnd8PtGridEngine.ELEVATED_SURFACE
    HAIRLINE_BORDER: str = DesignTokenAnd8PtGridEngine.HAIRLINE_BORDER

    PRIMARY_ACCENT: str = DesignTokenAnd8PtGridEngine.PRIMARY_ACCENT
    SECONDARY_SURFACE_BTN: str = DesignTokenAnd8PtGridEngine.SECONDARY_SURFACE_BTN
    STATUS_HEALTHY: str = DesignTokenAnd8PtGridEngine.STATUS_HEALTHY
    STATUS_WARNING: str = DesignTokenAnd8PtGridEngine.STATUS_WARNING
    STATUS_DANGER: str = DesignTokenAnd8PtGridEngine.STATUS_DANGER
    TEXT_PRIMARY: str = DesignTokenAnd8PtGridEngine.TEXT_PRIMARY
    TEXT_SECONDARY: str = DesignTokenAnd8PtGridEngine.TEXT_SECONDARY
    TEXT_MUTED: str = DesignTokenAnd8PtGridEngine.TEXT_MUTED

    SPACE_1: int = DesignTokenAnd8PtGridEngine.SPACE_1
    SPACE_2: int = DesignTokenAnd8PtGridEngine.SPACE_2
    SPACE_3: int = DesignTokenAnd8PtGridEngine.SPACE_3
    SPACE_4: int = DesignTokenAnd8PtGridEngine.SPACE_4
    SPACE_6: int = DesignTokenAnd8PtGridEngine.SPACE_6
    SPACE_8: int = DesignTokenAnd8PtGridEngine.SPACE_8

    FONT_DISPLAY: Tuple[str, int, str] = DesignTokenAnd8PtGridEngine.FONT_DISPLAY
    FONT_SECTION: Tuple[str, int, str] = DesignTokenAnd8PtGridEngine.FONT_SECTION
    FONT_BODY: Tuple[str, int] = DesignTokenAnd8PtGridEngine.FONT_BODY
    FONT_CAPTION: Tuple[str, int] = DesignTokenAnd8PtGridEngine.FONT_CAPTION
    FONT_MONO: Tuple[str, int] = DesignTokenAnd8PtGridEngine.FONT_MONO

    def __init__(self, engine: Optional[DesignTokenAnd8PtGridEngine] = None):
        self.engine = engine or DesignTokenAnd8PtGridEngine()

    def snap_to_8pt_grid(self, value: int, allow_half_step: bool = False) -> int:
        """Snap an integer pixel value to the nearest 8pt (or 4pt half-step) spatial grid unit."""
        return self.engine.snap_to_8pt_grid(value, allow_half_step=allow_half_step)

    def compute_wcag_contrast_ratio(self, hex_fg: str, hex_bg: str) -> float:
        """Compute WCAG 2.1 contrast ratio between foreground and background hex colors."""
        return self.engine.compute_wcag_contrast_ratio(hex_fg, hex_bg)

    def audit_token_compliance(self, widget_tree_spec: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Audit a widget specification tree against canonical design tokens and the 8pt grid."""
        return self.engine.audit_token_compliance(widget_tree_spec)

    def get_all_tokens(self) -> Dict[str, Any]:
        """Return all canonical surface, accent, spacing, and typography tokens."""
        return self.engine.get_all_tokens()


class VisualScreenshotClutterCriticSubagent:
    """
    Subagent #56: Diagnoses visual clutter, rainbow button overload, Hick's Law
    choice overload, cramped whitespace, and weak visual hierarchy on UI specs
    or screenshots, and renders high-resolution Before (v12) vs After (v13) comparisons.
    """

    SUBAGENT_ID: int = 56
    SUBAGENT_NAME: str = "VisualScreenshotClutterCriticSubagent"

    def __init__(
        self,
        engine: Optional[VisualScreenshotClutterCriticEngine] = None,
        token_subagent: Optional[DesignTokenAnd8PtGridSubagent] = None,
    ):
        self.token_subagent = token_subagent or DesignTokenAnd8PtGridSubagent()
        self.engine = engine or VisualScreenshotClutterCriticEngine(
            token_engine=self.token_subagent.engine
        )

    def critique(
        self, target: Union[Dict[str, Any], Image.Image, str, Path]
    ) -> Dict[str, Any]:
        """Analyze a UI layout spec or screenshot image and return clutter critique & score."""
        return self.engine.analyze_ui(target)

    def analyze_ui(
        self, target: Union[Dict[str, Any], Image.Image, str, Path]
    ) -> Dict[str, Any]:
        """Alias for `critique` matching `VisualScreenshotClutterCriticEngine.analyze_ui`."""
        return self.engine.analyze_ui(target)

    def render_before_and_after_ui_comparison(
        self, output_dir: Union[str, Path]
    ) -> Dict[str, Any]:
        """Render 1340x880 Before (v12 Cluttered) and After (v13 Linear/Raycast Bento) screenshots."""
        return self.engine.render_before_and_after_ui_comparison(output_dir)
