"""
Scrcpy On-Demand Screen Viewer Manager
Lightweight screen streaming on demand without halting background headless instances.
"""

import subprocess
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.farm_config import find_scrcpy


class ScrcpyManager:
    def __init__(self, scrcpy_path: Optional[str] = None):
        self.scrcpy_path = scrcpy_path or find_scrcpy()
        self._active_sessions: Dict[str, subprocess.Popen] = {}

    def is_available(self) -> bool:
        """Check if scrcpy executable exists."""
        return os.path.exists(self.scrcpy_path) or self.scrcpy_path == "scrcpy"

    def open_viewer(
        self,
        serial: str,
        title: Optional[str] = None,
        max_size: int = 800,
        max_fps: int = 30,
        window_x: Optional[int] = None,
        window_y: Optional[int] = None,
        window_width: Optional[int] = None,
        window_height: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Open a lightweight scrcpy window for the specified device serial.
        Runs asynchronously in a separate process. Supports tiled window positioning.
        """
        if self.is_viewer_open(serial):
            return True, f"Viewer already open for {serial}"

        window_title = title or f"Farm Phone ({serial})"
        cmd = [
            self.scrcpy_path,
            "-s", serial,
            "--window-title", window_title,
            "--max-size", str(max_size),
            "--max-fps", str(max_fps),
            "-b", "2M",
            "--stay-awake"
        ]
        if window_x is not None:
            cmd.extend(["--window-x", str(window_x)])
        if window_y is not None:
            cmd.extend(["--window-y", str(window_y)])
        if window_width is not None:
            cmd.extend(["--window-width", str(window_width)])
        if window_height is not None:
            cmd.extend(["--window-height", str(window_height)])

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            self._active_sessions[serial] = proc
            return True, f"Scrcpy viewer launched for {serial} (PID: {proc.pid})"
        except Exception as e:
            return False, f"Failed to launch scrcpy: {e}"

    def open_multi_device_wall(
        self,
        serials: List[str],
        cols: int = 4,
        tile_width: int = 340,
        tile_height: int = 680,
        start_x: int = 40,
        start_y: int = 40,
        max_fps: int = 24
    ) -> Dict[str, Any]:
        """
        Open multiple scrcpy windows arranged neatly in a tiled grid wall on the desktop.
        Supports simultaneous viewing of real phones and headless emulators.
        """
        launched = []
        for idx, serial in enumerate(serials):
            row = idx // max(1, cols)
            col = idx % max(1, cols)
            wx = start_x + col * (tile_width + 12)
            wy = start_y + row * (tile_height + 36)
            ok, msg = self.open_viewer(
                serial=serial,
                title=f"[{idx + 1}] {serial}",
                max_size=720,
                max_fps=max_fps,
                window_x=wx,
                window_y=wy,
                window_width=tile_width,
                window_height=tile_height
            )
            launched.append({"serial": serial, "success": ok, "window_pos": [wx, wy], "message": msg})
        return {
            "total_requested": len(serials),
            "launched_count": sum(1 for item in launched if item["success"]),
            "sessions": launched
        }

    def close_viewer(self, serial: str) -> bool:
        """Close the scrcpy window for the specified serial."""
        proc = self._active_sessions.get(serial)
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            self._active_sessions.pop(serial, None)
            return True
        return False

    def is_viewer_open(self, serial: str) -> bool:
        """Check if viewer process is currently running for serial."""
        proc = self._active_sessions.get(serial)
        if proc:
            if proc.poll() is None:
                return True
            else:
                self._active_sessions.pop(serial, None)
        return False

    def close_all(self):
        """Close all active scrcpy viewer windows."""
        for serial in list(self._active_sessions.keys()):
            self.close_viewer(serial)


if __name__ == "__main__":
    mgr = ScrcpyManager()
    print("Scrcpy path:", mgr.scrcpy_path)
    print("Scrcpy available:", mgr.is_available())
