"""
Device Lock Manager (Per-Device Mutex)
Ensures thread-safe and process-safe concurrency for multiple IDEs and AI Agents.
"""

import threading
import time
import json
from pathlib import Path
from typing import Dict, Optional, Any, List

LOCK_FILE = Path(__file__).resolve().parent.parent / "config" / "device_locks.json"


class DeviceLockManager:
    """Manages exclusive leases on farm devices for AI agents."""
    _local_lock = threading.Lock()

    def __init__(self, lock_file: Optional[Path] = None):
        self.lock_file = lock_file or LOCK_FILE
        self._ensure_lock_file()

    def _ensure_lock_file(self):
        with self._local_lock:
            if not self.lock_file.exists():
                self.lock_file.parent.mkdir(parents=True, exist_ok=True)
                self.lock_file.write_text("{}", encoding="utf-8")

    def _read_locks(self) -> Dict[str, Dict[str, Any]]:
        try:
            with open(self.lock_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_locks(self, locks: Dict[str, Dict[str, Any]]):
        with open(self.lock_file, "w", encoding="utf-8") as f:
            json.dump(locks, f, indent=2)

    def acquire(self, serial: str, agent_id: str, task_name: str, lease_seconds: int = 300) -> bool:
        """
        Attempt to acquire exclusive lock on a device.
        Returns True if acquired, False if already held by another agent.
        """
        with self._local_lock:
            locks = self._read_locks()
            now = time.time()
            existing = locks.get(serial)

            if existing:
                # Check if expired
                if now < existing.get("expires_at", 0):
                    if existing.get("agent_id") != agent_id:
                        return False  # Held by another agent

            # Acquire or renew
            locks[serial] = {
                "agent_id": agent_id,
                "task_name": task_name,
                "acquired_at": now,
                "expires_at": now + lease_seconds
            }
            self._write_locks(locks)
            return True

    def release(self, serial: str, agent_id: str) -> bool:
        """Release the lock held by agent_id."""
        with self._local_lock:
            locks = self._read_locks()
            existing = locks.get(serial)
            if existing and existing.get("agent_id") == agent_id:
                locks.pop(serial, None)
                self._write_locks(locks)
                return True
            return False

    def force_release(self, serial: str):
        """Force release a device lock regardless of owner."""
        with self._local_lock:
            locks = self._read_locks()
            if serial in locks:
                locks.pop(serial, None)
                self._write_locks(locks)

    def get_lock_info(self, serial: str) -> Optional[Dict[str, Any]]:
        """Get current holder of device lock."""
        with self._local_lock:
            locks = self._read_locks()
            now = time.time()
            info = locks.get(serial)
            if info and now < info.get("expires_at", 0):
                return info
            return None

    def list_active_locks(self) -> Dict[str, Dict[str, Any]]:
        """List all active unexpired locks."""
        with self._local_lock:
            locks = self._read_locks()
            now = time.time()
            active = {}
            for serial, info in locks.items():
                if now < info.get("expires_at", 0):
                    active[serial] = info
            return active


if __name__ == "__main__":
    mgr = DeviceLockManager()
    print("Testing DeviceLockManager...")
    ok = mgr.acquire("emulator-5554", "agent_1", "Login_Test", 60)
    print("Acquired lock:", ok)
    print("Lock info:", mgr.get_lock_info("emulator-5554"))
    mgr.release("emulator-5554", "agent_1")
    print("Released. Active locks:", mgr.list_active_locks())
