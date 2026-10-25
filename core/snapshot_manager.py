"""
Snapshot Manager for Android Farm
Creates, restores, and manages 'Golden Snapshots' for instant 2-second boot and zero disk wear.
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper


class SnapshotManager:
    def __init__(self, adb: Optional[ADBWrapper] = None):
        self.adb = adb or ADBWrapper()

    def save_snapshot(self, serial: str, snapshot_name: str = "golden_clean") -> Tuple[bool, str]:
        """
        Save current state of running emulator as a named snapshot.
        """
        code, out, err = self.adb.run_device_cmd(serial, ["emu", "avd", "snapshot", "save", snapshot_name], timeout=60)
        success = code == 0 and "KO" not in out
        return success, out or err

    def load_snapshot(self, serial: str, snapshot_name: str = "golden_clean") -> Tuple[bool, str]:
        """
        Load a named snapshot into running emulator.
        """
        code, out, err = self.adb.run_device_cmd(serial, ["emu", "avd", "snapshot", "load", snapshot_name], timeout=60)
        success = code == 0 and "KO" not in out
        return success, out or err

    def list_snapshots(self, serial: str) -> List[str]:
        """List available snapshots for device."""
        code, out, _ = self.adb.run_device_cmd(serial, ["emu", "avd", "snapshot", "list"], timeout=10)
        snapshots = []
        for line in out.splitlines():
            line = line.strip()
            if line and not line.startswith("OK") and not line.startswith("Android Console"):
                parts = line.split()
                if parts:
                    snapshots.append(parts[0])
        return snapshots

    def delete_snapshot(self, serial: str, snapshot_name: str) -> Tuple[bool, str]:
        """Delete a named snapshot."""
        code, out, err = self.adb.run_device_cmd(serial, ["emu", "avd", "snapshot", "delete", snapshot_name], timeout=15)
        success = code == 0 and "KO" not in out
        return success, out or err


if __name__ == "__main__":
    sm = SnapshotManager()
    print("SnapshotManager initialized.")
