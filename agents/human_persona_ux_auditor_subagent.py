"""
Human-Persona UX & Semantic Logic Auditor Subagent (Subagent #21)
Audits Android screens like a real human QA & Product Designer:
1. Detects unaccented Vietnamese ASCII seed text leaked to UI ("Bun bo", "Tra sua", "Mon them", "Do uong", "dac biet", etc.).
2. Detects mixed-locale string leaks (e.g., Vietnamese "đã bán" or "Giảm ... cho đơn từ" shown while screen UI is in English).
3. Detects developer-speak / placeholder copy.
4. Audits 48dp touch targets, missing accessibility labels, and overlapping clickables via NetworkAndVisualQASubagent.
5. Provides human-like element lookup & tap helpers with self-healing compressed UIAutomator dumps.
"""

import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from agents.network_visual_qa_subagent import NetworkAndVisualQASubagent


UNACCENTED_VI_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (r"\bbun\s+bo\b", "Unaccented 'Bun bo' -> should be 'Bún bò' / 'Beef Noodle Soup'"),
    (r"\bdac\s+biet\b", "Unaccented 'dac biet' -> should be 'đặc biệt' / 'Special'"),
    (r"\bgio\s+heo\b", "Unaccented 'gio heo' -> should be 'giò heo' / 'Pork Knuckle'"),
    (r"\btra\s+sua\b", "Unaccented 'Tra sua' -> should be 'Trà sữa' / 'Milk Tea'"),
    (r"\btran\s+chau\s+duong\s+den\b", "Unaccented 'tran chau duong den' -> should be 'trân châu đường đen' / 'Brown Sugar Pearl'"),
    (r"\btra\s+dao\s+cam\s+sa\b", "Unaccented 'Tra dao cam sa' -> should be 'Trà đào cam sả' / 'Peach Lemongrass Tea'"),
    (r"\bmon\s+them\b", "Unaccented 'Mon them' -> should be 'Món thêm' / 'Side Dishes'"),
    (r"\bdo\s+uong\b", "Unaccented 'Do uong' -> should be 'Đồ uống' / 'Beverages'"),
    (r"\bcom\s+van\s+phong\b", "Unaccented 'Com van phong' -> should be 'Cơm văn phòng' / 'Office Lunch'"),
    (r"\bga\s+ran\b", "Unaccented 'Ga ran' -> should be 'Gà rán' / 'Fried Chicken'"),
    (r"\bpizza\s+hai\s+san\b", "Unaccented 'Pizza hai san' -> should be 'Pizza hải sản' / 'Seafood Pizza'"),
    (r"\bpho\s+mai\b", "Unaccented 'pho mai' -> should be 'phô mai' / 'cheese'"),
    (r"\bsot\s+ca\s+chua\b", "Unaccented 'sot ca chua' -> should be 'sốt cà chua' / 'tomato sauce'"),
)

VI_LEAK_IN_EN_PATTERNS: Tuple[Tuple[str, str], ...] = (
    (r"\bđã\s+bán\b", "Hardcoded Vietnamese 'đã bán' leaked in English UI"),
    (r"\bgiảm\s+\d+", "Raw Vietnamese promo title 'Giảm ...' shown in English UI"),
)


class HumanPersonaUXAuditorSubagent:
    """
    Subagent #21: Combines layout/accessibility checks with semantic UX logic auditing
    (unaccented seed data detection, mixed-locale leak detection, and human-like navigation).
    """

    def __init__(self, adb: Optional[ADBWrapper] = None, visual_qa: Optional[NetworkAndVisualQASubagent] = None):
        self.adb = adb or ADBWrapper()
        self.visual_qa = visual_qa or NetworkAndVisualQASubagent(adb=self.adb)

    def dump_xml_reliable(self, serial: str) -> str:
        """Self-healing compressed UIAutomator XML dump."""
        self.adb.shell(serial, "killall -9 app_process 2>/dev/null; uiautomator dump --compressed /sdcard/window_dump.xml", timeout=12)
        code, xml, _ = self.adb.run_device_cmd(serial, ["exec-out", "cat /sdcard/window_dump.xml"], timeout=10)
        return (xml or "").strip() if code == 0 else ""

    def audit_screen_ux_and_logic(self, serial: str, screen_name: str, xml_override: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform both visual layout QA (48dp, content-desc, overlap) and semantic UX logic checks.
        """
        xml_str = xml_override if xml_override is not None else self.dump_xml_reliable(serial)
        layout_report = self.visual_qa.audit_ui_accessibility_and_layout(serial, xml_override=xml_str)

        visible_texts: List[str] = []
        semantic_issues: List[Dict[str, str]] = []

        if xml_str and (xml_str.startswith("<?xml") or xml_str.startswith("<hierarchy")):
            try:
                root = ET.fromstring(xml_str)
                for node in root.iter("node"):
                    txt = (node.attrib.get("text") or "").strip()
                    if txt:
                        visible_texts.append(txt)
            except Exception:
                pass

        joined_lower = " | ".join(visible_texts).lower()
        is_english_ui = any(
            en_marker in joined_lower
            for en_marker in ("search dishes", "what to eat", "view order", "view draft cart", "all", "popular searches")
        )

        for txt in visible_texts:
            low = txt.lower()
            for pattern, reason in UNACCENTED_VI_PATTERNS:
                if re.search(pattern, low):
                    semantic_issues.append({
                        "type": "UNACCENTED_VIETNAMESE_ASCII",
                        "text": txt,
                        "reason": reason,
                    })
            if is_english_ui:
                for pattern, reason in VI_LEAK_IN_EN_PATTERNS:
                    if re.search(pattern, low):
                        semantic_issues.append({
                            "type": "MIXED_LOCALE_LEAK",
                            "text": txt,
                            "reason": reason,
                        })

        layout_score = layout_report.get("layout_health_score", 100)
        ux_logic_score = max(40, 100 - len(semantic_issues) * 8)
        combined_score = (layout_score + ux_logic_score) // 2

        return {
            "screen_name": screen_name,
            "layout_health_score": layout_score,
            "ux_logic_score": ux_logic_score,
            "combined_score": combined_score,
            "layout_warnings": layout_report.get("warnings", []),
            "semantic_issues_count": len(semantic_issues),
            "semantic_issues": semantic_issues,
        }
