"""
Universal Multi-Stage APK Installer & Anti-Dark-Pattern Engine (Iterations #1, #2, #3).

Defeats OEM package installer dark patterns across Vivo OriginOS / FuntouchOS,
Xiaomi HyperOS / MIUI, OPPO / Realme ColorOS, Samsung OneUI, and Google Play Protect:
- Unicode NFC normalization for Vietnamese NFD/NFC diacritics
- Anti-Dark-Pattern negative trap filter (blocks 'Mở V-Appstore', 'Cài đặt an toàn', 'Hủy', etc.)
- Spatial Header Guard (ignores top 20% toolbar title traps like 'Cài đặt' at y=236)
- Multi-stage un-hiding via expander links ('Chi tiết khác', 'More details')
- Mandatory risk-acceptance checkbox detection & auto-ticking ('deleted_file_state_cb')
- Dynamic countdown timer regex parser ('Tiếp tục (5s)', '(10 giây)', '[3s]')
- Post-install completion handling ('Xong' / 'Done' vs 'Mở' / 'Open')
"""

import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple


class UniversalAPKInstallerEngine:
    """
    Zero-Token Universal Multi-Stage APK Installer & Anti-Dark-Pattern Engine.
    """

    NEGATIVE_TRAP_KEYWORDS: List[str] = [
        "hủy",
        "huỷ",
        "cancel",
        "không cài đặt",
        "từ chối",
        "đóng",
        "mở v-appstore",
        "cài đặt an toàn",
        "quét virus",
        "xóa gói",
        "gỡ cài đặt",
        "báo cáo",
        "tìm hiểu thêm",
    ]

    EXPANDER_KEYWORDS: List[str] = [
        "chi tiết khác",
        "more details",
        "xem thêm",
        "tùy chọn khác",
        "other options",
        "hiển thị thêm",
    ]

    PRIMARY_CONFIRM_KEYWORDS: List[str] = [
        "tiếp tục cài đặt",
        "vẫn cài đặt",
        "install anyway",
        "tiếp tục",
        "cài đặt",
        "install",
        "cho phép",
        "đồng ý",
        "xác nhận",
        "ok",
        "got it",
        "chấp nhận",
    ]

    COMPLETION_KEYWORDS: List[str] = [
        "xong",
        "done",
        "hoàn tất",
        "mở",
        "open",
    ]

    RISK_CHECKBOX_IDS: List[str] = [
        "deleted_file_state_cb",
        "vivo_security_CheckBox",
        "security_checkbox",
        "risk_checkbox",
        "cb_allow",
        "checkbox",
    ]

    RISK_CHECKBOX_KEYWORDS: List[str] = [
        "tôi đã hiểu",
        "phát hiện rủi ro",
        "chấp nhận rủi ro",
        "tôi hiểu",
        "understand the risk",
        "i understand",
        "vẫn muốn cài đặt",
        "đồng ý",
    ]

    _BOUNDS_RE = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
    _COUNTDOWN_RE = re.compile(
        r"(?:[\(\[\s]|^)(\d{1,2})\s*(?:s|sec|seconds|giây|秒)(?:[\)\]\s]|$)",
        re.IGNORECASE,
    )

    def __init__(self, default_width: int = 1260, default_height: int = 2800):
        self.default_width = default_width
        self.default_height = default_height
        self._normalized_traps = [self.normalize_text(k) for k in self.NEGATIVE_TRAP_KEYWORDS]
        self._normalized_expanders = [self.normalize_text(k) for k in self.EXPANDER_KEYWORDS]
        self._normalized_confirms = [self.normalize_text(k) for k in self.PRIMARY_CONFIRM_KEYWORDS]
        self._normalized_completions = [self.normalize_text(k) for k in self.COMPLETION_KEYWORDS]
        self._normalized_cb_keywords = [self.normalize_text(k) for k in self.RISK_CHECKBOX_KEYWORDS]
        self._normalized_cb_ids = [cid.lower() for cid in self.RISK_CHECKBOX_IDS]

    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """Normalize text and content-desc via unicodedata.normalize('NFC', text).lower()."""
        if not text:
            return ""
        return unicodedata.normalize("NFC", str(text)).strip().lower()

    @classmethod
    def parse_bounds(cls, bounds_str: str) -> Optional[Dict[str, int]]:
        """Parse UIAutomator bounds='[x1,y1][x2,y2]' into dict with coordinates and center."""
        if not bounds_str:
            return None
        match = cls._BOUNDS_RE.search(bounds_str)
        if not match:
            return None
        x1, y1, x2, y2 = (
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
        )
        if x2 <= x1 or y2 <= y1:
            return None
        return {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "width": x2 - x1,
            "height": y2 - y1,
            "center_x": (x1 + x2) // 2,
            "center_y": (y1 + y2) // 2,
        }

    @classmethod
    def detect_countdown_seconds(cls, text: Optional[str]) -> int:
        """
        Parse countdown timer patterns like '(5s)', '(10 giây)', '5s', '[3s]'
        and return integer seconds N (or 0 if none found).
        """
        if not text:
            return 0
        norm = cls.normalize_text(text)
        match = cls._COUNTDOWN_RE.search(norm)
        if match:
            return int(match.group(1))
        return 0

    def _is_negative_trap(self, norm_text: str, norm_desc: str) -> Optional[str]:
        """Return the matched negative trap keyword if text/desc is a dark-pattern trap."""
        combined = f"{norm_text} {norm_desc}".strip()
        if not combined:
            return None
        for trap_kw in self._normalized_traps:
            if trap_kw in ("hủy", "huỷ", "cancel", "đóng"):
                # Match standalone word or exact phrase so we don't false-match unrelated words
                pattern = rf"(?:^|[\s\(\[\-_]){re.escape(trap_kw)}(?:$|[\s\)\]\-_,.!])"
                if re.search(pattern, combined):
                    return trap_kw
            else:
                if trap_kw in combined:
                    return trap_kw
        return None

    def _passes_spatial_guard(
        self, center_y: int, resource_id: str, screen_height: int
    ) -> bool:
        """
        Spatial Guard: Ignore any button in the top 20% of the screen
        (center_y < int(screen_height * 0.20)) unless its resource-id explicitly
        ends with 'button1' or 'continue_button'.
        """
        res_lower = (resource_id or "").strip().lower()
        if res_lower.endswith("button1") or res_lower.endswith("continue_button"):
            return True
        if center_y < int(screen_height * 0.20):
            return False
        return True

    def _score_primary_confirm(
        self, norm_text: str, norm_desc: str, resource_id: str, center_y: int, screen_height: int
    ) -> int:
        """Calculate priority score for a primary confirmation button."""
        combined = f"{norm_text} {norm_desc}".strip()
        res_lower = (resource_id or "").strip().lower()
        score = 0

        # High-specificity multi-word confirm phrases
        high_priority = ("tiếp tục cài đặt", "vẫn cài đặt", "install anyway")
        mid_priority = ("tiếp tục", "cho phép", "đồng ý", "xác nhận", "chấp nhận", "got it", "ok")
        generic_priority = ("cài đặt", "install")

        for kw in high_priority:
            if kw in combined:
                score = max(score, 100)
                break

        if score == 0:
            for kw in mid_priority:
                if kw == "ok":
                    if re.search(r"(?:^|[\s\(\[])ok(?:$|[\s\)\]])", combined):
                        score = max(score, 85)
                        break
                elif kw in combined:
                    score = max(score, 90)
                    break

        if score == 0:
            for kw in generic_priority:
                if kw in combined:
                    score = max(score, 75)
                    break

        if res_lower.endswith("button1") or res_lower.endswith("continue_button"):
            score = max(score, 90) + 15

        if score > 0 and screen_height > 0:
            # Slight preference for lower-half action buttons
            score += int((center_y / screen_height) * 5)

        return score

    def _score_completion_button(
        self, norm_text: str, norm_desc: str, prefer_done_over_open: bool = True
    ) -> int:
        """Score post-installation completion buttons ('Xong'/'Done' vs 'Mở'/'Open')."""
        combined = f"{norm_text} {norm_desc}".strip()
        if not combined:
            return 0

        done_kws = ("xong", "done", "hoàn tất")
        open_kws = ("mở", "open")

        is_done = any(
            re.search(rf"(?:^|[\s\(\[]){re.escape(k)}(?:$|[\s\)\]])", combined)
            for k in done_kws
        )
        is_open = any(
            re.search(rf"(?:^|[\s\(\[]){re.escape(k)}(?:$|[\s\)\]])", combined)
            for k in open_kws
        )

        if is_done:
            return 95 if prefer_done_over_open else 80
        if is_open:
            return 80 if prefer_done_over_open else 95
        return 0

    def analyze_installer_hierarchy(
        self,
        xml_str: str,
        screen_width: int = 1260,
        screen_height: int = 2800,
        prefer_done_over_open: bool = True,
    ) -> Dict[str, Any]:
        """
        Parse UIAutomator XML hierarchy and return a structured multi-stage action plan:
          - stage: 'checkbox_required' | 'countdown_waiting' | 'expander_required' |
                   'confirm_ready' | 'install_completed' | 'none'
          - checkbox_to_tick: dict with center_x, center_y, text, resource_id (or None)
          - countdown_seconds: int (0 if none)
          - action_button: dict with center_x, center_y, text, resource_id, score (or None)
          - traps_filtered: list of negative trap buttons safely rejected
        """
        plan: Dict[str, Any] = {
            "stage": "none",
            "checkbox_to_tick": None,
            "countdown_seconds": 0,
            "action_button": None,
            "traps_filtered": [],
        }

        if not xml_str or not xml_str.strip():
            return plan

        try:
            # Strip any leading garbage before XML declaration or root tag
            idx = xml_str.find("<")
            clean_xml = xml_str[idx:] if idx >= 0 else xml_str
            root = ET.fromstring(clean_xml)
        except Exception:
            return plan

        checkbox_candidates: List[Dict[str, Any]] = []
        confirm_candidates: List[Dict[str, Any]] = []
        expander_candidates: List[Dict[str, Any]] = []
        completion_candidates: List[Dict[str, Any]] = []
        max_countdown = 0

        for elem in root.iter():
            bounds_str = elem.attrib.get("bounds", "")
            bounds = self.parse_bounds(bounds_str)
            if not bounds:
                continue

            raw_text = (elem.attrib.get("text") or "").strip()
            raw_desc = (elem.attrib.get("content-desc") or "").strip()
            res_id = (elem.attrib.get("resource-id") or "").strip()
            cls_name = (elem.attrib.get("class") or "").strip()
            checkable = (elem.attrib.get("checkable") or "").strip().lower() == "true"
            checked = (elem.attrib.get("checked") or "").strip().lower() == "true"

            norm_text = self.normalize_text(raw_text)
            norm_desc = self.normalize_text(raw_desc)
            combined_norm = f"{norm_text} {norm_desc}".strip()
            res_lower = res_id.lower()
            cls_lower = cls_name.lower()

            cx = bounds["center_x"]
            cy = bounds["center_y"]
            display_label = unicodedata.normalize("NFC", raw_text or raw_desc or res_id)

            # 1. Check if this node is a Risk Checkbox
            matches_cb_id = any(cid in res_lower for cid in self._normalized_cb_ids)
            matches_cb_kw = any(kw in combined_norm for kw in self._normalized_cb_keywords)
            is_checkbox_node = (
                checkable
                or "checkbox" in cls_lower
                or matches_cb_id
            )

            if is_checkbox_node and (matches_cb_id or matches_cb_kw):
                if not checked:
                    checkbox_candidates.append(
                        {
                            "center_x": cx,
                            "center_y": cy,
                            "text": display_label,
                            "resource_id": res_id,
                            "bounds": bounds,
                        }
                    )
                continue

            # Skip empty nodes with no text/desc and no relevant button resource-id
            if not combined_norm and not (
                res_lower.endswith("button1") or res_lower.endswith("continue_button")
            ):
                continue

            # 2. Check Anti-Dark-Pattern Negative Trap Filter FIRST
            trap_match = self._is_negative_trap(norm_text, norm_desc)
            if trap_match:
                plan["traps_filtered"].append(
                    {
                        "center_x": cx,
                        "center_y": cy,
                        "text": display_label,
                        "resource_id": res_id,
                        "matched_trap": trap_match,
                    }
                )
                continue

            # 3. Spatial Guard: Ignore top 20% header/toolbar traps unless button1 / continue_button
            if not self._passes_spatial_guard(cy, res_id, screen_height):
                plan["traps_filtered"].append(
                    {
                        "center_x": cx,
                        "center_y": cy,
                        "text": display_label,
                        "resource_id": res_id,
                        "matched_trap": "spatial_top_20_percent_guard",
                    }
                )
                continue

            # 4. Check Expander Keywords ('Chi tiết khác', 'More details', etc.)
            if any(exp_kw in combined_norm for exp_kw in self._normalized_expanders):
                expander_candidates.append(
                    {
                        "center_x": cx,
                        "center_y": cy,
                        "text": display_label,
                        "resource_id": res_id,
                        "score": 65,
                    }
                )
                continue

            # 5. Check Primary Confirm Keywords
            confirm_score = self._score_primary_confirm(
                norm_text, norm_desc, res_id, cy, screen_height
            )
            if confirm_score > 0:
                cd_sec = self.detect_countdown_seconds(raw_text or raw_desc)
                if cd_sec > 0:
                    max_countdown = max(max_countdown, cd_sec)
                confirm_candidates.append(
                    {
                        "center_x": cx,
                        "center_y": cy,
                        "text": display_label,
                        "resource_id": res_id,
                        "score": confirm_score,
                        "countdown_seconds": cd_sec,
                    }
                )
                continue

            # 6. Check Post-Install Completion Keywords ('Xong', 'Done', 'Mở', 'Open')
            comp_score = self._score_completion_button(
                norm_text, norm_desc, prefer_done_over_open=prefer_done_over_open
            )
            if comp_score > 0:
                completion_candidates.append(
                    {
                        "center_x": cx,
                        "center_y": cy,
                        "text": display_label,
                        "resource_id": res_id,
                        "score": comp_score,
                    }
                )

        # Sort candidates by score descending
        confirm_candidates.sort(key=lambda item: item["score"], reverse=True)
        expander_candidates.sort(key=lambda item: item["score"], reverse=True)
        completion_candidates.sort(key=lambda item: item["score"], reverse=True)

        if checkbox_candidates:
            plan["checkbox_to_tick"] = checkbox_candidates[0]

        if max_countdown > 0:
            plan["countdown_seconds"] = max_countdown

        # Stage resolution priority
        if plan["checkbox_to_tick"] is not None:
            plan["stage"] = "checkbox_required"
            if confirm_candidates:
                best_btn = dict(confirm_candidates[0])
                best_btn.pop("countdown_seconds", None)
                plan["action_button"] = best_btn
            else:
                plan["action_button"] = {
                    "center_x": plan["checkbox_to_tick"]["center_x"],
                    "center_y": plan["checkbox_to_tick"]["center_y"],
                    "text": plan["checkbox_to_tick"]["text"],
                    "resource_id": plan["checkbox_to_tick"]["resource_id"],
                    "score": 100,
                }
        elif confirm_candidates:
            best_btn = dict(confirm_candidates[0])
            btn_cd = best_btn.pop("countdown_seconds", 0)
            plan["action_button"] = best_btn
            if btn_cd > 0 or max_countdown > 0:
                plan["stage"] = "countdown_waiting"
                plan["countdown_seconds"] = max(btn_cd, max_countdown)
            else:
                plan["stage"] = "confirm_ready"
        elif expander_candidates:
            plan["stage"] = "expander_required"
            plan["action_button"] = expander_candidates[0]
        elif completion_candidates:
            plan["stage"] = "install_completed"
            plan["action_button"] = completion_candidates[0]
        else:
            plan["stage"] = "none"
            plan["action_button"] = None

        return plan

    def _dump_xml_from_adb(self, adb_wrapper: Any, serial: Optional[str] = None) -> str:
        """Flexibly dump UIAutomator XML from an ADBWrapper instance or mock."""
        target_serial = serial or getattr(adb_wrapper, "serial", None) or getattr(
            adb_wrapper, "default_serial", None
        )
        if hasattr(adb_wrapper, "dump_ui_hierarchy"):
            try:
                if target_serial is not None:
                    return adb_wrapper.dump_ui_hierarchy(target_serial) or ""
                return adb_wrapper.dump_ui_hierarchy() or ""
            except TypeError:
                return adb_wrapper.dump_ui_hierarchy(target_serial or "default") or ""
        if hasattr(adb_wrapper, "get_ui_xml"):
            return adb_wrapper.get_ui_xml() or ""
        return ""

    def _tap_via_adb(
        self, adb_wrapper: Any, x: int, y: int, serial: Optional[str] = None
    ) -> None:
        """Perform a tap/micro-dwell swipe via adb_wrapper."""
        target_serial = serial or getattr(adb_wrapper, "serial", None) or getattr(
            adb_wrapper, "default_serial", None
        )
        if hasattr(adb_wrapper, "tap"):
            try:
                if target_serial is not None:
                    adb_wrapper.tap(target_serial, x, y)
                else:
                    adb_wrapper.tap(x, y)
                return
            except TypeError:
                adb_wrapper.tap(x, y)
                return
        if hasattr(adb_wrapper, "shell"):
            cmd = f"input tap {x} {y}"
            try:
                if target_serial is not None:
                    adb_wrapper.shell(target_serial, cmd)
                else:
                    adb_wrapper.shell(cmd)
            except TypeError:
                adb_wrapper.shell(target_serial or "default", cmd)

    def execute_installer_step(
        self,
        adb_wrapper: Any,
        auto_sleep: bool = True,
        prefer_done_over_open: bool = True,
        serial: Optional[str] = None,
        screen_width: Optional[int] = None,
        screen_height: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Dump XML from adb_wrapper, run analyze_installer_hierarchy, tick unchecked
        risk checkbox first, wait if countdown > 0 (capped at 10s), and click the
        highest-scoring safe confirm/expander/completion button.
        """
        w = screen_width or self.default_width
        h = screen_height or self.default_height

        xml_str = self._dump_xml_from_adb(adb_wrapper, serial=serial)
        plan = self.analyze_installer_hierarchy(
            xml_str,
            screen_width=w,
            screen_height=h,
            prefer_done_over_open=prefer_done_over_open,
        )

        actions_taken: List[Dict[str, Any]] = []
        waited_seconds = 0.0

        # 1. Tick unchecked risk checkbox first
        if plan["checkbox_to_tick"] is not None:
            cb = plan["checkbox_to_tick"]
            self._tap_via_adb(adb_wrapper, cb["center_x"], cb["center_y"], serial=serial)
            actions_taken.append(
                {
                    "type": "tick_checkbox",
                    "center_x": cb["center_x"],
                    "center_y": cb["center_y"],
                    "text": cb["text"],
                    "resource_id": cb["resource_id"],
                }
            )
            if auto_sleep:
                time.sleep(0.35)

        # 2. Wait if countdown > 0 (capped at 10s)
        if plan["countdown_seconds"] > 0:
            wait_sec = min(int(plan["countdown_seconds"]), 10)
            waited_seconds = float(wait_sec)
            if auto_sleep and wait_sec > 0:
                time.sleep(wait_sec + 0.2)

        # 3. Click the highest-scoring safe confirm / expander / completion button
        btn = plan.get("action_button")
        if btn is not None:
            # Avoid double-tapping the exact same coordinates if action_button was just the checkbox itself
            already_tapped_same_cb = (
                plan["checkbox_to_tick"] is not None
                and btn["center_x"] == plan["checkbox_to_tick"]["center_x"]
                and btn["center_y"] == plan["checkbox_to_tick"]["center_y"]
            )
            if not already_tapped_same_cb:
                self._tap_via_adb(adb_wrapper, btn["center_x"], btn["center_y"], serial=serial)
                actions_taken.append(
                    {
                        "type": "click_button",
                        "center_x": btn["center_x"],
                        "center_y": btn["center_y"],
                        "text": btn["text"],
                        "resource_id": btn["resource_id"],
                        "score": btn.get("score", 0),
                    }
                )

        return {
            "stage": plan["stage"],
            "checkbox_to_tick": plan["checkbox_to_tick"],
            "countdown_seconds": plan["countdown_seconds"],
            "waited_seconds": waited_seconds,
            "action_button": plan["action_button"],
            "traps_filtered": plan["traps_filtered"],
            "actions_taken": actions_taken,
        }
