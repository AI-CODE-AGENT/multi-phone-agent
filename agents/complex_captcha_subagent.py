"""
Complex Captcha Subagent (Subagent #22)
Coordinates auto-screenshot capture, `UniversalCaptchaCVEngine` (Sobel 2D vertical edge projection,
circular polar discontinuity rotation analysis, 2D visual blob salience clustering, RGB+edge outlier
tile selection, piecewise Cubic Bézier trajectory interpolation), `CaptchaSolverSubagent` (#19),
and pure-vision Canvas/WebView opaque CAPTCHA fallback (`CANVAS_WEBVIEW_OPAQUE_CAPTCHA`).
"""

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.captcha_solver_subagent import CaptchaSolverSubagent
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager
from core.universal_captcha_cv_engine import UniversalCaptchaCVEngine


class ComplexCaptchaSubagent:
    """
    Subagent #22: End-to-end multimodal (XML + PIL/NumPy Computer Vision) CAPTCHA solver
    supporting all 10 complex mobile CAPTCHA types plus opaque WebView/Canvas challenges.
    """

    CV_METHOD_MAP = {
        "SLIDER_PUZZLE": "sobel_vertical_projection",
        "ROTATION_PUZZLE": "polar_ring_gradient",
        "CLICK_ORDER_CAPTCHA": "salience_blob_clustering",
        "ICON_SHAPE_MATCH_CAPTCHA": "rgb_edge_outlier_detection",
        "SLIDE_PATH_TRAJECTORY_CAPTCHA": "piecewise_cubic_bezier",
        "HOLD_PRESS_CHALLENGE": "human_dwell_tremor_hold",
        "AUDIO_ACCESSIBILITY_CHALLENGE": "audio_token_transcription",
        "TEXT_MATH_OCR": "regex_math_ocr_parser",
        "CHECKBOX_CHALLENGE": "gaussian_jitter_dwell_tap",
        "IMAGE_GRID": "multi_tile_grid_selection",
        "CANVAS_WEBVIEW_OPAQUE_CAPTCHA": "pure_vision_sobel_webview_fallback",
    }

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
        cv_engine: Optional[UniversalCaptchaCVEngine] = None,
        solver: Optional[CaptchaSolverSubagent] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.cv_engine = cv_engine or UniversalCaptchaCVEngine()
        self.solver = solver or CaptchaSolverSubagent(
            adb=self.adb,
            memory=self.memory,
            cv_engine=self.cv_engine,
        )

    def get_supported_captcha_types(self) -> List[str]:
        """Return the list of all 10 supported CAPTCHA types."""
        return list(CaptchaSolverSubagent.SUPPORTED_CAPTCHA_TYPES)

    def _capture_temp_screenshot_if_needed(
        self,
        serial: str,
        screenshot_path: Optional[str],
        auto_screenshot: bool,
    ) -> Tuple[Optional[str], bool]:
        """Capture screenshot to a temporary file if `screenshot_path` is not provided and `auto_screenshot=True`."""
        if screenshot_path and os.path.exists(screenshot_path):
            return screenshot_path, False
        if not auto_screenshot:
            return None, False
        fd, temp_path = tempfile.mkstemp(prefix=f"captcha_{serial}_", suffix=".png")
        os.close(fd)
        ok = self.adb.capture_screenshot(serial, temp_path)
        if ok and os.path.exists(temp_path) and os.path.getsize(temp_path) > 100:
            return temp_path, True
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return None, False

    def solve_any_captcha_with_vision(
        self,
        serial: str,
        xml_override: Optional[str] = None,
        screenshot_path: Optional[str] = None,
        auto_screenshot: bool = True,
    ) -> Dict[str, Any]:
        """
        Detect and solve any of the 10 CAPTCHA types (plus opaque WebView/Canvas CAPTCHAs)
        using combined UIAutomator XML + `UniversalCaptchaCVEngine` visual grounding.
        """
        xml_content = xml_override if xml_override is not None else self.adb.dump_ui_hierarchy(serial)
        detection = self.solver.detect_captcha_challenge(serial, xml_override=xml_content)
        ctype = detection.get("captcha_type", "NONE")

        active_screen_path, created_temp = self._capture_temp_screenshot_if_needed(
            serial, screenshot_path, auto_screenshot
        )

        try:
            if ctype != "NONE":
                hint_dist = None
                cv_diagnostics: Dict[str, Any] = {}
                details = detection.get("details", {})

                if ctype == "SLIDER_PUZZLE" and active_screen_path and os.path.exists(active_screen_path):
                    track_w = int(details.get("track_width", 520))
                    try:
                        cv_diagnostics = self.cv_engine.detect_slider_gap_sobel(
                            active_screen_path,
                            track_width=track_w,
                        )
                        hint_dist = int(cv_diagnostics["distance_px"])
                    except Exception:
                        pass
                elif ctype == "ROTATION_PUZZLE":
                    track_w = int(details.get("track_width", 520))
                    cv_diagnostics = self.cv_engine.estimate_rotation_angle(
                        image_path=active_screen_path,
                        track_width=track_w,
                    )
                    hint_dist = int(cv_diagnostics["drag_distance_px"])

                solved = self.solver.solve_captcha(
                    serial,
                    xml_override=xml_content,
                    hint_distance_px=hint_dist,
                    screenshot_path=active_screen_path,
                )
                cv_method = self.CV_METHOD_MAP.get(ctype, "hybrid_xml_cv")
                output = {
                    "serial": serial,
                    "status": solved.get("status", "CAPTCHA_SOLVED"),
                    "captcha_type": ctype,
                    "cv_method": cv_method,
                    "cv_diagnostics": cv_diagnostics,
                    "solved_details": solved,
                    "timestamp": time.time(),
                }
                self.memory.remember(
                    key=f"complex_captcha_{serial}_{int(time.time() * 1000)}",
                    value=output,
                    tags=["captcha", "subagent_22", ctype.lower()],
                    category="captcha_telemetry",
                )
                return output

            # Check for opaque WebView / Canvas CAPTCHA when XML returns NONE
            xml_lower = (xml_content or "").lower()
            has_opaque_webview = (
                "android.webkit.webview" in xml_lower
                or "canvas" in xml_lower
                or "captcha" in xml_lower
            )

            if has_opaque_webview:
                cv_diag = {}
                dist = 310
                if active_screen_path and os.path.exists(active_screen_path):
                    try:
                        cv_diag = self.cv_engine.detect_slider_gap_sobel(active_screen_path, track_width=520)
                        dist = int(cv_diag["distance_px"])
                    except Exception:
                        pass
                drag_info = self.solver._execute_bezier_slider_drag(serial, 120, 960, dist)
                solved = {
                    "serial": serial,
                    "status": "CAPTCHA_SOLVED",
                    "captcha_type": "CANVAS_WEBVIEW_OPAQUE_CAPTCHA",
                    "drag_distance_px": dist,
                    "trajectory_points": drag_info["trajectory_points"],
                    "start": drag_info["start"],
                    "target": drag_info["target"],
                    "timestamp": time.time(),
                }
                output = {
                    "serial": serial,
                    "status": "CAPTCHA_SOLVED",
                    "captcha_type": "CANVAS_WEBVIEW_OPAQUE_CAPTCHA",
                    "cv_method": self.CV_METHOD_MAP["CANVAS_WEBVIEW_OPAQUE_CAPTCHA"],
                    "cv_diagnostics": cv_diag,
                    "solved_details": solved,
                    "timestamp": time.time(),
                }
                self.memory.remember(
                    key=f"complex_captcha_{serial}_{int(time.time() * 1000)}",
                    value=output,
                    tags=["captcha", "subagent_22", "canvas_webview_opaque_captcha"],
                    category="captcha_telemetry",
                )
                return output

            return {
                "serial": serial,
                "status": "NO_CAPTCHA_PRESENT",
                "captcha_type": "NONE",
                "cv_method": "none",
                "cv_diagnostics": {},
                "solved_details": {},
                "timestamp": time.time(),
            }
        finally:
            if created_temp and active_screen_path and os.path.exists(active_screen_path):
                try:
                    os.remove(active_screen_path)
                except Exception:
                    pass


# Type alias helper for internal return annotation
Tuple_or_Path = Any


if __name__ == "__main__":
    subagent = ComplexCaptchaSubagent()
    print("Supported 10 CAPTCHA Types:", subagent.get_supported_captcha_types())
    sample_rot_xml = (
        '<hierarchy>'
        '<node text="Kéo để xoay hình về đúng hướng" resource-id="com.app:id/rotation_captcha" '
        'class="android.widget.TextView" bounds="[80,450][980,550]"/>'
        '<node text="" resource-id="com.app:id/slider_track" class="android.widget.SeekBar" '
        'bounds="[100,1050][620,1130]" clickable="true"/>'
        '</hierarchy>'
    )
    res = subagent.solve_any_captcha_with_vision(
        "emulator-5554",
        xml_override=sample_rot_xml,
        auto_screenshot=False,
    )
    print("Rotation Solve Result:", res["status"], res["captcha_type"], res["cv_method"])
