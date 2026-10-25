"""
Vivo OriginOS Hardware & OS Telemetry + Touch Inset Calibration Engine (AMAF 8.0)
Specialized engine for Vivo / OriginOS devices (such as Vivo V2417A / PD2417 running OriginOS 6
at 1260x2800, 560 dpi) and other OEM skins. Provides telemetry parsing, safe touch zone inset
calibration, normalized coordinate mapping, and multi-language system popup/interception detection.
"""

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple


class VivoOriginOSEngine:
    """
    Hardware & OS telemetry parser, touch inset calibrator, and system interception detector
    tailored for Vivo OriginOS devices (e.g. V2417A / PD2417 @ 1260x2800, 560 dpi).
    """

    VIVO_INTERCEPTION_LABELS: List[str] = [
        "Tiếp tục cài đặt",
        "Cho phép cài đặt qua USB",
        "Cài đặt",
        "Luôn cho phép",
        "Trong khi dùng ứng dụng",
        "Cho phép",
        "Đồng ý",
        "Install anyway",
        "Allow USB install",
        "Continue installing",
        "继续安装",
        "允许",
    ]

    # Calibrated 1260x2800 fallback coordinates for Vivo OriginOS bottom confirmation buttons
    DEFAULT_VIVO_1260x2800_FALLBACK: Tuple[int, int] = (630, 2550)

    def parse_originos_telemetry(
        self,
        props_raw: str,
        size_raw: str,
        density_raw: str,
        window_raw: str = ""
    ) -> Dict[str, Any]:
        """
        Parse hardware & OriginOS properties, screen geometry, density, current focused window,
        and compute safe touch zone bounding box compensating for OriginOS status bar,
        punch-hole camera cutout, and bottom gesture navigation bar.
        """
        props_text = (props_raw or "").strip()
        size_text = (size_raw or "").strip()
        density_text = (density_raw or "").strip()
        window_text = (window_raw or "").strip()

        model = "unknown"
        device_code = "unknown"
        os_display_id = ""

        # Parse bracketed getprop output or key=value / raw lines
        prop_map: Dict[str, str] = {}
        for line in props_text.splitlines():
            line_s = line.strip()
            if not line_s:
                continue
            m_bracket = re.match(r"^\[([^\]]+)\]:\s*\[([^\]]*)\]", line_s)
            if m_bracket:
                prop_map[m_bracket.group(1).strip()] = m_bracket.group(2).strip()
            elif "=" in line_s:
                k, v = line_s.split("=", 1)
                prop_map[k.strip()] = v.strip()

        if prop_map:
            model = (
                prop_map.get("ro.product.model")
                or prop_map.get("ro.vivo.product.model")
                or "unknown"
            )
            device_code = (
                prop_map.get("ro.product.device")
                or prop_map.get("ro.vivo.product.model")
                or model
            )
            os_display_id = (
                prop_map.get("ro.vivo.os.build.display.id")
                or prop_map.get("ro.vivo.os.version")
                or ""
            )
        else:
            lines = [ln.strip() for ln in props_text.splitlines() if ln.strip()]
            for ln in lines:
                if "OriginOS" in ln or "Funtouch" in ln:
                    os_display_id = ln
                elif model == "unknown":
                    model = ln
                elif device_code == "unknown":
                    device_code = ln
            if device_code == "unknown" and model != "unknown":
                device_code = model

        if not os_display_id and "OriginOS" in props_text:
            m_os = re.search(r"(OriginOS\s*[\w\.]+)", props_text, re.IGNORECASE)
            if m_os:
                os_display_id = m_os.group(1).strip()

        # Parse physical width/height
        width, height = 1080, 2400
        if "1260x2800" in size_text:
            width, height = 1260, 2800
        else:
            m_size = re.search(r"(\d{3,4})x(\d{3,4})", size_text)
            if m_size:
                width = int(m_size.group(1))
                height = int(m_size.group(2))

        # Parse density
        density = 560 if width == 1260 and height == 2800 else 440
        m_dens = re.search(r"(\d{2,4})", density_text)
        if m_dens:
            density = int(m_dens.group(1))

        # Parse focused window / package
        focused_package = "unknown"
        focused_activity = "unknown"
        for line in window_text.splitlines():
            if "/" in line:
                for token in line.split():
                    if "/" in token:
                        cleaned = token.strip("{}")
                        parts = cleaned.split("/", 1)
                        if len(parts) == 2 and "." in parts[0]:
                            focused_package = parts[0]
                            focused_activity = parts[1]
                            break
                if focused_package != "unknown":
                    break

        # Compute OriginOS safe touch bounds
        top_inset_px = int(height * 0.042)
        bottom_inset_px = int(height * 0.038)
        side_inset_px = max(12, int(width * 0.015))

        safe_touch_bounds = {
            "x_min": side_inset_px,
            "y_min": top_inset_px,
            "x_max": width - side_inset_px,
            "y_max": height - bottom_inset_px,
            "top_inset_px": top_inset_px,
            "bottom_inset_px": bottom_inset_px,
            "side_inset_px": side_inset_px,
        }

        is_vivo_originos = bool(
            "originos" in os_display_id.lower()
            or "vivo" in props_text.lower()
            or model.upper().startswith("V2")
            or device_code.upper().startswith("PD")
        )

        aspect_ratio = round(height / float(width), 4) if width > 0 else 0.0

        return {
            "is_vivo_originos": is_vivo_originos,
            "model": model,
            "device_code": device_code,
            "os_display_id": os_display_id or ("OriginOS 6" if is_vivo_originos else "Android"),
            "width": width,
            "height": height,
            "density": density,
            "safe_touch_bounds": safe_touch_bounds,
            "aspect_ratio": aspect_ratio,
            "focused_package": focused_package,
            "focused_activity": focused_activity,
        }

    def calibrate_normalized_coordinates(
        self,
        norm_x: float,
        norm_y: float,
        width: int = 1260,
        height: int = 2800,
        respect_insets: bool = True
    ) -> Dict[str, int]:
        """
        Convert normalized (norm_x, norm_y) in [0.0, 1.0] into exact pixel coordinates (px, py)
        clamped inside the OriginOS safe touch area so touches never accidentally trigger
        the top status bar shade or OriginOS bottom gesture bar.
        """
        clamped_norm_x = max(0.0, min(1.0, float(norm_x)))
        clamped_norm_y = max(0.0, min(1.0, float(norm_y)))

        raw_px = int(round(clamped_norm_x * width))
        raw_py = int(round(clamped_norm_y * height))

        top_inset_px = int(height * 0.042)
        bottom_inset_px = int(height * 0.038)
        side_inset_px = max(12, int(width * 0.015))

        x_min = side_inset_px if respect_insets else 0
        x_max = (width - side_inset_px) if respect_insets else max(0, width - 1)
        y_min = top_inset_px if respect_insets else 0
        y_max = (height - bottom_inset_px) if respect_insets else max(0, height - 1)

        px = max(x_min, min(x_max, raw_px))
        py = max(y_min, min(y_max, raw_py))

        return {
            "px": px,
            "py": py,
            "raw_px": raw_px,
            "raw_py": raw_py,
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
            "clamped": (px != raw_px) or (py != raw_py),
        }

    def detect_vivo_system_interceptions(self, ui_xml: str) -> Dict[str, Any]:
        """
        Scan UIAutomator XML for Vivo / OriginOS security overlays, USB install prompts,
        high-power consumption warnings, and permission dialogs across Vietnamese, English,
        and Chinese. Extracts [x1,y1][x2,y2] and center (cx, cy) if present, else provides
        calibrated 1260x2800 fallback coordinates.
        """
        fallback_cx, fallback_cy = self.DEFAULT_VIVO_1260x2800_FALLBACK
        if not ui_xml or not ui_xml.strip():
            return {
                "interception_detected": False,
                "matched_label": None,
                "bounds": None,
                "center": None,
                "fallback_coords": {"cx": fallback_cx, "cy": fallback_cy},
            }

        # Try structured XML parsing first
        try:
            root = ET.fromstring(ui_xml.strip())
            for node in root.iter("node"):
                attrib = node.attrib
                text = (attrib.get("text") or "").strip()
                desc = (attrib.get("content-desc") or "").strip()
                combined = f"{text} {desc}".strip()
                if not combined:
                    continue

                for label in self.VIVO_INTERCEPTION_LABELS:
                    if label.lower() in combined.lower():
                        bounds_str = attrib.get("bounds", "")
                        parsed_bounds = self._parse_bounds_string(bounds_str)
                        if parsed_bounds:
                            return {
                                "interception_detected": True,
                                "matched_label": label,
                                "node_text": text or desc,
                                "resource_id": attrib.get("resource-id", ""),
                                "bounds": parsed_bounds,
                                "center": (parsed_bounds["cx"], parsed_bounds["cy"]),
                                "fallback_coords": {"cx": fallback_cx, "cy": fallback_cy},
                            }
                        return {
                            "interception_detected": True,
                            "matched_label": label,
                            "node_text": text or desc,
                            "resource_id": attrib.get("resource-id", ""),
                            "bounds": None,
                            "center": (fallback_cx, fallback_cy),
                            "fallback_coords": {"cx": fallback_cx, "cy": fallback_cy},
                        }
        except ET.ParseError:
            # Regex fallback for malformed/partial XML
            for label in self.VIVO_INTERCEPTION_LABELS:
                if label.lower() in ui_xml.lower():
                    m_bounds = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', ui_xml)
                    if m_bounds:
                        x1, y1, x2, y2 = (int(m_bounds.group(i)) for i in range(1, 5))
                        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                        return {
                            "interception_detected": True,
                            "matched_label": label,
                            "node_text": label,
                            "resource_id": "",
                            "bounds": {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "cx": cx, "cy": cy},
                            "center": (cx, cy),
                            "fallback_coords": {"cx": fallback_cx, "cy": fallback_cy},
                        }
                    return {
                        "interception_detected": True,
                        "matched_label": label,
                        "node_text": label,
                        "resource_id": "",
                        "bounds": None,
                        "center": (fallback_cx, fallback_cy),
                        "fallback_coords": {"cx": fallback_cx, "cy": fallback_cy},
                    }

        return {
            "interception_detected": False,
            "matched_label": None,
            "bounds": None,
            "center": None,
            "fallback_coords": {"cx": fallback_cx, "cy": fallback_cy},
        }

    @staticmethod
    def _parse_bounds_string(bounds_str: str) -> Optional[Dict[str, int]]:
        """Parse UIAutomator bounds '[x1,y1][x2,y2]' into dict with x1, y1, x2, y2, cx, cy."""
        if not bounds_str:
            return None
        m = re.match(r"^\[(\d+),(\d+)\]\[(\d+),(\d+)\]$", bounds_str.strip())
        if not m:
            return None
        x1, y1, x2, y2 = (int(m.group(i)) for i in range(1, 5))
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        return {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "cx": cx, "cy": cy}
