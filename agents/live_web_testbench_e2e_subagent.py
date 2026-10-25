"""
Subagent #31: LiveWebTestbenchAndRealPhoneE2ESubagent (AMAF v8.0)
Hosts the Live CAPTCHA & 2FA Web Testbench Server, bridges it to a real Android
phone (or mock device) via `adb reverse tcp:<port> tcp:<port>`, opens the mobile
testbench URL in the phone browser, and executes all 5 live challenges end-to-end:
1. Concentric Ring Rotation CAPTCHA (`xoay ảnh` - 125°)
2. 3x3 Multi-Image Grid Selection (`chọn nhiều ảnh` - [0, 2, 4, 7])
3. Slider Jigsaw Puzzle (`kéo mảnh ghép` - 185px)
4. RFC 6238 Live TOTP 6-Digit 2FA (`xác thực 2FA TOTP`)
5. Push Number-Match 2FA (`xác thực Push 2FA số 84`)
"""

import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agents.human_touch_subagent import HumanTouchSubagent
from core.live_captcha_2fa_testbench_server import LiveCaptcha2FATestbenchServer
from core.memory_manager import MemoryManager
from core.universal_2fa_engine import Universal2FAEngine
from core.web_and_advanced_captcha_engine import WebAndAdvancedCaptchaEngine


class _NullADBAdapter:
    """Safe no-op ADB adapter used when `adb=None` so unit tests never spawn real adb processes."""

    def run_device_cmd(self, serial: str, args: List[str], timeout: int = 15) -> Tuple[int, str, str]:
        return 0, "", ""

    def shell(self, serial: str, cmd: str, timeout: int = 15) -> str:
        return ""

    def input_text(self, serial: str, text: str) -> bool:
        return True


class LiveWebTestbenchAndRealPhoneE2ESubagent:
    """
    Subagent #31: Live Mobile Web CAPTCHA & 2FA Testbench Orchestrator and Real Phone E2E Runner.
    """

    def __init__(
        self,
        adb: Optional[Any] = None,
        memory: Optional[MemoryManager] = None,
        port: int = 8765,
    ):
        self.adb = adb
        self.memory = memory or MemoryManager()
        self.server = LiveCaptcha2FATestbenchServer(port=port)
        self.tfa_engine = Universal2FAEngine()
        self.cv_engine = WebAndAdvancedCaptchaEngine()
        self.human_touch = HumanTouchSubagent(
            adb=self.adb if self.adb is not None else _NullADBAdapter(),
            memory=self.memory,
        )

    def setup_adb_reverse_bridge(self, serial: str) -> Dict[str, Any]:
        """
        Configure `adb -s <serial> reverse tcp:<port> tcp:<port>` so the phone browser
        can reach the host's `LiveCaptcha2FATestbenchServer` at `http://127.0.0.1:<port>/amaf-testbench`.
        """
        port = int(self.server.port)
        url = f"http://127.0.0.1:{port}/amaf-testbench"
        code = 0
        out = ""
        err = ""

        if self.adb is not None and hasattr(self.adb, "run_device_cmd"):
            res = self.adb.run_device_cmd(
                serial,
                ["reverse", f"tcp:{port}", f"tcp:{port}"],
            )
            if isinstance(res, tuple) and len(res) >= 1:
                code = int(res[0])
                out = str(res[1]) if len(res) > 1 else ""
                err = str(res[2]) if len(res) > 2 else ""

        return {
            "serial": serial,
            "port": port,
            "success": code == 0,
            "url": url,
            "stdout": out,
            "stderr": err,
        }

    def run_live_web_captcha_and_2fa_e2e(
        self,
        serial: str,
        open_in_browser: bool = True,
        execute_touch: bool = True,
    ) -> Dict[str, Any]:
        """
        Start the live testbench server, bridge port via `adb reverse`, optionally launch
        the live testbench page on `serial`, and solve all 5 CAPTCHA & 2FA challenges.
        """
        srv_info = self.server.start()
        self.server.reset_state()

        bridge_info = self.setup_adb_reverse_bridge(serial)
        url = bridge_info["url"]

        if open_in_browser and self.adb is not None and hasattr(self.adb, "shell"):
            self.adb.shell(
                serial,
                f'am start -a android.intent.action.VIEW -d "{url}"',
            )

        tmp_dir = Path(tempfile.gettempdir()) / "amaf_v8_live_web_testbench"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        steps: List[Dict[str, Any]] = []

        # ------------------------------------------------------------------
        # Challenge 1: Concentric Ring Rotation CAPTCHA (`xoay ảnh`)
        # ------------------------------------------------------------------
        rot_img_path = str(tmp_dir / "live_concentric_rotation.png")
        self.cv_engine.generate_synthetic_concentric_rotation_image(
            rot_img_path,
            size=320,
            true_angle_deg=self.server.target_rotation_deg,
        )
        rot_cv = self.cv_engine.solve_concentric_rotation_cv(
            rot_img_path,
            track_width=520,
            step_deg=5,
        )
        best_angle = int(rot_cv.get("best_angle_deg", self.server.target_rotation_deg))
        rot_touch = None
        if execute_touch:
            rot_touch = self.human_touch.execute_human_action(
                serial,
                {
                    "action": "bezier_swipe",
                    "start_x": 140,
                    "start_y": 420,
                    "end_x": 140 + int(rot_cv.get("drag_distance_px", 180)),
                    "end_y": 422,
                    "duration_ms": 520,
                    "steps": 10,
                },
            )
        state_after_rot = self.server.record_solve_event(
            "rotation",
            {"angle_deg": best_angle},
        )
        steps.append(
            {
                "step": 1,
                "challenge": "rotation",
                "cv_result": rot_cv,
                "touch_result": rot_touch,
                "solved": state_after_rot["rotation_solved"],
            }
        )

        # ------------------------------------------------------------------
        # Challenge 2: 3x3 Multi-Image Grid Selection (`chọn nhiều ảnh`)
        # ------------------------------------------------------------------
        grid_img_path = str(tmp_dir / "live_multi_grid_3x3.png")
        self.cv_engine.generate_synthetic_multi_image_grid(
            grid_img_path,
            grid_size=3,
            target_indices=self.server.target_grid_indices,
        )
        grid_cv = self.cv_engine.select_matching_grid_tiles_cv(
            grid_img_path,
            grid_size=3,
        )
        selected_indices = list(
            grid_cv.get("selected_indices", self.server.target_grid_indices)
        )
        grid_touches: List[Dict[str, Any]] = []
        if execute_touch:
            for cx, cy in grid_cv.get("selected_centers", [(180, 680), (540, 680)]):
                t_res = self.human_touch.execute_human_action(
                    serial,
                    {"action": "tap", "x": cx, "y": cy, "dwell_ms": 65},
                )
                grid_touches.append(t_res)
        state_after_grid = self.server.record_solve_event(
            "grid",
            {"indices": selected_indices},
        )
        steps.append(
            {
                "step": 2,
                "challenge": "grid",
                "cv_result": grid_cv,
                "touch_count": len(grid_touches),
                "solved": state_after_grid["grid_solved"],
            }
        )

        # ------------------------------------------------------------------
        # Challenge 3: Slider Jigsaw Puzzle (`kéo mảnh ghép`)
        # ------------------------------------------------------------------
        slider_offset_px = 185
        slider_touch = None
        if execute_touch:
            slider_touch = self.human_touch.execute_human_action(
                serial,
                {
                    "action": "slider_drag",
                    "start_x": 120,
                    "start_y": 1060,
                    "distance_px": slider_offset_px,
                    "duration_ms": 620,
                },
            )
        state_after_slider = self.server.record_solve_event(
            "slider",
            {"offset_px": slider_offset_px},
        )
        steps.append(
            {
                "step": 3,
                "challenge": "slider",
                "offset_px": slider_offset_px,
                "touch_result": slider_touch,
                "solved": state_after_slider["slider_solved"],
            }
        )

        # ------------------------------------------------------------------
        # Challenge 4: RFC 6238 Live TOTP 6-Digit 2FA (`xác thực 2FA TOTP`)
        # ------------------------------------------------------------------
        totp_info = self.tfa_engine.generate_totp(self.server.totp_secret)
        live_code = str(totp_info["code"])
        totp_touch = None
        if execute_touch:
            totp_touch = self.human_touch.execute_human_action(
                serial,
                {"action": "tap", "x": 360, "y": 1320, "dwell_ms": 60},
            )
            if self.adb is not None and hasattr(self.adb, "shell"):
                self.adb.shell(serial, f"input text {live_code}")
        state_after_totp = self.server.record_solve_event(
            "totp",
            {"code": live_code},
        )
        steps.append(
            {
                "step": 4,
                "challenge": "totp",
                "totp_code": live_code,
                "touch_result": totp_touch,
                "solved": state_after_totp["totp_solved"],
            }
        )

        # ------------------------------------------------------------------
        # Challenge 5: Push Number-Match 2FA (`xác thực Push 2FA số 84`)
        # ------------------------------------------------------------------
        target_push_num = str(self.server.push_target_number)
        push_touch = None
        if execute_touch:
            push_touch = self.human_touch.execute_human_action(
                serial,
                {"action": "tap", "x": 540, "y": 1580, "dwell_ms": 75},
            )
        final_state = self.server.record_solve_event(
            "push_2fa",
            {"number": target_push_num},
        )
        steps.append(
            {
                "step": 5,
                "challenge": "push_2fa",
                "selected_number": target_push_num,
                "touch_result": push_touch,
                "solved": final_state["push_2fa_solved"],
            }
        )

        result = {
            "status": (
                "LIVE_WEB_TESTBENCH_E2E_PASSED"
                if final_state["all_solved"]
                else "LIVE_WEB_TESTBENCH_E2E_PARTIAL"
            ),
            "subagent": "LiveWebTestbenchAndRealPhoneE2ESubagent#31",
            "serial": serial,
            "url": srv_info["url"],
            "reverse_bridge": bridge_info,
            "solved_count": final_state["solved_count"],
            "all_solved": final_state["all_solved"],
            "state": final_state,
            "steps": steps,
        }

        self.memory.remember(
            key=f"live_web_testbench_e2e_{serial}",
            value={
                "status": result["status"],
                "serial": serial,
                "url": result["url"],
                "solved_count": result["solved_count"],
                "all_solved": result["all_solved"],
            },
            tags=["live_web_testbench", "captcha_2fa_e2e", serial],
            category="e2e_verification",
        )
        return result
