"""
Cross-App Notetaker Subagent (Subagent #13)
Inspired by Mobile-Agent-E & Google DeepMind AndroidWorld.
Bridges multi-app workflows by capturing, persisting, and resolving cross-app state
such as 6-digit OTP codes, Order/Transaction IDs, Deep Links/URLs, Currency/Price totals,
system notifications, and clipboard contents across apps and devices.
"""

import json
import os
import re
import sys
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
NOTES_FILE = CONFIG_DIR / "cross_app_notes.json"

OTP_REGEX = re.compile(r"\b\d{6}\b")
ORDER_ID_REGEX = re.compile(r"(?:ORD|TXN|INV|ID)[-_#]?[A-Z0-9]{4,12}")
URL_REGEX = re.compile(r'https?://[^\s"<>]+|[a-z0-9_]+://[^\s"<>]+')
PRICE_REGEX = re.compile(r"(?:\$|₫|VND|USD)\s?[\d,.]+|[\d,.]+\s?(?:VND|₫|USD)")
TEMPLATE_PATTERN = re.compile(r"\$\{NOTE:([a-zA-Z0-9_.-]+)\}|\$NOTE:([a-zA-Z0-9_.-]+)")


class CrossAppNotetakerSubagent:
    """
    Subagent #13: Captures and resolves structured cross-app notes (OTP, Order IDs,
    URLs, Prices, Clipboard, and Notifications) for seamless multi-app task execution.
    """

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
        notes_file: Optional[Path] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.notes_file = notes_file or NOTES_FILE
        self._lock = threading.Lock()
        self.notes_ledger: Dict[str, Dict[str, Any]] = {}
        self._load_persisted_notes()

    def _load_persisted_notes(self) -> None:
        """Load previously persisted cross-app notes if available."""
        with self._lock:
            if not self.notes_file.exists():
                return
            try:
                with open(self.notes_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    notes = data.get("notes", data)
                    if isinstance(notes, dict):
                        for k, v in notes.items():
                            if isinstance(v, dict) and "value" in v:
                                self.notes_ledger[str(k)] = v
            except Exception as e:
                print(f"[CrossAppNotetakerSubagent] Warning loading notes: {e}", file=sys.stderr)

    def _persist_notes(self) -> None:
        """Atomically persist the current notes ledger to config/cross_app_notes.json."""
        with self._lock:
            self.notes_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "count": len(self.notes_ledger),
                "notes": self.notes_ledger,
            }
            tmp_path = self.notes_file.with_suffix(".tmp")
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                if tmp_path.exists():
                    os.replace(tmp_path, self.notes_file)
            except Exception as e:
                print(f"[CrossAppNotetakerSubagent] Error persisting notes: {e}", file=sys.stderr)

    def record_note(
        self,
        key: str,
        value: str,
        source_app: str = "unknown",
        serial: str = "global",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Store a structured cross-app note in self.notes_ledger[key] and persist
        to config/cross_app_notes.json.
        """
        entry: Dict[str, Any] = {
            "key": key,
            "value": str(value),
            "source_app": source_app,
            "serial": serial,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "metadata": metadata or {},
        }
        with self._lock:
            self.notes_ledger[key] = entry
        self._persist_notes()

        return dict(entry)

    def get_note(self, key: str, default: str = "") -> str:
        """Return the stored note value for key or default."""
        with self._lock:
            entry = self.notes_ledger.get(key)
            if not entry:
                return default
            return str(entry.get("value", default))

    def get_all_notes(self) -> Dict[str, Dict[str, Any]]:
        """Return a shallow copy of self.notes_ledger."""
        with self._lock:
            return {k: dict(v) for k, v in self.notes_ledger.items()}

    def _collect_text_candidates(self, xml_content: str) -> List[str]:
        """Extract text and content-desc candidates from UIAutomator XML hierarchy."""
        if not xml_content:
            return []

        candidates: List[str] = []
        elements = self.adb.parse_ui_elements(xml_content)
        if elements:
            for el in elements:
                txt = (el.get("text") or "").strip()
                desc = (el.get("content_desc") or "").strip()
                if txt:
                    candidates.append(txt)
                if desc and desc != txt:
                    candidates.append(desc)
            return candidates

        # Fallback XML attribute extraction if parse_ui_elements returned empty
        try:
            root = ET.fromstring(xml_content)
            for node in root.iter("node"):
                txt = (node.attrib.get("text") or "").strip()
                desc = (node.attrib.get("content-desc") or "").strip()
                if txt:
                    candidates.append(txt)
                if desc and desc != txt:
                    candidates.append(desc)
        except Exception:
            # Regex fallback over raw XML attributes
            for m in re.finditer(r'(?:text|content-desc)="([^"]+)"', xml_content):
                val = m.group(1).strip()
                if val:
                    candidates.append(val)

        return candidates

    def extract_notes_from_screen(self, serial: str, source_app: str = "unknown") -> Dict[str, Any]:
        """
        Dump UI hierarchy via self.adb.dump_ui_hierarchy(serial), parse text/content-desc
        attributes, and automatically extract OTP codes, Order IDs, URLs, and Price totals.
        """
        xml_content = self.adb.dump_ui_hierarchy(serial)
        candidates = self._collect_text_candidates(xml_content)
        combined_text = "\n".join(candidates)

        extracted: Dict[str, str] = {}

        # 1. 6-digit OTP codes (\b\d{6}\b) -> "otp_code"
        otp_match = OTP_REGEX.search(combined_text)
        if otp_match:
            val = otp_match.group(0).strip()
            self.record_note(
                key="otp_code",
                value=val,
                source_app=source_app,
                serial=serial,
                metadata={"extractor": "screen_ui", "pattern": "otp_6_digit"},
            )
            extracted["otp_code"] = val

        # 2. Order/Transaction IDs ((?:ORD|TXN|INV|ID)[-_#]?[A-Z0-9]{4,12}) -> "order_id"
        order_match = ORDER_ID_REGEX.search(combined_text)
        if order_match:
            val = order_match.group(0).strip()
            self.record_note(
                key="order_id",
                value=val,
                source_app=source_app,
                serial=serial,
                metadata={"extractor": "screen_ui", "pattern": "order_txn_id"},
            )
            extracted["order_id"] = val

        # 3. Deep links / URLs (https?://[^\s"<>]+|[a-z0-9_]+://[^\s"<>]+) -> "extracted_url"
        url_match = URL_REGEX.search(combined_text)
        if url_match:
            val = url_match.group(0).strip()
            self.record_note(
                key="extracted_url",
                value=val,
                source_app=source_app,
                serial=serial,
                metadata={"extractor": "screen_ui", "pattern": "url_or_deeplink"},
            )
            extracted["extracted_url"] = val

        # 4. Currency / Price totals ((?:\$|₫|VND|USD)\s?[\d,.]+|[\d,.]+\s?(?:VND|₫|USD)) -> "price_amount"
        price_match = PRICE_REGEX.search(combined_text)
        if price_match:
            val = price_match.group(0).strip()
            self.record_note(
                key="price_amount",
                value=val,
                source_app=source_app,
                serial=serial,
                metadata={"extractor": "screen_ui", "pattern": "currency_price"},
            )
            extracted["price_amount"] = val

        return {
            "serial": serial,
            "source_app": source_app,
            "extracted_count": len(extracted),
            "extracted": extracted,
            "ledger_size": len(self.notes_ledger),
        }

    def extract_from_notifications_and_clipboard(self, serial: str) -> Dict[str, Any]:
        """
        Inspect adb shell 'cmd clipboard get-text' and 'dumpsys notification --noredact'
        for 6-digit OTPs or URLs, store them in self.notes_ledger, and return extracted items.
        """
        clipboard_raw = self.adb.shell(serial, "cmd clipboard get-text") or ""
        notif_raw = self.adb.shell(serial, "dumpsys notification --noredact") or ""

        extracted: Dict[str, Any] = {}

        sources = [
            ("clipboard", clipboard_raw),
            ("notification", notif_raw),
        ]

        for source_name, raw_text in sources:
            if not raw_text or raw_text.startswith("ERROR:"):
                continue

            otp_match = OTP_REGEX.search(raw_text)
            if otp_match:
                otp_val = otp_match.group(0).strip()
                self.record_note(
                    key="otp_code",
                    value=otp_val,
                    source_app=source_name,
                    serial=serial,
                    metadata={"extractor": source_name, "pattern": "otp_6_digit"},
                )
                extracted["otp_code"] = otp_val
                extracted[f"{source_name}_otp"] = otp_val

            url_match = URL_REGEX.search(raw_text)
            if url_match:
                url_val = url_match.group(0).strip()
                self.record_note(
                    key="extracted_url",
                    value=url_val,
                    source_app=source_name,
                    serial=serial,
                    metadata={"extractor": source_name, "pattern": "url_or_deeplink"},
                )
                extracted["extracted_url"] = url_val
                extracted[f"{source_name}_url"] = url_val

        return {
            "serial": serial,
            "extracted_count": len(extracted),
            "extracted": extracted,
            "ledger_size": len(self.notes_ledger),
        }

    def resolve_template(self, template_text: str) -> str:
        """
        Replace placeholders like $NOTE:otp_code or ${NOTE:order_id} with actual
        values from self.notes_ledger. Unresolved placeholders remain intact.
        """
        if not template_text or "$NOTE:" not in template_text and "${NOTE:" not in template_text:
            return template_text

        def _replacer(match: re.Match) -> str:
            note_key = match.group(1) or match.group(2)
            with self._lock:
                if note_key in self.notes_ledger:
                    return str(self.notes_ledger[note_key].get("value", ""))
            return match.group(0)

        return TEMPLATE_PATTERN.sub(_replacer, template_text)


if __name__ == "__main__":
    notetaker = CrossAppNotetakerSubagent()
    print(f"CrossAppNotetakerSubagent initialized with {len(notetaker.get_all_notes())} notes.")
