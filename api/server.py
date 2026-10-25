"""
Lightweight REST API Server for Multi-Agent & Multi-IDE Integration (AMAF 4.0)
Built on standard library http.server (Zero external dependencies).
Enables Cursor, OpenCode, Kilo Code, and Antigravity agents to control the farm over HTTP.
"""

import sys
import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.farm_config import DEFAULT_FARM_DEVICES
from core.process_manager import ProcessManager
from core.avd_optimizer import AVDOptimizer
from core.mock_otp_service import MockOTPService
from core.adb_wrapper import ADBWrapper
from core.hardware_simulator import HardwareSimulator
from core.scrcpy_manager import ScrcpyManager
from core.real_device_manager import RealDeviceManager
from core.group_control_broadcaster import GroupControlBroadcaster
from core.multi_app_manager import MultiAppAutomationManager
from agents.loop_orchestrator import LoopOrchestrator
from agents.device_lock_manager import DeviceLockManager
from agents.bug_reporter import BugReporter


class FarmAPIHandler(BaseHTTPRequestHandler):
    adb = ADBWrapper()
    real_mgr = RealDeviceManager(adb)
    broadcaster = GroupControlBroadcaster(adb, real_mgr)
    multi_app_mgr = MultiAppAutomationManager(adb, real_mgr, broadcaster)
    proc_mgr = ProcessManager(adb, real_mgr)
    hardware = HardwareSimulator(adb)
    scrcpy_mgr = ScrcpyManager()
    lock_mgr = DeviceLockManager()
    reporter = BugReporter()

    def _send_json(self, status_code: int, data: Any):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _read_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            raw = self.rfile.read(length).decode("utf-8")
            try:
                return json.loads(raw)
            except Exception:
                return {}
        return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/status" or path == "/":
            states = self.proc_mgr.get_hybrid_farm_state()
            locks = self.lock_mgr.list_active_locks()
            self._send_json(200, {
                "status": "ok",
                "farm_mode": self.real_mgr.get_farm_mode(),
                "devices": states,
                "locks": locks
            })
        elif path == "/api/real-devices":
            real_devs = self.real_mgr.discover_real_devices(include_unauthorized=True)
            self._send_json(200, {
                "farm_mode": self.real_mgr.get_farm_mode(),
                "real_devices_count": len(real_devs),
                "real_devices": real_devs
            })
        elif path == "/api/apps/list":
            query = urllib.parse.parse_qs(parsed.query)
            serial = query.get("serial", ["emulator-5554"])[0]
            inc_sys = query.get("include_system", ["false"])[0].lower() == "true"
            res = self.multi_app_mgr.list_installed_apps(serial, include_system=inc_sys)
            self._send_json(200, res)
        elif path == "/api/memory/macros":
            from core.memory_manager import MemoryManager
            self._send_json(200, {"macros": MemoryManager().list_macros()})
        elif path == "/api/reports":
            reports = self.reporter.list_reports()
            self._send_json(200, {"reports": reports})
        elif path == "/api/otp/latest":
            query = urllib.parse.parse_qs(parsed.query)
            phone = query.get("phone", [""])[0]
            otp = MockOTPService()
            code = otp.get_latest_otp(phone)
            self._send_json(200, {"phone": phone, "code": code})
        elif path == "/api/memory/summary":
            from core.memory_manager import MemoryManager
            self._send_json(200, MemoryManager().get_summary())
        elif path == "/api/memory/patches":
            from core.memory_manager import MemoryManager
            self._send_json(200, {"patches": MemoryManager().get_patches()})
        elif path == "/api/memory/prompts":
            from core.memory_manager import MemoryManager
            data = MemoryManager()._read_data()
            self._send_json(200, {"prompts": data.get("prompts", {})})
        elif path == "/api/kanban/board":
            from core.kanban_board import KanbanBoard
            self._send_json(200, KanbanBoard().get_board_summary())
        elif path == "/api/kanban/cards":
            from core.kanban_board import KanbanBoard
            query = urllib.parse.parse_qs(parsed.query)
            state = query.get("state", [None])[0]
            self._send_json(200, {"cards": KanbanBoard().list_cards(state=state)})
        else:
            self._send_json(404, {"error": "Not Found", "path": path})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        # OTP routes (0 VND carrier cost)
        if path == "/api/otp/generate":
            phone = body.get("phone", "0941189263")
            code = MockOTPService().generate_otp(phone)
            self._send_json(200, {"phone": phone, "code": code})

        elif path == "/api/otp/verify":
            phone = body.get("phone", "")
            code = body.get("code", "")
            valid = MockOTPService().verify_otp(phone, code)
            self._send_json(200, {"phone": phone, "valid": valid})

        # Route: /api/start-all
        elif path == "/api/start-all":
            res = self.proc_mgr.start_farm(4, headless=True)
            self._send_json(200, {"results": res})

        # Route: /api/matrix/run
        elif path == "/api/matrix/run":
            from agents.agents_orchestrator import AgentsOrchestrator
            orch = AgentsOrchestrator()
            res = orch.run_parallel_matrix()
            self._send_json(200, res)

        # Route: /api/pipeline/run (Autonomous Pipeline Director)
        elif path == "/api/pipeline/run":
            from agents.autonomous_pipeline_director import AutonomousPipelineDirector
            director = AutonomousPipelineDirector()
            res = director.run_4_device_autonomous_pipeline()
            self._send_json(200, res)

        # Route: /api/evolution/run (16-Subagent Self-Evolution Loop)
        elif path == "/api/evolution/run":
            from agents.self_evolution_engine import SelfEvolutionEngine
            iterations = int(body.get("iterations", 1))
            pkg = body.get("package", "com.android.settings")
            engine = SelfEvolutionEngine()
            res = engine.run_evolution_loop(iterations=iterations, package_name=pkg)
            self._send_json(200, res)

        # Route: /api/apps/state (grant_permissions, clear_data, snapshot, restore)
        elif path == "/api/apps/state":
            act = body.get("action", "grant_permissions")
            serial = body.get("serial", "emulator-5554")
            pkg = body.get("package", "com.android.settings")
            label = body.get("label", "checkpoint_1")
            if act == "grant_permissions":
                res = self.multi_app_mgr.grant_all_runtime_permissions(serial, pkg)
            elif act == "clear_data":
                res = self.multi_app_mgr.clear_app_data(serial, pkg)
            elif act == "snapshot":
                res = self.multi_app_mgr.snapshot_app_state(serial, pkg, label=label)
            else:
                res = self.multi_app_mgr.restore_app_state(serial, pkg, label=label)
            self._send_json(200, res)

        # Route: /api/apps/deeplink
        elif path == "/api/apps/deeplink":
            serial = body.get("serial", "emulator-5554")
            uri = body.get("uri", "https://example.com")
            pkg = body.get("package")
            res = self.multi_app_mgr.open_deep_link(serial, uri, package=pkg)
            self._send_json(200, res)

        # Route: /api/apps/flow (Declarative Multi-App Flow)
        elif path == "/api/apps/flow":
            steps = body.get("steps", [])
            serials = body.get("serials")
            res = self.multi_app_mgr.run_declarative_multi_app_flow(flow_steps=steps, serials=serials)
            self._send_json(200, res)

        # Route: /api/apps/crawl (UI State-Graph Crawler)
        elif path == "/api/apps/crawl":
            from agents.multi_app_crawler_subagent import MultiAppCrawlerSubagent
            serial = body.get("serial", "emulator-5554")
            pkg = body.get("package", "com.android.settings")
            steps = int(body.get("max_steps", 3))
            crawler = MultiAppCrawlerSubagent(self.adb)
            res = crawler.crawl_application(serial, pkg, max_steps=steps)
            self._send_json(200, res)

        # Route: /api/farm-mode (Switch HYBRID / AVD_ONLY / REAL_ONLY)
        elif path == "/api/farm-mode":
            mode = body.get("mode", "HYBRID")
            res = self.real_mgr.set_farm_mode(mode)
            self._send_json(200, res)

        # Route: /api/real-devices/connect-wireless
        elif path == "/api/real-devices/connect-wireless":
            ip = body.get("ip", "")
            port = int(body.get("port", 5555))
            usb_serial = body.get("usb_serial", "")
            if usb_serial:
                ok, msg = self.real_mgr.enable_wireless_adb(usb_serial, port)
            else:
                ok, msg = self.real_mgr.connect_wireless_device(ip, port)
            self._send_json(200, {"success": ok, "message": msg})

        # Route: /api/group/broadcast (Multi-Device Synchronized Broadcast)
        elif path == "/api/group/broadcast":
            act = body.get("action", "tap")
            serials = body.get("serials")
            gf = body.get("group_filter", "ALL")
            if act == "tap":
                res = self.broadcaster.broadcast_tap(
                    float(body.get("x", 360)), float(body.get("y", 800)),
                    serials=serials, group_filter=gf
                )
            elif act == "swipe":
                res = self.broadcaster.broadcast_swipe(
                    float(body.get("x", 360)), float(body.get("y", 1100)),
                    float(body.get("x2", 360)), float(body.get("y2", 400)),
                    serials=serials, group_filter=gf
                )
            elif act == "text":
                res = self.broadcaster.broadcast_text(str(body.get("text", "")), serials=serials, group_filter=gf)
            elif act == "key":
                res = self.broadcaster.broadcast_key(str(body.get("text", "HOME")), serials=serials, group_filter=gf)
            elif act == "launch_app":
                res = self.broadcaster.broadcast_launch_app(str(body.get("text", "com.android.settings")), serials=serials, group_filter=gf)
            else:
                res = self.broadcaster.broadcast_shell(str(body.get("text", "getprop ro.product.model")), serials=serials, group_filter=gf)
            self._send_json(200, res)

        # Route: /api/security/audit
        elif path == "/api/security/audit":
            from agents.security_auditor_subagent import SecurityAuditorSubagent
            serial = body.get("serial", "emulator-5554")
            pkg = body.get("package", "com.android.settings")
            sec = SecurityAuditorSubagent()
            res = sec.audit_package_security(serial, pkg)
            self._send_json(200, res)

        # Route: /api/regression/verify
        elif path == "/api/regression/verify":
            from agents.regression_verifier_subagent import RegressionVerifierSubagent
            serial = body.get("serial", "emulator-5554")
            pkg = body.get("package", "com.android.settings")
            patch_info = body.get("patch_info", {})
            reg = RegressionVerifierSubagent()
            res = reg.verify_patch_on_device(patch_info, serial, pkg)
            self._send_json(200, res)

        # Route: /api/stop-all
        elif path == "/api/stop-all":
            self.scrcpy_mgr.close_all()
            res = self.proc_mgr.stop_farm()
            self._send_json(200, {"results": res})

        # Device specific: /api/device/{serial}/...
        elif path.startswith("/api/device/"):
            parts = path.strip("/").split("/")
            if len(parts) >= 4:
                serial = parts[2]
                action = parts[3]

                if action == "start":
                    dev = next((d for d in DEFAULT_FARM_DEVICES if d["serial"] == serial), None)
                    if dev:
                        ok, msg = self.proc_mgr.start_instance(dev["name"], dev["port"], headless=True)
                        self._send_json(200, {"success": ok, "message": msg})
                    else:
                        self._send_json(404, {"error": f"Unknown serial {serial}"})

                elif action == "stop":
                    self.scrcpy_mgr.close_viewer(serial)
                    ok, msg = self.proc_mgr.stop_instance(serial)
                    self._send_json(200, {"success": ok, "message": msg})

                elif action == "view":
                    ok, msg = self.scrcpy_mgr.open_viewer(serial)
                    self._send_json(200, {"success": ok, "message": msg})

                elif action == "lock":
                    agent_id = body.get("agent_id", "external_agent")
                    task = body.get("task_name", "task")
                    ok = self.lock_mgr.acquire(serial, agent_id, task, lease_seconds=body.get("lease_seconds", 300))
                    self._send_json(200, {"acquired": ok, "serial": serial, "agent_id": agent_id})

                elif action == "unlock":
                    agent_id = body.get("agent_id", "")
                    ok = self.lock_mgr.release(serial, agent_id)
                    self._send_json(200, {"released": ok, "serial": serial})

                elif action == "sms":
                    phone = body.get("phone", "+84901234567")
                    code = body.get("code", "123456")
                    ok, msg = self.hardware.send_sms_otp(serial, phone, f"Ma OTP: {code}")
                    self._send_json(200, {"success": ok, "message": msg})

                elif action == "fingerprint":
                    ok, msg = self.hardware.touch_fingerprint(serial, body.get("finger_id", 1))
                    self._send_json(200, {"success": ok, "message": msg})

                elif action == "gps":
                    lat = float(body.get("lat", 10.776889))
                    lng = float(body.get("lng", 106.700806))
                    ok, msg = self.hardware.set_gps_location(serial, lat, lng)
                    self._send_json(200, {"success": ok, "message": msg})

                elif action == "optimize":
                    opt = AVDOptimizer(self.adb)
                    res = opt.optimize_device(serial)
                    self._send_json(200, {"success": True, "result": res})

                elif action == "loop":
                    goal = body.get("goal", "Kiem tra luong dang nhap")
                    pkg = body.get("package", "com.android.settings")
                    orch = LoopOrchestrator(serial, self.adb)
                    res = orch.run_autonomous_loop(goal, pkg)
                    self._send_json(200, {"success": True, "result": res})
                else:
                    self._send_json(400, {"error": f"Unknown device action {action}"})
            else:
                self._send_json(400, {"error": "Invalid path format"})
        else:
            self._send_json(404, {"error": "Not Found"})


def run_server(port: int = 8088):
    server = HTTPServer(("127.0.0.1", port), FarmAPIHandler)
    print(f"Android Farm API Server listening on http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("API Server stopped.")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8088
    run_server(port)
