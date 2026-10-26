"""
Subagents #76, #77, #78, #81, #82 for Multi-Screen Responsive Matrix Testing (AMAF v15.0):
  - Subagent #76: MultiScreenViewportMatrixSubagent
  - Subagent #77: ResponsiveDOMAndXMLCriticSubagent
  - Subagent #78: SynchronizedMultiDeviceMirrorSubagent
  - Subagent #81: VisualMultiScreenGridComposerSubagent
  - Subagent #82: AutoFixLayoutPatchSynthesizerSubagent
"""

from typing import Any, Dict, List, Optional
from core.adb_wrapper import ADBWrapper
from core.multi_screen_responsive_engine import (
    MultiScreenResponsiveEngine,
    ResponsiveLayoutAnalyzer,
    SCREEN_PROFILES,
    SCREEN_SUITES,
    resolve_screen_profile,
)


class MultiScreenViewportMatrixSubagent:
    """Subagent #76: Dynamic Android `wm size` / `wm density` / orientation matrix controller with guaranteed `finally` reset."""

    ROLE = "Multi-Screen Viewport Matrix Subagent #76"
    subagent_id = 76

    def __init__(self, adb: Any = None, memory: Any = None, output_dir: Optional[str] = None):
        self.adb = adb or ADBWrapper()
        self.memory = memory
        self.output_dir = output_dir
        self.engine = MultiScreenResponsiveEngine(self.adb)

    def list_supported_profiles(self) -> Dict[str, Any]:
        return {
            "subagent": self.ROLE,
            "profiles": {
                k: {
                    "id": v.id,
                    "label": v.label,
                    "width": v.width,
                    "height": v.height,
                    "density_dpi": v.density_dpi,
                    "dp_size": f"{v.dp_width}x{v.dp_height}dp",
                    "category": v.category,
                }
                for k, v in SCREEN_PROFILES.items()
            },
            "suites": SCREEN_SUITES,
        }

    def run_matrix_sweep(
        self,
        serial: str = "10CF5L0TYL00312",
        suite: str = "default_3",
        profiles: Optional[List[Any]] = None,
        apply_hardware_wm: bool = False,
        landscape: bool = False,
        capture_screenshots: bool = True,
        xml_override: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        res = self.engine.run_multi_screen_responsive_audit(
            serial=serial,
            profiles=profiles,
            suite=suite,
            apply_hardware_wm=apply_hardware_wm,
            landscape=landscape,
            capture_screenshots=capture_screenshots,
            output_dir=output_dir or self.output_dir,
            xml_override=xml_override,
        )
        return {"subagent": self.ROLE, **res}

    def execute(self, serial: str = "10CF5L0TYL00312", suite: str = "full_5_screens", apply_hardware_wm: bool = False, **kwargs: Any) -> Dict[str, Any]:
        return self.run_matrix_sweep(serial=serial, suite=suite, apply_hardware_wm=apply_hardware_wm, **kwargs)


class ResponsiveDOMAndXMLCriticSubagent:
    """Subagent #77: Audits UIAutomator XML & WebView DOM across screen ratios for clipping, overlap, ellipsis, and <48dp targets."""

    ROLE = "Responsive DOM & XML Critic Subagent #77"
    subagent_id = 77

    def __init__(self, adb: Any = None, memory: Any = None):
        self.adb = adb
        self.memory = memory
        self.analyzer = ResponsiveLayoutAnalyzer()

    def critique_xml_at_profile(
        self,
        xml_content: str,
        profile_spec: Any = "compact_phone",
        landscape: bool = False,
        source_resolution: Optional[tuple] = None,
    ) -> Dict[str, Any]:
        prof = resolve_screen_profile(profile_spec, landscape=landscape)
        res = self.analyzer.analyze_xml_for_profile(xml_content, prof, source_resolution=source_resolution)
        return {"subagent": self.ROLE, "defect_count": len(res.get("findings", [])), **res}

    def execute(self, xml_content: str, profile_id: str = "compact_phone", landscape: bool = False) -> Dict[str, Any]:
        return self.critique_xml_at_profile(xml_content, profile_spec=profile_id, landscape=landscape)


class SynchronizedMultiDeviceMirrorSubagent:
    """Subagent #78: Responsively-style normalized [0..1] coordinate action mirroring across multiple screens/devices."""

    ROLE = "Synchronized Multi-Device Mirror Subagent #78"
    subagent_id = 78

    def __init__(self, adb: Any = None, memory: Any = None, output_dir: Optional[str] = None):
        self.adb = adb or ADBWrapper()
        self.memory = memory
        self.output_dir = output_dir
        self.engine = MultiScreenResponsiveEngine(self.adb)

    def mirror_action(
        self,
        serials: List[str],
        action_type: str = "tap",
        norm_x: float = 0.5,
        norm_y: float = 0.5,
        norm_to_x: float = 0.5,
        norm_to_y: float = 0.25,
        text: str = "",
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        res = self.engine.sync_multi_screen_action(
            serials=serials,
            action_type=action_type,
            norm_x=norm_x,
            norm_y=norm_y,
            norm_to_x=norm_to_x,
            norm_to_y=norm_to_y,
            text=text,
            dry_run=dry_run,
        )
        return {"subagent": self.ROLE, "devices_mirrored": res["total_targets"], **res}

    def execute(
        self,
        serials: List[str],
        action_type: str = "tap",
        norm_x: float = 0.5,
        norm_y: float = 0.5,
        execute_adb: bool = False,
    ) -> Dict[str, Any]:
        return self.mirror_action(
            serials=serials,
            action_type=action_type,
            norm_x=norm_x,
            norm_y=norm_y,
            dry_run=not execute_adb,
        )


class VisualMultiScreenGridComposerSubagent:
    """Subagent #81: Renders side-by-side multi-screen visual comparison grids and MCP base64 image blocks."""

    ROLE = "Visual Multi-Screen Grid Composer Subagent #81"
    subagent_id = 81

    def __init__(self, adb: Any = None, memory: Any = None, output_dir: Optional[str] = None):
        self.adb = adb or ADBWrapper()
        self.memory = memory
        self.output_dir = output_dir
        self.engine = MultiScreenResponsiveEngine(self.adb)


class AutoFixLayoutPatchSynthesizerSubagent:
    """Subagent #82: Synthesizes Android ConstraintLayout XML, Jetpack Compose Modifier, and WebView CSS @media fixes."""

    ROLE = "Auto-Fix Layout Patch Synthesizer Subagent #82"
    subagent_id = 82

    def __init__(self, adb: Any = None, memory: Any = None):
        self.adb = adb
        self.memory = memory
        self.analyzer = ResponsiveLayoutAnalyzer()

    def summarize_fixes(self, responsive_audit: Dict[str, Any]) -> Dict[str, Any]:
        fixes = responsive_audit.get("auto_fixes", [])
        return {
            "subagent": self.ROLE,
            "total_fixes": len(fixes),
            "auto_fix_count": len(fixes),
            "fixes": fixes,
        }

    def execute(self, xml_content: str, profile_id: str = "compact_phone") -> Dict[str, Any]:
        prof = resolve_screen_profile(profile_id)
        audit = self.analyzer.analyze_xml_for_profile(xml_content, prof)
        return self.summarize_fixes(audit)
