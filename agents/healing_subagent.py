"""
Self-Healing Subagent
Autonomous failure diagnosis, semantic element recovery, and modal dismissal.
"""

import sys
import time
import difflib
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper


class SelfHealingSubagent:
    """Diagnoses action failures and executes dynamic recovery strategies."""

    def __init__(self, serial: str, adb: Optional[ADBWrapper] = None):
        self.serial = serial
        self.adb = adb or ADBWrapper()

    def attempt_recovery(
        self,
        failed_step: Dict[str, Any],
        elements: List[Dict[str, Any]],
        max_attempts: int = 3
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Attempt multi-stage self-healing for a failed UI action:
        1. Dismiss overlay / permission dialogs
        2. Hide soft keyboard if obstructing
        3. Scroll viewport to discover off-screen element
        4. Fuzzy semantic matching on all visible nodes
        """
        locator = failed_step.get("locator", "")

        # Strategy 1: Check and dismiss obstructing dialogs
        dismissed = self._dismiss_obstructions(elements)
        if dismissed:
            # Re-fetch elements after modal dismissal
            new_xml = self.adb.dump_ui_hierarchy(self.serial)
            elements = self.adb.parse_ui_elements(new_xml)
            match = self._fuzzy_find_element(elements, locator)
            if match:
                return True, match, "Dismissed obstructing modal; element recovered"

        # Strategy 2: Hide soft keyboard (Escape / Back)
        self.adb.press_key(self.serial, 111)  # KEYCODE_ESCAPE
        time.sleep(0.5)

        # Strategy 3: Scroll down to reveal off-screen items
        self.adb.swipe(self.serial, 360, 1100, 360, 400, 350)
        time.sleep(0.8)
        new_xml = self.adb.dump_ui_hierarchy(self.serial)
        elements = self.adb.parse_ui_elements(new_xml)
        match = self._fuzzy_find_element(elements, locator)
        if match:
            return True, match, "Scrolled viewport down; element revealed"

        # Strategy 4: Scroll up if previously scrolled too far
        self.adb.swipe(self.serial, 360, 400, 360, 1100, 350)
        time.sleep(0.8)
        new_xml = self.adb.dump_ui_hierarchy(self.serial)
        elements = self.adb.parse_ui_elements(new_xml)
        match = self._fuzzy_find_element(elements, locator)
        if match:
            return True, match, "Scrolled viewport up; element recovered"

        return False, None, f"Self-healing exhausted {max_attempts} strategies; element '{locator}' not reachable."

    def _dismiss_obstructions(self, elements: List[Dict[str, Any]]) -> bool:
        """Dismiss common system permission prompts or promotional overlays."""
        dismiss_keywords = [
            "cho phép", "allow", "đồng ý", "agree", "chấp nhận", "accept",
            "tiếp tục", "continue", "đóng", "close", "bỏ qua", "skip", "ok", "got it"
        ]
        for el in elements:
            txt = (el.get("text") or "").lower().strip()
            desc = (el.get("content_desc") or "").lower().strip()
            for kw in dismiss_keywords:
                if kw == txt or kw == desc:
                    c = el.get("bounds")
                    if c:
                        self.adb.tap(self.serial, c["center_x"], c["center_y"])
                        time.sleep(1.0)
                        return True
        return False

    def _fuzzy_find_element(self, elements: List[Dict[str, Any]], target_query: str, threshold: float = 0.65) -> Optional[Dict[str, Any]]:
        """Find highest semantic match among visible elements using Levenshtein ratio."""
        if not target_query:
            return None
        q = target_query.lower().strip()
        best_match = None
        best_score = 0.0

        for el in elements:
            candidates = [
                (el.get("text") or "").lower().strip(),
                (el.get("content_desc") or "").lower().strip(),
                (el.get("resource_id") or "").lower().strip().split("/")[-1]
            ]
            for cand in candidates:
                if not cand:
                    continue
                # Exact contains
                if q in cand:
                    return el
                # Similarity ratio
                ratio = difflib.SequenceMatcher(None, q, cand).ratio()
                if ratio > best_score and ratio >= threshold:
                    best_score = ratio
                    best_match = el

        return best_match


if __name__ == "__main__":
    healer = SelfHealingSubagent("emulator-5554")
    print("SelfHealingSubagent initialized.")
