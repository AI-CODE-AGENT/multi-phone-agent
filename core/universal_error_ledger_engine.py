"""
AMAF v20.0 — Universal Cross-Project Error Ledger, Auto-Reflexion Guard & MCP Oneshot Probe Engine.

Maintains a shared cross-project error database at:
- Global: D:/Project/universal_error_ledger.jsonl & D:/Project/UNIVERSAL_ENGINEERING_ERROR_PLAYBOOK.md
- Repo-Local: config/universal_error_ledger.jsonl & docs/UNIVERSAL_ERROR_PLAYBOOK.md

Also provides `probe_mcp_stdio_server()` which safely tests any stdio MCP server (Python, Node.js, `npx tsx`)
by piping a JSON-RPC `initialize` request and immediately closing `stdin` (EOF) with a strict timeout,
permanently eliminating the 'Status: RUNNING / No log output recorded yet' hang.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GLOBAL_LEDGER_JSONL = Path(r"D:\Project\universal_error_ledger.jsonl")
GLOBAL_PLAYBOOK_MD = Path(r"D:\Project\UNIVERSAL_ENGINEERING_ERROR_PLAYBOOK.md")
LOCAL_LEDGER_JSONL = PROJECT_ROOT / "config" / "universal_error_ledger.jsonl"
LOCAL_PLAYBOOK_MD = PROJECT_ROOT / "docs" / "UNIVERSAL_ERROR_PLAYBOOK.md"

_DETERMINISTIC_RULES = [
    (
        "ERR-001",
        re.compile(r"(no log output recorded yet|npx\s+tsx|stdio.*hang|status:\s*running)", re.I),
    ),
    (
        "ERR-002",
        re.compile(r"(mojibake|cp1252|utf-?8.*powershell|\?\s*light mode|tiếng việt.*\?)", re.I),
    ),
    (
        "ERR-003",
        re.compile(r"(filename or extension is too long|winerror 206|lpcommandline)", re.I),
    ),
    (
        "ERR-004",
        re.compile(r"(screen grab failed|imagegrab\.grab|bitblt.*failed)", re.I),
    ),
    (
        "ERR-005",
        re.compile(r"(ui.*freeze|main thread.*adb|get_connected_devices.*blocking|not responding)", re.I),
    ),
    (
        "ERR-006",
        re.compile(r"(localgpuvisionocrengine.*init|eager.*torch.*import|startup.*lag.*ocr)", re.I),
    ),
    (
        "ERR-007",
        re.compile(r"(n\+1.*getprop|sequential.*adb shell getprop)", re.I),
    ),
    (
        "ERR-008",
        re.compile(r"(pack.*side.*right.*clipped|header.*badge.*squeezed)", re.I),
    ),
    (
        "ERR-009",
        re.compile(r"(apply_theme.*all.*tabs|unconditional.*redraw|widget\.config.*loop)", re.I),
    ),
    (
        "ERR-010",
        re.compile(r"(bmp.*unicode|emoji.*tcl|broken.*icon|\*\s*view|\+\s*finger)", re.I),
    ),
    (
        "ERR-011",
        re.compile(r"(indentationerror|expected an indented block)", re.I),
    ),
    (
        "ERR-012",
        re.compile(r"(git status.*dirty.*pytest|test.*state.*pollution)", re.I),
    ),
]


class UniversalErrorLedgerEngine:
    """Singleton Cross-Project Error Ledger & Auto-Reflexion Guard Engine."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(UniversalErrorLedgerEngine, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, ledger_path: Optional[Path] = None):
        if getattr(self, "_initialized", False):
            return
        self._rw_lock = threading.Lock()
        self.local_ledger_path = Path(ledger_path) if ledger_path else LOCAL_LEDGER_JSONL
        self.global_ledger_path = GLOBAL_LEDGER_JSONL
        self._entries: List[Dict[str, Any]] = []
        self._load_ledger()
        self._initialized = True

    def _load_ledger(self) -> None:
        source = self.local_ledger_path if self.local_ledger_path.exists() else self.global_ledger_path
        if not source.exists():
            self._entries = []
            return
        entries: List[Dict[str, Any]] = []
        try:
            for line in source.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        except Exception:
            pass
        self._entries = entries

    def list_errors(self, category: Optional[str] = None, tech_stack: Optional[str] = None) -> List[Dict[str, Any]]:
        results = list(self._entries)
        if category:
            results = [e for e in results if category.lower() in str(e.get("category", "")).lower()]
        if tech_stack:
            results = [
                e for e in results
                if any(tech_stack.lower() in str(t).lower() for t in e.get("tech_stack", []))
            ]
        return results

    def diagnose_error(self, error_text: str, tech_stack: Optional[str] = None) -> Dict[str, Any]:
        """
        Deterministically match an error string, exception, or symptom against the cross-project error ledger.
        Returns the matched error entry along with actionable `golden_rule` and `verification_hook`.
        """
        if not self._entries:
            self._load_ledger()

        by_id = {e.get("error_id"): e for e in self._entries}
        for err_id, regex in _DETERMINISTIC_RULES:
            if regex.search(error_text or "") and err_id in by_id:
                matched = by_id[err_id]
                return {
                    "matched": True,
                    "confidence": 0.99,
                    "match_method": "deterministic_regex",
                    "entry": matched,
                    "recommended_action": matched.get("golden_rule"),
                    "verification_hook": matched.get("verification_hook"),
                }

        # Fallback token overlap scoring across symptom + root_cause + category
        q_tokens = set(re.findall(r"[a-zA-Z0-9_]{3,}", (error_text or "").lower()))
        best_entry = None
        best_score = 0.0
        for entry in self._entries:
            corpus = " ".join(
                [
                    str(entry.get("symptom", "")),
                    str(entry.get("root_cause", "")),
                    str(entry.get("category", "")),
                    " ".join(entry.get("tech_stack", [])),
                ]
            ).lower()
            c_tokens = set(re.findall(r"[a-zA-Z0-9_]{3,}", corpus))
            if not q_tokens or not c_tokens:
                continue
            overlap = len(q_tokens & c_tokens) / max(1, min(len(q_tokens), 8))
            if tech_stack and any(tech_stack.lower() in t.lower() for t in entry.get("tech_stack", [])):
                overlap += 0.15
            if overlap > best_score:
                best_score = overlap
                best_entry = entry

        if best_entry and best_score >= 0.2:
            return {
                "matched": True,
                "confidence": round(min(0.95, best_score), 3),
                "match_method": "keyword_similarity",
                "entry": best_entry,
                "recommended_action": best_entry.get("golden_rule"),
                "verification_hook": best_entry.get("verification_hook"),
            }

        fallback = self._entries[0] if self._entries else {}
        return {
            "matched": False,
            "confidence": 0.0,
            "match_method": "unmatched_new_pattern",
            "entry": fallback,
            "recommended_action": "Record this new failure pattern into universal_error_ledger.jsonl via register_error().",
            "verification_hook": "pytest -q",
        }

    def register_error(
        self,
        category: str,
        tech_stack: List[str],
        symptom: str,
        root_cause: str,
        golden_rule: str,
        verification_hook: str = "pytest -q",
        error_id: Optional[str] = None,
        persist_to_disk: bool = True,
    ) -> Dict[str, Any]:
        """
        Register a new engineering error lesson so it can be reused across any project.
        """
        with self._rw_lock:
            if not self._entries:
                self._load_ledger()
            for existing in self._entries:
                if existing.get("symptom", "").strip().lower() == symptom.strip().lower():
                    return {"status": "already_exists", "entry": existing}

            next_num = len(self._entries) + 1
            e_id = error_id or f"ERR-{next_num:03d}"
            new_entry = {
                "error_id": e_id,
                "category": category,
                "tech_stack": tech_stack,
                "symptom": symptom,
                "root_cause": root_cause,
                "golden_rule": golden_rule,
                "verification_hook": verification_hook,
            }
            self._entries.append(new_entry)

            if persist_to_disk:
                line = json.dumps(new_entry, ensure_ascii=False) + "\n"
                for target in (self.local_ledger_path, self.global_ledger_path):
                    try:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with open(target, "a", encoding="utf-8") as f:
                            f.write(line)
                    except Exception:
                        pass

                md_block = (
                    f"\n---\n\n### `{e_id}` — {symptom}\n"
                    f"- **Bối cảnh / Công nghệ**: {', '.join(tech_stack)}\n"
                    f"- **Triệu chứng (Symptom)**: {symptom}\n"
                    f"- **Nguyên nhân gốc (Root Cause)**: {root_cause}\n"
                    f"- **Quy tắc bắt buộc (Golden Rule)**: {golden_rule}\n"
                    f"- **Kiểm chứng (Verification Hook)**: `{verification_hook}`\n"
                )
                for md_target in (LOCAL_PLAYBOOK_MD, GLOBAL_PLAYBOOK_MD):
                    try:
                        if md_target.exists():
                            with open(md_target, "a", encoding="utf-8") as f:
                                f.write(md_block)
                    except Exception:
                        pass

            return {
                "status": "registered",
                "total_errors_in_ledger": len(self._entries),
                "global_ledger_path": str(self.global_ledger_path),
                "local_ledger_path": str(self.local_ledger_path),
                "entry": new_entry,
            }

    @staticmethod
    def probe_mcp_stdio_server(
        command: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        timeout_sec: float = 4.0,
    ) -> Dict[str, Any]:
        """
        Feature #3: Safe Oneshot JSON-RPC Probe for any stdio MCP Server (`python`, `node`, `npx tsx`).
        Pipes `initialize` + `tools/list` and immediately closes `stdin` (EOF) with a hard timeout,
        preventing the 'Status: RUNNING / No log output recorded yet' hang (`ERR-001`).
        """
        if not command:
            command = [sys.executable, "-u", str(PROJECT_ROOT / "mcp_bridge" / "android_farm_mcp_server.py")]

        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "amaf-v20-oneshot-probe", "version": "20.0.0"},
            },
        }
        payload = json.dumps(init_req) + "\n"
        env = dict(os.environ)
        env["PYTHONUNBUFFERED"] = "1"

        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                command,
                input=payload,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=cwd or str(PROJECT_ROOT),
                env=env,
                timeout=timeout_sec,
            )
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            stdout_lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
            parsed_json = None
            for ln in stdout_lines:
                if ln.startswith("{") and ln.endswith("}"):
                    try:
                        parsed_json = json.loads(ln)
                        break
                    except Exception:
                        pass

            return {
                "healthy": proc.returncode == 0 and parsed_json is not None,
                "status": "ONESHOT_PROBE_OK" if parsed_json is not None else "NO_JSONRPC_RESPONSE",
                "command": command,
                "returncode": proc.returncode,
                "duration_ms": elapsed_ms,
                "stdin_eof_closed": True,
                "hang_prevented": True,
                "jsonrpc_response": parsed_json,
                "stderr_preview": (proc.stderr or "").strip()[:300],
            }
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return {
                "healthy": False,
                "status": "TIMEOUT_INTERCEPTED_BY_GUARD",
                "command": command,
                "duration_ms": elapsed_ms,
                "stdin_eof_closed": True,
                "hang_prevented": True,
                "error_id": "ERR-001",
                "stderr_preview": str(exc.stderr or "")[:300],
            }
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            return {
                "healthy": False,
                "status": "PROBE_ERROR",
                "command": command,
                "duration_ms": elapsed_ms,
                "error": str(exc),
            }
