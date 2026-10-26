"""
Unit & Integration Tests for Proposal 3 (Subagent #38: Android Chrome DevTools Protocol
(CDP) Hardware Bridge) in `core/android_cdp_bridge.py` and `agents/android_cdp_subagent.py`.
"""

import base64
import hashlib
import json
import socket
import struct
import sys
import threading
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.android_cdp_subagent import AndroidCDPSubagent
from core.adb_wrapper import ADBWrapper
from core.android_cdp_bridge import AndroidCDPBridge


class _FakeADBForCDP:
    """In-memory mock ADB object for deterministic unit testing of AndroidCDPBridge."""

    def __init__(self, unix_out: str = "", forward_rc: int = 0):
        self.unix_out = unix_out
        self.forward_rc = forward_rc
        self.commands_ran: List[Tuple[str, List[str]]] = []
        self.shell_commands: List[Tuple[str, str]] = []

    def shell(self, serial: str, command: str, timeout: int = 30) -> str:
        self.shell_commands.append((serial, command))
        if "/proc/net/unix" in command:
            return self.unix_out
        return ""

    def run_device_cmd(self, serial: str, args: List[str], timeout: int = 30) -> Tuple[int, str, str]:
        self.commands_ran.append((serial, args))
        if args and args[0] == "forward":
            if "--list" in args:
                return 0, "", ""
            return self.forward_rc, "", "" if self.forward_rc == 0 else "error: cannot bind listener"
        return 0, "", ""


class TestAndroidCDPBridge(unittest.TestCase):
    def setUp(self):
        self.sample_proc_net_unix = """
Num       RefCount Protocol Flags    Type St Inode Path
0000000000000000: 00000002 00000000 00010000 0001 01 128492 @JsEngine_com.ss.android.ugc.trill_devtools_remote
0000000000000000: 00000002 00000000 00010000 0001 01  94821 @chrome_devtools_remote
0000000000000000: 00000003 00000000 00000000 0001 03  94822 @chrome_devtools_remote
0000000000000000: 00000002 00000000 00010000 0001 01 159201 @webview_devtools_remote_28412
        """
        self.fake_adb = _FakeADBForCDP(unix_out=self.sample_proc_net_unix)
        self.bridge = AndroidCDPBridge(adb=self.fake_adb)

    def test_discover_devtools_sockets_parses_proc_net_unix(self):
        sockets = self.bridge.discover_devtools_sockets("10CF5L0TYL00312")
        self.assertIn("chrome_devtools_remote", sockets)
        self.assertIn("JsEngine_com.ss.android.ugc.trill_devtools_remote", sockets)
        self.assertIn("webview_devtools_remote_28412", sockets)
        # Standard chrome_devtools_remote should be prioritized first and deduplicated
        self.assertEqual(sockets[0], "chrome_devtools_remote")
        self.assertEqual(len(sockets), 3)

    def test_forward_socket_auto_port_selection(self):
        # Occupy a temporary local port to verify automatic fallback to a free port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy_sock:
            busy_sock.bind(("127.0.0.1", 0))
            busy_sock.listen(1)
            busy_port = busy_sock.getsockname()[1]

            ok = self.bridge.forward_socket(
                serial="10CF5L0TYL00312",
                local_port=busy_port,
                socket_name="@chrome_devtools_remote",
            )
            self.assertTrue(ok)
            assigned_port = self.bridge.active_forwards["10CF5L0TYL00312:chrome_devtools_remote"]
            self.assertNotEqual(assigned_port, busy_port)
            self.assertGreater(assigned_port, 0)

    def test_css_to_physical_screen_coords_1260x2800_dpr3(self):
        # 1260x2800 screen with devicePixelRatio=3.0 and outerHeight - innerHeight = 80 CSS px (240 physical px)
        vp_metrics = {
            "devicePixelRatio": 3.0,
            "innerWidth": 420,
            "innerHeight": 853,
            "outerWidth": 420,
            "outerHeight": 933,  # (933 - 853) * 3.0 = 240px Chrome toolbar + status bar offset
            "visualViewportOffsetLeft": 0,
            "visualViewportOffsetTop": 0,
            "visualViewportScale": 1.0,
        }
        phys_x, phys_y = self.bridge.css_to_physical_screen_coords(
            css_x=210.0,
            css_y=300.0,
            viewport_metrics=vp_metrics,
            screen_size=(1260, 2800),
        )
        self.assertEqual(phys_x, 630)
        self.assertEqual(phys_y, 300 * 3 + 240)  # 1140

        # Test explicit chrome_top_offset_px = 250 and visualViewport offsets
        vp_metrics_explicit = {
            "devicePixelRatio": 3.0,
            "visualViewportOffsetLeft": 10.0,
            "visualViewportOffsetTop": 20.0,
            "chrome_top_offset_px": 250,
        }
        px2, py2 = self.bridge.css_to_physical_screen_coords(
            css_x=100.0,
            css_y=200.0,
            viewport_metrics=vp_metrics_explicit,
            screen_size=(1260, 2800),
        )
        self.assertEqual(px2, int((100.0 + 10.0) * 3.0))  # 330
        self.assertEqual(py2, int((200.0 + 20.0) * 3.0 + 250))  # 910

    def test_evaluate_js_over_local_websocket_server(self):
        # Spin up a tiny local RFC 6455 WebSocket server to test real wire-level evaluate_js_on_tab
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(("127.0.0.1", 0))
        server_sock.listen(1)
        ws_port = server_sock.getsockname()[1]
        received_requests: List[Dict[str, Any]] = []

        def _ws_server_worker():
            try:
                conn, _ = server_sock.accept()
                with conn:
                    req_data = conn.recv(4096).decode("utf-8", errors="replace")
                    key_line = [l for l in req_data.splitlines() if l.lower().startswith("sec-websocket-key:")][0]
                    client_key = key_line.split(":", 1)[1].strip()
                    accept_val = base64.b64encode(
                        hashlib.sha1((client_key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
                    ).decode("ascii")
                    resp_headers = (
                        "HTTP/1.1 101 Switching Protocols\r\n"
                        "Upgrade: websocket\r\n"
                        "Connection: Upgrade\r\n"
                        f"Sec-WebSocket-Accept: {accept_val}\r\n\r\n"
                    )
                    conn.sendall(resp_headers.encode("ascii"))

                    # Read client masked frame
                    hdr = conn.recv(2)
                    b1 = hdr[1]
                    length = b1 & 0x7F
                    if length == 126:
                        length = struct.unpack("!H", conn.recv(2))[0]
                    mask = conn.recv(4)
                    enc = bytearray(conn.recv(length))
                    for i in range(length):
                        enc[i] ^= mask[i % 4]
                    msg_obj = json.loads(enc.decode("utf-8"))
                    received_requests.append(msg_obj)

                    reply = json.dumps(
                        {
                            "id": msg_obj["id"],
                            "result": {
                                "result": {
                                    "type": "object",
                                    "value": {"navigator_webdriver": False, "title": "AMAF Testbench"},
                                }
                            },
                        }
                    ).encode("utf-8")
                    out_frame = bytearray([0x81, len(reply)]) + reply
                    conn.sendall(out_frame)
            finally:
                server_sock.close()

        t = threading.Thread(target=_ws_server_worker, daemon=True)
        t.start()

        ws_url = f"ws://127.0.0.1:{ws_port}/devtools/page/TAB_1"
        eval_res = self.bridge.evaluate_js_on_tab(ws_url, "({navigator_webdriver: false})", timeout=3.0)
        t.join(timeout=3.0)

        self.assertEqual(eval_res["status"], "CDP_OK")
        self.assertEqual(eval_res["tokens_used"], 0)
        self.assertEqual(eval_res["value"]["navigator_webdriver"], False)
        self.assertEqual(len(received_requests), 1)
        self.assertEqual(received_requests[0]["method"], "Runtime.evaluate")
        self.assertTrue(received_requests[0]["params"]["returnByValue"])

    def test_locate_and_tap_dom_element_physically_via_subagent(self):
        mock_tabs = [
            {
                "id": "TAB_CAPTCHA_01",
                "title": "AMAF CAPTCHA Testbench",
                "url": "http://127.0.0.1:8765/captcha",
                "webSocketDebuggerUrl": "ws://127.0.0.1:9229/devtools/page/TAB_CAPTCHA_01",
                "type": "page",
            }
        ]
        mock_cdp_eval = {
            "id": 1,
            "result": {
                "result": {
                    "type": "object",
                    "value": {
                        "found": True,
                        "matched_type": "turnstile",
                        "matched_selector": ".cf-turnstile",
                        "tag_name": "div",
                        "id": "cf-turnstile-box",
                        "class_name": "cf-turnstile",
                        "text": "Verify you are human",
                        "css_rect": {
                            "left": 60.0,
                            "top": 280.0,
                            "right": 360.0,
                            "bottom": 345.0,
                            "width": 300.0,
                            "height": 65.0,
                            "center_x": 210.0,
                            "center_y": 312.5,
                        },
                        "viewport_metrics": {
                            "devicePixelRatio": 3.0,
                            "innerWidth": 420,
                            "innerHeight": 853,
                            "outerWidth": 420,
                            "outerHeight": 933,
                            "visualViewportOffsetLeft": 0,
                            "visualViewportOffsetTop": 0,
                            "visualViewportScale": 1.0,
                            "webdriver": False,
                        },
                    },
                }
            },
        }

        subagent = AndroidCDPSubagent(adb=self.fake_adb)
        attach_res = subagent.discover_and_attach(
            serial="10CF5L0TYL00312",
            mock_tabs_response=mock_tabs,
        )
        self.assertEqual(attach_res["status"], "CDP_BRIDGE_ATTACHED")
        self.assertEqual(attach_res["subagent_id"], 38)
        self.assertEqual(attach_res["tab_count"], 1)
        self.assertEqual(attach_res["tokens_used"], 0)

        tap_res = subagent.inspect_and_tap_via_cdp(
            serial="10CF5L0TYL00312",
            selector_or_type="turnstile",
            screen_size=(1260, 2800),
            perform_tap=True,
            mock_tabs=mock_tabs,
            mock_eval_result=mock_cdp_eval,
        )
        self.assertEqual(tap_res["status"], "CDP_PHYSICAL_TAP_OK")
        self.assertEqual(tap_res["matched_type"], "turnstile")
        self.assertEqual(tap_res["phys_x"], 630)
        self.assertEqual(tap_res["phys_y"], int(round(312.5 * 3.0 + 240)))  # 1178
        self.assertTrue(tap_res["webdriver_clean"])
        self.assertEqual(tap_res["tokens_used"], 0)
        self.assertEqual(tap_res["tap_result"]["status"], "HUMAN_TAP_OK")

        # Verify physical touch command was sent over ADB (`input swipe`) and NOT CDP Input.dispatchTouchEvent
        self.assertTrue(any("input swipe" in cmd for _, cmd in self.fake_adb.shell_commands))

    def test_live_device_10CF5L0TYL00312_if_connected(self):
        real_adb = ADBWrapper()
        connected = [d["serial"] for d in real_adb.get_connected_devices() if d.get("status") == "device"]
        if "10CF5L0TYL00312" not in connected:
            # Gracefully pass when physical device is not attached
            self.assertTrue(True)
            return

        live_bridge = AndroidCDPBridge(adb=real_adb)
        sockets = live_bridge.discover_devtools_sockets("10CF5L0TYL00312")
        self.assertIsInstance(sockets, list)
        if sockets:
            forwarded = live_bridge.forward_socket("10CF5L0TYL00312", socket_name=sockets[0])
            self.assertTrue(forwarded)
            port = live_bridge.active_forwards.get(f"10CF5L0TYL00312:{sockets[0]}", 9229)
            tabs = live_bridge.list_open_tabs(local_port=port)
            self.assertIsInstance(tabs, list)


if __name__ == "__main__":
    unittest.main()
