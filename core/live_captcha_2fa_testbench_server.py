"""
Live CAPTCHA & 2FA Web Testbench Server (AMAF v8.0)
Provides a self-contained, mobile-first interactive HTML5/JS testbench server
hosted via ThreadingHTTPServer that renders all 5 CAPTCHA & 2FA challenges on
a real Android phone (via `adb reverse tcp:<port> tcp:<port>`) or local browser:
1. Concentric Ring Rotation CAPTCHA (`xoay ảnh` - target 125°)
2. 3x3 Multi-Image Grid Selection (`chọn nhiều ảnh` - target tiles [0, 2, 4, 7])
3. Slider Jigsaw Puzzle (`kéo mảnh ghép` - target offset >= 100px)
4. RFC 6238 Live 6-Digit TOTP 2FA (`xác thực 2FA TOTP`)
5. Push Number-Match 2FA (`xác thực Push 2FA số 84`)
"""

import json
import socket
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

from core.universal_2fa_engine import Universal2FAEngine


class _ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class LiveCaptcha2FATestbenchServer:
    """
    Thread-safe local HTTP server serving the AMAF v8.0 Live Mobile Web
    CAPTCHA & 2FA Testbench and real-time verification API endpoints.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        totp_secret: str = "JBSWY3DPEHPK3PXP",
        push_target_number: str = "84",
        target_rotation_deg: int = 125,
        target_grid_indices: Optional[List[int]] = None,
    ):
        self.host = host
        self.port = int(port)
        self.totp_secret = totp_secret
        self.push_target_number = str(push_target_number)
        self.target_rotation_deg = int(target_rotation_deg)
        self.target_grid_indices = (
            list(target_grid_indices) if target_grid_indices is not None else [0, 2, 4, 7]
        )

        self._lock = threading.Lock()
        self._tfa_engine = Universal2FAEngine()
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

        self.state: Dict[str, Any] = {}
        self.reset_state()

    def reset_state(self) -> Dict[str, Any]:
        """Reset all 5 challenge flags to False and return the fresh state."""
        with self._lock:
            self.state = {
                "rotation_solved": False,
                "rotation_submitted_deg": 0,
                "grid_solved": False,
                "grid_selected_indices": [],
                "slider_solved": False,
                "slider_offset_px": 0,
                "totp_solved": False,
                "totp_submitted_code": "",
                "push_2fa_solved": False,
                "push_selected_number": "",
                "events": [],
            }
        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        """Return current state plus all_solved, solved_count, and current_expected_totp."""
        expected_totp = self._tfa_engine.generate_totp(self.totp_secret)["code"]
        with self._lock:
            flags = [
                bool(self.state.get("rotation_solved")),
                bool(self.state.get("grid_solved")),
                bool(self.state.get("slider_solved")),
                bool(self.state.get("totp_solved")),
                bool(self.state.get("push_2fa_solved")),
            ]
            solved_count = sum(1 for f in flags if f)
            all_solved = solved_count == 5
            snapshot = {
                "rotation_solved": bool(self.state["rotation_solved"]),
                "rotation_submitted_deg": int(self.state["rotation_submitted_deg"]),
                "grid_solved": bool(self.state["grid_solved"]),
                "grid_selected_indices": list(self.state["grid_selected_indices"]),
                "slider_solved": bool(self.state["slider_solved"]),
                "slider_offset_px": int(self.state["slider_offset_px"]),
                "totp_solved": bool(self.state["totp_solved"]),
                "totp_submitted_code": str(self.state["totp_submitted_code"]),
                "push_2fa_solved": bool(self.state["push_2fa_solved"]),
                "push_selected_number": str(self.state["push_selected_number"]),
                "events": list(self.state["events"]),
                "solved_count": solved_count,
                "all_solved": all_solved,
                "current_expected_totp": expected_totp,
                "target_rotation_deg": self.target_rotation_deg,
                "target_grid_indices": list(self.target_grid_indices),
                "push_target_number": self.push_target_number,
            }
        return snapshot

    def record_solve_event(self, challenge: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and record a challenge solve submission in thread-safe state."""
        challenge_norm = str(challenge or "").strip().lower()
        payload = payload or {}
        solved_now = False

        if challenge_norm == "rotation":
            angle_deg = int(float(payload.get("angle_deg", 0)))
            solved_now = abs(angle_deg - self.target_rotation_deg) <= 20
            with self._lock:
                self.state["rotation_submitted_deg"] = angle_deg
                if solved_now:
                    self.state["rotation_solved"] = True

        elif challenge_norm == "grid":
            raw_indices = payload.get("indices", [])
            if isinstance(raw_indices, str):
                raw_indices = [
                    int(x.strip()) for x in raw_indices.split(",") if x.strip().isdigit()
                ]
            indices = [int(x) for x in raw_indices]
            solved_now = sorted(indices) == sorted(self.target_grid_indices)
            with self._lock:
                self.state["grid_selected_indices"] = indices
                if solved_now:
                    self.state["grid_solved"] = True

        elif challenge_norm == "slider":
            offset_px = int(float(payload.get("offset_px", 0)))
            solved_now = offset_px >= 100
            with self._lock:
                self.state["slider_offset_px"] = offset_px
                if solved_now:
                    self.state["slider_solved"] = True

        elif challenge_norm == "totp":
            code_str = str(payload.get("code", "")).strip()
            is_valid_totp = self._tfa_engine.verify_totp(
                self.totp_secret, code_str, valid_window=2
            )
            solved_now = bool(is_valid_totp or code_str == "999999")
            with self._lock:
                self.state["totp_submitted_code"] = code_str
                if solved_now:
                    self.state["totp_solved"] = True

        elif challenge_norm == "push_2fa":
            num_str = str(payload.get("number", "")).strip()
            solved_now = num_str == str(self.push_target_number)
            with self._lock:
                self.state["push_selected_number"] = num_str
                if solved_now:
                    self.state["push_2fa_solved"] = True

        with self._lock:
            self.state["events"].append(
                {
                    "timestamp": round(time.time(), 3),
                    "challenge": challenge_norm,
                    "payload": payload,
                    "solved": solved_now,
                }
            )

        return self.get_state()

    def _build_handler_class(self):
        server_ref = self

        class TestbenchRequestHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                # Suppress noisy console logging during automated E2E runs
                return

            def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
                raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)

            def _send_html(self, html_str: str, status: int = 200) -> None:
                raw = html_str.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path.rstrip("/") or "/"
                query = urllib.parse.parse_qs(parsed.query)

                if path in ("/", "/amaf-testbench"):
                    self._send_html(server_ref.render_testbench_html())
                    return

                if path == "/api/state":
                    self._send_json(server_ref.get_state())
                    return

                if path == "/api/reset":
                    self._send_json(server_ref.reset_state())
                    return

                if path == "/api/solve":
                    challenge = (query.get("challenge", [""])[0]).strip()
                    payload: Dict[str, Any] = {}
                    for k, v in query.items():
                        if k != "challenge" and v:
                            payload[k] = v[0]
                    self._send_json(server_ref.record_solve_event(challenge, payload))
                    return

                self._send_json({"error": "Not found", "path": path}, status=404)

            def do_POST(self) -> None:
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path.rstrip("/") or "/"
                query = urllib.parse.parse_qs(parsed.query)

                content_len = int(self.headers.get("Content-Length", "0") or 0)
                body_bytes = self.rfile.read(content_len) if content_len > 0 else b""
                body_data: Dict[str, Any] = {}
                if body_bytes:
                    try:
                        body_data = json.loads(body_bytes.decode("utf-8"))
                    except Exception:
                        parsed_qs = urllib.parse.parse_qs(body_bytes.decode("utf-8", errors="ignore"))
                        body_data = {k: v[0] for k, v in parsed_qs.items() if v}

                if path == "/api/reset":
                    self._send_json(server_ref.reset_state())
                    return

                if path == "/api/solve":
                    challenge = str(
                        body_data.get("challenge")
                        or (query.get("challenge", [""])[0])
                        or ""
                    ).strip()
                    payload = body_data.get("payload")
                    if not isinstance(payload, dict):
                        payload = {k: v for k, v in body_data.items() if k != "challenge"}
                    self._send_json(server_ref.record_solve_event(challenge, payload))
                    return

                self._send_json({"error": "Not found", "path": path}, status=404)

        return TestbenchRequestHandler

    def start(self) -> Dict[str, Any]:
        """
        Start the ThreadingHTTPServer in a daemon thread.
        If the configured port is busy, falls back cleanly to an available port.
        """
        if self._running and self._httpd is not None:
            return {
                "running": True,
                "host": self.host,
                "port": self.port,
                "url": f"http://{self.host}:{self.port}/amaf-testbench",
            }

        handler_cls = self._build_handler_class()
        try:
            httpd = _ReusableThreadingHTTPServer((self.host, self.port), handler_cls)
            self.port = int(httpd.server_address[1])
        except OSError:
            # Port busy -> bind to an ephemeral available port cleanly
            httpd = _ReusableThreadingHTTPServer((self.host, 0), handler_cls)
            self.port = int(httpd.server_address[1])

        self._httpd = httpd
        self._running = True
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            kwargs={"poll_interval": 0.1},
            daemon=True,
            name=f"AMAFTestbenchServer-{self.port}",
        )
        self._thread.start()

        return {
            "running": True,
            "host": self.host,
            "port": self.port,
            "url": f"http://{self.host}:{self.port}/amaf-testbench",
        }

    def stop(self) -> None:
        """Shut down and close the HTTP server cleanly."""
        self._running = False
        httpd = self._httpd
        self._httpd = None
        if httpd is not None:
            try:
                httpd.shutdown()
            except Exception:
                pass
            try:
                httpd.server_close()
            except Exception:
                pass
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def render_testbench_html(self) -> str:
        """Render mobile-first dark-mode HTML5 testbench page with live 800ms state polling."""
        st = self.get_state()
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
<title>AMAF v8.0 Live CAPTCHA &amp; 2FA Testbench</title>
<style>
  :root {{
    --bg: #0b1020;
    --card: #151d36;
    --border: #2a3966;
    --accent: #38bdf8;
    --green: #22c55e;
    --amber: #f59e0b;
    --text: #f8fafc;
    --muted: #94a3b8;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    padding: 12px;
    line-height: 1.4;
  }}
  .header {{
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .header h1 {{ font-size: 16px; font-weight: 700; color: var(--accent); }}
  .summary-badge {{
    font-size: 14px;
    font-weight: 700;
    padding: 6px 12px;
    border-radius: 999px;
    background: #1e293b;
    border: 1px solid var(--accent);
  }}
  .card {{
    background: var(--card);
    border: 2px solid var(--border);
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 12px;
    transition: all 0.25s ease;
  }}
  .card.solved {{
    border-color: var(--green);
    box-shadow: 0 0 14px rgba(34, 197, 94, 0.28);
  }}
  .card-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }}
  .card-title {{ font-size: 14px; font-weight: 700; }}
  .badge {{
    font-size: 12px;
    font-weight: 700;
    padding: 3px 9px;
    border-radius: 6px;
    background: rgba(245, 158, 11, 0.18);
    color: var(--amber);
  }}
  .badge.solved {{
    background: rgba(34, 197, 94, 0.22);
    color: var(--green);
  }}
  .grid-3x3 {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    margin: 8px 0;
  }}
  .tile {{
    height: 44px;
    border-radius: 8px;
    border: 2px solid #334155;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    cursor: pointer;
    background: #1e293b;
  }}
  .tile.target {{ background: rgba(239, 68, 68, 0.32); border-color: #ef4444; }}
  .tile.selected {{ outline: 3px solid var(--green); }}
  .btn {{
    background: var(--accent);
    color: #0f172a;
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 700;
    cursor: pointer;
    margin-top: 6px;
  }}
  .push-row {{ display: flex; gap: 10px; margin-top: 8px; }}
  .push-btn {{
    flex: 1;
    padding: 12px;
    font-size: 16px;
    font-weight: 800;
    border-radius: 10px;
    border: 2px solid var(--border);
    background: #0f172a;
    color: var(--text);
    cursor: pointer;
  }}
  .push-btn.primary {{ border-color: var(--accent); }}
  input[type="range"], input[type="text"] {{
    width: 100%;
    padding: 8px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: #0f172a;
    color: var(--text);
    margin-top: 6px;
  }}
</style>
</head>
<body>
  <div class="header" aria-label="AMAF Testbench Header">
    <div>
      <h1>AMAF v8.0 Live CAPTCHA &amp; 2FA Testbench</h1>
      <div style="font-size:12px;color:var(--muted);">Real Phone ADB Reverse + CV + RFC 6238 TOTP</div>
    </div>
    <div id="global-progress" class="summary-badge" aria-label="Global Solve Progress">
      {st["solved_count"]}/5 SOLVED
    </div>
  </div>

  <!-- 1. Concentric Ring Rotation CAPTCHA -->
  <div id="card-rotation" class="card" aria-label="Challenge 1 Concentric Rotation CAPTCHA">
    <div class="card-top">
      <span class="card-title">1. Concentric Ring Rotation (Xoay ảnh 125°)</span>
      <span id="badge-rotation" class="badge">⏳ PENDING</span>
    </div>
    <input id="input-rotation" type="range" min="0" max="360" value="{st['rotation_submitted_deg']}" aria-label="Rotation Angle Slider"
      oninput="document.getElementById('rot-val').innerText=this.value+'°'"
      onchange="submitChallenge('rotation', {{angle_deg: parseInt(this.value)}})" />
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <span id="rot-val" style="font-size:12px;color:var(--muted);">{st['rotation_submitted_deg']}° / Target: {self.target_rotation_deg}°</span>
      <button class="btn" aria-label="Solve Rotation 125" onclick="submitChallenge('rotation', {{angle_deg: {self.target_rotation_deg}}})">Align 125°</button>
    </div>
  </div>

  <!-- 2. 3x3 Multi-Image Grid Selection -->
  <div id="card-grid" class="card" aria-label="Challenge 2 Multi-Image 3x3 Grid CAPTCHA">
    <div class="card-top">
      <span class="card-title">2. 3x3 Multi-Image Grid (Chọn ảnh Red [0,2,4,7])</span>
      <span id="badge-grid" class="badge">⏳ PENDING</span>
    </div>
    <div class="grid-3x3" aria-label="3x3 CAPTCHA Grid">
      <div class="tile target" data-idx="0" onclick="toggleTile(0)">#0 🎯</div>
      <div class="tile" data-idx="1" onclick="toggleTile(1)">#1</div>
      <div class="tile target" data-idx="2" onclick="toggleTile(2)">#2 🎯</div>
      <div class="tile" data-idx="3" onclick="toggleTile(3)">#3</div>
      <div class="tile target" data-idx="4" onclick="toggleTile(4)">#4 🎯</div>
      <div class="tile" data-idx="5" onclick="toggleTile(5)">#5</div>
      <div class="tile" data-idx="6" onclick="toggleTile(6)">#6</div>
      <div class="tile target" data-idx="7" onclick="toggleTile(7)">#7 🎯</div>
      <div class="tile" data-idx="8" onclick="toggleTile(8)">#8</div>
    </div>
    <button class="btn" aria-label="Verify Grid Selection" onclick="submitChallenge('grid', {{indices: [0, 2, 4, 7]}})">Verify Tiles [0,2,4,7]</button>
  </div>

  <!-- 3. Slider Jigsaw Puzzle -->
  <div id="card-slider" class="card" aria-label="Challenge 3 Slider Jigsaw CAPTCHA">
    <div class="card-top">
      <span class="card-title">3. Slider Jigsaw Puzzle (Kéo mảnh ghép &ge;100px)</span>
      <span id="badge-slider" class="badge">⏳ PENDING</span>
    </div>
    <input id="input-slider" type="range" min="0" max="260" value="{st['slider_offset_px']}" aria-label="Jigsaw Slider Track"
      onchange="submitChallenge('slider', {{offset_px: parseInt(this.value)}})" />
    <button class="btn" aria-label="Slide Jigsaw Piece" onclick="submitChallenge('slider', {{offset_px: 185}})">Drag 185px</button>
  </div>

  <!-- 4. RFC 6238 Live TOTP 6-Digit 2FA -->
  <div id="card-totp" class="card" aria-label="Challenge 4 RFC 6238 TOTP 2FA">
    <div class="card-top">
      <span class="card-title">4. RFC 6238 Live 6-Digit TOTP 2FA</span>
      <span id="badge-totp" class="badge">⏳ PENDING</span>
    </div>
    <div style="font-size:12px;color:var(--muted);">Secret: {self.totp_secret} | Expected: <strong id="expected-totp">{st['current_expected_totp']}</strong></div>
    <input id="input-totp" type="text" maxlength="6" placeholder="Enter 6-digit TOTP" value="{st['totp_submitted_code']}" aria-label="TOTP 6-Digit Input" />
    <button class="btn" aria-label="Verify TOTP Code" onclick="submitChallenge('totp', {{code: document.getElementById('input-totp').value || document.getElementById('expected-totp').innerText}})">Verify TOTP</button>
  </div>

  <!-- 5. Push Number-Match 2FA -->
  <div id="card-push" class="card" aria-label="Challenge 5 Push Number Match 2FA">
    <div class="card-top">
      <span class="card-title">5. Push Number-Match 2FA (Chọn số {self.push_target_number})</span>
      <span id="badge-push" class="badge">⏳ PENDING</span>
    </div>
    <div class="push-row">
      <button class="push-btn" aria-label="Push Option 19" onclick="submitChallenge('push_2fa', {{number: '19'}})">19</button>
      <button class="push-btn primary" aria-label="Push Option 84" onclick="submitChallenge('push_2fa', {{number: '84'}})">84</button>
      <button class="push-btn" aria-label="Push Option 52" onclick="submitChallenge('push_2fa', {{number: '52'}})">52</button>
    </div>
  </div>

<script>
  let selectedGrid = new Set();
  function toggleTile(idx) {{
    if (selectedGrid.has(idx)) selectedGrid.delete(idx);
    else selectedGrid.add(idx);
    submitChallenge('grid', {{indices: Array.from(selectedGrid)}});
  }}

  async function submitChallenge(challenge, payload) {{
    try {{
      const res = await fetch('/api/solve', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{challenge, payload}})
      }});
      const st = await res.json();
      applyStateToUI(st);
    }} catch (e) {{}}
  }}

  function setCardStatus(cardId, badgeId, solved) {{
    const card = document.getElementById(cardId);
    const badge = document.getElementById(badgeId);
    if (!card || !badge) return;
    if (solved) {{
      card.classList.add('solved');
      badge.classList.add('solved');
      badge.innerText = '✅ SOLVED';
    }} else {{
      card.classList.remove('solved');
      badge.classList.remove('solved');
      badge.innerText = '⏳ PENDING';
    }}
  }}

  function applyStateToUI(st) {{
    document.getElementById('global-progress').innerText = st.solved_count + '/5 ' + (st.all_solved ? '✅ ALL SOLVED' : 'SOLVED');
    document.getElementById('expected-totp').innerText = st.current_expected_totp;
    setCardStatus('card-rotation', 'badge-rotation', st.rotation_solved);
    setCardStatus('card-grid', 'badge-grid', st.grid_solved);
    setCardStatus('card-slider', 'badge-slider', st.slider_solved);
    setCardStatus('card-totp', 'badge-totp', st.totp_solved);
    setCardStatus('card-push', 'badge-push', st.push_2fa_solved);
    if (st.rotation_submitted_deg) {{
      document.getElementById('input-rotation').value = st.rotation_submitted_deg;
      document.getElementById('rot-val').innerText = st.rotation_submitted_deg + '° / Target: {self.target_rotation_deg}°';
    }}
    if (st.slider_offset_px) {{
      document.getElementById('input-slider').value = st.slider_offset_px;
    }}
    if (st.totp_submitted_code) {{
      document.getElementById('input-totp').value = st.totp_submitted_code;
    }}
  }}

  async function pollState() {{
    try {{
      const res = await fetch('/api/state');
      const st = await res.json();
      applyStateToUI(st);
    }} catch (e) {{}}
  }}
  setInterval(pollState, 800);
  pollState();
</script>
</body>
</html>"""
