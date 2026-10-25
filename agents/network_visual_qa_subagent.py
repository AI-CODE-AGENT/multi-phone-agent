"""
Network & Visual QA Subagent (Subagent #20)
Inspired by Google Accessibility Scanner & Netflix Chaos Monkey for multi-app testing.
Audits Android UI hierarchies for 48dp touch target sizing, accessibility labels, and
overlapping interactive elements, and verifies application resilience under network transitions.
"""

import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager


class LayoutWarning(str):
    """
    String subclass representing a layout/accessibility warning code (e.g. 'SMALL_TOUCH_TARGET')
    that also supports dict-style metadata lookup (.get / []) for flexible inspection.
    """

    def __new__(cls, code: str, details: Optional[Dict[str, Any]] = None):
        obj = super().__new__(cls, code)
        obj.details = {"type": code, "code": code, "warning": code, **(details or {})}
        return obj

    def get(self, key: str, default: Any = None) -> Any:
        return self.details.get(key, default)

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, str):
            return self.details[key]
        return super().__getitem__(key)


class NetworkAndVisualQASubagent:
    """
    Subagent #20: Visual layout & accessibility auditor (48dp touch target, content-desc,
    overlapping clickables) + Chaos Monkey network transition resilience verifier.
    """

    MIN_TOUCH_TARGET_PX = 48
    OVERLAP_RATIO_THRESHOLD = 0.50

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.audit_history: List[Dict[str, Any]] = []
        self.network_check_history: List[Dict[str, Any]] = []

    @staticmethod
    def _parse_bounds(bounds_str: str) -> Optional[Tuple[int, int, int, int]]:
        """Parse UIAutomator bounds '[x1,y1][x2,y2]' into (x1, y1, x2, y2)."""
        if not bounds_str:
            return None
        nums = re.findall(r"-?\d+", bounds_str)
        if len(nums) == 4:
            x1, y1, x2, y2 = (int(v) for v in nums)
            return x1, y1, x2, y2
        return None

    @staticmethod
    def _compute_overlap_ratio(
        b1: Tuple[int, int, int, int],
        b2: Tuple[int, int, int, int],
    ) -> float:
        """
        Compute the intersection-over-smaller-element area ratio for two bounding boxes.
        Returns a float in [0.0, 1.0].
        """
        x1_a, y1_a, x2_a, y2_a = b1
        x1_b, y1_b, x2_b, y2_b = b2

        area_a = max(0, x2_a - x1_a) * max(0, y2_a - y1_a)
        area_b = max(0, x2_b - x1_b) * max(0, y2_b - y1_b)
        min_area = min(area_a, area_b)
        if min_area <= 0:
            return 0.0

        inter_x1 = max(x1_a, x1_b)
        inter_y1 = max(y1_a, y1_b)
        inter_x2 = min(x2_a, x2_b)
        inter_y2 = min(y2_a, y2_b)

        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        return inter_area / float(min_area)

    def audit_ui_accessibility_and_layout(
        self,
        serial: str,
        xml_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parse the UIAutomator XML hierarchy and audit clickable elements for:
        1. SMALL_TOUCH_TARGET: width < 48 or height < 48.
        2. MISSING_ACCESSIBILITY_LABEL: both `text` and `content-desc` are empty.
        3. OVERLAPPING_CLICKABLES: two clickable sibling elements overlap by > 50% area.

        Computes `layout_health_score` (0..100, starting at 100 and deducting 5 per warning, min 50).
        """
        xml_content = xml_override if xml_override is not None else self.adb.dump_ui_hierarchy(serial)
        xml_str = (xml_content or "").strip()

        warnings: List[str] = []
        warning_details: List[Dict[str, Any]] = []
        clickable_count = 0

        if xml_str:
            try:
                root = ET.fromstring(xml_str)
                parent_map = {child: parent for parent in root.iter() for child in parent}
                clickable_nodes: List[Dict[str, Any]] = []

                for idx, node in enumerate(root.iter("node")):
                    attrib = node.attrib
                    if attrib.get("clickable", "false").lower() != "true":
                        continue

                    clickable_count += 1
                    text = (attrib.get("text") or "").strip()
                    content_desc = (attrib.get("content-desc") or "").strip()
                    resource_id = (attrib.get("resource-id") or "").strip()
                    bounds_str = (attrib.get("bounds") or "").strip()
                    bounds = self._parse_bounds(bounds_str)

                    # 1. Small Touch Target (< 48px)
                    if bounds is not None:
                        x1, y1, x2, y2 = bounds
                        width = x2 - x1
                        height = y2 - y1
                        if width < self.MIN_TOUCH_TARGET_PX or height < self.MIN_TOUCH_TARGET_PX:
                            detail = {
                                "type": "SMALL_TOUCH_TARGET",
                                "resource_id": resource_id,
                                "bounds": bounds_str,
                                "width": width,
                                "height": height,
                            }
                            warnings.append(LayoutWarning("SMALL_TOUCH_TARGET", detail))
                            warning_details.append(detail)

                    # 2. Missing Accessibility Label
                    if not text and not content_desc:
                        detail = {
                            "type": "MISSING_ACCESSIBILITY_LABEL",
                            "resource_id": resource_id,
                            "bounds": bounds_str,
                        }
                        warnings.append(LayoutWarning("MISSING_ACCESSIBILITY_LABEL", detail))
                        warning_details.append(detail)

                    clickable_nodes.append({
                        "index": idx,
                        "element": node,
                        "parent": parent_map.get(node),
                        "resource_id": resource_id,
                        "bounds_str": bounds_str,
                        "bounds": bounds,
                    })

                # 3. Overlapping Interactive Bounds (> 50% area between clickable siblings)
                for i in range(len(clickable_nodes)):
                    node_a = clickable_nodes[i]
                    bounds_a = node_a["bounds"]
                    if bounds_a is None:
                        continue
                    for j in range(i + 1, len(clickable_nodes)):
                        node_b = clickable_nodes[j]
                        bounds_b = node_b["bounds"]
                        if bounds_b is None:
                            continue
                        if node_a["parent"] is not node_b["parent"]:
                            continue

                        overlap_ratio = self._compute_overlap_ratio(bounds_a, bounds_b)
                        if overlap_ratio > self.OVERLAP_RATIO_THRESHOLD:
                            detail = {
                                "type": "OVERLAPPING_CLICKABLES",
                                "first_resource_id": node_a["resource_id"],
                                "second_resource_id": node_b["resource_id"],
                                "first_bounds": node_a["bounds_str"],
                                "second_bounds": node_b["bounds_str"],
                                "overlap_ratio": round(overlap_ratio, 3),
                            }
                            warnings.append(LayoutWarning("OVERLAPPING_CLICKABLES", detail))
                            warning_details.append(detail)
            except Exception:
                # Fallback regex scan if XML is malformed
                for match in re.finditer(r"<node\b([^>]*)/?>", xml_str):
                    attr_chunk = match.group(1)
                    if 'clickable="true"' not in attr_chunk:
                        continue
                    clickable_count += 1
                    txt_m = re.search(r'\btext="([^"]*)"', attr_chunk)
                    desc_m = re.search(r'\bcontent-desc="([^"]*)"', attr_chunk)
                    b_m = re.search(r'\bbounds="([^"]*)"', attr_chunk)

                    txt_val = (txt_m.group(1) if txt_m else "").strip()
                    desc_val = (desc_m.group(1) if desc_m else "").strip()
                    bounds = self._parse_bounds(b_m.group(1) if b_m else "")

                    if bounds is not None:
                        width = bounds[2] - bounds[0]
                        height = bounds[3] - bounds[1]
                        if width < self.MIN_TOUCH_TARGET_PX or height < self.MIN_TOUCH_TARGET_PX:
                            warnings.append(LayoutWarning("SMALL_TOUCH_TARGET"))
                    if not txt_val and not desc_val:
                        warnings.append(LayoutWarning("MISSING_ACCESSIBILITY_LABEL"))

        score = max(50, 100 - 5 * len(warnings))

        result: Dict[str, Any] = {
            "status": "LAYOUT_AUDIT_COMPLETED",
            "serial": serial,
            "clickable_elements_checked": clickable_count,
            "warnings_count": len(warnings),
            "warnings": warnings,
            "warning_details": warning_details,
            "layout_health_score": score,
        }
        self.audit_history.append(result)
        return result

    def run_network_resilience_check(
        self,
        serial: str,
        package: str,
        toggle_wifi: bool = True,
    ) -> Dict[str, Any]:
        """
        Test application resilience under a brief network transition:
        - If `toggle_wifi` is True: disables Wi-Fi via `svc wifi disable` and immediately
          restores it via `svc wifi enable`.
        - Launches/checks `package` and scans `logcat -d -t 60` for `FATAL EXCEPTION` or `ANR in {package}`.
        """
        wifi_restored = True
        if toggle_wifi:
            try:
                self.adb.shell(serial, "svc wifi disable")
            finally:
                self.adb.shell(serial, "svc wifi enable")
                wifi_restored = True

        self.adb.shell(serial, f"monkey -p {package} -c android.intent.category.LAUNCHER 1")
        logcat_out = self.adb.shell(serial, "logcat -d -t 60") or ""

        crashes: List[str] = []
        for line in logcat_out.splitlines():
            if "FATAL EXCEPTION" in line or f"ANR in {package}" in line:
                crashes.append(line.strip())

        result: Dict[str, Any] = {
            "status": "NETWORK_RESILIENCE_VERIFIED",
            "serial": serial,
            "package": package,
            "crashes_found": len(crashes),
            "crashes": crashes,
            "wifi_restored": wifi_restored,
            "timestamp": time.time(),
        }
        self.network_check_history.append(result)
        return result


if __name__ == "__main__":
    qa = NetworkAndVisualQASubagent()
    sample_xml = (
        '<hierarchy rotation="0">'
        '<node index="0" text="" content-desc="" clickable="true" bounds="[0,0][32,32]" />'
        '<node index="1" text="OK" content-desc="Confirm" clickable="true" bounds="[0,0][30,30]" />'
        "</hierarchy>"
    )
    print("Sample Audit:", qa.audit_ui_accessibility_and_layout("emulator-5554", xml_override=sample_xml))
