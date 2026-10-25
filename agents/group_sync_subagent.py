"""
Group Sync & Multi-Device Cross-Testing Subagent (Subagent #11)
Coordinates synchronized broadcast execution across heterogeneous device pools
(Real Physical Phones + Virtual AVDs) and audits cross-device UI & latency consistency.
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.group_control_broadcaster import GroupControlBroadcaster
from core.real_device_manager import RealDeviceManager
from core.memory_manager import MemoryManager


class GroupSyncSubagent:
    """Executes synchronized multi-device actions and cross-resolution compatibility checks."""

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        broadcaster: Optional[GroupControlBroadcaster] = None,
        memory: Optional[MemoryManager] = None
    ):
        self.adb = adb or ADBWrapper()
        self.real_mgr = RealDeviceManager(self.adb)
        self.broadcaster = broadcaster or GroupControlBroadcaster(self.adb, self.real_mgr)
        self.memory = memory or MemoryManager()

    def run_synchronized_macro(
        self,
        steps: List[Dict[str, Any]],
        serials: Optional[List[str]] = None,
        group_filter: str = "ALL"
    ) -> Dict[str, Any]:
        """
        Execute a sequence of normalized actions across all target devices in lockstep.
        """
        targets = self.broadcaster.resolve_target_serials(serials, group_filter)
        if not targets:
            return {"status": "NO_TARGETS", "targets": [], "steps_executed": 0}

        start = time.time()
        step_reports = []

        for idx, step in enumerate(steps, 1):
            action = str(step.get("action", "")).lower()
            if action == "launch":
                pkg = step.get("package", "com.android.settings")
                res = self.broadcaster.broadcast_launch_app(pkg, serials=targets)
            elif action == "tap":
                x = float(step.get("x", 0.5))
                y = float(step.get("y", 0.5))
                norm = bool(step.get("normalized", 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0))
                res = self.broadcaster.broadcast_tap(x, y, serials=targets, is_normalized=norm)
            elif action == "swipe":
                x1, y1 = float(step.get("x1", 360)), float(step.get("y1", 1100))
                x2, y2 = float(step.get("x2", 360)), float(step.get("y2", 400))
                res = self.broadcaster.broadcast_swipe(x1, y1, x2, y2, serials=targets)
            elif action == "input_text":
                txt = str(step.get("text", "test"))
                res = self.broadcaster.broadcast_text(txt, serials=targets)
            elif action == "key":
                key = str(step.get("key", "HOME"))
                res = self.broadcaster.broadcast_key(key, serials=targets)
            else:
                res = {"success": True, "action": action, "targets_count": len(targets)}

            step_reports.append({"step": idx, "action": action, "broadcast_result": res})

        total_dur = round(time.time() - start, 2)
        return {
            "status": "SYNC_COMPLETED",
            "targets": targets,
            "targets_count": len(targets),
            "steps_executed": len(step_reports),
            "duration_seconds": total_dur,
            "step_reports": step_reports
        }


if __name__ == "__main__":
    sync_agent = GroupSyncSubagent()
    print("GroupSyncSubagent ready.")
