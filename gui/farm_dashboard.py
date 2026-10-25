"""
Android Multi-Agent Farm - Modern Desktop Control Center
High-DPI aware, dark-themed control center for managing headless Android devices,
hardware simulation, scrcpy viewing, and parallel AI agent testing.
"""

import sys
import os
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Dict, List, Optional, Any
import psutil

# Ensure high-DPI awareness on Windows
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.farm_config import DEFAULT_FARM_DEVICES
from core.avd_cloner import setup_farm, get_farm_status
from core.avd_optimizer import AVDOptimizer
from core.mock_otp_service import MockOTPService
from core.process_manager import ProcessManager
from core.adb_wrapper import ADBWrapper
from core.hardware_simulator import HardwareSimulator, PRESET_LOCATIONS
from core.scrcpy_manager import ScrcpyManager
from core.real_device_manager import RealDeviceManager
from core.group_control_broadcaster import GroupControlBroadcaster
from agents.multi_agent_orchestrator import MultiAgentOrchestrator
from agents.loop_orchestrator import LoopOrchestrator
from agents.agents_orchestrator import AgentsOrchestrator
from agents.autonomous_pipeline_director import AutonomousPipelineDirector
from agents.self_evolution_engine import SelfEvolutionEngine
from core.memory_manager import MemoryManager
from core.kanban_board import KanbanBoard
from agents.device_lock_manager import DeviceLockManager
from agents.bug_reporter import BugReporter

# Color Palette (Catppuccin Mocha / Dark Minimalist)
C_BASE = "#1e1e2e"
C_MANTLE = "#181825"
C_CRUST = "#11111b"
C_SURFACE0 = "#313244"
C_SURFACE1 = "#45475a"
C_TEXT = "#cdd6f4"
C_SUBTEXT = "#a6adc8"
C_BLUE = "#89b4fa"
C_GREEN = "#a6e3a1"
C_RED = "#f38ba8"
C_YELLOW = "#f9e2af"
C_MAUVE = "#cba6f7"
C_PEACH = "#fab387"
C_TEAL = "#94e2d5"


class FarmDashboardApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Android Multi-Agent Farm | Control Center")
        self.root.geometry("1280x860")
        self.root.minsize(1050, 720)
        self.root.configure(bg=C_BASE)

        # Core Engines
        self.adb = ADBWrapper()
        self.real_mgr = RealDeviceManager(self.adb)
        self.broadcaster = GroupControlBroadcaster(self.adb, self.real_mgr)
        self.proc_mgr = ProcessManager(self.adb, self.real_mgr)
        self.hardware = HardwareSimulator(self.adb)
        self.scrcpy_mgr = ScrcpyManager()
        self.lock_mgr = DeviceLockManager()
        self.reporter = BugReporter()
        self.orchestrator = MultiAgentOrchestrator(self.adb, self.lock_mgr, self.reporter)
        self.agents_orchestrator = AgentsOrchestrator(self.adb)
        self.memory = MemoryManager()
        self.kanban = KanbanBoard()
        self.pipeline_director = AutonomousPipelineDirector(self.adb, self.memory, self.kanban)
        self.evolution_engine = SelfEvolutionEngine(self.adb, self.memory, self.kanban)

        # Device card widget references: serial -> widget dict
        self.device_cards: Dict[str, Dict[str, Any]] = {}

        self._init_styles()
        self._build_header()
        self._build_main_content()
        self._build_status_bar()

        # Background state refresher
        self._is_running = True
        self.refresh_thread = threading.Thread(target=self._auto_refresh_loop, daemon=True)
        self.refresh_thread.start()

        # Clean shutdown on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _init_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Global style overrides
        style.configure(".", background=C_BASE, foreground=C_TEXT, font=("Segoe UI", 10))
        style.configure("TNotebook", background=C_MANTLE, borderwidth=0)
        style.configure("TNotebook.Tab", background=C_SURFACE0, foreground=C_TEXT, padding=[16, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", C_SURFACE1), ("active", C_SURFACE0)],
                  foreground=[("selected", C_BLUE), ("active", C_TEXT)])

        style.configure("Treeview",
                        background=C_MANTLE,
                        foreground=C_TEXT,
                        fieldbackground=C_MANTLE,
                        rowheight=28,
                        bordercolor=C_SURFACE0,
                        borderwidth=1)
        style.map("Treeview", background=[("selected", C_SURFACE0)], foreground=[("selected", C_BLUE)])
        style.configure("Treeview.Heading", background=C_SURFACE0, foreground=C_TEXT, font=("Segoe UI", 10, "bold"), relief="flat")

    def _build_header(self):
        header = tk.Frame(self.root, bg=C_MANTLE, height=70, padx=20, pady=12)
        header.pack(fill=tk.X, side=tk.TOP)

        # Title & Subtitle
        title_frame = tk.Frame(header, bg=C_MANTLE)
        title_frame.pack(side=tk.LEFT)

        title_lbl = tk.Label(title_frame, text="⚡ Android Multi-Agent Farm", font=("Segoe UI", 16, "bold"), fg=C_BLUE, bg=C_MANTLE)
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(title_frame, text="Ultra-Light Headless Farm | RTX 3050 Offload | Multi-Agent Testing", font=("Segoe UI", 9), fg=C_SUBTEXT, bg=C_MANTLE)
        sub_lbl.pack(anchor="w")

        # System Metrics Badges
        self.metrics_frame = tk.Frame(header, bg=C_MANTLE)
        self.metrics_frame.pack(side=tk.RIGHT, padx=10)

        self.sys_ram_lbl = tk.Label(self.metrics_frame, text="RAM: Free -- GB", font=("Segoe UI", 9, "bold"), fg=C_GREEN, bg=C_SURFACE0, padx=10, pady=4)
        self.sys_ram_lbl.pack(side=tk.LEFT, padx=4)

        self.sys_cpu_lbl = tk.Label(self.metrics_frame, text="CPU: --%", font=("Segoe UI", 9, "bold"), fg=C_YELLOW, bg=C_SURFACE0, padx=10, pady=4)
        self.sys_cpu_lbl.pack(side=tk.LEFT, padx=4)

        # Batch Action Buttons
        btn_start_all = tk.Button(header, text="▶ Start All Headless", font=("Segoe UI", 10, "bold"), bg=C_GREEN, fg=C_CRUST,
                                  activebackground="#89dceb", relief="flat", padx=12, pady=6, cursor="hand2", command=self.on_start_all)
        btn_start_all.pack(side=tk.RIGHT, padx=4)

        btn_stop_all = tk.Button(header, text="⏹ Stop All", font=("Segoe UI", 10, "bold"), bg=C_RED, fg=C_CRUST,
                                 activebackground="#f2cdcd", relief="flat", padx=12, pady=6, cursor="hand2", command=self.on_stop_all)
        btn_stop_all.pack(side=tk.RIGHT, padx=4)

        btn_apk = tk.Button(header, text="📦 Install APK to All", font=("Segoe UI", 10, "bold"), bg=C_MAUVE, fg=C_CRUST,
                            activebackground="#b4befe", relief="flat", padx=12, pady=6, cursor="hand2", command=self.on_install_apk_all)
        btn_apk.pack(side=tk.RIGHT, padx=4)

    def _build_main_content(self):
        main_pane = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg=C_BASE, sashrelief="flat", sashwidth=4)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

        # Top Section: 4 Device Cards Grid
        devices_wrapper = tk.LabelFrame(main_pane, text=" Virtual Phone Devices (4 Headless Instances) ", font=("Segoe UI", 11, "bold"), fg=C_BLUE, bg=C_BASE, padx=10, pady=10)
        main_pane.add(devices_wrapper, minsize=290)

        self.cards_grid = tk.Frame(devices_wrapper, bg=C_BASE)
        self.cards_grid.pack(fill=tk.BOTH, expand=True)

        for i in range(4):
            self.cards_grid.columnconfigure(i, weight=1, uniform="device_col")

        for idx, dev in enumerate(DEFAULT_FARM_DEVICES):
            self._create_device_card(dev, idx)

        # Bottom Section: Tabs for Multi-Agent & Bug Reports
        tabs_frame = tk.Frame(main_pane, bg=C_BASE)
        main_pane.add(tabs_frame, minsize=350)

        self.notebook = ttk.Notebook(tabs_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Multi-Agent Parallel Testing
        self.tab_agents = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_agents, text=" 🤖 Multi-Agent & 12-Subagent Evolution ")
        self._build_agents_tab()

        # Tab 2: Real Phone Farm & Group Broadcast Control
        self.tab_real_farm = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_real_farm, text=" 📱 Real Phone Farm & Group Control ")
        self._build_real_farm_tab()

        # Tab 3: Defect Reports (Bug Tracker)
        self.tab_reports = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_reports, text=" 🐞 Defect Reports & Evidence ")
        self._build_reports_tab()

        # Tab 4: Codebase Memory & Auto-Patches
        self.tab_memory = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_memory, text=" 🧠 Memory, Macros & Patches ")
        self._build_memory_tab()

    def _create_device_card(self, dev: Dict[str, Any], col: int):
        serial = dev["serial"]
        card = tk.Frame(self.cards_grid, bg=C_MANTLE, highlightbackground=C_SURFACE0, highlightthickness=1, padx=12, pady=12)
        card.grid(row=0, column=col, sticky="nsew", padx=6, pady=4)

        # Header: Name + Badge
        top = tk.Frame(card, bg=C_MANTLE)
        top.pack(fill=tk.X)

        name_lbl = tk.Label(top, text=dev["name"], font=("Segoe UI", 11, "bold"), fg=C_TEXT, bg=C_MANTLE)
        name_lbl.pack(side=tk.LEFT)

        status_badge = tk.Label(top, text="OFFLINE", font=("Segoe UI", 8, "bold"), fg=C_SUBTEXT, bg=C_SURFACE0, padx=6, pady=2)
        status_badge.pack(side=tk.RIGHT)

        # Port & Serial & Description
        sub = tk.Label(card, text=f"{serial} | Port {dev['port']}", font=("Segoe UI", 8), fg=C_SUBTEXT, bg=C_MANTLE)
        sub.pack(anchor="w", pady=(2, 0))

        desc = tk.Label(card, text=dev["description"], font=("Segoe UI", 8, "italic"), fg=C_TEAL, bg=C_MANTLE)
        desc.pack(anchor="w", pady=(0, 8))

        # Metrics box
        metrics_box = tk.Frame(card, bg=C_CRUST, padx=8, pady=6)
        metrics_box.pack(fill=tk.X, pady=4)

        ram_lbl = tk.Label(metrics_box, text="RAM: -- MB", font=("Segoe UI", 9), fg=C_TEXT, bg=C_CRUST)
        ram_lbl.pack(anchor="w")

        cpu_lbl = tk.Label(metrics_box, text="CPU: --%", font=("Segoe UI", 9), fg=C_TEXT, bg=C_CRUST)
        cpu_lbl.pack(anchor="w")

        lock_lbl = tk.Label(metrics_box, text="Agent: None (Idle)", font=("Segoe UI", 8), fg=C_SUBTEXT, bg=C_CRUST)
        lock_lbl.pack(anchor="w")

        # Action Buttons
        btn_row1 = tk.Frame(card, bg=C_MANTLE)
        btn_row1.pack(fill=tk.X, pady=(8, 4))

        btn_toggle = tk.Button(btn_row1, text="▶ Start", font=("Segoe UI", 9, "bold"), bg=C_GREEN, fg=C_CRUST,
                               relief="flat", cursor="hand2", command=lambda s=serial, d=dev: self.on_toggle_device(s, d))
        btn_toggle.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        btn_view = tk.Button(btn_row1, text="👁 View", font=("Segoe UI", 9, "bold"), bg=C_BLUE, fg=C_CRUST,
                             relief="flat", cursor="hand2", command=lambda s=serial: self.on_view_screen(s))
        btn_view.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))

        # Hardware Simulator Toolbar
        hw_row = tk.Frame(card, bg=C_MANTLE)
        hw_row.pack(fill=tk.X, pady=4)

        btn_fp = tk.Button(hw_row, text="🔑 Fingerprint", font=("Segoe UI", 8), bg=C_SURFACE0, fg=C_TEXT,
                           relief="flat", cursor="hand2", command=lambda s=serial: self.on_trigger_fingerprint(s))
        btn_fp.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        btn_sms = tk.Button(hw_row, text="💬 SMS OTP", font=("Segoe UI", 8), bg=C_SURFACE0, fg=C_TEXT,
                            relief="flat", cursor="hand2", command=lambda s=serial: self.on_popup_sms_otp(s))
        btn_sms.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        btn_gps = tk.Button(hw_row, text="📍 GPS", font=("Segoe UI", 8), bg=C_SURFACE0, fg=C_TEXT,
                            relief="flat", cursor="hand2", command=lambda s=serial: self.on_popup_gps(s))
        btn_gps.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        btn_opt = tk.Button(hw_row, text="⚡ Debloat", font=("Segoe UI", 8), bg=C_SURFACE0, fg=C_YELLOW,
                            relief="flat", cursor="hand2", command=lambda s=serial: self.on_optimize_device(s))
        btn_opt.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        # Store widget references
        self.device_cards[serial] = {
            "card": card,
            "badge": status_badge,
            "ram_lbl": ram_lbl,
            "cpu_lbl": cpu_lbl,
            "lock_lbl": lock_lbl,
            "btn_toggle": btn_toggle,
            "btn_view": btn_view
        }

    def _build_agents_tab(self):
        # Config & Control Bar (Row 1: Parallel Exploration)
        ctl = tk.Frame(self.tab_agents, bg=C_BASE)
        ctl.pack(fill=tk.X, pady=(0, 6))

        tk.Label(ctl, text="Package:", font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 4))
        self.pkg_entry = tk.Entry(ctl, font=("Segoe UI", 9), bg=C_MANTLE, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", width=26)
        self.pkg_entry.insert(0, "com.android.settings")
        self.pkg_entry.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(ctl, text="Steps:", font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 4))
        self.steps_spin = tk.Spinbox(ctl, from_=5, to=100, font=("Segoe UI", 9), width=4, bg=C_MANTLE, fg=C_TEXT, relief="flat")
        self.steps_spin.delete(0, "end")
        self.steps_spin.insert(0, "15")
        self.steps_spin.pack(side=tk.LEFT, padx=(0, 10))

        btn_run_parallel = tk.Button(ctl, text="🚀 Parallel Test", font=("Segoe UI", 9, "bold"), bg=C_MAUVE, fg=C_CRUST,
                                     relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_run_parallel_test)
        btn_run_parallel.pack(side=tk.LEFT, padx=3)

        btn_stop_agents = tk.Button(ctl, text="⏹ Abort", font=("Segoe UI", 9, "bold"), bg=C_RED, fg=C_CRUST,
                                    relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_abort_agents)
        btn_stop_agents.pack(side=tk.LEFT, padx=3)

        # Config & Control Bar (Row 2: 4-Subagent Closed Loop: Planner -> Operator -> Healer -> Auditor)
        ctl2 = tk.Frame(self.tab_agents, bg=C_BASE)
        ctl2.pack(fill=tk.X, pady=(0, 8))

        tk.Label(ctl2, text="Goal Prompt:", font=("Segoe UI", 9, "bold"), fg=C_BLUE, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 4))
        self.goal_entry = tk.Entry(ctl2, font=("Segoe UI", 9), bg=C_MANTLE, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", width=38)
        self.goal_entry.insert(0, "Kiem tra luong dang nhap OTP so 0941189263")
        self.goal_entry.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(ctl2, text="Device:", font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 4))
        self.device_combo = ttk.Combobox(ctl2, values=["emulator-5554", "emulator-5556", "emulator-5558", "emulator-5560"], width=13, state="readonly")
        self.device_combo.current(0)
        self.device_combo.pack(side=tk.LEFT, padx=(0, 10))

        btn_run_loop = tk.Button(ctl2, text="🧠 Run 4-Subagent Closed Loop", font=("Segoe UI", 9, "bold"), bg=C_GREEN, fg=C_CRUST,
                                 relief="flat", padx=12, pady=3, cursor="hand2", command=self.on_run_closed_loop)
        btn_run_loop.pack(side=tk.LEFT, padx=3)

        btn_matrix = tk.Button(ctl2, text="⚡ Run 4-Device Persona Matrix", font=("Segoe UI", 9, "bold"), bg=C_PEACH, fg=C_CRUST,
                               relief="flat", padx=12, pady=3, cursor="hand2", command=self.on_run_matrix)
        btn_matrix.pack(side=tk.LEFT, padx=3)

        btn_pipeline = tk.Button(ctl2, text="🚀 Run Autonomous Agile Pipeline", font=("Segoe UI", 9, "bold"), bg=C_MAUVE, fg=C_CRUST,
                                 relief="flat", padx=12, pady=3, cursor="hand2", command=self.on_run_pipeline)
        btn_pipeline.pack(side=tk.LEFT, padx=3)

        btn_evo = tk.Button(ctl2, text="🧬 Run 12-Subagent Self-Evolution", font=("Segoe UI", 9, "bold"), bg=C_TEAL, fg=C_CRUST,
                            relief="flat", padx=12, pady=3, cursor="hand2", command=self.on_run_self_evolution)
        btn_evo.pack(side=tk.LEFT, padx=3)

        # Live Execution Logs
        log_frame = tk.Frame(self.tab_agents, bg=C_MANTLE, highlightbackground=C_SURFACE0, highlightthickness=1)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.agent_log_text = tk.Text(log_frame, bg=C_MANTLE, fg=C_TEXT, font=("Consolas", 9), relief="flat", padx=8, pady=8)
        scroll = tk.Scrollbar(log_frame, command=self.agent_log_text.yview)
        self.agent_log_text.configure(yscrollcommand=scroll.set)

        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.agent_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Setup text tags
        self.agent_log_text.tag_configure("info", foreground=C_BLUE)
        self.agent_log_text.tag_configure("success", foreground=C_GREEN)
        self.agent_log_text.tag_configure("warn", foreground=C_YELLOW)
        self.agent_log_text.tag_configure("error", foreground=C_RED)
        self.agent_log_text.tag_configure("agent", foreground=C_MAUVE, font=("Consolas", 9, "bold"))

        self.log_agent_msg("System", "Multi-Agent Orchestrator is ready. Connects with ARTEMIS MCP Server and IDE sessions.", "info")

    def _build_real_farm_tab(self):
        # Row 1: Farm Mode Selector & Wireless ADB Connection Bar
        bar1 = tk.Frame(self.tab_real_farm, bg=C_BASE)
        bar1.pack(fill=tk.X, pady=(0, 8))

        tk.Label(bar1, text="Farm Mode:", font=("Segoe UI", 9, "bold"), fg=C_BLUE, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 4))
        self.farm_mode_combo = ttk.Combobox(bar1, values=["HYBRID", "AVD_ONLY", "REAL_ONLY"], width=12, state="readonly")
        self.farm_mode_combo.set(self.real_mgr.get_farm_mode().get("farm_mode", "HYBRID"))
        self.farm_mode_combo.pack(side=tk.LEFT, padx=(0, 6))
        self.farm_mode_combo.bind("<<ComboboxSelected>>", self.on_change_farm_mode)

        btn_scan_real = tk.Button(bar1, text="🔍 Scan Real Phones & Apply Thermal Guard", font=("Segoe UI", 9, "bold"),
                                  bg=C_GREEN, fg=C_CRUST, relief="flat", padx=10, pady=3, cursor="hand2", command=self.refresh_real_devices_tab)
        btn_scan_real.pack(side=tk.LEFT, padx=4)

        tk.Label(bar1, text="Wireless IP:Port:", font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_BASE).pack(side=tk.LEFT, padx=(12, 4))
        self.wireless_ip_entry = tk.Entry(bar1, font=("Segoe UI", 9), bg=C_MANTLE, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", width=18)
        self.wireless_ip_entry.insert(0, "192.168.1.50:5555")
        self.wireless_ip_entry.pack(side=tk.LEFT, padx=(0, 4))

        btn_wifi_conn = tk.Button(bar1, text="📡 Connect Wi-Fi ADB", font=("Segoe UI", 9, "bold"),
                                  bg=C_BLUE, fg=C_CRUST, relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_connect_wireless_adb)
        btn_wifi_conn.pack(side=tk.LEFT, padx=3)

        btn_usb2wifi = tk.Button(bar1, text="🔌➔📡 USB to Wireless", font=("Segoe UI", 9, "bold"),
                                 bg=C_MAUVE, fg=C_CRUST, relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_usb_to_wireless)
        btn_usb2wifi.pack(side=tk.LEFT, padx=3)

        btn_wall = tk.Button(bar1, text="🖥️ Open Multi-Scrcpy Wall", font=("Segoe UI", 9, "bold"),
                             bg=C_PEACH, fg=C_CRUST, relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_open_scrcpy_wall)
        btn_wall.pack(side=tk.RIGHT, padx=3)

        # Row 2: Group Control Broadcast Bar (Synchronized Multi-Device Actions)
        bar2 = tk.LabelFrame(self.tab_real_farm, text=" ⚡ Group Control Synchronized Broadcast (Normalized Cross-Resolution) ",
                             font=("Segoe UI", 9, "bold"), fg=C_TEAL, bg=C_BASE, padx=8, pady=6)
        bar2.pack(fill=tk.X, pady=(0, 8))

        tk.Label(bar2, text="Target Group:", font=("Segoe UI", 9), fg=C_TEXT, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 4))
        self.bcast_group_combo = ttk.Combobox(bar2, values=["ALL", "REAL_ONLY", "AVD_ONLY"], width=10, state="readonly")
        self.bcast_group_combo.current(0)
        self.bcast_group_combo.pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(bar2, text="Norm/Ref X,Y:", font=("Segoe UI", 9), fg=C_TEXT, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 4))
        self.bcast_xy_entry = tk.Entry(bar2, font=("Segoe UI", 9), bg=C_MANTLE, fg=C_TEXT, relief="flat", width=10)
        self.bcast_xy_entry.insert(0, "0.5,0.5")
        self.bcast_xy_entry.pack(side=tk.LEFT, padx=(0, 4))

        tk.Button(bar2, text="👆 Sync Tap", font=("Segoe UI", 9, "bold"), bg=C_BLUE, fg=C_CRUST, relief="flat",
                  padx=8, cursor="hand2", command=self.on_broadcast_tap).pack(side=tk.LEFT, padx=3)

        tk.Button(bar2, text="🏠 Sync HOME", font=("Segoe UI", 9), bg=C_SURFACE0, fg=C_TEXT, relief="flat",
                  padx=8, cursor="hand2", command=lambda: self.on_broadcast_key("HOME")).pack(side=tk.LEFT, padx=2)

        tk.Button(bar2, text="🔙 Sync BACK", font=("Segoe UI", 9), bg=C_SURFACE0, fg=C_TEXT, relief="flat",
                  padx=8, cursor="hand2", command=lambda: self.on_broadcast_key("BACK")).pack(side=tk.LEFT, padx=2)

        tk.Label(bar2, text="Text/App:", font=("Segoe UI", 9), fg=C_TEXT, bg=C_BASE).pack(side=tk.LEFT, padx=(8, 4))
        self.bcast_text_entry = tk.Entry(bar2, font=("Segoe UI", 9), bg=C_MANTLE, fg=C_TEXT, relief="flat", width=20)
        self.bcast_text_entry.insert(0, "com.android.settings")
        self.bcast_text_entry.pack(side=tk.LEFT, padx=(0, 4))

        tk.Button(bar2, text="⌨️ Sync Type", font=("Segoe UI", 9, "bold"), bg=C_GREEN, fg=C_CRUST, relief="flat",
                  padx=8, cursor="hand2", command=self.on_broadcast_text).pack(side=tk.LEFT, padx=2)

        tk.Button(bar2, text="🚀 Sync Launch App", font=("Segoe UI", 9, "bold"), bg=C_MAUVE, fg=C_CRUST, relief="flat",
                  padx=8, cursor="hand2", command=self.on_broadcast_launch).pack(side=tk.LEFT, padx=2)

        # Row 3: Real Devices Table
        cols = ("serial", "name", "conn_type", "android", "resolution", "battery", "temp_c", "wifi_ip", "status")
        self.real_tree = ttk.Treeview(self.tab_real_farm, columns=cols, show="headings", selectmode="browse")
        self.real_tree.heading("serial", text="Serial / Endpoint")
        self.real_tree.heading("name", text="Phone Model")
        self.real_tree.heading("conn_type", text="Connection")
        self.real_tree.heading("android", text="Android")
        self.real_tree.heading("resolution", text="Resolution")
        self.real_tree.heading("battery", text="Battery %")
        self.real_tree.heading("temp_c", text="Temp (°C)")
        self.real_tree.heading("wifi_ip", text="Wi-Fi IP")
        self.real_tree.heading("status", text="Health / Status")

        for col_id, w in [("serial", 150), ("name", 160), ("conn_type", 100), ("android", 80),
                          ("resolution", 100), ("battery", 85), ("temp_c", 85), ("wifi_ip", 120), ("status", 140)]:
            self.real_tree.column(col_id, width=w)

        r_scroll = tk.Scrollbar(self.tab_real_farm, command=self.real_tree.yview)
        self.real_tree.configure(yscrollcommand=r_scroll.set)
        r_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.real_tree.pack(fill=tk.BOTH, expand=True)
        self.refresh_real_devices_tab()

    def _build_reports_tab(self):
        top_bar = tk.Frame(self.tab_reports, bg=C_BASE)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        btn_refresh_rep = tk.Button(top_bar, text="🔄 Refresh Reports", font=("Segoe UI", 9, "bold"), bg=C_SURFACE0, fg=C_TEXT,
                                    relief="flat", padx=10, pady=4, cursor="hand2", command=self.refresh_reports)
        btn_refresh_rep.pack(side=tk.LEFT, padx=4)

        btn_open_folder = tk.Button(top_bar, text="📁 Open Reports Folder", font=("Segoe UI", 9), bg=C_SURFACE0, fg=C_TEXT,
                                    relief="flat", padx=10, pady=4, cursor="hand2", command=self.on_open_reports_folder)
        btn_open_folder.pack(side=tk.LEFT, padx=4)

        # Reports Table
        cols = ("report_id", "created_at", "serial", "package", "error_type", "error_message")
        self.rep_tree = ttk.Treeview(self.tab_reports, columns=cols, show="headings", selectmode="browse")

        self.rep_tree.heading("report_id", text="Report ID")
        self.rep_tree.heading("created_at", text="Detected At")
        self.rep_tree.heading("serial", text="Device")
        self.rep_tree.heading("package", text="Package")
        self.rep_tree.heading("error_type", text="Defect Type")
        self.rep_tree.heading("error_message", text="Summary Message")

        self.rep_tree.column("report_id", width=160)
        self.rep_tree.column("created_at", width=140)
        self.rep_tree.column("serial", width=110)
        self.rep_tree.column("package", width=160)
        self.rep_tree.column("error_type", width=120)
        self.rep_tree.column("error_message", width=350)

        tree_scroll = tk.Scrollbar(self.tab_reports, command=self.rep_tree.yview)
        self.rep_tree.configure(yscrollcommand=tree_scroll.set)

        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.rep_tree.pack(fill=tk.BOTH, expand=True)

        self.rep_tree.bind("<Double-1>", self.on_double_click_report)
        self.refresh_reports()

    def _build_memory_tab(self):
        top_bar = tk.Frame(self.tab_memory, bg=C_BASE)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        btn_refresh_mem = tk.Button(top_bar, text="🔄 Refresh Memory & Patches", font=("Segoe UI", 9, "bold"), bg=C_SURFACE0, fg=C_TEXT,
                                    relief="flat", padx=10, pady=4, cursor="hand2", command=self.refresh_memory_tab)
        btn_refresh_mem.pack(side=tk.LEFT, padx=4)

        btn_open_patches = tk.Button(top_bar, text="📁 Open Patches Folder", font=("Segoe UI", 9), bg=C_SURFACE0, fg=C_TEXT,
                                     relief="flat", padx=10, pady=4, cursor="hand2", command=self.on_open_patches_folder)
        btn_open_patches.pack(side=tk.LEFT, padx=4)

        self.mem_summary_lbl = tk.Label(top_bar, text="Tri thức: -- | Bản vá: -- | Prompts: --", font=("Segoe UI", 9, "italic"), fg=C_TEAL, bg=C_BASE)
        self.mem_summary_lbl.pack(side=tk.RIGHT, padx=8)

        # Split pane for Patches List (Left) and Content Viewer (Right)
        paned = tk.PanedWindow(self.tab_memory, orient=tk.HORIZONTAL, bg=C_BASE, sashrelief="flat", sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(paned, bg=C_MANTLE)
        paned.add(left_frame, minsize=380)

        right_frame = tk.Frame(paned, bg=C_MANTLE)
        paned.add(right_frame, minsize=420)

        # Left: Patches Treeview
        tk.Label(left_frame, text=" Auto-Generated Git Patches (.diff) ", font=("Segoe UI", 9, "bold"), fg=C_BLUE, bg=C_MANTLE).pack(anchor="w", padx=6, pady=4)
        cols = ("patch_id", "defect_id", "target_file")
        self.patch_tree = ttk.Treeview(left_frame, columns=cols, show="headings", selectmode="browse")
        self.patch_tree.heading("patch_id", text="Patch ID")
        self.patch_tree.heading("defect_id", text="Defect ID")
        self.patch_tree.heading("target_file", text="Target File")
        self.patch_tree.column("patch_id", width=120)
        self.patch_tree.column("defect_id", width=110)
        self.patch_tree.column("target_file", width=220)

        patch_scroll = tk.Scrollbar(left_frame, command=self.patch_tree.yview)
        self.patch_tree.configure(yscrollcommand=patch_scroll.set)
        patch_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.patch_tree.pack(fill=tk.BOTH, expand=True)
        self.patch_tree.bind("<<TreeviewSelect>>", self.on_select_patch)

        # Right: Content Viewer
        tk.Label(right_frame, text=" Patch Diff & Self-Optimized Prompt Inspector ", font=("Segoe UI", 9, "bold"), fg=C_GREEN, bg=C_MANTLE).pack(anchor="w", padx=6, pady=4)
        self.mem_content_text = tk.Text(right_frame, bg=C_CRUST, fg=C_TEXT, font=("Consolas", 9), relief="flat", padx=8, pady=8)
        content_scroll = tk.Scrollbar(right_frame, command=self.mem_content_text.yview)
        self.mem_content_text.configure(yscrollcommand=content_scroll.set)
        content_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.mem_content_text.pack(fill=tk.BOTH, expand=True)

        self.refresh_memory_tab()

    def refresh_memory_tab(self):
        for item in self.patch_tree.get_children():
            self.patch_tree.delete(item)

        patches = self.memory.get_patches()
        for p in patches:
            self.patch_tree.insert(
                "",
                "end",
                values=(
                    p.get("patch_id"),
                    p.get("defect_id"),
                    p.get("target_file")
                ),
                tags=(p.get("diff_content", ""), p.get("explanation", ""))
            )

        summary = self.memory.get_summary()
        self.mem_summary_lbl.config(
            text=(
                f"Tri thức: {summary.get('knowledge_items_count')} | "
                f"Macros: {summary.get('macros_count', 0)} | "
                f"Bản vá: {summary.get('patches_count')} | "
                f"Prompts: {summary.get('prompts_count')}"
            )
        )

    def on_select_patch(self, event):
        selected = self.patch_tree.selection()
        if not selected:
            return
        item = self.patch_tree.item(selected[0])
        tags = item.get("tags", ())
        diff_text = tags[0] if len(tags) > 0 else "No diff content"
        explanation = tags[1] if len(tags) > 1 else ""

        self.mem_content_text.delete("1.0", tk.END)
        self.mem_content_text.insert(tk.END, f"=== EXPLANATION ===\n{explanation}\n\n=== UNIFIED GIT DIFF ===\n{diff_text}")

    def on_open_patches_folder(self):
        patches_dir = Path(__file__).resolve().parent.parent / "reports" / "patches"
        patches_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(patches_dir))

    def _build_status_bar(self):
        status_bar = tk.Frame(self.root, bg=C_CRUST, height=26, padx=12)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_lbl = tk.Label(status_bar, text="Ready | 4 AVDs Provisioned on D:\\Android_AVD", font=("Segoe UI", 8), fg=C_SUBTEXT, bg=C_CRUST)
        self.status_lbl.pack(side=tk.LEFT)

        author_lbl = tk.Label(status_bar, text="Antigravity Multi-Device Testing Core", font=("Segoe UI", 8), fg=C_SURFACE1, bg=C_CRUST)
        author_lbl.pack(side=tk.RIGHT)

    def log_agent_msg(self, sender: str, msg: str, tag: str = "info"):
        t_str = time.strftime("%H:%M:%S")
        self.agent_log_text.insert(tk.END, f"[{t_str}] ", "sub")
        self.agent_log_text.insert(tk.END, f"[{sender}] ", "agent")
        self.agent_log_text.insert(tk.END, f"{msg}\n", tag)
        self.agent_log_text.see(tk.END)

    def _auto_refresh_loop(self):
        """Periodically poll device states and system metrics every 2.5s."""
        while self._is_running:
            try:
                # 1. System Metrics
                mem = psutil.virtual_memory()
                free_gb = round(mem.available / (1024**3), 1)
                cpu_pct = psutil.cpu_percent(interval=None)

                # 2. Farm States
                states = self.proc_mgr.get_farm_state()
                locks = self.lock_mgr.list_active_locks()

                # Update UI on main thread
                self.root.after(0, self._update_ui_state, free_gb, cpu_pct, states, locks)
            except Exception:
                pass
            time.sleep(2.5)

    def _update_ui_state(self, free_gb: float, cpu_pct: float, states: List[Dict[str, Any]], locks: Dict[str, Any]):
        self.sys_ram_lbl.config(text=f"RAM: Free {free_gb} GB")
        self.sys_cpu_lbl.config(text=f"CPU: {cpu_pct}%")

        for s in states:
            serial = s["serial"]
            card_info = self.device_cards.get(serial)
            if not card_info:
                continue

            badge = card_info["badge"]
            btn_toggle = card_info["btn_toggle"]
            ram_lbl = card_info["ram_lbl"]
            cpu_lbl = card_info["cpu_lbl"]
            lock_lbl = card_info["lock_lbl"]

            if s["is_running"]:
                if s["boot_completed"]:
                    badge.config(text="ONLINE", bg=C_GREEN, fg=C_CRUST)
                else:
                    badge.config(text="BOOTING", bg=C_YELLOW, fg=C_CRUST)
                btn_toggle.config(text="⏹ Stop", bg=C_RED, fg=C_CRUST)
                ram_lbl.config(text=f"RAM: {s['ram_mb']} MB (PID: {s['pid'] or '--'})")
                cpu_lbl.config(text=f"CPU: {s['cpu_pct']}%")
            else:
                badge.config(text="OFFLINE", bg=C_SURFACE0, fg=C_SUBTEXT)
                btn_toggle.config(text="▶ Start", bg=C_GREEN, fg=C_CRUST)
                ram_lbl.config(text="RAM: -- MB")
                cpu_lbl.config(text="CPU: --%")

            # Lock status
            active_lock = locks.get(serial)
            if active_lock:
                agent = active_lock.get("agent_id", "Agent")
                task = active_lock.get("task_name", "Running")
                lock_lbl.config(text=f"Locked by: {agent} ({task})", fg=C_MAUVE)
            else:
                lock_lbl.config(text="Agent: None (Idle)", fg=C_SUBTEXT)

    # UI Action Handlers
    def on_toggle_device(self, serial: str, dev: Dict[str, Any]):
        states = {s["serial"]: s for s in self.proc_mgr.get_farm_state()}
        curr = states.get(serial, {})

        def _worker():
            if curr.get("is_running"):
                self.log_agent_msg("ProcessManager", f"Stopping {serial}...", "warn")
                ok, msg = self.proc_mgr.stop_instance(serial)
                self.scrcpy_mgr.close_viewer(serial)
                self.log_agent_msg("ProcessManager", f"Stop result: {msg}", "info" if ok else "error")
            else:
                self.log_agent_msg("ProcessManager", f"Starting {dev['name']} ({serial}) in Ultra-Light Headless mode...", "info")
                ok, msg = self.proc_mgr.start_instance(dev["name"], dev["port"], headless=True)
                self.log_agent_msg("ProcessManager", f"Start result: {msg}", "success" if ok else "error")

        threading.Thread(target=_worker, daemon=True).start()


    def on_view_screen(self, serial: str):
        if self.scrcpy_mgr.is_viewer_open(serial):
            self.scrcpy_mgr.close_viewer(serial)
            return

        ok, msg = self.scrcpy_mgr.open_viewer(serial, title=f"Phone Display ({serial})")
        if not ok:
            messagebox.showerror("Scrcpy Error", f"Could not launch scrcpy viewer:\n{msg}")

    def on_start_all(self):
        def _worker():
            self.log_agent_msg("Farm", "Starting all 4 AVDs in Ultra-Light Headless mode...", "info")
            res = self.proc_mgr.start_farm(4, headless=True)
            for r in res:
                self.log_agent_msg("Farm", f"Instance {r['name']}: {r['message']}", "success" if r["success"] else "error")
        threading.Thread(target=_worker, daemon=True).start()


    def on_stop_all(self):
        def _worker():
            self.log_agent_msg("Farm", "Stopping all running farm devices...", "warn")
            self.scrcpy_mgr.close_all()
            res = self.proc_mgr.stop_farm()
            for r in res:
                self.log_agent_msg("Farm", f"Shutdown {r['name']}: {r['message']}", "info")
        threading.Thread(target=_worker, daemon=True).start()


    def on_install_apk_all(self):
        apk_path = filedialog.askopenfilename(
            title="Select Mobile Application APK",
            filetypes=[("Android Package (*.apk)", "*.apk"), ("All Files", "*.*")]
        )
        if not apk_path:
            return

        def _worker():
            connected = [d["serial"] for d in self.adb.get_connected_devices() if d["status"] == "device"]
            if not connected:
                self.log_agent_msg("InstallAPK", "No devices currently online to install APK!", "error")
                return

            self.log_agent_msg("InstallAPK", f"Broadcasting install for: {Path(apk_path).name}...", "info")
            for serial in connected:
                ok, msg = self.adb.install_apk(serial, apk_path)
                self.log_agent_msg("InstallAPK", f"[{serial}] Install: {'Success' if ok else msg}", "success" if ok else "error")

        threading.Thread(target=_worker, daemon=True).start()


    def on_trigger_fingerprint(self, serial: str):
        ok, msg = self.hardware.touch_fingerprint(serial)
        self.log_agent_msg("HardwareSim", f"[{serial}] Fingerprint sensor touched -> {msg}", "success" if ok else "error")

    def on_popup_sms_otp(self, serial: str):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Inject SMS OTP - {serial}")
        dialog.geometry("380x240")
        dialog.configure(bg=C_MANTLE)
        dialog.transient(self.root)

        tk.Label(dialog, text="Sender Phone Number:", font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_MANTLE).pack(anchor="w", padx=16, pady=(16, 2))
        phone_entry = tk.Entry(dialog, font=("Segoe UI", 9), bg=C_CRUST, fg=C_TEXT, insertbackground=C_TEXT, relief="flat")
        phone_entry.insert(0, "+84901234567")
        phone_entry.pack(fill=tk.X, padx=16, pady=(0, 8))

        tk.Label(dialog, text="OTP Code / Message:", font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_MANTLE).pack(anchor="w", padx=16, pady=(4, 2))
        otp_entry = tk.Entry(dialog, font=("Segoe UI", 9), bg=C_CRUST, fg=C_TEXT, insertbackground=C_TEXT, relief="flat")
        otp_entry.insert(0, "889900")
        otp_entry.pack(fill=tk.X, padx=16, pady=(0, 16))

        def _send():
            p = phone_entry.get().strip()
            o = otp_entry.get().strip()
            ok, msg = self.hardware.send_sms_otp(serial, p, f"Ma OTP xac thuc cua ban la: {o}")
            self.log_agent_msg("HardwareSim", f"[{serial}] Sent SMS OTP '{o}' from {p} -> {msg}", "success" if ok else "error")
            dialog.destroy()

        btn_send = tk.Button(dialog, text="🚀 Send SMS", font=("Segoe UI", 9, "bold"), bg=C_BLUE, fg=C_CRUST, relief="flat", command=_send)
        btn_send.pack(fill=tk.X, padx=16)

    def on_popup_gps(self, serial: str):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Spoof GPS Coordinates - {serial}")
        dialog.geometry("400x260")
        dialog.configure(bg=C_MANTLE)
        dialog.transient(self.root)

        tk.Label(dialog, text="Select City Preset:", font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_MANTLE).pack(anchor="w", padx=16, pady=(16, 4))

        combo = ttk.Combobox(dialog, values=[loc["name"] for loc in PRESET_LOCATIONS.values()], state="readonly")
        combo.current(0)
        combo.pack(fill=tk.X, padx=16, pady=(0, 12))

        def _apply():
            idx = combo.current()
            key = list(PRESET_LOCATIONS.keys())[idx]
            loc = PRESET_LOCATIONS[key]
            ok, msg = self.hardware.set_gps_location(serial, loc["lat"], loc["lng"], loc["alt"])
            self.log_agent_msg("HardwareSim", f"[{serial}] GPS updated to {loc['name']} ({loc['lat']}, {loc['lng']})", "success" if ok else "error")
            dialog.destroy()

        btn_apply = tk.Button(dialog, text="📍 Apply Location", font=("Segoe UI", 9, "bold"), bg=C_TEAL, fg=C_CRUST, relief="flat", command=_apply)
        btn_apply.pack(fill=tk.X, padx=16, pady=8)

    def on_run_parallel_test(self):
        pkg = self.pkg_entry.get().strip()
        if not pkg:
            messagebox.showwarning("Missing Package", "Please enter target package name.")
            return

        try:
            steps = int(self.steps_spin.get())
        except ValueError:
            steps = 20

        def _worker():
            self.log_agent_msg("Orchestrator", f"Launching Parallel Exploration for {pkg} across all online farm devices...", "info")
            online = self.orchestrator.get_online_devices()
            if not online:
                self.log_agent_msg("Orchestrator", "No devices online! Please start at least one device first.", "error")
                return

            def _log_cb(serial: str, step_info: Dict[str, Any]):
                act = step_info.get("action", "")
                tgt = step_info.get("target", "")
                self.log_agent_msg(serial, f"Step {step_info.get('step')}: {act} -> {tgt}", "info")

            res = self.orchestrator.run_parallel_exploration(pkg, max_steps=steps, log_callback=_log_cb)
            self.log_agent_msg("Orchestrator", f"Run completed in {res.get('duration_seconds')}s. Tested {res.get('devices_tested')} devices.", "success")
            self.root.after(0, self.refresh_reports)

        threading.Thread(target=_worker, daemon=True).start()


    def on_abort_agents(self):
        self.orchestrator.stop_all_agents()
        self.log_agent_msg("Orchestrator", "Abort signal sent to all active agents.", "warn")

    def on_optimize_device(self, serial: str):
        def _worker():
            self.log_agent_msg("Optimizer", f"Applying Zero-Lag performance profile & debloating {serial}...", "info")
            opt = AVDOptimizer(self.adb)
            res = opt.optimize_device(serial)
            debloated_count = len(res.get("debloated_packages", []))
            self.log_agent_msg("Optimizer", f"[{serial}] Debloated {debloated_count} telemetry packages; animations & sync disabled.", "success")
        threading.Thread(target=_worker, daemon=True).start()


    def on_run_closed_loop(self):
        goal = self.goal_entry.get().strip()
        pkg = self.pkg_entry.get().strip()
        serial = self.device_combo.get().strip()
        if not goal:
            messagebox.showwarning("Missing Goal", "Please enter test goal prompt.")
            return

        def _worker():
            self.log_agent_msg("LoopOrchestrator", f"Starting 4-Subagent Closed Loop on {serial} for goal: '{goal}'...", "info")
            orch = LoopOrchestrator(serial, self.adb)

            def _event_cb(agent_name: str, event_data: Dict[str, Any]):
                stat = event_data.get("status", "")
                detail = event_data.get("detail") or event_data.get("reason") or event_data.get("goal") or ""
                self.log_agent_msg(agent_name, f"{stat.upper()}: {detail}", "success" if "healed" in stat or "success" in stat or "ready" in stat else "info")

            res = orch.run_autonomous_loop(goal, pkg, callback=_event_cb)
            dur = res.get("duration_seconds", 0)
            steps = res.get("steps_executed", 0)
            self.log_agent_msg("LoopOrchestrator", f"Closed loop finished in {dur}s ({steps} milestones). Status: {res.get('status')}", "success")
            self.root.after(0, self.refresh_reports)

        threading.Thread(target=_worker, daemon=True).start()


    def on_run_matrix(self):
        def _worker():
            self.log_agent_msg("AgentsOrchestrator", "Launching 4-Device Parallel Persona Matrix across all devices...", "info")
            def _log_cb(serial, role, msg):
                self.log_agent_msg(f"{serial}:{role}", msg, "info")

            res = self.agents_orchestrator.run_parallel_matrix(log_callback=_log_cb)
            dur = res.get("total_duration_seconds", 0)
            rep = res.get("report_path", "")
            self.log_agent_msg("AgentsOrchestrator", f"Matrix Run Finished in {dur}s! Generated Master Report: {rep}", "success")
            self.root.after(0, self.refresh_reports)
            self.root.after(0, self.refresh_memory_tab)

        threading.Thread(target=_worker, daemon=True).start()


    def on_run_pipeline(self):
        def _worker():
            self.log_agent_msg("Pipeline", "Starting Autonomous Dev-QA-Patch Agile Pipeline across 4 devices...", "info")
            def _log_cb(serial, subagent, msg):
                self.log_agent_msg(f"{serial}:{subagent}", msg, "info")

            res = self.pipeline_director.run_4_device_autonomous_pipeline(log_callback=_log_cb)
            dur = res.get("total_duration_seconds", 0)
            self.log_agent_msg("Pipeline", f"Pipeline completed in {dur}s. All Kanban cards moved to DONE!", "success")
            self.root.after(0, self.refresh_reports)
            self.root.after(0, self.refresh_memory_tab)

        threading.Thread(target=_worker, daemon=True).start()

    def on_run_self_evolution(self):
        pkg = self.pkg_entry.get().strip() or "com.android.settings"

        def _worker():
            self.log_agent_msg("SelfEvolutionEngine", "Launching 12-Subagent Autonomous Self-Evolution Loop...", "info")
            def _cb(agent, msg):
                self.log_agent_msg(agent, msg, "info")

            res = self.evolution_engine.run_evolution_loop(iterations=1, package_name=pkg, callback=_cb)
            dur = res.get("total_duration_seconds", 0)
            rep = res.get("report_path", "")
            self.log_agent_msg("SelfEvolutionEngine", f"Evolution Completed in {dur}s! Report: {rep}", "success")
            self.root.after(0, self.refresh_reports)
            self.root.after(0, self.refresh_memory_tab)
            self.root.after(0, self.refresh_real_devices_tab)

        threading.Thread(target=_worker, daemon=True).start()

    def on_change_farm_mode(self, event=None):
        mode = self.farm_mode_combo.get().strip()
        res = self.real_mgr.set_farm_mode(mode)
        self.log_agent_msg("RealDeviceManager", f"Switched Farm Mode to {res['farm_mode']} (Real Phones Enabled: {res['real_phone_farm_enabled']})", "info")
        self.refresh_real_devices_tab()

    def refresh_real_devices_tab(self):
        if not hasattr(self, "real_tree"):
            return
        for item in self.real_tree.get_children():
            self.real_tree.delete(item)

        def _worker():
            real_devs = self.real_mgr.discover_real_devices(include_unauthorized=True)
            for d in real_devs:
                if d.get("status") == "device":
                    self.real_mgr.apply_real_phone_health_guard(d["serial"])

            def _populate():
                for d in real_devs:
                    bat = d.get("battery", {})
                    health_str = "OVERHEATED!" if bat.get("overheated") else ("ONLINE (GUARDED)" if d.get("status") == "device" else d.get("status", "offline").upper())
                    self.real_tree.insert(
                        "",
                        "end",
                        values=(
                            d.get("serial"),
                            d.get("name"),
                            d.get("connection_type"),
                            d.get("android_version"),
                            d.get("resolution"),
                            f"{bat.get('level', 0)}%",
                            f"{bat.get('temperature_c', 0.0)}°C",
                            d.get("wifi_ip") or "--",
                            health_str
                        )
                    )
            self.root.after(0, _populate)

        threading.Thread(target=_worker, daemon=True).start()

    def on_connect_wireless_adb(self):
        ep = self.wireless_ip_entry.get().strip()
        if not ep:
            return
        def _worker():
            self.log_agent_msg("WirelessADB", f"Connecting to Wireless Phone {ep}...", "info")
            ok, msg = self.real_mgr.connect_wireless_device(ep)
            self.log_agent_msg("WirelessADB", msg, "success" if ok else "error")
            self.root.after(0, self.refresh_real_devices_tab)
        threading.Thread(target=_worker, daemon=True).start()

    def on_usb_to_wireless(self):
        sel = self.real_tree.selection()
        if not sel:
            messagebox.showinfo("Select USB Phone", "Please select a USB-connected real phone in the table first.")
            return
        serial = self.real_tree.item(sel[0], "values")[0]
        def _worker():
            self.log_agent_msg("WirelessADB", f"Switching {serial} from USB to Wireless TCP/IP :5555...", "info")
            ok, msg = self.real_mgr.enable_wireless_adb(serial, 5555)
            self.log_agent_msg("WirelessADB", msg, "success" if ok else "error")
            self.root.after(0, self.refresh_real_devices_tab)
        threading.Thread(target=_worker, daemon=True).start()

    def on_open_scrcpy_wall(self):
        gf = self.bcast_group_combo.get().strip() if hasattr(self, "bcast_group_combo") else "ALL"
        targets = self.broadcaster.resolve_target_serials(group_filter=gf)
        if not targets:
            messagebox.showwarning("No Online Devices", "No online devices found for the selected group.")
            return
        res = self.scrcpy_mgr.open_multi_device_wall(targets, cols=4)
        self.log_agent_msg("ScrcpyWall", f"Launched {res['launched_count']}/{res['total_requested']} tiled screen viewers.", "success")

    def on_broadcast_tap(self):
        raw = self.bcast_xy_entry.get().strip()
        gf = self.bcast_group_combo.get().strip()
        try:
            parts = [float(p.strip()) for p in raw.split(",")]
            x, y = parts[0], parts[1]
        except Exception:
            x, y = 0.5, 0.5
        def _worker():
            res = self.broadcaster.broadcast_tap(x, y, group_filter=gf)
            self.log_agent_msg("GroupBroadcast", f"Synced Tap ({x}, {y}) to {res['targets_count']} devices in {res.get('total_duration_ms', 0)}ms", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_broadcast_key(self, key_name: str):
        gf = self.bcast_group_combo.get().strip()
        def _worker():
            res = self.broadcaster.broadcast_key(key_name, group_filter=gf)
            self.log_agent_msg("GroupBroadcast", f"Synced Key '{key_name}' to {res['targets_count']} devices in {res.get('total_duration_ms', 0)}ms", "info")
        threading.Thread(target=_worker, daemon=True).start()

    def on_broadcast_text(self):
        txt = self.bcast_text_entry.get().strip()
        gf = self.bcast_group_combo.get().strip()
        def _worker():
            res = self.broadcaster.broadcast_text(txt, group_filter=gf)
            self.log_agent_msg("GroupBroadcast", f"Synced Text '{txt}' to {res['targets_count']} devices in {res.get('total_duration_ms', 0)}ms", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_broadcast_launch(self):
        pkg = self.bcast_text_entry.get().strip()
        gf = self.bcast_group_combo.get().strip()
        def _worker():
            res = self.broadcaster.broadcast_launch_app(pkg, group_filter=gf)
            self.log_agent_msg("GroupBroadcast", f"Synced Launch '{pkg}' across {res['targets_count']} devices in {res.get('total_duration_ms', 0)}ms", "success")
        threading.Thread(target=_worker, daemon=True).start()


    def refresh_reports(self):
        for item in self.rep_tree.get_children():
            self.rep_tree.delete(item)

        reports = self.reporter.list_reports()
        for r in reports:
            self.rep_tree.insert(
                "",
                "end",
                values=(
                    r.get("report_id"),
                    r.get("created_at"),
                    r.get("serial"),
                    r.get("package_name"),
                    r.get("error_type"),
                    r.get("error_message")
                ),
                tags=(r.get("report_path"),)
            )

    def on_double_click_report(self, event):
        item = self.rep_tree.selection()
        if not item:
            return
        tags = self.rep_tree.item(item[0], "tags")
        if tags and os.path.exists(tags[0]):
            os.startfile(tags[0])

    def on_open_reports_folder(self):
        os.startfile(str(self.reporter.reports_dir))

    def on_close(self):
        self._is_running = False
        self.scrcpy_mgr.close_all()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = FarmDashboardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
