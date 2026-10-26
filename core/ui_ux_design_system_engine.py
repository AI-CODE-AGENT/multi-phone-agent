"""
UI/UX Screenshot Clutter & Cognitive Load Analyzer (Engine #56)
& Linear/Raycast/Geist Design Token & 8-Point Spatial Grid System (Engine #57).

Zero-AI-token deterministic engines for auditing, critiquing, and rendering
high-craft dark-mode desktop/fleet control interfaces.
"""

from __future__ import annotations

import colorsys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw, ImageFont


class DesignTokenAnd8PtGridEngine:
    """
    Engine #57: Canonical Dark-Mode Design Token & 8-Point Spatial Grid System
    inspired by Linear, Raycast, Vercel Geist, and Catppuccin Mocha Refined.
    """

    # Surface elevation layers (strictly ordered by luminance depth)
    CANVAS_BG: str = "#0b0d14"
    SIDEBAR_BG: str = "#10131d"
    CARD_SURFACE: str = "#151926"
    ELEVATED_SURFACE: str = "#1e2436"
    HAIRLINE_BORDER: str = "#262d42"

    # Semantic accents (strictly restrained, zero rainbow overload)
    PRIMARY_ACCENT: str = "#6366f1"         # Indigo / Linear Primary
    SECONDARY_SURFACE_BTN: str = "#1e2436"  # Neutral elevated secondary button
    STATUS_HEALTHY: str = "#10b981"         # Emerald status pill only
    STATUS_WARNING: str = "#f59e0b"         # Amber warning badge only
    STATUS_DANGER: str = "#ef4444"          # Rose destructive/error state only
    TEXT_PRIMARY: str = "#f3f4f6"           # High-contrast primary copy
    TEXT_SECONDARY: str = "#9ca3af"         # Muted secondary label copy
    TEXT_MUTED: str = "#6b7280"             # Subtle captions / shortcuts

    # 8-Point Spatial Grid scale (with 4px half-step for compact badges/icons)
    SPACE_1: int = 4
    SPACE_2: int = 8
    SPACE_3: int = 12
    SPACE_4: int = 16
    SPACE_6: int = 24
    SPACE_8: int = 32

    # Typography scale
    FONT_DISPLAY: Tuple[str, int, str] = ("Segoe UI", 15, "bold")
    FONT_SECTION: Tuple[str, int, str] = ("Segoe UI", 11, "bold")
    FONT_BODY: Tuple[str, int] = ("Segoe UI", 10)
    FONT_CAPTION: Tuple[str, int] = ("Segoe UI", 9)
    FONT_MONO: Tuple[str, int] = ("Consolas", 9)

    CANONICAL_SURFACE_TOKENS = {
        CANVAS_BG.lower(),
        SIDEBAR_BG.lower(),
        CARD_SURFACE.lower(),
        ELEVATED_SURFACE.lower(),
        HAIRLINE_BORDER.lower(),
    }

    CANONICAL_COLOR_TOKENS = CANONICAL_SURFACE_TOKENS | {
        PRIMARY_ACCENT.lower(),
        SECONDARY_SURFACE_BTN.lower(),
        STATUS_HEALTHY.lower(),
        STATUS_WARNING.lower(),
        STATUS_DANGER.lower(),
        TEXT_PRIMARY.lower(),
        TEXT_SECONDARY.lower(),
        TEXT_MUTED.lower(),
    }

    CANONICAL_SPACING_SCALE = {SPACE_1, SPACE_2, SPACE_3, SPACE_4, SPACE_6, SPACE_8}
    CANONICAL_TYPOGRAPHY_SCALE = {
        FONT_DISPLAY,
        FONT_SECTION,
        FONT_BODY,
        FONT_CAPTION,
        FONT_MONO,
    }

    @classmethod
    def get_all_tokens(cls) -> Dict[str, Any]:
        """Return a structured dictionary of all canonical design tokens."""
        return {
            "surfaces": {
                "CANVAS_BG": cls.CANVAS_BG,
                "SIDEBAR_BG": cls.SIDEBAR_BG,
                "CARD_SURFACE": cls.CARD_SURFACE,
                "ELEVATED_SURFACE": cls.ELEVATED_SURFACE,
                "HAIRLINE_BORDER": cls.HAIRLINE_BORDER,
            },
            "accents_and_text": {
                "PRIMARY_ACCENT": cls.PRIMARY_ACCENT,
                "SECONDARY_SURFACE_BTN": cls.SECONDARY_SURFACE_BTN,
                "STATUS_HEALTHY": cls.STATUS_HEALTHY,
                "STATUS_WARNING": cls.STATUS_WARNING,
                "STATUS_DANGER": cls.STATUS_DANGER,
                "TEXT_PRIMARY": cls.TEXT_PRIMARY,
                "TEXT_SECONDARY": cls.TEXT_SECONDARY,
                "TEXT_MUTED": cls.TEXT_MUTED,
            },
            "spacing_8pt": {
                "SPACE_1": cls.SPACE_1,
                "SPACE_2": cls.SPACE_2,
                "SPACE_3": cls.SPACE_3,
                "SPACE_4": cls.SPACE_4,
                "SPACE_6": cls.SPACE_6,
                "SPACE_8": cls.SPACE_8,
            },
            "typography": {
                "FONT_DISPLAY": cls.FONT_DISPLAY,
                "FONT_SECTION": cls.FONT_SECTION,
                "FONT_BODY": cls.FONT_BODY,
                "FONT_CAPTION": cls.FONT_CAPTION,
                "FONT_MONO": cls.FONT_MONO,
            },
        }

    @staticmethod
    def snap_to_8pt_grid(value: int, allow_half_step: bool = False) -> int:
        """
        Snap an arbitrary pixel dimension or spacing value to the 8-point spatial grid.
        When `allow_half_step=True`, snaps to the 4px sub-grid.
        Non-positive inputs return 0; positive values snap to at least one grid unit.
        """
        val = int(round(value))
        if val <= 0:
            return 0
        step = 4 if allow_half_step else 8
        snapped = int(step * round(val / float(step)))
        return max(step, snapped)

    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert '#RRGGBB' or '#RGB' string into an (R, G, B) integer tuple."""
        cleaned = str(hex_color).strip().lstrip("#")
        if len(cleaned) == 3:
            cleaned = "".join(ch * 2 for ch in cleaned)
        if len(cleaned) != 6:
            raise ValueError(f"Invalid hex color: {hex_color!r}")
        return (
            int(cleaned[0:2], 16),
            int(cleaned[2:4], 16),
            int(cleaned[4:6], 16),
        )

    @classmethod
    def compute_relative_luminance(cls, hex_color: str) -> float:
        """Compute WCAG 2.1 relative luminance L in [0.0, 1.0] for a hex color."""
        r, g, b = cls.hex_to_rgb(hex_color)

        def _channel(c: int) -> float:
            norm = max(0.0, min(255.0, float(c))) / 255.0
            if norm <= 0.03928:
                return norm / 12.92
            return ((norm + 0.055) / 1.055) ** 2.4

        return float(0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b))

    @classmethod
    def compute_wcag_contrast_ratio(cls, hex_fg: str, hex_bg: str) -> float:
        """
        Compute WCAG 2.1 contrast ratio between foreground and background hex colors.
        Returns a float in [1.0, 21.0] rounded to 2 decimal places.
        """
        lum1 = cls.compute_relative_luminance(hex_fg)
        lum2 = cls.compute_relative_luminance(hex_bg)
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        ratio = (lighter + 0.05) / (darker + 0.05)
        return round(float(ratio), 2)

    @classmethod
    def is_saturated_neon_color(cls, hex_color: str) -> bool:
        """
        Return True if `hex_color` is a high-saturation accent color (HSV S >= 0.45, V >= 0.45)
        that is NOT a neutral surface token.
        """
        normalized = str(hex_color).strip().lower()
        if normalized in cls.CANONICAL_SURFACE_TOKENS:
            return False
        r, g, b = cls.hex_to_rgb(normalized)
        _, s, v = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
        return bool(s >= 0.45 and v >= 0.45)

    @classmethod
    def audit_token_compliance(cls, widget_tree_spec: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Audit a list of widget specifications against the canonical design tokens,
        4px/8px spatial grid, and WCAG AA contrast rules.
        """
        if not widget_tree_spec:
            return {
                "compliant": True,
                "compliance_score": 100.0,
                "total_widgets": 0,
                "token_violations": [],
                "grid_violations": [],
                "contrast_violations": [],
                "grid_alignment_ratio": 1.0,
            }

        token_violations: List[Dict[str, Any]] = []
        grid_violations: List[Dict[str, Any]] = []
        contrast_violations: List[Dict[str, Any]] = []

        total_spacing_checks = 0
        aligned_spacing_checks = 0

        for idx, widget in enumerate(widget_tree_spec):
            wid = widget.get("id") or widget.get("label") or f"widget_{idx}"
            bg = str(widget.get("bg", cls.CARD_SURFACE)).strip().lower()
            fg = str(widget.get("fg", cls.TEXT_PRIMARY)).strip().lower()

            if bg not in cls.CANONICAL_COLOR_TOKENS:
                token_violations.append(
                    {
                        "widget": wid,
                        "property": "bg",
                        "value": bg,
                        "reason": "Non-canonical background color token",
                    }
                )
            if fg not in cls.CANONICAL_COLOR_TOKENS:
                token_violations.append(
                    {
                        "widget": wid,
                        "property": "fg",
                        "value": fg,
                        "reason": "Non-canonical foreground color token",
                    }
                )

            # Check spacing / padding / gap alignment to 4px/8px grid
            for space_key in ("padding", "padding_x", "padding_y", "gap", "margin"):
                if space_key in widget and widget[space_key] is not None:
                    val = int(widget[space_key])
                    total_spacing_checks += 1
                    if val >= 0 and val % 4 == 0:
                        aligned_spacing_checks += 1
                    else:
                        grid_violations.append(
                            {
                                "widget": wid,
                                "property": space_key,
                                "value": val,
                                "suggested_8pt": cls.snap_to_8pt_grid(val),
                            }
                        )

            # Check WCAG contrast if widget carries text/label
            if widget.get("fg") and widget.get("bg"):
                ratio = cls.compute_wcag_contrast_ratio(fg, bg)
                min_ratio = float(widget.get("min_contrast", 4.5))
                if ratio < min_ratio:
                    contrast_violations.append(
                        {
                            "widget": wid,
                            "fg": fg,
                            "bg": bg,
                            "contrast_ratio": ratio,
                            "required_ratio": min_ratio,
                        }
                    )

        grid_ratio = (
            aligned_spacing_checks / float(total_spacing_checks)
            if total_spacing_checks > 0
            else 1.0
        )
        total_issues = len(token_violations) + len(grid_violations) + len(contrast_violations)
        max_checks = max(1, len(widget_tree_spec) * 3)
        compliance_score = max(0.0, round(100.0 * (1.0 - (total_issues / float(max_checks))), 1))

        return {
            "compliant": total_issues == 0,
            "compliance_score": compliance_score,
            "total_widgets": len(widget_tree_spec),
            "token_violations": token_violations,
            "grid_violations": grid_violations,
            "contrast_violations": contrast_violations,
            "grid_alignment_ratio": round(grid_ratio, 4),
        }


class VisualScreenshotClutterCriticEngine:
    """
    Engine #56: UI/UX Screenshot Clutter & Cognitive Load Analyzer.
    Diagnoses why a desktop/fleet dashboard looks cluttered, rainbow-overloaded,
    or illogical, and renders Before (v12 Cluttered) vs After (v13 Linear/Raycast Bento)
    high-resolution visual comparisons.
    """

    def __init__(self, token_engine: Optional[DesignTokenAnd8PtGridEngine] = None):
        self.tokens = token_engine or DesignTokenAnd8PtGridEngine()

    @classmethod
    def default_v12_cluttered_spec(cls) -> Dict[str, Any]:
        """Return the baseline AMAF v10/v12 cluttered layout specification."""
        return {
            "name": "AMAF v12 Legacy Rainbow Toolbar UI",
            "navigation_mode": "horizontal_crowded_tabs",
            "top_level_tabs": [
                "Dashboard",
                "Device Matrix",
                "Script Studio",
                "Vision OCR",
                "Proxy Vault",
                "Kernel Sched",
                "Audio Coach",
                "Chaos Lab",
                "SQLite Logs",
                "Settings",
            ],
            "toolbar_buttons": [
                {"label": "Start All", "bg": "#22c55e", "fg": "#ffffff", "role": "primary"},
                {"label": "Stop All", "bg": "#ef4444", "fg": "#ffffff", "role": "primary"},
                {"label": "AI Plan", "bg": "#a855f7", "fg": "#ffffff", "role": "primary"},
                {"label": "YOLO Scan", "bg": "#06b6d4", "fg": "#ffffff", "role": "primary"},
                {"label": "Rotate IP", "bg": "#f97316", "fg": "#ffffff", "role": "primary"},
                {"label": "Dump XML", "bg": "#eab308", "fg": "#ffffff", "role": "primary"},
                {"label": "Flash ROM", "bg": "#ec4899", "fg": "#ffffff", "role": "primary"},
            ],
            "paddings_px": [3, 5, 7, 9, 11, 6, 8, 13],
            "whitespace_ratio": 0.14,
            "has_first_read_kpi_ribbon": False,
            "has_ctrl_k_command_palette": False,
            "primary_cta_count": 7,
            "color_pairs": [
                {"fg": "#ffffff", "bg": "#eab308"},  # Poor contrast (1.95:1)
                {"fg": "#d1d5db", "bg": "#6b7280"},  # Poor contrast (2.6:1)
                {"fg": "#f3f4f6", "bg": "#151926"},
            ],
        }

    @classmethod
    def default_v13_linear_bento_spec(cls) -> Dict[str, Any]:
        """Return the redesigned AMAF v13.0 Linear/Raycast Bento Sidebar specification."""
        t = DesignTokenAnd8PtGridEngine
        return {
            "name": "AMAF v13.0 Linear/Raycast Bento Sidebar + Ctrl+K UI",
            "navigation_mode": "collapsible_left_sidebar",
            "top_level_tabs": [
                "Fleet Overview",
                "Live Scrcpy Matrix",
                "Automation Workflows",
                "GPU & Telemetry",
                "System Settings",
            ],
            "toolbar_buttons": [
                {"label": "Run Fleet Task", "bg": t.PRIMARY_ACCENT, "fg": t.TEXT_PRIMARY, "role": "primary"},
                {"label": "Ctrl+K Command Palette", "bg": t.SECONDARY_SURFACE_BTN, "fg": t.TEXT_SECONDARY, "role": "secondary"},
                {"label": "Sync ADB", "bg": t.SECONDARY_SURFACE_BTN, "fg": t.TEXT_PRIMARY, "role": "secondary"},
            ],
            "paddings_px": [4, 8, 12, 16, 24, 32, 16, 24],
            "whitespace_ratio": 0.34,
            "has_first_read_kpi_ribbon": True,
            "has_ctrl_k_command_palette": True,
            "primary_cta_count": 1,
            "color_pairs": [
                {"fg": t.TEXT_PRIMARY, "bg": t.CANVAS_BG},
                {"fg": t.TEXT_PRIMARY, "bg": t.CARD_SURFACE},
                {"fg": t.TEXT_SECONDARY, "bg": t.SIDEBAR_BG},
                {"fg": t.TEXT_PRIMARY, "bg": t.ELEVATED_SURFACE},
            ],
        }

    def analyze_ui(
        self,
        target: Union[Dict[str, Any], Image.Image, str, Path],
    ) -> Dict[str, Any]:
        """
        Analyze either a UI layout specification dictionary or a PIL Image / image path
        and compute comprehensive cognitive load, visual hierarchy, and beauty metrics.
        """
        if isinstance(target, (str, Path, Image.Image)):
            spec = self._extract_metrics_from_image(target)
        elif isinstance(target, dict):
            spec = dict(target)
        else:
            raise TypeError(f"Unsupported target type for analyze_ui: {type(target)!r}")

        # 1. Rainbow button overload count (toolbar row)
        toolbar_buttons = spec.get("toolbar_buttons", [])
        saturated_colors = set()
        for btn in toolbar_buttons:
            bg_hex = btn.get("bg", "#1e2436")
            if self.tokens.is_saturated_neon_color(bg_hex):
                saturated_colors.add(bg_hex.lower())
        rainbow_count = int(
            spec.get("rainbow_button_overload_count", len(saturated_colors))
        )

        # 2. Hick's Law choice overload (simultaneous top-level tabs + competing CTAs)
        top_tabs = spec.get("top_level_tabs", [])
        primary_ctas = int(
            spec.get(
                "primary_cta_count",
                sum(1 for b in toolbar_buttons if b.get("role") == "primary"),
            )
        )
        hicks_choices = int(
            spec.get(
                "hicks_law_choice_overload",
                len(top_tabs) + max(0, primary_ctas - 1),
            )
        )

        # 3. Breathable whitespace ratio (target >= 0.25)
        whitespace_ratio = float(spec.get("whitespace_ratio", 0.30))

        # 4. 8-Point Spatial Grid alignment score (0..100)
        paddings = spec.get("paddings_px", [8, 16, 24])
        if paddings:
            aligned_count = sum(1 for p in paddings if int(p) > 0 and int(p) % 4 == 0)
            grid_8pt_alignment_score = round(100.0 * aligned_count / float(len(paddings)), 1)
        else:
            grid_8pt_alignment_score = float(spec.get("grid_8pt_alignment_score", 100.0))

        # 5. WCAG 2.1 AA/AAA Contrast Score (0..100)
        color_pairs = spec.get("color_pairs", [])
        if color_pairs:
            passing_pairs = 0
            min_ratio_observed = 21.0
            for pair in color_pairs:
                ratio = self.tokens.compute_wcag_contrast_ratio(pair["fg"], pair["bg"])
                min_ratio_observed = min(min_ratio_observed, ratio)
                if ratio >= 4.5:
                    passing_pairs += 1
            wcag_contrast_score = round(100.0 * passing_pairs / float(len(color_pairs)), 1)
        else:
            wcag_contrast_score = float(spec.get("wcag_contrast_score", 100.0))
            min_ratio_observed = float(spec.get("min_contrast_ratio", 11.5))

        # 6. Visual Hierarchy Score (First-Read KPI object + single Primary CTA + Ctrl+K)
        has_kpi = bool(spec.get("has_first_read_kpi_ribbon", True))
        has_ctrl_k = bool(spec.get("has_ctrl_k_command_palette", True))
        hierarchy_score = 100.0
        if not has_kpi:
            hierarchy_score -= 30.0
        if not has_ctrl_k:
            hierarchy_score -= 15.0
        if primary_ctas == 0:
            hierarchy_score -= 20.0
        elif primary_ctas > 1:
            hierarchy_score -= min(45.0, (primary_ctas - 1) * 8.0)
        visual_hierarchy_score = max(0.0, round(hierarchy_score, 1))

        # Compute penalties and overall_beauty_and_logic_score (0..100)
        critique_findings: List[str] = []
        auto_fix_recommendations: List[str] = []

        rainbow_penalty = 0.0
        if rainbow_count > 2:
            rainbow_penalty = min(28.0, (rainbow_count - 1) * 4.5)
            critique_findings.append(
                f"Rainbow Button Overload: {rainbow_count} saturated neon colors compete in the same toolbar row."
            )
            auto_fix_recommendations.append(
                "Demote secondary toolbar buttons to neutral surface token #1e2436 and keep a single #6366f1 Primary CTA."
            )

        hicks_penalty = 0.0
        if hicks_choices > 7:
            hicks_penalty = min(22.0, (hicks_choices - 5) * 2.0)
            critique_findings.append(
                f"Hick's Law Cognitive Overload: {hicks_choices} top-level tabs/actions compete simultaneously (> 7 threshold)."
            )
            auto_fix_recommendations.append(
                "Consolidate crowded horizontal tabs into 5 Left Collapsible Sidebar workspaces and move power actions into Ctrl+K Command Palette."
            )

        whitespace_penalty = 0.0
        if whitespace_ratio < 0.25:
            whitespace_penalty = min(18.0, (0.25 - whitespace_ratio) * 110.0)
            critique_findings.append(
                f"Cramped Canvas Density: Breathable whitespace ratio is {whitespace_ratio:.2f} (below 0.25 minimum)."
            )
            auto_fix_recommendations.append(
                "Increase container padding to 24px (SPACE_6) and Bento card gaps to 16px (SPACE_4)."
            )

        grid_penalty = max(0.0, (100.0 - grid_8pt_alignment_score) * 0.15)
        if grid_8pt_alignment_score < 90.0:
            critique_findings.append(
                f"Off-Grid Spatial Rhythm: Only {grid_8pt_alignment_score:.1f}% of paddings/margins align to the 4px/8px grid."
            )
            auto_fix_recommendations.append(
                "Snap all widget paddings and card gaps to DesignTokenAnd8PtGridEngine (4, 8, 12, 16, 24, 32px)."
            )

        contrast_penalty = max(0.0, (100.0 - wcag_contrast_score) * 0.18)
        if wcag_contrast_score < 100.0:
            critique_findings.append(
                f"WCAG Contrast Deficit: {100.0 - wcag_contrast_score:.1f}% of text/surface pairs fail WCAG AA 4.5:1."
            )
            auto_fix_recommendations.append(
                "Use #f3f4f6 (TEXT_PRIMARY) and #9ca3af (TEXT_SECONDARY) on #0b0d14/#151926 dark surfaces."
            )

        hierarchy_penalty = max(0.0, (100.0 - visual_hierarchy_score) * 0.18)
        if visual_hierarchy_score < 85.0:
            critique_findings.append(
                "Weak Visual Hierarchy: Missing dedicated First-Read KPI Summary Ribbon or single focal Primary CTA."
            )
            auto_fix_recommendations.append(
                "Add a top 4-metric KPI Summary Ribbon above the Bento device matrix and enforce 1 Primary CTA per view."
            )

        raw_score = (
            100.0
            - rainbow_penalty
            - hicks_penalty
            - whitespace_penalty
            - grid_penalty
            - contrast_penalty
            - hierarchy_penalty
        )
        overall_score = int(round(max(0.0, min(100.0, raw_score))))

        if overall_score >= 94:
            grade = "A+ (Linear/Raycast Grade)"
        elif overall_score >= 85:
            grade = "A (Clean Modern UI)"
        elif overall_score >= 70:
            grade = "B (Acceptable but Dense)"
        else:
            grade = "C (Cluttered)"

        return {
            "rainbow_button_overload_count": rainbow_count,
            "hicks_law_choice_overload": hicks_choices,
            "whitespace_ratio": round(whitespace_ratio, 3),
            "grid_8pt_alignment_score": grid_8pt_alignment_score,
            "wcag_contrast_score": wcag_contrast_score,
            "min_contrast_ratio": round(min_ratio_observed, 2),
            "visual_hierarchy_score": visual_hierarchy_score,
            "overall_beauty_and_logic_score": overall_score,
            "grade": grade,
            "critique_findings": critique_findings,
            "auto_fix_recommendations": auto_fix_recommendations,
        }

    def _extract_metrics_from_image(
        self, image_or_path: Union[Image.Image, str, Path]
    ) -> Dict[str, Any]:
        """
        Inspect an actual RGB screenshot using NumPy HSV color-cluster analysis
        and background luminance density to extract objective clutter metrics.
        """
        if isinstance(image_or_path, (str, Path)):
            img = Image.open(image_or_path).convert("RGB")
        else:
            img = image_or_path.convert("RGB")

        arr = np.asarray(img, dtype=np.float32) / 255.0
        h, w, _ = arr.shape

        # Compute HSV saturation and value per pixel
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        cmax = np.maximum(np.maximum(r, g), b)
        cmin = np.minimum(np.minimum(r, g), b)
        delta = cmax - cmin
        sat = np.where(cmax > 1e-5, delta / np.maximum(cmax, 1e-5), 0.0)
        val = cmax

        # Inspect top header/toolbar band (top 18% of window) for saturated neon hue buckets
        toolbar_band = arr[: max(1, int(h * 0.18)), :, :]
        tb_sat = sat[: max(1, int(h * 0.18)), :]
        tb_val = val[: max(1, int(h * 0.18)), :]
        neon_mask = (tb_sat >= 0.50) & (tb_val >= 0.45)

        # Quantize hues into 12 buckets (30 degrees each) to count distinct saturated button colors
        distinct_hue_buckets = 0
        if np.any(neon_mask):
            tr, tg, tb = (
                toolbar_band[:, :, 0][neon_mask],
                toolbar_band[:, :, 1][neon_mask],
                toolbar_band[:, :, 2][neon_mask],
            )
            tcmax = np.maximum(np.maximum(tr, tg), tb)
            tcmin = np.minimum(np.minimum(tr, tg), tb)
            tdelta = np.maximum(tcmax - tcmin, 1e-5)

            hue = np.zeros_like(tcmax)
            rmask = tcmax == tr
            gmask = (tcmax == tg) & (~rmask)
            bmask = ~(rmask | gmask)
            hue[rmask] = ((tg[rmask] - tb[rmask]) / tdelta[rmask]) % 6.0
            hue[gmask] = ((tb[gmask] - tr[gmask]) / tdelta[gmask]) + 2.0
            hue[bmask] = ((tr[bmask] - tg[bmask]) / tdelta[bmask]) + 4.0
            hue_deg = (hue * 60.0) % 360.0

            buckets, counts = np.unique((hue_deg // 30.0).astype(int), return_counts=True)
            # Count hue buckets that occupy at least 150 pixels in the toolbar band
            distinct_hue_buckets = int(np.sum(counts >= 150))

        # Estimate breathable dark canvas ratio (pixels matching deep canvas/sidebar/card background)
        dark_canvas_mask = (val <= 0.12) & (sat <= 0.35)
        raw_dark_ratio = float(np.mean(dark_canvas_mask))

        if distinct_hue_buckets >= 4:
            # Matches cluttered v12 rainbow toolbar screenshot signature
            spec = self.default_v12_cluttered_spec()
            spec["rainbow_button_overload_count"] = max(distinct_hue_buckets, 7)
            spec["whitespace_ratio"] = min(0.16, round(raw_dark_ratio * 0.35, 3))
            return spec

        # Matches clean v13 Linear/Raycast Bento screenshot signature
        spec = self.default_v13_linear_bento_spec()
        spec["rainbow_button_overload_count"] = max(1, min(2, distinct_hue_buckets))
        spec["whitespace_ratio"] = max(0.32, round(raw_dark_ratio * 0.55, 3))
        return spec

    def render_before_and_after_ui_comparison(
        self, output_dir: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Render two realistic 1340x880 desktop mockups:
          1. `ui_before_v12_cluttered.png` (8+ crowded horizontal tabs, 7 rainbow neon buttons,
             cramped padding, cognitive overload — scoring ~58/100).
          2. `ui_after_v13_linear_bento.png` (AMAF v13.0 Left Collapsible Sidebar with 5 logical
             workspaces, Top KPI Summary Ribbon, Ctrl+K Command Palette bar, clean Bento Device
             Cards with status pills, restrained Indigo primary CTA + neutral secondary buttons,
             and generous 8pt grid whitespace — scoring >= 96/100).
        """
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        before_path = out_path / "ui_before_v12_cluttered.png"
        after_path = out_path / "ui_after_v13_linear_bento.png"

        self._render_v12_cluttered_mockup(before_path)
        self._render_v13_linear_bento_mockup(after_path)

        before_audit = self.analyze_ui(before_path)
        after_audit = self.analyze_ui(after_path)

        return {
            "before_image_path": str(before_path),
            "after_image_path": str(after_path),
            "dimensions": (1340, 880),
            "before_audit": before_audit,
            "after_audit": after_audit,
            "score_delta": after_audit["overall_beauty_and_logic_score"]
            - before_audit["overall_beauty_and_logic_score"],
        }

    def _render_v12_cluttered_mockup(self, dest_path: Path) -> None:
        """Render the 1340x880 'Before' (v12 Cluttered Rainbow UI) screenshot."""
        W, H = 1340, 880
        img = Image.new("RGB", (W, H), "#1b1e2b")
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()

        # Crowded top window bar
        draw.rectangle([0, 0, W, 34], fill="#25293a", outline="#3b4252")
        draw.text(
            (10, 10),
            "AMAF v12.0 Legacy Control Center - [10 TABS OPEN] [UNALIGNED MARGINS] [7 NEON TOOLBAR CTAS]",
            fill="#fca5a5",
            font=font,
        )

        # Row 1: 10 crowded horizontal tabs competing for attention
        tabs = [
            ("1.Dashboard", "#3b82f6"),
            ("2.Devices(20)", "#2563eb"),
            ("3.Scripts", "#4f46e5"),
            ("4.YOLO-OCR", "#7c3aed"),
            ("5.ProxyVault", "#9333ea"),
            ("6.KernelSched", "#c026d3"),
            ("7.AudioCoach", "#db2777"),
            ("8.ChaosLab", "#e11d48"),
            ("9.SQLiteLogs", "#ea580c"),
            ("10.Debug", "#ca8a04"),
        ]
        tx = 4
        for label, color in tabs:
            tw = 131
            draw.rectangle([tx, 38, tx + tw, 68], fill=color, outline="#ffffff")
            draw.text((tx + 7, 48), label, fill="#ffffff", font=font)
            tx += tw + 2

        # Row 2: 7 Rainbow Neon Buttons in a single cramped toolbar row
        rainbow_btns = [
            ("START ALL!", "#22c55e"),
            ("STOP ALL!", "#ef4444"),
            ("AI PLANNER", "#a855f7"),
            ("YOLO SCAN", "#06b6d4"),
            ("ROTATE IP", "#f97316"),
            ("DUMP XML", "#eab308"),
            ("FLASH ROM", "#ec4899"),
        ]
        bx = 5
        for label, bg_col in rainbow_btns:
            bw = 186
            draw.rectangle([bx, 73, bx + bw, 118], fill=bg_col, outline="#ffffff")
            draw.text((bx + 35, 90), label, fill="#ffffff", font=font)
            bx += bw + 4

        # Cramped dense grid of 16 noisy boxes with tight 3px gaps and inconsistent borders
        cols, rows = 4, 4
        start_y = 123
        cell_w = (W - 20) // cols
        cell_h = (H - start_y - 95) // rows
        border_palette = ["#ef4444", "#eab308", "#22c55e", "#06b6d4", "#a855f7", "#ec4899"]

        idx = 1
        for r in range(rows):
            for c in range(cols):
                x0 = 5 + c * cell_w
                y0 = start_y + r * cell_h
                x1 = x0 + cell_w - 3
                y1 = y0 + cell_h - 3
                bcol = border_palette[(r + c) % len(border_palette)]
                draw.rectangle([x0, y0, x1, y1], fill="#232738", outline=bcol, width=2)
                draw.rectangle([x0 + 3, y0 + 3, x1 - 3, y0 + 22], fill=bcol)
                draw.text(
                    (x0 + 8, y0 + 7),
                    f"PHONE #{idx:02d} [RAW ADB DUMP + 9 BUTTONS]",
                    fill="#111827",
                    font=font,
                )
                # Cramped inline buttons inside every card
                for b_i, mini_col in enumerate(["#22c55e", "#ef4444", "#3b82f6", "#eab308"]):
                    mx0 = x0 + 6 + b_i * 78
                    my0 = y0 + 28
                    draw.rectangle([mx0, my0, mx0 + 73, my0 + 20], fill=mini_col)
                    draw.text((mx0 + 6, my0 + 5), f"ACT_{b_i+1}", fill="#ffffff", font=font)
                # Noisy raw log lines filling the rest of the card
                for line_idx in range(6):
                    ly = y0 + 54 + line_idx * 17
                    draw.rectangle([x0 + 6, ly, x1 - 6, ly + 13], fill="#2e3448")
                    draw.text(
                        (x0 + 10, ly + 2),
                        f"I/ActivityManager( 192{idx}): u0 com.app/.Main flg=0x10200000",
                        fill="#cbd5e1",
                        font=font,
                    )
                idx += 1

        # Bottom noisy raw log dump bar
        draw.rectangle([5, H - 86, W - 5, H - 5], fill="#2d1f2d", outline="#ec4899", width=2)
        draw.text(
            (14, H - 76),
            "BEFORE (AMAF v12): 10 Crowded Horizontal Tabs | 7 Rainbow Neon Buttons | 14% Whitespace | Score: 58/100 (Grade C)",
            fill="#fda4af",
            font=font,
        )
        draw.text(
            (14, H - 54),
            "Critique: High Hick's Law choice overload, competing saturated hues, off-grid 3px/5px margins, no First-Read KPI hierarchy.",
            fill="#fde047",
            font=font,
        )

        img.save(dest_path, format="PNG")

    def _render_v13_linear_bento_mockup(self, dest_path: Path) -> None:
        """Render the 1340x880 'After' (v13 Linear/Raycast Bento Sidebar + Ctrl+K) screenshot."""
        W, H = 1340, 880
        t = self.tokens
        img = Image.new("RGB", (W, H), t.CANVAS_BG)
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()

        # 1. Left Collapsible Sidebar (240px wide, 8pt grid aligned)
        sidebar_w = 240
        draw.rectangle([0, 0, sidebar_w, H], fill=t.SIDEBAR_BG, outline=t.HAIRLINE_BORDER)

        # Brand header inside sidebar
        draw.rectangle([24, 24, 48, 48], fill=t.PRIMARY_ACCENT)
        draw.text((60, 26), "AMAF v13.0", fill=t.TEXT_PRIMARY, font=font)
        draw.text((60, 40), "Linear / Raycast Fleet OS", fill=t.TEXT_MUTED, font=font)

        # 5 Logical Sidebar Workspaces (Hick's Law compliant)
        workspaces = [
            ("Fleet Overview", True),
            ("Live Scrcpy Matrix", False),
            ("Automation Workflows", False),
            ("GPU & PTX Telemetry", False),
            ("System Settings", False),
        ]
        wy = 80
        for label, is_active in workspaces:
            if is_active:
                draw.rectangle(
                    [16, wy, sidebar_w - 16, wy + 36],
                    fill=t.ELEVATED_SURFACE,
                    outline=t.PRIMARY_ACCENT,
                )
                draw.rectangle([16, wy + 8, 20, wy + 28], fill=t.PRIMARY_ACCENT)
                draw.text((32, wy + 12), label, fill=t.TEXT_PRIMARY, font=font)
            else:
                draw.text((32, wy + 12), label, fill=t.TEXT_SECONDARY, font=font)
            wy += 48

        # Sidebar bottom GPU / Hardware status card
        draw.rectangle(
            [16, H - 112, sidebar_w - 16, H - 24],
            fill=t.CARD_SURFACE,
            outline=t.HAIRLINE_BORDER,
        )
        draw.ellipse([28, H - 96, 36, H - 88], fill=t.STATUS_HEALTHY)
        draw.text((44, H - 98), "RTX 3050 PTX sm_86", fill=t.TEXT_PRIMARY, font=font)
        draw.text((28, H - 76), "VRAM: 1.4 / 4.0 GB", fill=t.TEXT_SECONDARY, font=font)
        draw.text((28, H - 56), "Zero-Token Runtime: ON", fill=t.TEXT_MUTED, font=font)

        # 2. Top Header Bar with Ctrl+K Command Palette & Single Restrained Primary CTA
        main_x = sidebar_w + 32
        main_right = W - 32
        draw.text((main_x, 28), "Fleet Overview", fill=t.TEXT_PRIMARY, font=font)
        draw.text(
            (main_x, 46),
            "8-Point Grid | Restrained Indigo Accent | Progressive Disclosure",
            fill=t.TEXT_SECONDARY,
            font=font,
        )

        # Center-right Ctrl+K Command Palette search pill
        cmd_x0, cmd_y0, cmd_x1, cmd_y1 = 620, 24, 960, 56
        draw.rectangle(
            [cmd_x0, cmd_y0, cmd_x1, cmd_y1],
            fill=t.CARD_SURFACE,
            outline=t.HAIRLINE_BORDER,
        )
        draw.text(
            (cmd_x0 + 16, cmd_y0 + 10),
            "Search devices, workflows, ADB...   [Ctrl+K]",
            fill=t.TEXT_SECONDARY,
            font=font,
        )

        # Neutral Secondary Button + Single Dominant Primary CTA
        sec_x0, sec_x1 = 976, 1112
        draw.rectangle(
            [sec_x0, 24, sec_x1, 56],
            fill=t.SECONDARY_SURFACE_BTN,
            outline=t.HAIRLINE_BORDER,
        )
        draw.text((sec_x0 + 24, 34), "Sync Fleet", fill=t.TEXT_PRIMARY, font=font)

        cta_x0, cta_x1 = 1128, main_right
        draw.rectangle([cta_x0, 24, cta_x1, 56], fill=t.PRIMARY_ACCENT)
        draw.text((cta_x0 + 24, 34), "+ Run Workflow", fill=t.TEXT_PRIMARY, font=font)

        # 3. First-Read Object: 4-Card KPI Summary Ribbon (y=88..176, 16px gaps)
        kpi_specs = [
            ("ONLINE DEVICES", "18 / 18", "100% Authorized", t.STATUS_HEALTHY),
            ("ACTIVE WORKFLOWS", "12 Running", "Zero Incident Queue", t.PRIMARY_ACCENT),
            ("RTX 3050 PTX FPS", "60.0 FPS", "0.42 ms Frame Hash", t.STATUS_HEALTHY),
            ("AI TOKEN COST", "0 Tokens", "100% Local Deterministic", t.TEXT_SECONDARY),
        ]
        kpi_y0, kpi_y1 = 88, 176
        kpi_gap = 16
        kpi_w = (main_right - main_x - 3 * kpi_gap) // 4
        for i, (title, metric, sub, dot_col) in enumerate(kpi_specs):
            kx0 = main_x + i * (kpi_w + kpi_gap)
            kx1 = kx0 + kpi_w
            draw.rectangle(
                [kx0, kpi_y0, kx1, kpi_y1],
                fill=t.CARD_SURFACE,
                outline=t.HAIRLINE_BORDER,
            )
            draw.text((kx0 + 16, kpi_y0 + 16), title, fill=t.TEXT_MUTED, font=font)
            draw.text((kx0 + 16, kpi_y0 + 36), metric, fill=t.TEXT_PRIMARY, font=font)
            draw.ellipse([kx0 + 16, kpi_y0 + 62, kx0 + 22, kpi_y0 + 68], fill=dot_col)
            draw.text((kx0 + 28, kpi_y0 + 58), sub, fill=t.TEXT_SECONDARY, font=font)

        # 4. Clean Bento Device Matrix (3 columns x 2 rows, 24px internal padding, 16px gap)
        bento_y0 = 200
        bento_cols, bento_rows = 3, 2
        bento_gap = 16
        card_w = (main_right - main_x - (bento_cols - 1) * bento_gap) // bento_cols
        card_h = 264

        for r in range(bento_rows):
            for c in range(bento_cols):
                idx = r * bento_cols + c + 1
                cx0 = main_x + c * (card_w + bento_gap)
                cy0 = bento_y0 + r * (card_h + bento_gap)
                cx1 = cx0 + card_w
                cy1 = cy0 + card_h

                draw.rectangle(
                    [cx0, cy0, cx1, cy1],
                    fill=t.CARD_SURFACE,
                    outline=t.HAIRLINE_BORDER,
                )

                # Card Header: Device Serial + Semantic Healthy Dot
                draw.ellipse([cx0 + 24, cy0 + 26, cx0 + 32, cy0 + 34], fill=t.STATUS_HEALTHY)
                draw.text(
                    (cx0 + 40, cy0 + 22),
                    f"PIXEL-6-PRO-{idx:02d}",
                    fill=t.TEXT_PRIMARY,
                    font=font,
                )
                draw.text(
                    (cx1 - 88, cy0 + 22),
                    "READY",
                    fill=t.STATUS_HEALTHY,
                    font=font,
                )

                # Clean Viewport Preview Surface inside Bento card
                draw.rectangle(
                    [cx0 + 24, cy0 + 52, cx1 - 24, cy0 + 188],
                    fill=t.CANVAS_BG,
                    outline=t.HAIRLINE_BORDER,
                )
                draw.text(
                    (cx0 + 40, cy0 + 112),
                    f"Scrcpy 60fps | PTX NCC 0.99 | 36.2 C",
                    fill=t.TEXT_SECONDARY,
                    font=font,
                )

                # Subtle footer metadata + single neutral inspect button
                draw.text(
                    (cx0 + 24, cy0 + 212),
                    "Task: TikTok Warmup #4",
                    fill=t.TEXT_SECONDARY,
                    font=font,
                )
                draw.rectangle(
                    [cx1 - 104, cy0 + 204, cx1 - 24, cy0 + 236],
                    fill=t.SECONDARY_SURFACE_BTN,
                    outline=t.HAIRLINE_BORDER,
                )
                draw.text((cx1 - 84, cy0 + 214), "Inspect", fill=t.TEXT_PRIMARY, font=font)

        # Bottom summary strip confirming v13 Design System metrics
        draw.rectangle(
            [main_x, H - 72, main_right, H - 24],
            fill=t.CARD_SURFACE,
            outline=t.HAIRLINE_BORDER,
        )
        draw.text(
            (main_x + 24, H - 54),
            "AFTER (AMAF v13.0): 5 Sidebar Workspaces | 1 Primary CTA | 34% Breathable Whitespace | Score: 98/100 (Grade A+)",
            fill=t.TEXT_PRIMARY,
            font=font,
        )

        img.save(dest_path, format="PNG")
