"""
Unit Tests for AMAF v8.0 Live CAPTCHA & 2FA Web Testbench Server and Subagent #31
(`LiveWebTestbenchAndRealPhoneE2ESubagent`).
Uses local loopback HTTP requests on an ephemeral port and a Mock ADB adapter
(no physical ADB commands executed during unit tests).
"""

import json
import tempfile
import unittest
import urllib.request
from pathlib import Path
from typing import List, Tuple

from agents.live_web_testbench_e2e_subagent import LiveWebTestbenchAndRealPhoneE2ESubagent
from core.live_captcha_2fa_testbench_server import LiveCaptcha2FATestbenchServer
from core.memory_manager import MemoryManager


class MockADBForTestbench:
    """In-memory mock ADB recording reverse port bridges and shell interactions."""

    def __init__(self):
        self.device_cmds: List[Tuple[str, List[str]]] = []
        self.shell_cmds: List[Tuple[str, str]] = []
        self.typed_texts: List[Tuple[str, str]] = []

    def run_device_cmd(self, serial: str, args: List[str], timeout: int = 15) -> Tuple[int, str, str]:
        self.device_cmds.append((serial, list(args)))
        return 0, "ok", ""

    def shell(self, serial: str, cmd: str, timeout: int = 15) -> str:
        self.shell_cmds.append((serial, cmd))
        return "ok"

    def input_text(self, serial: str, text: str) -> bool:
        self.typed_texts.append((serial, text))
        return True


class TestAMAFV8LiveWebTestbench(unittest.TestCase):
    """Tests for LiveCaptcha2FATestbenchServer and LiveWebTestbenchAndRealPhoneE2ESubagent."""

    def test_01_server_start_stop_and_html_page(self):
        """Test server starts on an ephemeral port, serves HTML at /amaf-testbench, and stops cleanly."""
        srv = LiveCaptcha2FATestbenchServer(host="127.0.0.1", port=0)
        try:
            info = srv.start()
            self.assertTrue(info["running"])
            self.assertGreater(info["port"], 0)
            self.assertIn("/amaf-testbench", info["url"])

            with urllib.request.urlopen(info["url"], timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                html = resp.read().decode("utf-8")
                self.assertIn("AMAF v8.0 Live CAPTCHA", html)
                self.assertIn("aria-label", html)
                self.assertIn("/api/solve", html)
        finally:
            srv.stop()

    def test_02_http_api_state_and_reset(self):
        """Test GET /api/state and POST /api/reset over HTTP."""
        srv = LiveCaptcha2FATestbenchServer(host="127.0.0.1", port=0)
        try:
            info = srv.start()
            base_url = f"http://127.0.0.1:{info['port']}"

            with urllib.request.urlopen(f"{base_url}/api/state", timeout=5) as resp:
                st = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(st["solved_count"], 0)
                self.assertFalse(st["all_solved"])
                self.assertEqual(len(st["current_expected_totp"]), 6)

            srv.record_solve_event("slider", {"offset_px": 180})
            self.assertEqual(srv.get_state()["solved_count"], 1)

            req = urllib.request.Request(
                f"{base_url}/api/reset",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                reset_st = json.loads(resp.read().decode("utf-8"))
                self.assertEqual(reset_st["solved_count"], 0)
                self.assertFalse(reset_st["slider_solved"])
        finally:
            srv.stop()

    def test_03_http_post_api_solve_all_5_challenges(self):
        """Test solving all 5 challenges via HTTP POST /api/solve."""
        srv = LiveCaptcha2FATestbenchServer(host="127.0.0.1", port=0)
        try:
            info = srv.start()
            solve_url = f"http://127.0.0.1:{info['port']}/api/solve"

            def post_solve(challenge: str, payload: dict) -> dict:
                body = json.dumps({"challenge": challenge, "payload": payload}).encode("utf-8")
                req = urllib.request.Request(
                    solve_url,
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5) as r:
                    return json.loads(r.read().decode("utf-8"))

            s1 = post_solve("rotation", {"angle_deg": 125})
            self.assertTrue(s1["rotation_solved"])
            self.assertEqual(s1["solved_count"], 1)

            s2 = post_solve("grid", {"indices": [0, 2, 4, 7]})
            self.assertTrue(s2["grid_solved"])
            self.assertEqual(s2["solved_count"], 2)

            s3 = post_solve("slider", {"offset_px": 185})
            self.assertTrue(s3["slider_solved"])
            self.assertEqual(s3["solved_count"], 3)

            expected_totp = s3["current_expected_totp"]
            s4 = post_solve("totp", {"code": expected_totp})
            self.assertTrue(s4["totp_solved"])
            self.assertEqual(s4["solved_count"], 4)

            s5 = post_solve("push_2fa", {"number": "84"})
            self.assertTrue(s5["push_2fa_solved"])
            self.assertEqual(s5["solved_count"], 5)
            self.assertTrue(s5["all_solved"])
        finally:
            srv.stop()

    def test_04_subagent_31_live_web_captcha_and_2fa_e2e_with_mock_adb(self):
        """Test Subagent #31 full 5-challenge E2E flow with a mock ADB."""
        mock_adb = MockADBForTestbench()
        with tempfile.TemporaryDirectory() as tmp_dir:
            mem = MemoryManager(memory_file=Path(tmp_dir) / "test_memory.json")
            sub = LiveWebTestbenchAndRealPhoneE2ESubagent(
                adb=mock_adb,
                memory=mem,
                port=0,
            )
            try:
                res = sub.run_live_web_captcha_and_2fa_e2e(
                    serial="10AC9C118R000CS",
                    open_in_browser=True,
                    execute_touch=True,
                )
                self.assertEqual(res["status"], "LIVE_WEB_TESTBENCH_E2E_PASSED")
                self.assertEqual(res["solved_count"], 5)
                self.assertTrue(res["all_solved"])
                self.assertEqual(len(res["steps"]), 5)
                self.assertTrue(all(step["solved"] for step in res["steps"]))

                # Verify adb reverse was called on the mock ADB
                self.assertTrue(
                    any("reverse" in cmd_args for _, cmd_args in mock_adb.device_cmds)
                )
                # Verify browser intent and touch gestures were sent to mock ADB
                self.assertTrue(
                    any("android.intent.action.VIEW" in cmd for _, cmd in mock_adb.shell_cmds)
                )
            finally:
                sub.server.stop()


if __name__ == "__main__":
    unittest.main()
