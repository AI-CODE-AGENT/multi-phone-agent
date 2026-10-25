"""
Kanban Task Board & State Management Engine
Enables autonomous multi-agent pipeline coordination, tracking test/dev lifecycle:
BACKLOG -> PLANNING -> DEV_IN_PROGRESS -> QA_VERIFYING -> HEALING -> PATCHED -> REGRESSION_PASSED -> DONE
"""

import json
import os
import sys
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
KANBAN_STORE_FILE = CONFIG_DIR / "kanban_store.json"

VALID_STATES = [
    "BACKLOG",
    "PLANNING",
    "DEV_IN_PROGRESS",
    "QA_VERIFYING",
    "HEALING",
    "PATCHED",
    "REGRESSION_PASSED",
    "DONE",
    "BLOCKED"
]


class KanbanBoard:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(KanbanBoard, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, store_file: Optional[Path] = None):
        if getattr(self, "_initialized", False):
            return
        self.store_file = store_file or KANBAN_STORE_FILE
        self._rw_lock = threading.Lock()
        self._ensure_store_file()
        self._initialized = True

    def _ensure_store_file(self):
        self.store_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_file.exists():
            default_data = {
                "version": "2.0",
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "cards": []
            }
            with open(self.store_file, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)

    def _read_data(self) -> Dict[str, Any]:
        with self._rw_lock:
            try:
                if self.store_file.exists():
                    with open(self.store_file, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception as e:
                print(f"[KanbanBoard] Error reading store: {e}", file=sys.stderr)
            return {"version": "2.0", "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"), "cards": []}

    def _write_data(self, data: Dict[str, Any]):
        with self._rw_lock:
            data["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            tmp_file = self.store_file.with_suffix(".tmp")
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                if tmp_file.exists():
                    os.replace(tmp_file, self.store_file)
            except Exception as e:
                print(f"[KanbanBoard] Error writing store: {e}", file=sys.stderr)

    def create_card(
        self,
        title: str,
        goal: str,
        target_device: str = "emulator-5554",
        assigned_subagent: str = "PlannerSubagent",
        priority: str = "HIGH"
    ) -> Dict[str, Any]:
        """Create a new task card on the board."""
        data = self._read_data()
        card_id = f"TASK_{int(time.time() * 1000) % 1000000:06d}"
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        card = {
            "card_id": card_id,
            "title": title,
            "goal": goal,
            "target_device": target_device,
            "assigned_subagent": assigned_subagent,
            "state": "BACKLOG",
            "priority": priority,
            "created_at": now_str,
            "updated_at": now_str,
            "retries": 0,
            "history": [
                {
                    "from_state": None,
                    "to_state": "BACKLOG",
                    "actor": "System",
                    "note": "Card created",
                    "timestamp": now_str
                }
            ],
            "artifacts": {}
        }
        data.setdefault("cards", []).append(card)
        self._write_data(data)
        return card

    def transition_state(
        self,
        card_id: str,
        new_state: str,
        actor: str = "System",
        note: str = ""
    ) -> bool:
        """Move a card to a new state and record transition history."""
        if new_state not in VALID_STATES:
            print(f"[KanbanBoard] Invalid state: {new_state}", file=sys.stderr)
            return False

        data = self._read_data()
        found = False
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        for card in data.get("cards", []):
            if card.get("card_id") == card_id:
                old_state = card.get("state")
                card["state"] = new_state
                card["updated_at"] = now_str
                card.setdefault("history", []).append({
                    "from_state": old_state,
                    "to_state": new_state,
                    "actor": actor,
                    "note": note,
                    "timestamp": now_str
                })
                if new_state == "HEALING":
                    card["retries"] = card.get("retries", 0) + 1
                found = True
                break

        if found:
            self._write_data(data)
        return found

    def add_artifact(self, card_id: str, artifact_type: str, artifact_path: str) -> bool:
        """Attach a deliverable (report, patch, screenshot) to a card."""
        data = self._read_data()
        found = False
        for card in data.get("cards", []):
            if card.get("card_id") == card_id:
                card.setdefault("artifacts", {})[artifact_type] = str(artifact_path)
                card["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                found = True
                break
        if found:
            self._write_data(data)
        return found

    def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single card by ID."""
        data = self._read_data()
        for card in data.get("cards", []):
            if card.get("card_id") == card_id:
                return card
        return None

    def list_cards(
        self,
        state: Optional[str] = None,
        device: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List cards filtered by state or device."""
        data = self._read_data()
        cards = data.get("cards", [])
        if state:
            cards = [c for c in cards if c.get("state") == state]
        if device:
            cards = [c for c in cards if c.get("target_device") == device]
        return cards

    def get_board_summary(self) -> Dict[str, Any]:
        """Get aggregate counts per state."""
        data = self._read_data()
        cards = data.get("cards", [])
        summary: Dict[str, int] = {st: 0 for st in VALID_STATES}
        for c in cards:
            st = c.get("state", "BACKLOG")
            summary[st] = summary.get(st, 0) + 1
        return {
            "total_cards": len(cards),
            "columns": summary,
            "last_updated": data.get("last_updated")
        }


if __name__ == "__main__":
    kb = KanbanBoard()
    c = kb.create_card("Login Flow Test", "Verify customer login with 0941189263")
    print("Created card:", c["card_id"])
    kb.transition_state(c["card_id"], "PLANNING", actor="PlannerSubagent")
    print("Board Summary:", kb.get_board_summary())
