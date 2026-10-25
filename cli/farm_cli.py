"""
Android Multi-Agent Farm - Command Line Interface (CLI) (AMAF 4.0)
Automation interface for terminal workflows, CI/CD pipelines, and script runners.
"""

import argparse
import sys
import os
import json
import time
from pathlib import Path

# Force UTF-8 output to prevent Windows cp1252 charmap encoding errors with Vietnamese
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.farm_config import DEFAULT_FARM_DEVICES
from core.avd_cloner import setup_farm, get_farm_status
from core.avd_optimizer import AVDOptimizer
from core.mock_otp_service import MockOTPService
from core.process_manager import ProcessManager
from core.adb_wrapper import ADBWrapper
from core.hardware_simulator import HardwareSimulator, PRESET_LOCATIONS
from core.scrcpy_manager import ScrcpyManager
from agents.multi_agent_orchestrator import MultiAgentOrchestrator
from agents.loop_orchestrator import LoopOrchestrator
from agents.device_lock_manager import DeviceLockManager
from agents.bug_reporter import BugReporter


def print_status():
    adb = ADBWrapper()
    pm = ProcessManager(adb)
    states = pm.get_farm_state()
    locks = DeviceLockManager().list_active_locks()

    print("\n" + "=" * 80)
    print(f"{'NAME':<15} {'SERIAL':<16} {'PORT':<6} {'STATUS':<10} {'RAM':<10} {'LOCKED BY':<20}")
    print("-" * 80)
    for s in states:
        stat_str = "ONLINE" if s["boot_completed"] else ("BOOTING" if s["is_running"] else "OFFLINE")
        ram_str = f"{s['ram_mb']} MB" if s["is_running"] else "--"
        lock_info = locks.get(s["serial"])
        lock_str = f"{lock_info['agent_id']}" if lock_info else "Free"

        print(f"{s['name']:<15} {s['serial']:<16} {s['port']:<6} {stat_str:<10} {ram_str:<10} {lock_str:<20}")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Android Multi-Agent Farm CLI (AMAF 4.0)")
    subparsers = parser.add_subparsers(dest="command", help="Available sub-commands")

    # setup
    p_setup = subparsers.add_parser("setup", help="Provision all 4 AVDs on D: drive")
    p_setup.add_argument("--count", type=int, default=4, help="Number of AVDs to provision")

    # status
    subparsers.add_parser("status", help="Print live farm status and metrics")

    # start
    p_start = subparsers.add_parser("start", help="Start farm devices in headless mode")
    p_start.add_argument("--device", choices=["1", "2", "3", "4", "all"], default="all", help="Target device")

    # stop
    p_stop = subparsers.add_parser("stop", help="Stop farm devices")
    p_stop.add_argument("--device", choices=["1", "2", "3", "4", "all"], default="all", help="Target device")

    # view
    p_view = subparsers.add_parser("view", help="Launch on-demand scrcpy viewer")
    p_view.add_argument("--device", required=True, choices=["1", "2", "3", "4"], help="Target device number")

    # sms
    p_sms = subparsers.add_parser("sms", help="Send SMS OTP to device")
    p_sms.add_argument("--serial", required=True, help="Target device serial (e.g. emulator-5554)")
    p_sms.add_argument("--phone", default="+84901234567", help="Sender phone number")
    p_sms.add_argument("--code", required=True, help="OTP code or message content")

    # finger
    p_finger = subparsers.add_parser("finger", help="Simulate fingerprint touch")
    p_finger.add_argument("--serial", required=True, help="Target device serial")

    # gps
    p_gps = subparsers.add_parser("gps", help="Spoof GPS location")
    p_gps.add_argument("--serial", required=True, help="Target device serial")
    p_gps.add_argument("--preset", choices=list(PRESET_LOCATIONS.keys()), default="hcm_center", help="Location preset")

    # test
    p_test = subparsers.add_parser("test", help="Run parallel multi-agent test")
    p_test.add_argument("--package", required=True, help="App package name (e.g. com.example.app)")
    p_test.add_argument("--steps", type=int, default=20, help="Max steps per agent")

    # optimize
    p_opt = subparsers.add_parser("optimize", help="Apply Zero-Lag profile and debloat device")
    p_opt.add_argument("--serial", required=True, help="Target device serial (e.g. emulator-5554)")

    # loop (4-Subagent Closed Loop: Planner -> Operator -> Healer -> Auditor)
    p_loop = subparsers.add_parser("loop", help="Run 4-Subagent autonomous closed-loop test")
    p_loop.add_argument("--serial", required=True, help="Target device serial")
    p_loop.add_argument("--goal", required=True, help="High-level test goal (e.g. 'Dang nhap bang so 0941189263 va nhap OTP')")
    p_loop.add_argument("--package", default="com.android.settings", help="Target package name")

    # mock-otp
    p_otp = subparsers.add_parser("mock-otp", help="Manage mock OTPs (0 VND carrier cost)")
    p_otp.add_argument("--phone", required=True, help="Target phone number")
    p_otp.add_argument("--generate", action="store_true", help="Generate a fresh mock OTP")
    p_otp.add_argument("--get", action="store_true", help="Get latest active mock OTP")
    p_otp.add_argument("--verify", help="Verify code against active mock OTP")
    p_otp.add_argument("--inject", help="Inject into device serial via mock SMS (e.g. emulator-5554)")

    # install
    p_inst = subparsers.add_parser("install", help="Broadcast install APK to all online devices")
    p_inst.add_argument("--apk", required=True, help="Path to .apk file")

    # matrix (Parallel Multi-Device Persona Matrix)
    subparsers.add_parser("matrix", help="Run 4-device parallel persona matrix test")

    # memory (Codebase Memory Inspector)
    p_mem = subparsers.add_parser("memory", help="Inspect Codebase Memory and Agent Knowledge")
    p_mem.add_argument("--summary", action="store_true", help="Print memory summary")
    p_mem.add_argument("--patches", action="store_true", help="List generated code patches")
    p_mem.add_argument("--prompts", action="store_true", help="List self-optimized prompts")

    # pipeline (Full Autonomous Kanban Pipeline)
    subparsers.add_parser("pipeline", help="Run full autonomous agile Dev-QA-Patch pipeline")

    # security (OWASP Mobile Audit)
    p_sec = subparsers.add_parser("security", help="Run Mobile OWASP security audit")
    p_sec.add_argument("--serial", default="emulator-5554", help="Target device serial")
    p_sec.add_argument("--package", default="com.android.settings", help="Target package name")

    # kanban (Inspect Kanban Board)
    subparsers.add_parser("kanban", help="Inspect live Kanban Board")

    # real-devices (Discover & manage optional Real Phone Farm)
    p_real = subparsers.add_parser("real-devices", help="Scan physical Android phones, switch farm mode, or connect Wireless ADB")
    p_real.add_argument("--mode", choices=["HYBRID", "AVD_ONLY", "REAL_ONLY"], help="Switch farm mode")
    p_real.add_argument("--connect-ip", help="Connect to Wireless ADB IP:Port (e.g. 192.168.1.50:5555)")
    p_real.add_argument("--usb-to-wireless", help="Switch USB serial to Wireless TCP/IP :5555")

    # broadcast (Group Control Synchronized Broadcast)
    p_bcast = subparsers.add_parser("broadcast", help="Broadcast synchronized action across multiple devices")
    p_bcast.add_argument("--action", required=True, choices=["tap", "swipe", "text", "key", "launch_app", "shell"], help="Broadcast action")
    p_bcast.add_argument("--group", default="ALL", choices=["ALL", "REAL_ONLY", "AVD_ONLY"], help="Target device group")
    p_bcast.add_argument("--x", type=float, default=0.5, help="Tap/Swipe X (normalized 0..1 or pixel)")
    p_bcast.add_argument("--y", type=float, default=0.5, help="Tap/Swipe Y (normalized 0..1 or pixel)")
    p_bcast.add_argument("--text", default="HOME", help="Text, key name, package name, or shell command")

    # evolve (16-Subagent Autonomous Self-Evolution Loop)
    p_evo = subparsers.add_parser("evolve", help="Run 16-Subagent Autonomous Self-Evolution Loop")
    p_evo.add_argument("--iterations", type=int, default=1, help="Number of evolution cycles")
    p_evo.add_argument("--package", default="com.android.settings", help="Target package name")

    # wall (Multi-Device Scrcpy Screen Wall)
    p_wall = subparsers.add_parser("wall", help="Open tiled Multi-Scrcpy Screen Wall for all online devices")
    p_wall.add_argument("--cols", type=int, default=4, help="Grid columns")

    # worktree (Git Worktree Subagent Isolation)
    p_wt = subparsers.add_parser("worktree", help="Manage isolated Git worktrees for Subagent feature development")
    p_wt.add_argument("--action", default="list", choices=["list", "create", "commit", "merge"], help="Worktree action")
    p_wt.add_argument("--feature", default="subagent-feature", help="Feature slug name")
    p_wt.add_argument("--subagent", default="CodeImproverSubagent", help="Subagent owner name")
    p_wt.add_argument("--message", default="feat: automated subagent improvement", help="Commit message")

    # apps (Multi-App Discovery, Permissions, State & Deep Links)
    p_apps = subparsers.add_parser("apps", help="Discover installed apps, grant permissions, clear/snapshot state, or open deep links")
    p_apps.add_argument("--serial", default="emulator-5554", help="Target device serial")
    p_apps.add_argument("--action", default="list", choices=["list", "grant", "clear", "snapshot", "restore", "deeplink"], help="Multi-app operation")
    p_apps.add_argument("--package", default="com.android.settings", help="Target package name")
    p_apps.add_argument("--uri", default="https://example.com", help="Deep link URI (for action=deeplink)")

    # crawl (UI State-Graph Crawler across one or multiple apps)
    p_crawl = subparsers.add_parser("crawl", help="Run DroidBot/Fastbot UI state-graph crawler on target package(s)")
    p_crawl.add_argument("--serial", default="emulator-5554", help="Target device serial")
    p_crawl.add_argument("--package", default="com.android.settings", help="Target package name")
    p_crawl.add_argument("--steps", type=int, default=3, help="Exploration steps")

    # auto-screenshot (Subagent #21 Set-of-Mark & NCC Template Matching)
    p_shot = subparsers.add_parser("auto-screenshot", help="Capture smart screenshot with Set-of-Mark (SoM) visual grounding badges")
    p_shot.add_argument("--serial", default="emulator-5554", help="Target device serial")
    p_shot.add_argument("--tag", default="cli_som", help="Screenshot tag")

    # solve-captcha (Subagent #19 & #22 Universal 10-Type Complex CAPTCHA CV Solver)
    p_cap = subparsers.add_parser("solve-captcha", help="Detect and solve all 10 simple & complex CAPTCHA types with CV + Cubic Bezier")
    p_cap.add_argument("--serial", default="emulator-5554", help="Target device serial")
    p_cap.add_argument("--list-types", action="store_true", help="List all 10 supported CAPTCHA types")

    # dismiss-oem-popup (Subagent #18 Vivo/OriginOS/Xiaomi/OPPO USB Guard)
    p_oem = subparsers.add_parser("dismiss-oem-popup", help="Auto-detect and click Vivo/OriginOS ('Tiếp tục cài đặt' / 'Cho phép cài đặt qua USB') popups")
    p_oem.add_argument("--serial", default="emulator-5554", help="Target device serial")
    p_oem.add_argument("--vivo-fallback", action="store_true", help="Use Vivo bottom-sheet coordinate fallback")

    # deeplink-qr (Subagent #23 DeepLink Fuzzing & QR Code Injection)
    p_qr = subparsers.add_parser("deeplink-qr", help="Open/fuzz Deep Links or inject synthetic QR code payload")
    p_qr.add_argument("--serial", default="emulator-5554", help="Target device serial")
    p_qr.add_argument("--payload", default="https://example.com/qr_verify", help="QR payload or Deep Link URI")

    # clipboard-biometric (Subagent #24 Clipboard OTP, Fingerprint & Notification Shade)
    p_cb = subparsers.add_parser("clipboard-biometric", help="Read/set clipboard OTP, trigger biometric auth, or inspect notifications")
    p_cb.add_argument("--serial", default="emulator-5554", help="Target device serial")
    p_cb.add_argument("--action", default="get_clipboard", choices=["get_clipboard", "set_clipboard", "biometric", "notifications"])
    p_cb.add_argument("--text", default="", help="Text for set_clipboard")

    # perf-audit (Subagent #25 FPS Jank & PSS Memory Leak Profiler)
    p_perf = subparsers.add_parser("perf-audit", help="Profile rendering FPS jank and PSS/Java/Native Heap memory leaks")
    p_perf.add_argument("--serial", default="emulator-5554", help="Target device serial")
    p_perf.add_argument("--package", default="com.android.settings", help="Target package name")

    args = parser.parse_args()

    if args.command == "setup":
        print(f"Setting up {args.count} AVDs...")
        res = setup_farm(args.count)
        for r in res:
            print(f"Provisioned {r['name']} at {r['path']}")
    elif args.command == "status" or not args.command:
        print_status()
    elif args.command == "start":
        adb = ADBWrapper()
        pm = ProcessManager(adb)
        if args.device == "all":
            print("Starting all 4 instances in Ultra-Light Headless mode...")
            res = pm.start_farm(4, headless=True)
            for r in res:
                print(f"[{r['serial']}] {r['message']}")
        else:
            dev_idx = int(args.device) - 1
            dev = DEFAULT_FARM_DEVICES[dev_idx]
            print(f"Starting {dev['name']} ({dev['serial']})...")
            ok, msg = pm.start_instance(dev["name"], dev["port"], headless=True)
            print(f"Result: {msg}")
    elif args.command == "stop":
        adb = ADBWrapper()
        pm = ProcessManager(adb)
        if args.device == "all":
            print("Stopping all farm devices...")
            res = pm.stop_farm()
            for r in res:
                print(f"[{r['serial']}] {r['message']}")
        else:
            dev_idx = int(args.device) - 1
            dev = DEFAULT_FARM_DEVICES[dev_idx]
            print(f"Stopping {dev['name']} ({dev['serial']})...")
            ok, msg = pm.stop_instance(dev["serial"])
            print(f"Result: {msg}")
    elif args.command == "view":
        dev_idx = int(args.device) - 1
        dev = DEFAULT_FARM_DEVICES[dev_idx]
        sm = ScrcpyManager()
        ok, msg = sm.open_viewer(dev["serial"], title=f"Phone Display ({dev['serial']})")
        print(msg)
    elif args.command == "sms":
        hw = HardwareSimulator()
        ok, msg = hw.send_sms_otp(args.serial, args.phone, f"Ma OTP: {args.code}")
        print(f"[{args.serial}] SMS sent: {'OK' if ok else 'FAILED'} -> {msg}")
    elif args.command == "finger":
        hw = HardwareSimulator()
        ok, msg = hw.touch_fingerprint(args.serial)
        print(f"[{args.serial}] Fingerprint: {'OK' if ok else 'FAILED'} -> {msg}")
    elif args.command == "gps":
        hw = HardwareSimulator()
        ok, msg = hw.set_preset_location(args.serial, args.preset)
        print(f"[{args.serial}] GPS {args.preset}: {'OK' if ok else 'FAILED'} -> {msg}")
    elif args.command == "test":
        orch = MultiAgentOrchestrator()
        print(f"Running autonomous testing on package '{args.package}' across online devices...")
        res = orch.run_parallel_exploration(args.package, max_steps=args.steps)
        print(f"Completed in {res.get('duration_seconds')}s. Summary:")
        for s, r in res.get("results", {}).items():
            print(f" - {s}: {r.get('status')} ({r.get('steps_executed', 0)} steps)")
    elif args.command == "install":
        adb = ADBWrapper()
        devices = [d["serial"] for d in adb.get_connected_devices() if d["status"] == "device"]
        if not devices:
            print("No devices online to install APK!")
            return
        for s in devices:
            ok, msg = adb.install_apk(s, args.apk)
            print(f"[{s}] Install: {'Success' if ok else msg}")
    elif args.command == "optimize":
        opt = AVDOptimizer()
        print(f"Applying Zero-Lag performance debloat to {args.serial}...")
        res = opt.optimize_device(args.serial)
        print(f"[{args.serial}] Animations & sync disabled. Debloated: {len(res['debloated_packages'])} packages.")
    elif args.command == "loop":
        print(f"Starting 4-Subagent Closed Loop on {args.serial} for goal: '{args.goal}'...")
        orch = LoopOrchestrator(args.serial)
        def _cb(subagent, data):
            print(f"[{subagent}] {data.get('status', '').upper()}: {data.get('detail') or data.get('goal') or data.get('action') or ''}")
        res = orch.run_autonomous_loop(args.goal, args.package, callback=_cb)
        print(f"Loop finished in {res.get('duration_seconds')}s. Status: {res.get('status')}")
    elif args.command == "mock-otp":
        otp = MockOTPService()
        if args.generate:
            c = otp.generate_otp(args.phone)
            print(f"Generated Mock OTP for {args.phone}: {c}")
        elif args.get:
            c = otp.get_latest_otp(args.phone)
            print(f"Active Mock OTP for {args.phone}: {c or 'None (Expired or not generated)'}")
        elif args.verify:
            ok = otp.verify_otp(args.phone, args.verify)
            print(f"Verification of {args.verify} for {args.phone}: {'VALID' if ok else 'INVALID'}")
        elif args.inject:
            ok, msg = otp.deliver_mock_sms_to_device(args.inject, args.phone)
            print(f"Inject result: {msg}")
    elif args.command == "matrix":
        from agents.agents_orchestrator import AgentsOrchestrator
        print("Launching 4-Device Parallel Multi-Agent Persona Matrix...")
        orch = AgentsOrchestrator()
        def _matrix_cb(serial, role, msg):
            print(f"[{serial}] [{role}] {msg}")
        res = orch.run_parallel_matrix(log_callback=_matrix_cb)
        print(f"\nMatrix Run Completed in {res.get('total_duration_seconds')}s.")
        print(f"Full Report: {res.get('report_path')}")
    elif args.command == "memory":
        from core.memory_manager import MemoryManager
        mm = MemoryManager()
        if args.patches:
            patches = mm.get_patches()
            print(f"Total Patches Generated: {len(patches)}")
            for p in patches:
                print(f" - [{p['patch_id']}] Defect: {p['defect_id']} -> File: {p['target_file']}")
                print(f"   Summary: {p['explanation']}")
        elif args.prompts:
            data = mm._read_data()
            prompts = data.get("prompts", {})
            print("Self-Optimized Prompts:")
            for agent, plist in prompts.items():
                print(f"Agent: {agent} ({len(plist)} iterations)")
                for p in plist:
                    print(f"   Version {p['version']}: {p['rationale']}")
        else:
            summary = mm.get_summary()
            print("=== Codebase Memory Summary ===")
            for k, v in summary.items():
                print(f" - {k}: {v}")
    elif args.command == "pipeline":
        from agents.autonomous_pipeline_director import AutonomousPipelineDirector
        print("Starting Autonomous Agile Pipeline across all 4 farm devices...")
        director = AutonomousPipelineDirector()
        def _pipe_cb(serial, subagent, msg):
            print(f"[{serial}] [{subagent}] {msg}")
        res = director.run_4_device_autonomous_pipeline(log_callback=_pipe_cb)
        print(f"\nPipeline Run Completed in {res.get('total_duration_seconds')}s.")
        print("Kanban Summary:", res.get("kanban_summary", {}).get("columns"))
    elif args.command == "security":
        from agents.security_auditor_subagent import SecurityAuditorSubagent
        print(f"Running Mobile OWASP Security Audit on {args.serial} for {args.package}...")
        sec = SecurityAuditorSubagent()
        res = sec.audit_package_security(args.serial, args.package)
        print(f"Audit completed: {res.get('findings_count')} findings detected.")
        print(f"Report: {res.get('report_file')}")
    elif args.command == "kanban":
        from core.kanban_board import KanbanBoard
        kb = KanbanBoard()
        summary = kb.get_board_summary()
        print("=== Agile Kanban Task Board ===")
        print(f"Total Tasks: {summary.get('total_cards')}")
        for col, cnt in summary.get("columns", {}).items():
            print(f" - {col:20s}: {cnt} cards")
    elif args.command == "real-devices":
        from core.real_device_manager import RealDeviceManager
        rm = RealDeviceManager()
        if args.mode:
            mres = rm.set_farm_mode(args.mode)
            print("Updated Farm Mode:", mres)
        if args.connect_ip:
            ok, msg = rm.connect_wireless_device(args.connect_ip)
            print(f"Connect Wireless ADB ({args.connect_ip}): {'OK' if ok else 'FAIL'} -> {msg}")
        if args.usb_to_wireless:
            ok, msg = rm.enable_wireless_adb(args.usb_to_wireless, 5555)
            print(f"USB to Wireless ({args.usb_to_wireless}): {'OK' if ok else 'FAIL'} -> {msg}")
        devs = rm.discover_real_devices(include_unauthorized=True)
        print(f"=== Physical Real Phones Discovered: {len(devs)} (Mode: {rm.get_farm_mode()['farm_mode']}) ===")
        for d in devs:
            bat = d.get("battery", {})
            print(f" - [{d['serial']}] {d['name']} | {d['connection_type']} | {d['resolution']} | Bat: {bat.get('level')}% ({bat.get('temperature_c')}°C)")
    elif args.command == "broadcast":
        from core.group_control_broadcaster import GroupControlBroadcaster
        bc = GroupControlBroadcaster()
        if args.action == "tap":
            res = bc.broadcast_tap(args.x, args.y, group_filter=args.group)
        elif args.action == "key":
            res = bc.broadcast_key(args.text, group_filter=args.group)
        elif args.action == "text":
            res = bc.broadcast_text(args.text, group_filter=args.group)
        elif args.action == "launch_app":
            res = bc.broadcast_launch_app(args.text, group_filter=args.group)
        else:
            res = bc.broadcast_shell(args.text, group_filter=args.group)
        print(f"Broadcast '{args.action}' to {res.get('targets_count')} devices in {res.get('total_duration_ms', 0)}ms:")
        for s, r in res.get("results", {}).items():
            print(f" - {s}: {r}")
    elif args.command == "evolve":
        from agents.self_evolution_engine import SelfEvolutionEngine
        engine = SelfEvolutionEngine()
        def _evo_cb(agent, msg):
            print(f"[{agent}] {msg}")
        res = engine.run_evolution_loop(iterations=args.iterations, package_name=args.package, callback=_evo_cb)
        print(f"\nSelf-Evolution Loop Completed in {res.get('total_duration_seconds')}s.")
        print(f"Report: {res.get('report_path')}")
    elif args.command == "wall":
        from core.group_control_broadcaster import GroupControlBroadcaster
        bc = GroupControlBroadcaster()
        sm = ScrcpyManager()
        targets = bc.resolve_target_serials(group_filter="ALL")
        res = sm.open_multi_device_wall(targets, cols=args.cols)
        print(f"Launched {res['launched_count']}/{res['total_requested']} tiled Scrcpy windows.")
    elif args.command == "worktree":
        from core.git_worktree_manager import GitWorktreeManager
        wm = GitWorktreeManager()
        if args.action == "list":
            wts = wm.list_worktrees()
            print(f"=== Active Git Worktrees ({len(wts)}) ===")
            for w in wts:
                print(f" - [{w.get('branch', 'detached')}] -> {w.get('path')} (HEAD: {w.get('head', '')[:8]})")
        elif args.action == "create":
            res = wm.create_feature_worktree(args.feature, subagent_name=args.subagent)
            print("Create Worktree Result:", res)
        elif args.action == "commit":
            wt_p = wm.worktrees_root / wm.slugify_feature(args.feature)
            res = wm.commit_in_worktree(wt_p, args.message, subagent_name=args.subagent)
            print("Commit Worktree Result:", res)
        elif args.action == "merge":
            res = wm.merge_worktree_to_main(args.feature, push_remote=True)
            print("Merge Worktree Result:", res)
    elif args.command == "apps":
        from core.multi_app_manager import MultiAppAutomationManager
        mm = MultiAppAutomationManager()
        if args.action == "list":
            res = mm.list_installed_apps(args.serial)
            print(f"=== Installed Packages on {args.serial} ({res['apps_count']}) ===")
            for p in res["packages"][:30]:
                print(f" - {p}")
        elif args.action == "grant":
            res = mm.grant_all_runtime_permissions(args.serial, args.package)
            print("Permissions Granted:", res)
        elif args.action == "clear":
            res = mm.clear_app_data(args.serial, args.package)
            print("Clear App Data:", res)
        elif args.action == "snapshot":
            res = mm.snapshot_app_state(args.serial, args.package)
            print("Snapshot Saved:", res)
        elif args.action == "restore":
            res = mm.restore_app_state(args.serial, args.package)
            print("State Restored:", res)
        elif args.action == "deeplink":
            res = mm.open_deep_link(args.serial, args.uri, package=args.package)
            print("Deep Link Opened:", res)
    elif args.command == "crawl":
        from agents.multi_app_crawler_subagent import MultiAppCrawlerSubagent
        crawler = MultiAppCrawlerSubagent()
        res = crawler.crawl_application(args.serial, args.package, max_steps=args.steps)
        print(f"Crawl completed on {args.serial} ({args.package}): {res['unique_states_discovered']} states, {res['transitions_recorded']} transitions.")
    elif args.command == "auto-screenshot":
        from agents.auto_screenshot_subagent import AutoScreenshotSubagent
        sub = AutoScreenshotSubagent()
        res = sub.capture_smart_screenshot(args.serial, tag=args.tag, annotate_som=True)
        print(f"Captured Set-of-Mark Screenshot on {args.serial}: {res['annotated_screenshot_path']} ({res['marks_count']} marks)")
    elif args.command == "solve-captcha":
        from agents.complex_captcha_subagent import ComplexCaptchaSubagent
        sub = ComplexCaptchaSubagent()
        if args.list_types:
            print("Supported 10 CAPTCHA Types:", sub.get_supported_captcha_types())
        else:
            res = sub.solve_any_captcha_with_vision(args.serial)
            print("Complex CAPTCHA CV Result:", res)
    elif args.command == "dismiss-oem-popup":
        from agents.oem_popup_guard_subagent import OEMPopupGuardSubagent
        sub = OEMPopupGuardSubagent()
        res = sub.guard_device(args.serial, use_vivo_fallback=args.vivo_fallback)
        print("OEM Popup Guard Result:", res)
    elif args.command == "deeplink-qr":
        from agents.deeplink_qr_scanner_subagent import DeepLinkAndQRScannerSubagent
        sub = DeepLinkAndQRScannerSubagent()
        res = sub.inject_qr_or_barcode_payload(args.serial, args.payload)
        print("DeepLink/QR Injection Result:", res)
    elif args.command == "clipboard-biometric":
        from agents.clipboard_biometric_subagent import ClipboardAndBiometricHookSubagent
        sub = ClipboardAndBiometricHookSubagent()
        if args.action == "set_clipboard":
            print(sub.set_clipboard(args.serial, args.text))
        elif args.action == "biometric":
            print(sub.authenticate_biometric(args.serial))
        elif args.action == "notifications":
            print(sub.inspect_and_interact_notifications(args.serial))
        else:
            print(sub.get_clipboard(args.serial))
    elif args.command == "perf-audit":
        from agents.performance_memleak_subagent import PerformanceAndMemLeakSubagent
        sub = PerformanceAndMemLeakSubagent()
        res = sub.run_comprehensive_performance_audit(args.serial, args.package)
        print(f"Performance Grade on {args.serial} ({args.package}): {res['performance_grade']} (Score: {res['performance_score']}/100, FPS: {res['graphics']['estimated_fps']}, PSS: {res['memory']['total_pss_mb']} MB)")


if __name__ == "__main__":
    main()
