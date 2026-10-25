"""
Codebase & Agent Memory Manager
Persistent storage and knowledge retrieval for multi-agent testing and continuous self-improvement.
Supports:
- UI Locators and Screen Signatures
- Known Defects and Root Causes
- Git-compatible Code Patches
- Self-Optimized System and Task Prompts
- Tag-based Semantic Recall
"""

import json
import os
import sys
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
MEMORY_FILE = CONFIG_DIR / "codebase_memory.json"


class MemoryManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(MemoryManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, memory_file: Optional[Path] = None):
        if getattr(self, "_initialized", False):
            if memory_file is not None:
                self.memory_file = Path(memory_file)
                self._ensure_memory_file()
            return
        self.memory_file = Path(memory_file) if memory_file else MEMORY_FILE
        self._rw_lock = threading.Lock()
        self._ensure_memory_file()
        self._initialized = True

    def _ensure_memory_file(self):
        """Create empty memory store if not present."""
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.memory_file.exists():
            default_data = {
                "version": "3.0",
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "locators": {},        # screen_signature -> list of locators
                "defects": [],         # list of tracked defects
                "patches": [],         # list of generated git patches
                "prompts": {},         # agent_type -> list of optimized prompts
                "macros": {},          # goal_signature -> macro action shortcut (Mobile-Agent-E)
                "evolution_history": [], # self-evolution cycle logs
                "knowledge_items": []  # general memories with tags
            }
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(default_data, f, indent=2, ensure_ascii=False)

    def _read_data(self) -> Dict[str, Any]:
        """Read data safely with lock."""
        with self._rw_lock:
            try:
                if self.memory_file.exists():
                    with open(self.memory_file, "r", encoding="utf-8") as f:
                        return json.load(f)
            except Exception as e:
                print(f"[MemoryManager] Error reading memory: {e}", file=sys.stderr)
            return {
                "version": "1.0",
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                "locators": {},
                "defects": [],
                "patches": [],
                "prompts": {},
                "knowledge_items": []
            }

    def _write_data(self, data: Dict[str, Any]):
        """Write data atomically."""
        with self._rw_lock:
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            data["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
            tmp_file = self.memory_file.with_suffix(".tmp")
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                if tmp_file.exists():
                    os.replace(tmp_file, self.memory_file)
            except Exception as e:
                print(f"[MemoryManager] Error writing memory: {e}", file=sys.stderr)

    # -------------------------------------------------------------
    # General Memory Operations: Remember & Recall
    # -------------------------------------------------------------
    def remember(
        self,
        key: str,
        value: Any,
        tags: Optional[List[str]] = None,
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store a general knowledge item."""
        data = self._read_data()
        item = {
            "id": f"mem_{int(time.time() * 1000)}",
            "key": key,
            "value": value,
            "category": category,
            "tags": tags or [],
            "metadata": metadata or {},
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        # Replace if same key exists in category
        existing = [i for i in data.get("knowledge_items", []) if not (i.get("key") == key and i.get("category") == category)]
        existing.append(item)
        data["knowledge_items"] = existing
        self._write_data(data)
        return item

    def recall(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve items matching category, tags, or text query."""
        data = self._read_data()
        items = data.get("knowledge_items", [])
        results = []

        for item in items:
            # Check category
            if category and item.get("category") != category:
                continue

            # Check tags
            if tags:
                item_tags = set(item.get("tags", []))
                if not any(t in item_tags for t in tags):
                    continue

            # Check text query
            if query:
                q_lower = query.lower()
                key_match = q_lower in str(item.get("key", "")).lower()
                val_match = q_lower in str(item.get("value", "")).lower()
                tag_match = any(q_lower in str(t).lower() for t in item.get("tags", []))
                if not (key_match or val_match or tag_match):
                    continue

            results.append(item)
        return results

    # -------------------------------------------------------------
    # UI Locators Memory
    # -------------------------------------------------------------
    def save_locator(
        self,
        screen_signature: str,
        element_role: str,
        dynamic_locator: Dict[str, str],
        coordinates: Optional[List[int]] = None,
        confidence: float = 1.0,
        notes: str = ""
    ):
        """Save a verified UI locator for rapid zero-latency retrieval."""
        data = self._read_data()
        locators = data.setdefault("locators", {})
        screen_entries = locators.setdefault(screen_signature, [])

        # Remove existing locator for same role
        screen_entries = [e for e in screen_entries if e.get("element_role") != element_role]
        screen_entries.append({
            "element_role": element_role,
            "locator": dynamic_locator,
            "coordinates": coordinates or [0, 0],
            "confidence": confidence,
            "notes": notes,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        locators[screen_signature] = screen_entries
        self._write_data(data)

    def get_locators_for_screen(self, screen_signature: str) -> List[Dict[str, Any]]:
        """Retrieve all known verified locators for a given screen."""
        data = self._read_data()
        return data.get("locators", {}).get(screen_signature, [])

    # -------------------------------------------------------------
    # Defects & Bug Tracking
    # -------------------------------------------------------------
    def record_defect(
        self,
        defect_type: str,
        title: str,
        serial: str,
        severity: str = "HIGH",
        stack_trace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record a defect detected by the Auditor subagent."""
        data = self._read_data()
        defect_id = f"DEFECT_{int(time.time())}"
        entry = {
            "defect_id": defect_id,
            "defect_type": defect_type,
            "title": title,
            "serial": serial,
            "severity": severity,
            "status": "OPEN",
            "stack_trace": stack_trace or "",
            "context": context or {},
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        data.setdefault("defects", []).append(entry)
        self._write_data(data)
        return entry

    def update_defect_status(self, defect_id: str, status: str, resolution_notes: str = ""):
        """Mark defect as RESOLVED, PATCHED, or VERIFIED."""
        data = self._read_data()
        for d in data.get("defects", []):
            if d.get("defect_id") == defect_id:
                d["status"] = status
                d["resolution_notes"] = resolution_notes
                d["resolved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                break
        self._write_data(data)

    # -------------------------------------------------------------
    # Code Patches & Diffs
    # -------------------------------------------------------------
    def record_patch(
        self,
        defect_id: str,
        target_file: str,
        diff_content: str,
        explanation: str,
        verified: bool = False
    ) -> Dict[str, Any]:
        """Record an auto-generated unified patch."""
        data = self._read_data()
        patch_id = f"PATCH_{int(time.time())}"
        entry = {
            "patch_id": patch_id,
            "defect_id": defect_id,
            "target_file": target_file,
            "diff_content": diff_content,
            "explanation": explanation,
            "verified": verified,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        data.setdefault("patches", []).append(entry)
        self._write_data(data)
        return entry

    def get_patches(self, verified_only: bool = False) -> List[Dict[str, Any]]:
        """List generated patches."""
        data = self._read_data()
        patches = data.get("patches", [])
        if verified_only:
            return [p for p in patches if p.get("verified")]
        return patches

    # -------------------------------------------------------------
    # Prompt Iterations & Self-Optimized Prompts
    # -------------------------------------------------------------
    def record_prompt_iteration(
        self,
        agent_type: str,
        prompt_text: str,
        rationale: str,
        version: Optional[str] = None,
        success_rate: float = 1.0
    ) -> Dict[str, Any]:
        """Save a newly synthesized, self-optimized prompt."""
        data = self._read_data()
        prompts = data.setdefault("prompts", {})
        agent_prompts = prompts.setdefault(agent_type, [])

        ver = version or f"v{len(agent_prompts) + 1}.0"
        entry = {
            "version": ver,
            "prompt": prompt_text,
            "rationale": rationale,
            "success_rate": success_rate,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        agent_prompts.append(entry)
        self._write_data(data)
        return entry

    def get_latest_prompt(self, agent_type: str, default_prompt: str = "") -> str:
        """Get the latest self-optimized prompt for an agent type."""
        data = self._read_data()
        agent_prompts = data.get("prompts", {}).get(agent_type, [])
        if agent_prompts:
            return agent_prompts[-1].get("prompt", default_prompt)
        return default_prompt

    # -------------------------------------------------------------
    # Macro-Actions & Self-Evolution History (Mobile-Agent-E)
    # -------------------------------------------------------------
    def save_macro_shortcut(
        self,
        goal_signature: str,
        package_name: str,
        steps: List[Dict[str, Any]],
        avg_duration_s: float = 1.0,
        success_count: int = 1
    ) -> Dict[str, Any]:
        """Store an extracted macro-action trajectory shortcut for rapid future replay."""
        data = self._read_data()
        macros = data.setdefault("macros", {})
        existing = macros.get(goal_signature, {})
        total_runs = existing.get("success_count", 0) + success_count
        entry = {
            "goal_signature": goal_signature,
            "package_name": package_name,
            "steps": steps,
            "steps_count": len(steps),
            "avg_duration_s": round(avg_duration_s, 2),
            "success_count": total_runs,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        macros[goal_signature] = entry
        self._write_data(data)
        return entry

    def get_macro_shortcut(self, goal_signature: str) -> Optional[Dict[str, Any]]:
        """Retrieve a verified macro shortcut if available."""
        data = self._read_data()
        return data.get("macros", {}).get(goal_signature)

    def list_macros(self) -> List[Dict[str, Any]]:
        """Return all stored macro shortcuts."""
        data = self._read_data()
        return list(data.get("macros", {}).values())

    def record_evolution_cycle(self, cycle_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Record an autonomous self-evolution cycle summary."""
        data = self._read_data()
        history = data.setdefault("evolution_history", [])
        entry = {
            "cycle_id": f"EVO_{int(time.time() * 1000)}",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            **cycle_summary
        }
        history.append(entry)
        data["evolution_history"] = history[-50:]  # Keep latest 50 evolution cycles
        self._write_data(data)
        return entry

    # -------------------------------------------------------------
    # Analytics & Summary
    # -------------------------------------------------------------
    def get_summary(self) -> Dict[str, Any]:
        """Return memory statistics."""
        data = self._read_data()
        return {
            "version": data.get("version", "3.0"),
            "last_updated": data.get("last_updated"),
            "locators_count": sum(len(v) for v in data.get("locators", {}).values()),
            "screen_count": len(data.get("locators", {})),
            "defects_count": len(data.get("defects", [])),
            "open_defects": len([d for d in data.get("defects", []) if d.get("status") == "OPEN"]),
            "patches_count": len(data.get("patches", [])),
            "prompts_count": sum(len(v) for v in data.get("prompts", {}).values()),
            "macros_count": len(data.get("macros", {})),
            "evolution_cycles_count": len(data.get("evolution_history", [])),
            "knowledge_items_count": len(data.get("knowledge_items", []))
        }


if __name__ == "__main__":
    mm = MemoryManager()
    mm.remember("system_status", "Running with 4 headless devices", tags=["setup", "hardware"])
    print("Memory Summary:", mm.get_summary())
