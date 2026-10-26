"""
Android Chrome DevTools Protocol (CDP) Hardware Bridge (AMAF v9.0 - Subagent #38 Core)

Bridges desktop Python directly to Android's internal Abstract Unix Domain Sockets
(`@chrome_devtools_remote`, `@webview_devtools_remote_*`, and `@JsEngine_*_devtools_remote`)
via `adb forward` while keeping all touch interactions on the physical Android input
subsystem (`input tap/swipe` or `HumanTouchEngine`) so `navigator.webdriver` remains
`false` / `undefined` and zero browser automation flags are triggered!

Operates with 100% ZERO AI TOKENS at runtime (`tokens_used = 0`).
"""

import base64
import hashlib
import json
import os
import re
import socket
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.human_touch_engine import HumanTouchEngine


# Pre-built zero-footprint DOM inspection JavaScript snippet for Runtime.evaluate
CDP_LOCATE_ELEMENT_JS_TEMPLATE = r"""
(function(selectorOrType) {
    var dpr = window.devicePixelRatio || 3.0;
    var vv = window.visualViewport || {offsetLeft: 0, offsetTop: 0, scale: 1.0, width: window.innerWidth, height: window.innerHeight};
    var outerH = window.outerHeight || 0;
    var innerH = window.innerHeight || 0;
    var innerW = window.innerWidth || 0;

    var candidates = [
        {type: "recaptcha", selector: 'iframe[src*="recaptcha"], .g-recaptcha, #g-recaptcha, iframe[title*="reCAPTCHA"]'},
        {type: "hcaptcha", selector: 'iframe[src*="hcaptcha"], .h-captcha, iframe[title*="hCaptcha"]'},
        {type: "turnstile", selector: 'iframe[src*="challenges.cloudflare.com"], .cf-turnstile, #cf-turnstile'},
        {type: "geetest", selector: '.geetest_slider_button, div.geetest_holder, .geetest_radar_tip, .geetest_btn'},
        {type: "submit", selector: 'button[type="submit"], input[type="submit"], button.submit-btn, #submit-btn'}
    ];

    var targetEl = null;
    var matchedType = selectorOrType || "auto";
    var matchedSelector = "";

    if (selectorOrType && selectorOrType !== "auto") {
        // Check if selectorOrType matches one of our known shorthand types first
        for (var i = 0; i < candidates.length; i++) {
            if (candidates[i].type === selectorOrType.toLowerCase()) {
                targetEl = document.querySelector(candidates[i].selector);
                matchedType = candidates[i].type;
                matchedSelector = candidates[i].selector;
                break;
            }
        }
        // Otherwise treat selectorOrType as a direct CSS selector
        if (!targetEl) {
            try {
                targetEl = document.querySelector(selectorOrType);
                matchedType = "custom_selector";
                matchedSelector = selectorOrType;
            } catch (e) {}
        }
    } else {
        for (var j = 0; j < candidates.length; j++) {
            var el = document.querySelector(candidates[j].selector);
            if (el) {
                var r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0) {
                    targetEl = el;
                    matchedType = candidates[j].type;
                    matchedSelector = candidates[j].selector;
                    break;
                }
            }
        }
    }

    var viewportMetrics = {
        devicePixelRatio: dpr,
        innerWidth: innerW,
        innerHeight: innerH,
        outerWidth: window.outerWidth || innerW,
        outerHeight: outerH,
        visualViewportOffsetLeft: vv.offsetLeft || 0,
        visualViewportOffsetTop: vv.offsetTop || 0,
        visualViewportScale: vv.scale || 1.0,
        pageXOffset: window.pageXOffset || window.scrollX || 0,
        pageYOffset: window.pageYOffset || window.scrollY || 0,
        webdriver: navigator.webdriver
    };

    if (!targetEl) {
        return {
            found: false,
            matched_type: matchedType,
            matched_selector: matchedSelector,
            viewport_metrics: viewportMetrics
        };
    }

    var rect = targetEl.getBoundingClientRect();
    return {
        found: true,
        matched_type: matchedType,
        matched_selector: matchedSelector,
        tag_name: (targetEl.tagName || "").toLowerCase(),
        id: targetEl.id || "",
        class_name: typeof targetEl.className === "string" ? targetEl.className : "",
        text: (targetEl.innerText || targetEl.value || "").slice(0, 120),
        css_rect: {
            left: rect.left,
            top: rect.top,
            right: rect.right,
            bottom: rect.bottom,
            width: rect.width,
            height: rect.height,
            center_x: rect.left + rect.width / 2.0,
            center_y: rect.top + rect.height / 2.0
        },
        viewport_metrics: viewportMetrics
    };
})
"""


class AndroidCDPBridge:
    """
    Zero-Token Hardware Bridge between desktop Python and Android Abstract Unix Domain
    DevTools sockets (`@chrome_devtools_remote`, `@JsEngine_*_devtools_remote`, etc.).
    """

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        touch_engine: Optional[HumanTouchEngine] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.touch_engine = touch_engine or HumanTouchEngine(adb=self.adb)
        self.active_forwards: Dict[str, int] = {}

    @staticmethod
    def parse_proc_net_unix_sockets(raw_output: str) -> List[str]:
        """
        Parse `/proc/net/unix` output and extract abstract DevTools socket names
        (stripping leading `@`), deduplicated while preserving discovery order.
        Prioritizes `chrome_devtools_remote` first if present.
        """
        if not raw_output:
            return []

        found: List[str] = []
        seen = set()

        for line in raw_output.splitlines():
            line = line.strip()
            if not line or "devtools" not in line.lower():
                continue
            # Match @<socket_name> at the end of /proc/net/unix lines or bare socket names
            match = re.search(r"@([A-Za-z0-9_.\-]*devtools[A-Za-z0-9_.\-]*)", line, re.IGNORECASE)
            if match:
                sock_name = match.group(1)
            else:
                # Fallback if line already has @ stripped or custom format
                tokens = line.split()
                last_tok = tokens[-1].lstrip("@") if tokens else ""
                if "devtools" in last_tok.lower():
                    sock_name = last_tok
                else:
                    continue

            if sock_name and sock_name not in seen:
                seen.add(sock_name)
                found.append(sock_name)

        # Prioritize standard Chrome socket at index 0 when available
        if "chrome_devtools_remote" in found:
            found.remove("chrome_devtools_remote")
            found.insert(0, "chrome_devtools_remote")

        return found

    def discover_devtools_sockets(
        self,
        serial: str,
        raw_unix_override: Optional[str] = None,
    ) -> List[str]:
        """
        Runs `adb -s <serial> shell "cat /proc/net/unix | grep devtools"` and extracts
        socket names (e.g. `chrome_devtools_remote`, `JsEngine_com.ss.android.ugc.trill_devtools_remote`).
        """
        if raw_unix_override is not None:
            raw_out = raw_unix_override
        else:
            raw_out = self.adb.shell(serial, "cat /proc/net/unix | grep devtools")
            if raw_out.startswith("ERROR:") or not raw_out.strip():
                # Fallback in case grep is restricted or returns non-zero when empty
                full_unix = self.adb.shell(serial, "cat /proc/net/unix")
                if not full_unix.startswith("ERROR:"):
                    raw_out = full_unix

        return self.parse_proc_net_unix_sockets(raw_out)

    @staticmethod
    def _is_local_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
        """Check whether a local TCP port already has a listener or cannot be bound."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.15)
            return s.connect_ex((host, port)) == 0

    @staticmethod
    def _find_free_local_port(preferred_port: int = 9229, host: str = "127.0.0.1") -> int:
        """Return `preferred_port` if free, otherwise ask OS for an available ephemeral port."""
        if not AndroidCDPBridge._is_local_port_in_use(preferred_port, host=host):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((host, preferred_port))
                    return preferred_port
            except OSError:
                pass

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            return int(s.getsockname()[1])

    def forward_socket(
        self,
        serial: str,
        local_port: int = 9229,
        socket_name: str = "chrome_devtools_remote",
    ) -> bool:
        """
        Runs `adb -s <serial> forward tcp:<local_port> localabstract:<socket_name>`,
        automatically picking a free port if `local_port` (default 9229) is busy on another
        process. Stores the active port in `self.active_forwards[f"{serial}:{socket_name}"]`
        and `self.active_forwards[serial]`.
        """
        clean_socket = socket_name.lstrip("@")
        chosen_port = local_port

        # Check if adb already forwarded this exact port or if another service holds it
        code, fwd_list, _ = self.adb.run_device_cmd(serial, ["forward", "--list"])
        already_forwarded_here = False
        if code == 0 and fwd_list:
            for line in fwd_list.splitlines():
                if f"tcp:{local_port}" in line and f"localabstract:{clean_socket}" in line:
                    already_forwarded_here = True
                    break

        if not already_forwarded_here and self._is_local_port_in_use(local_port):
            chosen_port = self._find_free_local_port(preferred_port=local_port + 1)

        rc, out, err = self.adb.run_device_cmd(
            serial,
            ["forward", f"tcp:{chosen_port}", f"localabstract:{clean_socket}"],
        )
        if rc != 0 or ("error" in (err or "").lower()):
            # Retry once with a guaranteed OS-assigned free port
            fallback_port = self._find_free_local_port(preferred_port=0)
            rc, out, err = self.adb.run_device_cmd(
                serial,
                ["forward", f"tcp:{fallback_port}", f"localabstract:{clean_socket}"],
            )
            if rc != 0 or ("error" in (err or "").lower()):
                return False
            chosen_port = fallback_port

        self.active_forwards[serial] = chosen_port
        self.active_forwards[f"{serial}:{clean_socket}"] = chosen_port
        return True

    def list_open_tabs(
        self,
        local_port: int = 9229,
        timeout: float = 3.0,
        mock_tabs_response: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Queries `http://127.0.0.1:<local_port>/json` and returns list of open tabs
        with standardized keys (`id`, `title`, `url`, `webSocketDebuggerUrl`, `type`).
        """
        if mock_tabs_response is not None:
            raw_tabs = mock_tabs_response
        else:
            url = f"http://127.0.0.1:{local_port}/json"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    payload = resp.read().decode("utf-8", errors="replace")
                    raw_tabs = json.loads(payload)
            except Exception:
                return []

        if not isinstance(raw_tabs, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for item in raw_tabs:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "id": str(item.get("id", "")),
                    "title": str(item.get("title", "")),
                    "url": str(item.get("url", "")),
                    "webSocketDebuggerUrl": str(item.get("webSocketDebuggerUrl", "")),
                    "type": str(item.get("type", "page")),
                }
            )
        return normalized

    @staticmethod
    def _raw_ws_evaluate(ws_url: str, message_str: str, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Zero-dependency RFC 6455 WebSocket client over standard library `socket`
        so CDP evaluation works whether or not third-party `websockets` is installed.
        """
        parsed = urllib.parse.urlparse(ws_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        raw_key = os.urandom(16)
        sec_key = base64.b64encode(raw_key).decode("ascii")

        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            handshake = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {sec_key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            )
            sock.sendall(handshake.encode("ascii"))

            # Read HTTP 101 response headers
            header_buf = b""
            while b"\r\n\r\n" not in header_buf:
                chunk = sock.recv(1024)
                if not chunk:
                    raise ConnectionError("WebSocket handshake closed prematurely")
                header_buf += chunk

            header_Part, leftover = header_buf.split(b"\r\n\r\n", 1)
            if b"101" not in header_Part.splitlines()[0]:
                raise ConnectionError(f"WebSocket upgrade rejected: {header_Part.decode('utf-8', 'replace')}")

            # Send masked text frame (FIN=1, opcode=0x1)
            payload_bytes = message_str.encode("utf-8")
            mask_key = os.urandom(4)
            length = len(payload_bytes)

            frame_header = bytearray([0x81])
            if length < 126:
                frame_header.append(0x80 | length)
            elif length < 65536:
                frame_header.append(0x80 | 126)
                frame_header.extend(struct.pack("!H", length))
            else:
                frame_header.append(0x80 | 127)
                frame_header.extend(struct.pack("!Q", length))

            frame_header.extend(mask_key)
            masked_payload = bytearray(length)
            for i in range(length):
                masked_payload[i] = payload_bytes[i] ^ mask_key[i % 4]

            sock.sendall(frame_header + masked_payload)

            # Read server frame(s) until we get our JSON response with id == 1
            buf = bytearray(leftover)

            def _read_exact(n: int) -> bytes:
                while len(buf) < n:
                    more = sock.recv(4096)
                    if not more:
                        raise ConnectionError("WebSocket closed while reading frame")
                    buf.extend(more)
                out_bytes = bytes(buf[:n])
                del buf[:n]
                return out_bytes

            while True:
                b0, b1 = _read_exact(2)
                opcode = b0 & 0x0F
                is_masked = bool(b1 & 0x80)
                frame_len = b1 & 0x7F
                if frame_len == 126:
                    frame_len = struct.unpack("!H", _read_exact(2))[0]
                elif frame_len == 127:
                    frame_len = struct.unpack("!Q", _read_exact(8))[0]

                srv_mask = _read_exact(4) if is_masked else b""
                frame_data = bytearray(_read_exact(frame_len))
                if is_masked:
                    for i in range(frame_len):
                        frame_data[i] ^= srv_mask[i % 4]

                if opcode == 0x8:  # Close frame
                    raise ConnectionError("WebSocket closed by server")
                if opcode == 0x9:  # Ping -> send Pong
                    pong = bytearray([0x8A, 0x80]) + os.urandom(4)
                    sock.sendall(pong)
                    continue
                if opcode in (0x1, 0x2):
                    text_msg = frame_data.decode("utf-8", errors="replace")
                    parsed_msg = json.loads(text_msg)
                    if isinstance(parsed_msg, dict) and parsed_msg.get("id") == 1:
                        return parsed_msg

    def evaluate_js_on_tab(
        self,
        ws_url: str,
        expression: str,
        timeout: float = 5.0,
        mock_cdp_response: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Connects to `ws_url`, sends:
          `{"id": 1, "method": "Runtime.evaluate", "params": {"expression": expression, "returnByValue": True}}`
        and returns a normalized dictionary containing the evaluated value and raw CDP payload.
        """
        request_payload = {
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "returnByValue": True,
            },
        }

        if mock_cdp_response is not None:
            raw_resp = mock_cdp_response
        else:
            if not ws_url or not ws_url.startswith("ws"):
                return {
                    "status": "CDP_ERROR",
                    "error": f"Invalid WebSocket URL: {ws_url}",
                    "value": None,
                    "tokens_used": 0,
                }
            try:
                raw_resp = self._raw_ws_evaluate(
                    ws_url=ws_url,
                    message_str=json.dumps(request_payload),
                    timeout=timeout,
                )
            except Exception as exc:
                return {
                    "status": "CDP_ERROR",
                    "error": str(exc),
                    "value": None,
                    "tokens_used": 0,
                }

        result_obj = (raw_resp or {}).get("result", {}).get("result", {})
        exception_details = (raw_resp or {}).get("result", {}).get("exceptionDetails")

        if exception_details:
            return {
                "status": "CDP_EXCEPTION",
                "error": str(exception_details.get("text", "Runtime.evaluate exception")),
                "value": None,
                "raw": raw_resp,
                "tokens_used": 0,
            }

        return {
            "status": "CDP_OK",
            "type": result_obj.get("type", "undefined"),
            "value": result_obj.get("value"),
            "raw": raw_resp,
            "tokens_used": 0,
        }

    def css_to_physical_screen_coords(
        self,
        css_x: float,
        css_y: float,
        viewport_metrics: Optional[Dict[str, Any]] = None,
        screen_size: Tuple[int, int] = (1260, 2800),
    ) -> Tuple[int, int]:
        """
        Converts DOM CSS coordinates (`getBoundingClientRect()`) into exact Android physical
        screen coordinates `(phys_x, phys_y)`.

        Accounts for:
        - `devicePixelRatio` (e.g. `3.0` on 1260x2800 Vivo OriginOS or `2.75`)
        - `visualViewport.offsetLeft` / `visualViewport.offsetTop` and `visualViewport.scale`
        - Top browser toolbar / status bar chrome offset (`chrome_top_offset_px` or derived from
          `(window.outerHeight - window.innerHeight) * dpr`, typically `220px..260px` on 1260x2800)
        """
        metrics = viewport_metrics or {}
        screen_w, screen_h = int(screen_size[0]), int(screen_size[1])

        dpr = float(metrics.get("devicePixelRatio", 0.0) or 0.0)
        inner_w = float(metrics.get("innerWidth", 0.0) or 0.0)
        inner_h = float(metrics.get("innerHeight", 0.0) or 0.0)
        outer_h = float(metrics.get("outerHeight", 0.0) or 0.0)

        if dpr <= 0.0:
            dpr = (screen_w / inner_w) if inner_w > 0 else 3.0

        vv_offset_left = float(
            metrics.get(
                "visualViewportOffsetLeft",
                metrics.get("offsetLeft", 0.0),
            )
            or 0.0
        )
        vv_offset_top = float(
            metrics.get(
                "visualViewportOffsetTop",
                metrics.get("offsetTop", 0.0),
            )
            or 0.0
        )
        vv_scale = float(
            metrics.get(
                "visualViewportScale",
                metrics.get("scale", 1.0),
            )
            or 1.0
        )

        # Determine Chrome top toolbar + Android status bar physical pixel offset
        if "chrome_top_offset_px" in metrics and metrics["chrome_top_offset_px"] is not None:
            top_chrome_phys = float(metrics["chrome_top_offset_px"])
        elif "toolbar_offset_css" in metrics and metrics["toolbar_offset_css"] is not None:
            top_chrome_phys = float(metrics["toolbar_offset_css"]) * dpr
        elif outer_h > inner_h and (outer_h - inner_h) * dpr <= 500:
            top_chrome_phys = (outer_h - inner_h) * dpr
        elif inner_h > 0 and (screen_h - inner_h * dpr) > 0:
            # On Android Chrome, the bottom nav bar is typically ~126px and top status+address bar is ~240px.
            # If total non-viewport height is small (<= 300px), treat it as top chrome; otherwise default to 240px
            missing_phys = screen_h - (inner_h * dpr)
            if 160 <= missing_phys <= 300:
                top_chrome_phys = missing_phys
            else:
                top_chrome_phys = 240.0
        else:
            # Standard Chrome top bar + status bar offset on 1260x2800 (220px..260px range -> 240px)
            top_chrome_phys = 240.0 if screen_h >= 2400 else 0.0

        phys_x_float = (css_x + vv_offset_left) * dpr * vv_scale
        phys_y_float = (css_y + vv_offset_top) * dpr * vv_scale + top_chrome_phys

        phys_x = max(0, min(screen_w, int(round(phys_x_float))))
        phys_y = max(0, min(screen_h, int(round(phys_y_float))))
        return phys_x, phys_y

    def locate_captcha_or_element_via_cdp(
        self,
        serial: str,
        selector_or_type: str = "auto",
        screen_size: Tuple[int, int] = (1260, 2800),
        local_port: int = 9229,
        mock_tabs: Optional[List[Dict[str, Any]]] = None,
        mock_eval_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Injects a zero-footprint inspection snippet via `Runtime.evaluate` that locates:
        - reCAPTCHA v2/v3 (`iframe[src*="recaptcha"]`, `.g-recaptcha`)
        - hCaptcha (`iframe[src*="hcaptcha"]`, `.h-captcha`)
        - Cloudflare Turnstile (`iframe[src*="challenges.cloudflare.com"]`, `.cf-turnstile`)
        - GeeTest (`div.geetest_holder`, `.geetest_slider_button`, `.geetest_radar_tip`)
        - Submit / Validate buttons (`button[type="submit"]`, `input[type="submit"]`)
        - Or any custom CSS selector passed in `selector_or_type`.

        Returns exact physical touch coordinates `(phys_x, phys_y)` + physical bounding box
        + `tokens_used: 0`.
        """
        sockets = self.discover_devtools_sockets(serial) if mock_tabs is None else ["chrome_devtools_remote"]
        socket_to_use = sockets[0] if sockets else "chrome_devtools_remote"

        if mock_tabs is None:
            self.forward_socket(serial, local_port=local_port, socket_name=socket_to_use)
            active_port = self.active_forwards.get(f"{serial}:{socket_to_use}", local_port)
            tabs = self.list_open_tabs(local_port=active_port)
        else:
            active_port = local_port
            tabs = mock_tabs

        # Pick first inspectable page tab with a webSocketDebuggerUrl
        target_tab: Optional[Dict[str, Any]] = None
        for t in tabs:
            if t.get("type", "page") == "page" and t.get("webSocketDebuggerUrl"):
                target_tab = t
                break
        if target_tab is None and tabs:
            target_tab = tabs[0]

        if not target_tab or not target_tab.get("webSocketDebuggerUrl"):
            return {
                "status": "NO_DEBUGGABLE_TAB",
                "serial": serial,
                "found": False,
                "socket_name": socket_to_use,
                "local_port": active_port,
                "phys_x": 0,
                "phys_y": 0,
                "bounds": {"left": 0, "top": 0, "right": 0, "bottom": 0},
                "tokens_used": 0,
            }

        js_expr = f"({CDP_LOCATE_ELEMENT_JS_TEMPLATE.strip()})({json.dumps(selector_or_type)})"
        eval_res = self.evaluate_js_on_tab(
            ws_url=target_tab["webSocketDebuggerUrl"],
            expression=js_expr,
            mock_cdp_response=mock_eval_result,
        )

        dom_data = eval_res.get("value") if isinstance(eval_res.get("value"), dict) else {}
        if not dom_data or not dom_data.get("found"):
            return {
                "status": "ELEMENT_NOT_FOUND",
                "serial": serial,
                "found": False,
                "selector_or_type": selector_or_type,
                "socket_name": socket_to_use,
                "tab_url": target_tab.get("url", ""),
                "phys_x": 0,
                "phys_y": 0,
                "bounds": {"left": 0, "top": 0, "right": 0, "bottom": 0},
                "viewport_metrics": dom_data.get("viewport_metrics", {}),
                "tokens_used": 0,
            }

        css_rect = dom_data.get("css_rect", {})
        vp_metrics = dom_data.get("viewport_metrics", {})

        center_css_x = float(css_rect.get("center_x", 0.0))
        center_css_y = float(css_rect.get("center_y", 0.0))
        phys_x, phys_y = self.css_to_physical_screen_coords(
            css_x=center_css_x,
            css_y=center_css_y,
            viewport_metrics=vp_metrics,
            screen_size=screen_size,
        )

        left_px, top_px = self.css_to_physical_screen_coords(
            css_x=float(css_rect.get("left", 0.0)),
            css_y=float(css_rect.get("top", 0.0)),
            viewport_metrics=vp_metrics,
            screen_size=screen_size,
        )
        right_px, bottom_px = self.css_to_physical_screen_coords(
            css_x=float(css_rect.get("right", 0.0)),
            css_y=float(css_rect.get("bottom", 0.0)),
            viewport_metrics=vp_metrics,
            screen_size=screen_size,
        )

        return {
            "status": "ELEMENT_LOCATED",
            "serial": serial,
            "found": True,
            "matched_type": dom_data.get("matched_type", selector_or_type),
            "matched_selector": dom_data.get("matched_selector", selector_or_type),
            "tag_name": dom_data.get("tag_name", ""),
            "id": dom_data.get("id", ""),
            "class_name": dom_data.get("class_name", ""),
            "text": dom_data.get("text", ""),
            "socket_name": socket_to_use,
            "tab_url": target_tab.get("url", ""),
            "tab_title": target_tab.get("title", ""),
            "phys_x": phys_x,
            "phys_y": phys_y,
            "physical_coords": (phys_x, phys_y),
            "bounds": {
                "left": left_px,
                "top": top_px,
                "right": right_px,
                "bottom": bottom_px,
            },
            "css_rect": css_rect,
            "viewport_metrics": vp_metrics,
            "navigator_webdriver": vp_metrics.get("webdriver"),
            "tokens_used": 0,
        }

    def tap_dom_element_physically(
        self,
        serial: str,
        selector: str = "auto",
        touch_engine: Optional[Any] = None,
        screen_size: Tuple[int, int] = (1260, 2800),
        mock_tabs: Optional[List[Dict[str, Any]]] = None,
        mock_eval_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Locates a DOM element or CAPTCHA widget via read-only CDP `Runtime.evaluate`,
        transforms its CSS bounding box to physical Android screen coordinates, and
        executes the touch via physical Android input (`HumanTouchEngine` or `adb shell input tap`)
        so zero browser automation flags (`Input.dispatchTouchEvent` / `navigator.webdriver`)
        are ever triggered!
        """
        loc = self.locate_captcha_or_element_via_cdp(
            serial=serial,
            selector_or_type=selector,
            screen_size=screen_size,
            mock_tabs=mock_tabs,
            mock_eval_result=mock_eval_result,
        )
        if not loc.get("found"):
            return {
                "status": "TAP_SKIPPED_NOT_FOUND",
                "serial": serial,
                "selector": selector,
                "location": loc,
                "tap_result": None,
                "tokens_used": 0,
            }

        phys_x = int(loc["phys_x"])
        phys_y = int(loc["phys_y"])
        bounds = loc.get("bounds")

        engine = touch_engine or self.touch_engine
        if engine is not None and hasattr(engine, "human_tap"):
            tap_res = engine.human_tap(
                serial=serial,
                x=phys_x,
                y=phys_y,
                bounds=bounds,
            )
        else:
            self.adb.shell(serial, f"input tap {phys_x} {phys_y}")
            tap_res = {
                "status": "ADB_TAP_OK",
                "serial": serial,
                "target": [phys_x, phys_y],
                "actual_point": [phys_x, phys_y],
            }

        return {
            "status": "CDP_PHYSICAL_TAP_OK",
            "serial": serial,
            "selector": selector,
            "matched_type": loc.get("matched_type"),
            "phys_x": phys_x,
            "phys_y": phys_y,
            "bounds": bounds,
            "location": loc,
            "tap_result": tap_res,
            "webdriver_clean": not bool(loc.get("navigator_webdriver", False)),
            "tokens_used": 0,
        }
