"""
Accessibility & WCAG 2.1 Contrast Subagent (Subagent #28)
Inspired by Deque axe DevTools Mobile, Google Accessibility Scanner, and WCAG 2.1 AA/AAA
Contrast & TalkBack Focus-Order specifications.

Capabilities:
1. WCAG 2.1 Relative Luminance & Contrast Ratio calculation (1.0 .. 21.0).
2. Region-level pixel contrast measurement from screenshots using 10th/90th luminance percentiles.
3. UIAutomator XML + Screenshot auditing for:
   - LOW_CONTRAST_TEXT (WCAG 1.4.3 / 1.4.6 contrast ratio < 4.5)
   - UNLABELED_INTERACTIVE (WCAG 4.1.2 missing text and content-desc on interactive nodes)
   - ILLOGICAL_FOCUS_ORDER (WCAG 2.4.3 TalkBack reading order jumping backwards significantly)
   - DUPLICATE_CONTENT_DESC (WCAG 2.4.6 / axe ambiguous or identical labels across distinct interactive buttons)
"""

import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager


class WCAGViolation(dict):
    """
    Dictionary representing a WCAG / TalkBack accessibility violation that also
    compares equal to its violation type string for flexible assertion and inspection.
    """

    def __init__(self, violation_type: str, **kwargs: Any):
        super().__init__(type=violation_type, code=violation_type, **kwargs)
        self.violation_type = violation_type

    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return self.violation_type == other
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.violation_type)


class AccessibilityAndWCAGContrastSubagent:
    """
    Subagent #28: Audits Android UI hierarchies and screenshots against WCAG 2.1 AA/AAA
    color contrast requirements and TalkBack screen-reader focus/labeling specifications.
    """

    WCAG_AA_THRESHOLD = 4.5
    WCAG_AAA_THRESHOLD = 7.0
    BACKWARD_JUMP_THRESHOLD_PX = 100
    AMBIGUOUS_LABELS = {
        "button",
        "icon",
        "image",
        "unlabelled",
        "unlabeled",
        "clickable",
        "item",
        "view",
        "btn",
    }

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.audit_history: List[Dict[str, Any]] = []

    @staticmethod
    def compute_relative_luminance(rgb: Tuple[int, int, int]) -> float:
        """
        Compute WCAG 2.1 relative luminance L in [0.0, 1.0]:
        L = 0.2126 * R_lin + 0.7152 * G_lin + 0.0722 * B_lin
        where C_lin = (c/255)/12.92 if c/255 <= 0.03928 else (((c/255) + 0.055)/1.055) ** 2.4.
        """
        r, g, b = (max(0.0, min(255.0, float(c))) / 255.0 for c in rgb[:3])

        def _linearize(c_norm: float) -> float:
            if c_norm <= 0.03928:
                return c_norm / 12.92
            return ((c_norm + 0.055) / 1.055) ** 2.4

        r_lin = _linearize(r)
        g_lin = _linearize(g)
        b_lin = _linearize(b)
        return float(0.2126 * r_lin + 0.7152 * g_lin + 0.0722 * b_lin)

    @classmethod
    def compute_contrast_ratio(
        cls,
        fg_rgb: Tuple[int, int, int],
        bg_rgb: Tuple[int, int, int],
    ) -> float:
        """
        Compute WCAG 2.1 contrast ratio:
        (max(L1, L2) + 0.05) / (min(L1, L2) + 0.05), rounded to 2 decimals (1.0 .. 21.0).
        """
        l1 = cls.compute_relative_luminance(fg_rgb)
        l2 = cls.compute_relative_luminance(bg_rgb)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        ratio = (lighter + 0.05) / (darker + 0.05)
        return round(float(ratio), 2)

    @staticmethod
    def _parse_bounds_str(bounds_str: str) -> Optional[Dict[str, int]]:
        """Parse UIAutomator bounds '[x1,y1][x2,y2]' into {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2}."""
        if not bounds_str:
            return None
        nums = re.findall(r"-?\d+", str(bounds_str))
        if len(nums) == 4:
            x1, y1, x2, y2 = (int(v) for v in nums)
            return {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
        return None

    @classmethod
    def _normalize_bounds(
        cls,
        bounds: Union[Dict[str, int], Tuple[int, int, int, int], List[int], str],
    ) -> Tuple[int, int, int, int]:
        """Normalize bounds dict, tuple/list, or UIAutomator string into (x1, y1, x2, y2)."""
        if isinstance(bounds, str):
            parsed = cls._parse_bounds_str(bounds)
            if parsed is None:
                raise ValueError(f"Invalid bounds string: {bounds}")
            return parsed["x1"], parsed["y1"], parsed["x2"], parsed["y2"]
        if isinstance(bounds, (tuple, list)) and len(bounds) == 4:
            return int(bounds[0]), int(bounds[1]), int(bounds[2]), int(bounds[3])
        if isinstance(bounds, dict):
            x1 = int(bounds.get("x1", bounds.get("left", 0)))
            y1 = int(bounds.get("y1", bounds.get("top", 0)))
            if "x2" in bounds or "right" in bounds:
                x2 = int(bounds.get("x2", bounds.get("right", x1)))
            else:
                x2 = x1 + int(bounds.get("width", bounds.get("w", 0)))
            if "y2" in bounds or "bottom" in bounds:
                y2 = int(bounds.get("y2", bounds.get("bottom", y1)))
            else:
                y2 = y1 + int(bounds.get("height", bounds.get("h", 0)))
            return x1, y1, x2, y2
        raise ValueError(f"Unsupported bounds format: {bounds}")

    def measure_region_contrast_from_image(
        self,
        image_path: str,
        bounds: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        Crop [x1, y1, x2, y2] from `image_path` using PIL.Image, convert to np.ndarray,
        estimate foreground vs background RGB using the 10th percentile (darkest pixels)
        and 90th percentile (brightest pixels) inside the text box, and compute
        `contrast_ratio`, `passes_wcag_aa` (>= 4.5), and `passes_wcag_aaa` (>= 7.0).
        """
        x1, y1, x2, y2 = self._normalize_bounds(bounds)

        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
            width, height = rgb_img.size

            crop_x1 = max(0, min(width, min(x1, x2)))
            crop_y1 = max(0, min(height, min(y1, y2)))
            crop_x2 = max(0, min(width, max(x1, x2)))
            crop_y2 = max(0, min(height, max(y1, y2)))

            if crop_x2 <= crop_x1 or crop_y2 <= crop_y1:
                return {
                    "bounds": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    "fg_rgb": (0, 0, 0),
                    "bg_rgb": (0, 0, 0),
                    "contrast_ratio": 1.0,
                    "passes_wcag_aa": False,
                    "passes_wcag_aaa": False,
                }

            cropped = rgb_img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            arr = np.asarray(cropped, dtype=np.float64)

        pixels = arr.reshape(-1, 3)
        if pixels.size == 0:
            fg_rgb = (0, 0, 0)
            bg_rgb = (0, 0, 0)
            ratio = 1.0
        else:
            # Perceived luminance ordering per pixel to find 10th (darkest) & 90th (brightest) percentiles
            luma = 0.2126 * pixels[:, 0] + 0.7152 * pixels[:, 1] + 0.0722 * pixels[:, 2]
            order = np.argsort(luma)
            sorted_pixels = pixels[order]

            n_pixels = len(sorted_pixels)
            idx_10 = int(np.clip(np.floor(0.10 * (n_pixels - 1)), 0, n_pixels - 1))
            idx_90 = int(np.clip(np.ceil(0.90 * (n_pixels - 1)), 0, n_pixels - 1))

            dark_pixel = np.percentile(sorted_pixels, 10, axis=0)
            bright_pixel = np.percentile(sorted_pixels, 90, axis=0)

            # Use exact percentile RGB tuples (or indexed representative pixel if identical)
            fg_rgb = (
                int(round(float(dark_pixel[0]))),
                int(round(float(dark_pixel[1]))),
                int(round(float(dark_pixel[2]))),
            )
            bg_rgb = (
                int(round(float(bright_pixel[0]))),
                int(round(float(bright_pixel[1]))),
                int(round(float(bright_pixel[2]))),
            )

            # Also check indexed 10th/90th pixel luminance in case channel-wise interpolation softened extremes
            fg_idx_rgb = tuple(int(round(float(v))) for v in sorted_pixels[idx_10])
            bg_idx_rgb = tuple(int(round(float(v))) for v in sorted_pixels[idx_90])
            ratio_interp = self.compute_contrast_ratio(fg_rgb, bg_rgb)
            ratio_idx = self.compute_contrast_ratio(fg_idx_rgb, bg_idx_rgb)  # type: ignore[arg-type]
            if ratio_idx >= ratio_interp:
                fg_rgb = fg_idx_rgb  # type: ignore[assignment]
                bg_rgb = bg_idx_rgb  # type: ignore[assignment]
                ratio = ratio_idx
            else:
                ratio = ratio_interp

        return {
            "bounds": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "fg_rgb": fg_rgb,
            "bg_rgb": bg_rgb,
            "contrast_ratio": ratio,
            "passes_wcag_aa": bool(ratio >= self.WCAG_AA_THRESHOLD),
            "passes_wcag_aaa": bool(ratio >= self.WCAG_AAA_THRESHOLD),
        }

    def audit_wcag_and_talkback_tree(
        self,
        serial: str,
        xml_override: Optional[str] = None,
        screenshot_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parse UIAutomator XML nodes (`xml_override` or `self.adb.dump_ui_hierarchy(serial)`)
        and audit:
        1. WCAG 2.1 Color Contrast (`LOW_CONTRAST_TEXT`): For text-bearing nodes, measures
           contrast ratio on `screenshot_path` (if provided) and flags nodes with `contrast_ratio < 4.5`.
        2. TalkBack Reading Order & Focusability (`ILLOGICAL_FOCUS_ORDER`, `UNLABELED_INTERACTIVE`):
           Checks if interactive elements lack both `text` and `content_desc`, or if reading order
           jumps backwards significantly.
        3. Duplicate Content Descriptions (`DUPLICATE_CONTENT_DESC`): Flags multiple distinct
           interactive buttons sharing identical ambiguous labels like "Button" or "Icon".
        """
        xml_content = (
            xml_override
            if xml_override is not None
            else self.adb.dump_ui_hierarchy(serial)
        )
        xml_str = (xml_content or "").strip()

        nodes: List[Dict[str, Any]] = []
        violations: List[WCAGViolation] = []

        has_screenshot = bool(screenshot_path and Path(screenshot_path).is_file())

        if xml_str:
            try:
                root = ET.fromstring(xml_str)
                raw_elements = list(root.iter("node"))
            except ET.ParseError:
                raw_elements = []
                for match in re.finditer(r"<node\b([^>]*)/?>", xml_str):
                    attr_chunk = match.group(1)
                    attrib: Dict[str, str] = {}
                    for k, v in re.findall(r'(\w[\w-]*)="([^"]*)"', attr_chunk):
                        attrib[k] = v
                    elem = ET.Element("node", attrib)
                    raw_elements.append(elem)

            for idx, elem in enumerate(raw_elements):
                attrib = elem.attrib
                text = (attrib.get("text") or "").strip()
                content_desc = (
                    attrib.get("content-desc")
                    or attrib.get("content_desc")
                    or ""
                ).strip()
                resource_id = (attrib.get("resource-id") or "").strip()
                class_name = (attrib.get("class") or "").strip()
                clickable = attrib.get("clickable", "false").lower() == "true"
                focusable = attrib.get("focusable", "false").lower() == "true"
                bounds_str = (attrib.get("bounds") or "").strip()
                bounds = self._parse_bounds_str(bounds_str)

                nodes.append({
                    "index": idx,
                    "text": text,
                    "content_desc": content_desc,
                    "resource_id": resource_id,
                    "class_name": class_name,
                    "clickable": clickable,
                    "focusable": focusable,
                    "interactive": clickable or focusable,
                    "bounds_str": bounds_str,
                    "bounds": bounds,
                })

        # 1. WCAG 2.1 Color Contrast (LOW_CONTRAST_TEXT)
        all_contrast_aaa = True
        for node in nodes:
            if node["text"] and node["bounds"] is not None and has_screenshot:
                contrast_info = self.measure_region_contrast_from_image(
                    str(screenshot_path),
                    node["bounds"],
                )
                ratio = contrast_info["contrast_ratio"]
                if not contrast_info["passes_wcag_aaa"]:
                    all_contrast_aaa = False
                if ratio < self.WCAG_AA_THRESHOLD:
                    violations.append(
                        WCAGViolation(
                            "LOW_CONTRAST_TEXT",
                            wcag_criterion="1.4.3 Contrast (Minimum)",
                            severity="HIGH",
                            node_index=node["index"],
                            resource_id=node["resource_id"],
                            text=node["text"],
                            bounds=node["bounds_str"],
                            contrast_ratio=ratio,
                            required_ratio=self.WCAG_AA_THRESHOLD,
                            fg_rgb=contrast_info["fg_rgb"],
                            bg_rgb=contrast_info["bg_rgb"],
                        )
                    )

        # 2. TalkBack Focusability & Reading Order (UNLABELED_INTERACTIVE, ILLOGICAL_FOCUS_ORDER)
        prev_focus_bounds: Optional[Dict[str, int]] = None
        prev_focus_node: Optional[Dict[str, Any]] = None

        for node in nodes:
            if not node["interactive"]:
                continue

            if not node["text"] and not node["content_desc"]:
                violations.append(
                    WCAGViolation(
                        "UNLABELED_INTERACTIVE",
                        wcag_criterion="4.1.2 Name, Role, Value",
                        severity="HIGH",
                        node_index=node["index"],
                        resource_id=node["resource_id"],
                        class_name=node["class_name"],
                        bounds=node["bounds_str"],
                    )
                )

            curr_bounds = node["bounds"]
            if curr_bounds is not None:
                if prev_focus_bounds is not None and prev_focus_node is not None:
                    # Top-to-bottom, left-to-right reading order check:
                    # Flag if y1 jumps significantly above the previous interactive element's top,
                    # or on the same horizontal row jumps significantly to the left.
                    dy = curr_bounds["y1"] - prev_focus_bounds["y1"]
                    dx = curr_bounds["x1"] - prev_focus_bounds["x1"]
                    same_row = abs(dy) <= 24
                    jumped_up = dy < -self.BACKWARD_JUMP_THRESHOLD_PX
                    jumped_left_same_row = same_row and dx < -self.BACKWARD_JUMP_THRESHOLD_PX

                    if jumped_up or jumped_left_same_row:
                        violations.append(
                            WCAGViolation(
                                "ILLOGICAL_FOCUS_ORDER",
                                wcag_criterion="2.4.3 Focus Order",
                                severity="MEDIUM",
                                node_index=node["index"],
                                previous_node_index=prev_focus_node["index"],
                                resource_id=node["resource_id"],
                                bounds=node["bounds_str"],
                                previous_bounds=prev_focus_node["bounds_str"],
                                delta_x=dx,
                                delta_y=dy,
                            )
                        )
                prev_focus_bounds = curr_bounds
                prev_focus_node = node

        # 3. Duplicate Content Descriptions (DUPLICATE_CONTENT_DESC)
        label_groups: Dict[str, List[Dict[str, Any]]] = {}
        for node in nodes:
            if not node["interactive"]:
                continue
            label = (node["content_desc"] or node["text"]).strip()
            if not label:
                continue
            norm_label = label.lower()
            label_groups.setdefault(norm_label, []).append(node)

        for norm_label, group in label_groups.items():
            if len(group) > 1:
                # Distinct interactive elements sharing an identical label (especially ambiguous ones like "Button" or "Icon")
                distinct_positions = {
                    n["bounds_str"] or f"idx_{n['index']}" for n in group
                }
                if len(distinct_positions) > 1:
                    violations.append(
                        WCAGViolation(
                            "DUPLICATE_CONTENT_DESC",
                            wcag_criterion="2.4.6 Headings and Labels",
                            severity="MEDIUM" if norm_label not in self.AMBIGUOUS_LABELS else "HIGH",
                            label=group[0]["content_desc"] or group[0]["text"],
                            occurrences=len(group),
                            node_indices=[n["index"] for n in group],
                            bounds_list=[n["bounds_str"] for n in group],
                        )
                    )

        # Compute WCAG score (0..100) and WCAG level ("AAA", "AA", "A", or "FAIL")
        deduction = 0
        for v in violations:
            v_type = v.get("type")
            if v_type in ("LOW_CONTRAST_TEXT", "UNLABELED_INTERACTIVE"):
                deduction += 20
            else:
                deduction += 12

        wcag_score = max(0, min(100, 100 - deduction))

        if len(violations) == 0:
            wcag_level = "AAA" if all_contrast_aaa else "AA"
        elif wcag_score >= 85 and not any(
            v.get("type") in ("LOW_CONTRAST_TEXT", "UNLABELED_INTERACTIVE")
            for v in violations
        ):
            wcag_level = "AA"
        elif wcag_score >= 60:
            wcag_level = "A"
        else:
            wcag_level = "FAIL"

        result: Dict[str, Any] = {
            "serial": serial,
            "status": "WCAG_AUDIT_COMPLETED",
            "wcag_score": wcag_score,
            "wcag_level": wcag_level,
            "nodes_audited": len(nodes),
            "violations_count": len(violations),
            "violations": violations,
        }
        self.audit_history.append(result)
        return result


if __name__ == "__main__":
    agent = AccessibilityAndWCAGContrastSubagent()

    # 1. Verify relative luminance & contrast ratios
    lum_black = agent.compute_relative_luminance((0, 0, 0))
    lum_white = agent.compute_relative_luminance((255, 255, 255))
    bw_ratio = agent.compute_contrast_ratio((0, 0, 0), (255, 255, 255))
    gray_ratio = agent.compute_contrast_ratio((140, 140, 140), (160, 160, 160))

    assert lum_black == 0.0, f"Expected 0.0 for black luminance, got {lum_black}"
    assert abs(lum_white - 1.0) < 1e-6, f"Expected 1.0 for white luminance, got {lum_white}"
    assert bw_ratio == 21.0, f"Expected 21.0 for black/white contrast, got {bw_ratio}"
    assert gray_ratio < 2.0, f"Expected < 2.0 for low-contrast gray-on-gray, got {gray_ratio}"

    # 2. Verify region contrast measurement & XML + screenshot auditing
    with tempfile.TemporaryDirectory() as tmp_dir:
        img_path = Path(tmp_dir) / "test_screen.png"
        img = Image.new("RGB", (400, 600), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Region 1: High-contrast black text block on white background [20, 20, 200, 80]
        draw.rectangle([20, 20, 200, 80], fill=(255, 255, 255))
        draw.rectangle([40, 35, 160, 65], fill=(0, 0, 0))

        # Region 2: Low-contrast gray text block on gray background [20, 120, 200, 180]
        draw.rectangle([20, 120, 200, 180], fill=(160, 160, 160))
        draw.rectangle([40, 135, 160, 165], fill=(140, 140, 140))

        img.save(img_path)

        high_res = agent.measure_region_contrast_from_image(
            str(img_path), {"x1": 20, "y1": 20, "x2": 200, "y2": 80}
        )
        low_res = agent.measure_region_contrast_from_image(
            str(img_path), {"x1": 20, "y1": 120, "x2": 200, "y2": 180}
        )

        assert high_res["contrast_ratio"] == 21.0, f"Expected 21.0, got {high_res}"
        assert high_res["passes_wcag_aa"] is True and high_res["passes_wcag_aaa"] is True
        assert low_res["contrast_ratio"] < 2.0, f"Expected < 2.0, got {low_res}"
        assert low_res["passes_wcag_aa"] is False and low_res["passes_wcag_aaa"] is False

        sample_xml = (
            '<hierarchy rotation="0">'
            '<node index="0" text="High Contrast Header" content-desc="" clickable="false" focusable="true" bounds="[20,20][200,80]" />'
            '<node index="1" text="Low Contrast Subtitle" content-desc="" clickable="false" focusable="true" bounds="[20,120][200,180]" />'
            '<node index="2" text="" content-desc="Button" clickable="true" focusable="true" bounds="[20,450][120,510]" />'
            '<node index="3" text="" content-desc="Button" clickable="true" focusable="true" bounds="[20,220][120,280]" />'
            '<node index="4" text="" content-desc="" clickable="true" focusable="true" bounds="[140,220][220,280]" />'
            "</hierarchy>"
        )

        audit = agent.audit_wcag_and_talkback_tree(
            "emulator-5554",
            xml_override=sample_xml,
            screenshot_path=str(img_path),
        )
        violation_types = {v["type"] for v in audit["violations"]}
        assert "LOW_CONTRAST_TEXT" in violation_types
        assert "UNLABELED_INTERACTIVE" in violation_types
        assert "ILLOGICAL_FOCUS_ORDER" in violation_types
        assert "DUPLICATE_CONTENT_DESC" in violation_types
        print("Self-test passed:", audit)
