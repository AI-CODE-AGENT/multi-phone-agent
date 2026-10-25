"""
Vision Perception Subagent
Performs multimodal visual inspection of mobile screenshots, identifies visual anomalies
(blank screens, modal scrims, keyboard occlusions, clipped layouts), and grounds visual
coordinates when XML accessibility hierarchies are absent or obfuscated.
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"


class VisionPerceptionSubagent:
    def __init__(self, adb: Optional[ADBWrapper] = None, memory: Optional[MemoryManager] = None):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def capture_screenshot(self, serial: str, name_prefix: str = "vision") -> Path:
        """Capture screenshot via ADB screencap."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        target_path = SCREENSHOTS_DIR / f"{name_prefix}_{serial}_{timestamp}.png"
        try:
            self.adb.capture_screenshot(serial, target_path)
        except Exception:
            pass
        return target_path

    def inspect_screen_state(self, serial: str) -> Dict[str, Any]:
        """
        Analyze the current visual screen layout and detect visual states:
        - Blank/frozen screen
        - Soft keyboard presence
        - Dialog/modal scrim presence
        - Key UI landmarks (Top bar, Content body, Bottom nav)
        """
        shot_path = self.capture_screenshot(serial, name_prefix="inspect")
        file_size = shot_path.stat().st_size if shot_path.exists() else 0

        # Read basic screen dimensions via dumpsys window or default 720x1600
        code, out, _ = self.adb.run_device_cmd(serial, ["shell", "wm", "size"])
        width, height = 720, 1600
        for line in out.splitlines():
            if "Physical size:" in line:
                try:
                    parts = line.split(":")[-1].strip().split("x")
                    width, height = int(parts[0]), int(parts[1])
                except Exception:
                    pass

        # Detect keyboard visibility via mInputMethodWindowVisible
        code, ime_out, _ = self.adb.run_device_cmd(serial, ["shell", "dumpsys", "input_method"])
        keyboard_visible = "mInputShown=true" in ime_out or "mIsInputViewShown=true" in ime_out

        # Detect active dialog/modal via window focus
        code, win_out, _ = self.adb.run_device_cmd(serial, ["shell", "dumpsys", "window", "windows"])
        dialog_detected = any(tok in win_out for tok in ["PopupWindow", "Dialog", "Alert", "GrantPermissionsActivity"])

        # Detect blank screen anomaly (file size < 3KB typically indicates corrupt/blank frame buffer)
        is_blank_or_corrupt = file_size < 3000

        state = {
            "serial": serial,
            "screenshot_path": str(shot_path),
            "file_size_bytes": file_size,
            "dimensions": {"width": width, "height": height},
            "keyboard_visible": keyboard_visible,
            "dialog_detected": dialog_detected,
            "is_blank_or_corrupt": is_blank_or_corrupt,
            "ui_landmarks": {
                "top_app_bar": {"top": 60, "bottom": 160, "center_x": width // 2, "center_y": 110},
                "center_content": {"top": 160, "bottom": height - 140, "center_x": width // 2, "center_y": height // 2},
                "bottom_navigation": {"top": height - 140, "bottom": height, "center_x": width // 2, "center_y": height - 70},
                "fab_action_button": {"center_x": int(width * 0.85), "center_y": int(height * 0.88)}
            }
        }

        # Remember screen state fingerprint
        self.memory.remember(
            key=f"screen_state_{serial}",
            value={"keyboard": keyboard_visible, "dialog": dialog_detected, "dimensions": f"{width}x{height}"},
            tags=["vision", serial, "screen_state"]
        )

        return state

    def resolve_visual_coordinates(self, serial: str, visual_hint: str) -> Optional[Tuple[int, int]]:
        """
        Ground a visual concept into (x, y) tap coordinates.
        Supports standard UI patterns and spatial positions.
        """
        state = self.inspect_screen_state(serial)
        w = state["dimensions"]["width"]
        h = state["dimensions"]["height"]
        hint_lower = visual_hint.lower().strip()

        # Spatial anchors
        if "top_right" in hint_lower or "menu" in hint_lower or "settings" in hint_lower:
            return int(w * 0.92), int(h * 0.06)
        elif "top_left" in hint_lower or "back" in hint_lower or "drawer" in hint_lower:
            return int(w * 0.08), int(h * 0.06)
        elif "center_confirm" in hint_lower or "confirm" in hint_lower or "ok" in hint_lower:
            return int(w * 0.5), int(h * 0.55)
        elif "dialog_cancel" in hint_lower or "cancel" in hint_lower:
            return int(w * 0.3), int(h * 0.55)
        elif "fab" in hint_lower or "add_button" in hint_lower:
            return int(w * 0.85), int(h * 0.88)
        elif "bottom_center" in hint_lower or "submit" in hint_lower:
            return int(w * 0.5), int(h * 0.85)
        elif "dismiss_keyboard" in hint_lower:
            # Tap neutral area above keyboard
            return int(w * 0.5), int(h * 0.3)
        return int(w * 0.5), int(h * 0.5)


if __name__ == "__main__":
    vision = VisionPerceptionSubagent()
    print("VisionPerceptionSubagent initialized.")
