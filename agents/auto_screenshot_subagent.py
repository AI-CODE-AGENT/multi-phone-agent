"""
Auto Screenshot & Visual Perception Subagent (#21) - AMAF 5.0
Autonomous screenshot capture, M3A Set-of-Mark (SoM) grounding, OmniParser-style
pure-vision region discovery, Airtest NCC template matching, and Maestro visual diffing.
"""

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager
from core.screenshot_perception_engine import ScreenshotPerceptionEngine


class AutoScreenshotSubagent:
    """
    Subagent #21: Autonomous Screenshot & Visual Perception Subagent.
    Provides smart screenshot capture with Set-of-Mark annotations, template/SoM coordinate
    resolution, coarse-to-fine zoom, and visual regression verification.
    """

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
        engine: Optional[ScreenshotPerceptionEngine] = None,
    ):
        self.adb = adb if isinstance(adb, ADBWrapper) else ADBWrapper()

        if isinstance(memory, ScreenshotPerceptionEngine) and engine is None:
            self.engine = memory
            self.memory = MemoryManager()
        else:
            self.memory = memory if isinstance(memory, MemoryManager) else MemoryManager()
            self.engine = (
                engine
                if isinstance(engine, ScreenshotPerceptionEngine)
                else ScreenshotPerceptionEngine(self.adb)
            )

    def capture_smart_screenshot(
        self,
        serial: str,
        tag: str = "smart",
        annotate_som: bool = True,
        xml_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Capture a screenshot via ScreenshotPerceptionEngine, optionally render Set-of-Mark
        badges (#1, #2, ...), store telemetry in MemoryManager, and return combined output.
        """
        cap = self.engine.capture_screenshot_auto(serial, tag=tag, fallback_synthetic=True)
        annotated_path: Optional[str] = None
        marks: Dict[str, Dict[str, Any]] = {}
        marks_count = 0

        if annotate_som:
            som = self.engine.render_set_of_mark_screenshot(
                serial=serial,
                screenshot_path=cap["screenshot_path"],
                xml_override=xml_override,
            )
            annotated_path = som["annotated_screenshot_path"]
            marks = som["marks"]
            marks_count = som["marks_count"]

        result = {
            "status": "SCREENSHOT_CAPTURED",
            "serial": serial,
            "tag": tag,
            "screenshot_path": cap["screenshot_path"],
            "annotated_screenshot_path": annotated_path,
            "width": cap["width"],
            "height": cap["height"],
            "sha256": cap["sha256"],
            "mean_brightness": cap["mean_brightness"],
            "contrast_std": cap["contrast_std"],
            "edge_density": cap["edge_density"],
            "is_blank": cap["is_blank"],
            "marks_count": marks_count,
            "marks": marks,
            "timestamp": cap["timestamp"],
        }

        try:
            self.memory.remember(
                key=f"smart_screenshot_{serial}_{tag}",
                value={
                    "screenshot_path": result["screenshot_path"],
                    "annotated_screenshot_path": annotated_path,
                    "marks_count": marks_count,
                    "mean_brightness": result["mean_brightness"],
                    "edge_density": result["edge_density"],
                    "is_blank": result["is_blank"],
                },
                tags=["screenshot", "perception", "som", serial],
                category="visual_perception",
            )
        except Exception:
            pass

        return result

    def locate_by_template_or_som(
        self,
        serial: str,
        template_path: Optional[str] = None,
        mark_id: Optional[int] = None,
        screenshot_path: Optional[str] = None,
        xml_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Locate a UI target either by Airtest-style NCC template matching (when template_path
        is provided) or by Set-of-Mark badge ID (when mark_id is provided).
        """
        if not screenshot_path or not os.path.exists(screenshot_path):
            cap = self.engine.capture_screenshot_auto(serial, tag="locate", fallback_synthetic=True)
            screenshot_path = cap["screenshot_path"]

        if template_path:
            match = self.engine.find_template_on_screen(screenshot_path, template_path)
            status = "LOCATED" if match["matched"] else "NOT_FOUND"
            return {
                "serial": serial,
                "status": status,
                "method": "ncc_template",
                "center_x": int(match["center_x"]),
                "center_y": int(match["center_y"]),
                "bounds": match["bounds"],
                "confidence": float(match["confidence"]),
                "screenshot_path": screenshot_path,
            }

        if mark_id is not None:
            som = self.engine.render_set_of_mark_screenshot(
                serial=serial,
                screenshot_path=screenshot_path,
                xml_override=xml_override,
            )
            mark_key = str(mark_id).lstrip("#")
            entry = som["marks"].get(mark_key)
            if entry:
                return {
                    "serial": serial,
                    "status": "LOCATED",
                    "method": "set_of_mark",
                    "mark_id": int(entry["mark_id"]),
                    "label": entry["label"],
                    "center_x": int(entry["center_x"]),
                    "center_y": int(entry["center_y"]),
                    "bounds": entry["bounds"],
                    "confidence": 1.0,
                    "annotated_screenshot_path": som["annotated_screenshot_path"],
                }

        return {
            "serial": serial,
            "status": "NOT_FOUND",
            "center_x": 0,
            "center_y": 0,
            "bounds": {"x1": 0, "y1": 0, "x2": 0, "y2": 0, "center_x": 0, "center_y": 0},
            "confidence": 0.0,
        }

    def visual_regression_check(
        self,
        serial: str,
        baseline_path: str,
        current_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compare the current screen against a baseline screenshot (Maestro assertScreenshot style)
        and return similarity score, MAE, PSNR, changed pixel ratio, and diff heatmap path.
        """
        if not current_path or not os.path.exists(current_path):
            cap = self.engine.capture_screenshot_auto(serial, tag="regression_current", fallback_synthetic=True)
            current_path = cap["screenshot_path"]

        diff_report = self.engine.compare_screenshots(baseline_path, current_path)
        return {
            "serial": serial,
            "baseline_path": str(baseline_path),
            "current_path": str(current_path),
            **diff_report,
        }


if __name__ == "__main__":
    subagent = AutoScreenshotSubagent()
    print("[Self-Test] Running AutoScreenshotSubagent (#21)...")
    smart_res = subagent.capture_smart_screenshot("emulator-5554", tag="subagent_test", annotate_som=True)
    print(
        f" -> Smart Screenshot: status={smart_res['status']}, marks_count={smart_res['marks_count']}, "
        f"brightness={smart_res['mean_brightness']}, edge_density={smart_res['edge_density']}"
    )

    som_loc = subagent.locate_by_template_or_som(
        "emulator-5554",
        mark_id=1,
        screenshot_path=smart_res["screenshot_path"],
    )
    print(" -> Locate by SoM #1:", som_loc)

    crop = subagent.engine.crop_and_zoom_region(
        smart_res["screenshot_path"],
        bounds={"x1": 80, "y1": 440, "x2": 320, "y2": 530},
        zoom_factor=1,
    )
    tpl_loc = subagent.locate_by_template_or_som(
        "emulator-5554",
        template_path=crop["cropped_path"],
        screenshot_path=smart_res["screenshot_path"],
    )
    print(" -> Locate by Template:", tpl_loc)

    reg_res = subagent.visual_regression_check(
        "emulator-5554",
        baseline_path=smart_res["screenshot_path"],
        current_path=smart_res["screenshot_path"],
    )
    print(" -> Visual Regression (identical check):", reg_res)
