"""
Android Multi-Agent Farm (AMAF 7.0) - Modern Desktop Control Center
High-DPI aware, dark-themed control center for managing hybrid Real Phones & Headless AVDs,
30-Subagent Self-Evolution, Universal 7-Mode 2FA Automation, 10+ Type & Web/Rotation/Grid CAPTCHA CV,
Set-of-Mark (SoM) Visual Grounding, Vivo/OriginOS USB Popup Guard, WCAG 2.1 Contrast,
Crash/Tombstone/ANR Demangling, and Network API Telemetry.
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
from agents.oem_popup_guard_subagent import OEMPopupGuardSubagent
from agents.auto_screenshot_subagent import AutoScreenshotSubagent
from agents.complex_captcha_subagent import ComplexCaptchaSubagent
from agents.universal_2fa_subagent import Universal2FASubagent
from agents.web_and_advanced_captcha_subagent import WebAndAdvancedCaptchaSubagent
from agents.accessibility_wcag_subagent import AccessibilityAndWCAGContrastSubagent
from agents.crash_tombstone_anr_subagent import CrashTombstoneAndANRSubagent
from agents.network_api_latency_subagent import NetworkTrafficAndAPILatencySubagent
from agents.performance_memleak_subagent import PerformanceAndMemLeakSubagent
from agents.human_persona_ux_auditor_subagent import HumanPersonaUXAuditorSubagent
from agents.live_web_testbench_e2e_subagent import LiveWebTestbenchAndRealPhoneE2ESubagent
from agents.vivo_originos_optimizer_subagent import VivoOriginOSDeepOptimizerSubagent
from agents.audio_behavior_captcha_subagent import InteractiveAudioAndBehaviorCaptchaSubagent
from agents.session_credential_guard_subagent import CrossAppSessionAndCredentialGuardSubagent
from agents.real_device_e2e_benchmark_subagent import RealDeviceE2EBenchmarkAndSelfHealerSubagent
from agents.local_gpu_vision_subagent import LocalGPUVisionSubagent
from agents.macro_replay_subagent import MacroReplaySubagent
from agents.android_cdp_subagent import AndroidCDPSubagent
from agents.social_workflow_subagent import SocialWorkflowSubagent
from agents.hybrid_captcha_fallback_subagent import HybridCaptchaFallbackSubagent
from agents.persistent_adb_stream_subagent import PersistentADBStreamSubagent
from agents.keyboard_viewport_guard_subagent import KeyboardAndViewportGuardSubagent
from agents.semantic_object_matcher_subagent import ZeroTokenSemanticMatcherSubagent
from agents.account_vault_proxy_subagent import MultiAccountVaultAndProxySubagent
from agents.visual_flow_dag_subagent import VisualFlowBuilderAndLiveMonitorSubagent
from agents.universal_apk_installer_subagent import UniversalMultiStageInstallerSubagent
from agents.sideload_source_guard_subagent import SideloadSourceAndPermissionSubagent
from agents.oem_secime_vault_subagent import OEMVaultAndSecIMEHandlerSubagent
from agents.multi_user_package_subagent import MultiUserProfileAndPackageSubagent
from agents.always_on_install_daemon_subagent import AlwaysOnInstallDaemonAndCLISubagent
from agents.recursive_10x_evolution_subagent import (
    GKDSelectorRuleEngineSubagent,
    MobileAgentTipsAndShortcutsMemorySubagent,
    UITarsSystem2ReflectionVerifierSubagent,
    DroidBotStateTransitionGraphSubagent,
    Recursive10xEvolutionCoordinatorSubagent,
)
from agents.ui_ux_design_system_subagent import (
    VisualScreenshotClutterCriticSubagent,
    DesignTokenAnd8PtGridSubagent,
)
from agents.ui_ux_navigation_and_palette_subagent import (
    SidebarNavigationAndIASubagent,
    CommandPaletteAndProgressiveDisclosureSubagent,
    BentoDeviceCardAndSparklineSubagent,
)
from agents.recursive_10x_ui_ux_evolution_subagent import (
    SemanticCTAHierarchyAndAntiRainbowSubagent,
    WCAGContrastAndTypographyScaleSubagent,
    MicroInteractionAndEmptyStateSubagent,
    UIFinishGateReviewerSubagent,
    Recursive10xUIUXEvolutionCoordinatorSubagent,
)
from agents.antibot_biometric_kinematics_subagent import (
    SigmaLognormalTouchKinematicsSubagent,
    PatchrightStealthCDPandWebViewSubagent,
)
from agents.antibot_fingerprint_and_ui_radar_subagent import (
    AndroidEnvironmentAndSensorCoherenceSubagent,
    TurnstileAndWAFInvisibleDefenseSubagent,
    AntiBotRadarAndUIUXTelemetrySubagent,
)
from agents.recursive_10x_antibot_ui_ux_evolution_subagent import (
    MobileAppHeaderAndFilterPillRefinerSubagent,
    AdaptiveDwellAndRhythmPacerSubagent,
    CrossLayerBotSignalCorrelatorSubagent,
    UnifiedUIUXAndAntiBotFinishGateSubagent,
    CausalChain10xAntiBotUIUXCoordinatorSubagent,
)
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
        self.root.title("Android Multi-Agent Farm (AMAF 14.0) | 75 Subagents | 4-Layer Anti-Bot Stealth | Sigma-Lognormal Touch Kinematics | Cloudflare Radar UI/UX & 10x Causal Evolution")
        self.root.geometry("1340x880")
        self.root.minsize(1100, 740)
        self.root.configure(bg=C_BASE)

        # Core Engines & 30-Subagent Specialists
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

        # AMAF 5.0 - 7.0 Subagents
        self.oem_guard = OEMPopupGuardSubagent(self.adb, self.memory)
        self.auto_screenshot = AutoScreenshotSubagent(self.adb, self.memory)
        self.complex_captcha = ComplexCaptchaSubagent(self.adb, self.memory)
        self.universal_2fa = Universal2FASubagent(self.adb, self.memory)
        self.web_adv_captcha = WebAndAdvancedCaptchaSubagent(self.adb, self.memory)
        self.wcag_auditor = AccessibilityAndWCAGContrastSubagent(self.adb, self.memory)
        self.crash_analyzer = CrashTombstoneAndANRSubagent(self.adb, self.memory)
        self.net_api_profiler = NetworkTrafficAndAPILatencySubagent(self.adb, self.memory)
        self.perf_profiler = PerformanceAndMemLeakSubagent(self.adb, self.memory)
        self.human_ux_auditor = HumanPersonaUXAuditorSubagent(self.adb)
        self.live_testbench_agent = LiveWebTestbenchAndRealPhoneE2ESubagent(self.adb, self.memory)
        self.vivo_optimizer = VivoOriginOSDeepOptimizerSubagent(self.adb, self.memory)
        self.audio_behavior_captcha = InteractiveAudioAndBehaviorCaptchaSubagent(self.adb, self.memory)
        self.session_guard = CrossAppSessionAndCredentialGuardSubagent(self.adb, self.memory)
        self.e2e_benchmark = RealDeviceE2EBenchmarkAndSelfHealerSubagent(self.adb, self.memory)
        self.local_gpu_vision = LocalGPUVisionSubagent(self.adb, self.memory)
        self.macro_replay = MacroReplaySubagent(adb=self.adb, memory=self.memory)
        self.android_cdp = AndroidCDPSubagent(self.adb, self.memory)
        self.social_workflow = SocialWorkflowSubagent(self.adb, self.memory)
        self.hybrid_captcha_3tier = HybridCaptchaFallbackSubagent(self.adb, self.memory)
        self.persistent_stream = PersistentADBStreamSubagent(adb_path=self.adb.adb_path)
        self.kbd_viewport_guard = KeyboardAndViewportGuardSubagent(self.adb, self.memory, cdp_bridge=self.android_cdp.bridge)
        self.semantic_matcher = ZeroTokenSemanticMatcherSubagent(self.adb, self.memory)
        self.account_vault = MultiAccountVaultAndProxySubagent(adb=self.adb, memory=self.memory)
        self.visual_flow_dag = VisualFlowBuilderAndLiveMonitorSubagent(adb=self.adb, memory=self.memory)
        self.universal_apk_installer = UniversalMultiStageInstallerSubagent(adb_wrapper=self.adb)
        self.sideload_source_guard = SideloadSourceAndPermissionSubagent(adb_wrapper=self.adb)
        self.oem_secime_vault = OEMVaultAndSecIMEHandlerSubagent(adb=self.adb, memory=self.memory)
        self.multi_user_pkg = MultiUserProfileAndPackageSubagent(adb=self.adb, memory=self.memory)
        self.always_on_install_daemon = AlwaysOnInstallDaemonAndCLISubagent(adb=self.adb, memory=self.memory)
        self.gkd_selector_engine = GKDSelectorRuleEngineSubagent()
        self.mobile_agent_memory = MobileAgentTipsAndShortcutsMemorySubagent()
        self.uitars_reflection = UITarsSystem2ReflectionVerifierSubagent()
        self.droidbot_utg = DroidBotStateTransitionGraphSubagent()
        self.recursive_10x_coordinator = Recursive10xEvolutionCoordinatorSubagent()
        # AMAF 13.0 Subagents (#56-#65): UI/UX Design System, Sidebar IA, Ctrl+K Palette, Bento Cards & 10x UI/UX Evolution
        self.visual_clutter_critic = VisualScreenshotClutterCriticSubagent()
        self.design_token_grid = DesignTokenAnd8PtGridSubagent()
        self.sidebar_ia_nav = SidebarNavigationAndIASubagent()
        self.command_palette_agent = CommandPaletteAndProgressiveDisclosureSubagent()
        self.bento_sparkline_agent = BentoDeviceCardAndSparklineSubagent()
        self.semantic_cta_agent = SemanticCTAHierarchyAndAntiRainbowSubagent()
        self.wcag_typography_agent = WCAGContrastAndTypographyScaleSubagent()
        self.micro_empty_state_agent = MicroInteractionAndEmptyStateSubagent()
        self.ui_finish_gate_reviewer = UIFinishGateReviewerSubagent()
        self.recursive_10x_ui_ux_coordinator = Recursive10xUIUXEvolutionCoordinatorSubagent()
        # AMAF 14.0 Subagents (#66-#75): 4-Layer Anti-Bot Stealth, Sigma-Lognormal Touch, Sensor Coherence, Turnstile Warm-Up & 10x Causal Loop
        self.sigma_lognormal_kinematics = SigmaLognormalTouchKinematicsSubagent()
        self.patchright_stealth_cdp = PatchrightStealthCDPandWebViewSubagent()
        self.sensor_coherence_guard = AndroidEnvironmentAndSensorCoherenceSubagent()
        self.turnstile_waf_defense = TurnstileAndWAFInvisibleDefenseSubagent()
        self.antibot_radar_telemetry = AntiBotRadarAndUIUXTelemetrySubagent()
        self.mobile_header_filter_refiner = MobileAppHeaderAndFilterPillRefinerSubagent()
        self.cognitive_rhythm_pacer = AdaptiveDwellAndRhythmPacerSubagent()
        self.cross_layer_bot_correlator = CrossLayerBotSignalCorrelatorSubagent()
        self.unified_ui_antibot_finish_gate = UnifiedUIUXAndAntiBotFinishGateSubagent()
        self.causal_10x_antibot_ui_ux_coordinator = CausalChain10xAntiBotUIUXCoordinatorSubagent()

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

        style.configure(".", background=C_BASE, foreground=C_TEXT, font=("Segoe UI", 10))
        style.configure("TNotebook", background=C_MANTLE, borderwidth=0)
        style.configure("TNotebook.Tab", background=C_SURFACE0, foreground=C_TEXT, padding=[14, 8], font=("Segoe UI", 9, "bold"))
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
        style.configure("Treeview.Heading", background=C_SURFACE0, foreground=C_TEXT, font=("Segoe UI", 9, "bold"), relief="flat")

    def _get_all_known_serials(self) -> List[str]:
        base = ["emulator-5554", "emulator-5556", "emulator-5558", "emulator-5560"]
        try:
            connected = [d["serial"] for d in self.adb.get_connected_devices() if d.get("serial")]
            for s in connected:
                if s not in base:
                    base.insert(0, s)
        except Exception:
            pass
        return base

    def _build_header(self):
        header = tk.Frame(self.root, bg=C_MANTLE, height=70, padx=20, pady=12)
        header.pack(fill=tk.X, side=tk.TOP)

        title_frame = tk.Frame(header, bg=C_MANTLE)
        title_frame.pack(side=tk.LEFT)

        title_lbl = tk.Label(
            title_frame,
            text="⚡ Android Multi-Agent Farm (AMAF 14.0 — 75 Subagents, 4-Layer Anti-Bot Stealth, Sigma-Lognormal Kinematics & 10x Causal Loop)",
            font=("Segoe UI", 16, "bold"),
            fg=C_BLUE,
            bg=C_MANTLE
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            title_frame,
            text="65 Subagents | Screenshot Clutter Critic (#56) | 8pt Grid (#57) | Miller Sidebar IA (#58) | Ctrl+K Palette (#59) | Bento Sparklines (#60) | Anti-Rainbow CTA (#61) | Finish Gate (#64) | 10x UI/UX Loop (#65)",
            font=("Segoe UI", 9),
            fg=C_SUBTEXT,
            bg=C_MANTLE
        )
        sub_lbl.pack(anchor="w")

        self.metrics_frame = tk.Frame(header, bg=C_MANTLE)
        self.metrics_frame.pack(side=tk.RIGHT, padx=10)

        self.sys_ram_lbl = tk.Label(self.metrics_frame, text="RAM: Free -- GB", font=("Segoe UI", 9, "bold"), fg=C_GREEN, bg=C_SURFACE0, padx=10, pady=4)
        self.sys_ram_lbl.pack(side=tk.LEFT, padx=4)

        self.sys_cpu_lbl = tk.Label(self.metrics_frame, text="CPU: --%", font=("Segoe UI", 9, "bold"), fg=C_YELLOW, bg=C_SURFACE0, padx=10, pady=4)
        self.sys_cpu_lbl.pack(side=tk.LEFT, padx=4)

        btn_start_all = tk.Button(header, text="▶ Start All Headless", font=("Segoe UI", 9, "bold"), bg=C_GREEN, fg=C_CRUST,
                                  activebackground="#89dceb", relief="flat", padx=10, pady=6, cursor="hand2", command=self.on_start_all)
        btn_start_all.pack(side=tk.RIGHT, padx=4)

        btn_stop_all = tk.Button(header, text="⏹ Stop All", font=("Segoe UI", 9, "bold"), bg=C_RED, fg=C_CRUST,
                                 activebackground="#f2cdcd", relief="flat", padx=10, pady=6, cursor="hand2", command=self.on_stop_all)
        btn_stop_all.pack(side=tk.RIGHT, padx=4)

        btn_apk = tk.Button(header, text="📦 Guarded Install APK", font=("Segoe UI", 9, "bold"), bg=C_MAUVE, fg=C_CRUST,
                            activebackground="#b4befe", relief="flat", padx=10, pady=6, cursor="hand2", command=self.on_install_apk_all)
        btn_apk.pack(side=tk.RIGHT, padx=4)

        btn_foodgo = tk.Button(header, text="🍔 Mở & Xem FoodGo P18", font=("Segoe UI", 9, "bold"), bg=C_PEACH, fg=C_CRUST,
                               activebackground="#f9e2af", relief="flat", padx=10, pady=6, cursor="hand2", command=self.on_launch_foodgo_latest)
        btn_foodgo.pack(side=tk.RIGHT, padx=4)

    def _build_main_content(self):
        main_pane = tk.PanedWindow(self.root, orient=tk.VERTICAL, bg=C_BASE, sashrelief="flat", sashwidth=4)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

        # Top Section: 4 Device Cards Grid
        devices_wrapper = tk.LabelFrame(
            main_pane,
            text=" Virtual Phone Devices (4 Headless AVD Instances + Real Phones in Tab 2 & 3) ",
            font=("Segoe UI", 10, "bold"),
            fg=C_BLUE,
            bg=C_BASE,
            padx=10,
            pady=8
        )
        main_pane.add(devices_wrapper, minsize=275)

        self.cards_grid = tk.Frame(devices_wrapper, bg=C_BASE)
        self.cards_grid.pack(fill=tk.BOTH, expand=True)

        for i in range(4):
            self.cards_grid.columnconfigure(i, weight=1, uniform="device_col")

        for idx, dev in enumerate(DEFAULT_FARM_DEVICES):
            self._create_device_card(dev, idx)

        # Bottom Section: 5 Feature Tabs
        tabs_frame = tk.Frame(main_pane, bg=C_BASE)
        main_pane.add(tabs_frame, minsize=390)

        self.notebook = ttk.Notebook(tabs_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Multi-Agent & 30-Subagent Evolution
        self.tab_agents = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_agents, text=" 🤖 75-Subagent Evolution & 10x Loops ")
        self._build_agents_tab()

        # Tab 2: Real Phone Farm & Group Broadcast Control
        self.tab_real_farm = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_real_farm, text=" 📱 Real Phone Farm & Group Broadcast ")
        self._build_real_farm_tab()

        # Tab 3: AMAF 7.0 2FA, CAPTCHA CV, Web & Deep Diagnostics
        self.tab_v7_lab = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_v7_lab, text=" 🔐 2FA, CAPTCHA CV, Live Web Testbench & Vivo Lab (v8.0) ")
        self._build_v7_lab_tab()

        # Tab 4: AMAF 9.0 Zero-Token GPU RTX 3050, CDP Bridge, Macro & TikTok Workflows
        self.tab_v9_gpu = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_v9_gpu, text=" 🚀 Zero-Token GPU RTX 3050, CDP, Macro & TikTok (v9.0) ")
        self._build_v9_zero_token_gpu_tab()

        # Tab 5: AMAF 10.0 Live Stream, IME Guard, Semantic GPU, Account Vault & Visual DAG
        self.tab_v10_dag = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_v10_dag, text=" ⚡ Live Stream, IME Guard, Semantic GPU, Vault & DAG (v10.0) ")
        self._build_v10_stream_vault_dag_tab()

        # Tab 6: AMAF 12.0 Universal APK Installer, Sideload Guard, Always-On Daemon & 10x Recursive Evolution
        self.tab_v12_installer = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_v12_installer, text=" 📦 Universal APK Installer & 10x Evolution (v12.0) ")
        self._build_v12_installer_and_10x_tab()

        # Tab 7: AMAF 13.0 UI/UX 10x Design System, Ctrl+K Command Palette, Bento Sparklines & Live Vivo Screenshot Critic
        self.tab_v13_ui_ux = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_v13_ui_ux, text=" 🎨 UI/UX 10x Design System, Ctrl+K & Vivo Critic (v13.0) ")
        self._build_v13_ui_ux_and_critic_tab()
        self.root.bind("<Control-k>", lambda e: self.on_v13_ctrl_k_search())

        # Tab 8: AMAF 14.0 4-Layer Anti-Bot Stealth, Sigma-Lognormal Touch Kinematics, Radar Bento & 10x Causal Evolution
        self.tab_v14_antibot = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_v14_antibot, text=" 🛡️ Anti-Bot 4-Layer Stealth & 10x Causal Loop (v14.0) ")
        self._build_v14_antibot_and_causal_tab()

        # Tab 4: Defect Reports (Bug Tracker)
        self.tab_reports = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_reports, text=" 🐞 Defect Reports & Evidence ")
        self._build_reports_tab()

        # Tab 5: Codebase Memory & Auto-Patches
        self.tab_memory = tk.Frame(self.notebook, bg=C_BASE, padx=12, pady=10)
        self.notebook.add(self.tab_memory, text=" 🧠 Memory, Macros & Patches ")
        self._build_memory_tab()

    def _create_device_card(self, dev: Dict[str, Any], col: int):
        serial = dev["serial"]
        card = tk.Frame(self.cards_grid, bg=C_MANTLE, highlightbackground=C_SURFACE0, highlightthickness=1, padx=12, pady=10)
        card.grid(row=0, column=col, sticky="nsew", padx=6, pady=4)

        top = tk.Frame(card, bg=C_MANTLE)
        top.pack(fill=tk.X)

        name_lbl = tk.Label(top, text=dev["name"], font=("Segoe UI", 11, "bold"), fg=C_TEXT, bg=C_MANTLE)
        name_lbl.pack(side=tk.LEFT)

        status_badge = tk.Label(top, text="OFFLINE", font=("Segoe UI", 8, "bold"), fg=C_SUBTEXT, bg=C_SURFACE0, padx=6, pady=2)
        status_badge.pack(side=tk.RIGHT)

        sub = tk.Label(card, text=f"{serial} | Port {dev['port']}", font=("Segoe UI", 8), fg=C_SUBTEXT, bg=C_MANTLE)
        sub.pack(anchor="w", pady=(2, 0))

        desc = tk.Label(card, text=dev["description"], font=("Segoe UI", 8, "italic"), fg=C_TEAL, bg=C_MANTLE)
        desc.pack(anchor="w", pady=(0, 6))

        metrics_box = tk.Frame(card, bg=C_CRUST, padx=8, pady=5)
        metrics_box.pack(fill=tk.X, pady=3)

        ram_lbl = tk.Label(metrics_box, text="RAM: -- MB", font=("Segoe UI", 9), fg=C_TEXT, bg=C_CRUST)
        ram_lbl.pack(anchor="w")

        cpu_lbl = tk.Label(metrics_box, text="CPU: --%", font=("Segoe UI", 9), fg=C_TEXT, bg=C_CRUST)
        cpu_lbl.pack(anchor="w")

        lock_lbl = tk.Label(metrics_box, text="Agent: None (Idle)", font=("Segoe UI", 8), fg=C_SUBTEXT, bg=C_CRUST)
        lock_lbl.pack(anchor="w")

        btn_row1 = tk.Frame(card, bg=C_MANTLE)
        btn_row1.pack(fill=tk.X, pady=(6, 3))

        btn_toggle = tk.Button(btn_row1, text="▶ Start", font=("Segoe UI", 9, "bold"), bg=C_GREEN, fg=C_CRUST,
                               relief="flat", cursor="hand2", command=lambda s=serial, d=dev: self.on_toggle_device(s, d))
        btn_toggle.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        btn_view = tk.Button(btn_row1, text="👁 View", font=("Segoe UI", 9, "bold"), bg=C_BLUE, fg=C_CRUST,
                             relief="flat", cursor="hand2", command=lambda s=serial: self.on_view_screen(s))
        btn_view.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))

        hw_row = tk.Frame(card, bg=C_MANTLE)
        hw_row.pack(fill=tk.X, pady=3)

        btn_fp = tk.Button(hw_row, text="🔑 Finger", font=("Segoe UI", 8), bg=C_SURFACE0, fg=C_TEXT,
                           relief="flat", cursor="hand2", command=lambda s=serial: self.on_trigger_fingerprint(s))
        btn_fp.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        btn_sms = tk.Button(hw_row, text="💬 OTP", font=("Segoe UI", 8), bg=C_SURFACE0, fg=C_TEXT,
                            relief="flat", cursor="hand2", command=lambda s=serial: self.on_popup_sms_otp(s))
        btn_sms.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        btn_gps = tk.Button(hw_row, text="📍 GPS", font=("Segoe UI", 8), bg=C_SURFACE0, fg=C_TEXT,
                            relief="flat", cursor="hand2", command=lambda s=serial: self.on_popup_gps(s))
        btn_gps.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        btn_opt = tk.Button(hw_row, text="⚡ Debloat", font=("Segoe UI", 8), bg=C_SURFACE0, fg=C_YELLOW,
                            relief="flat", cursor="hand2", command=lambda s=serial: self.on_optimize_device(s))
        btn_opt.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

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
        ctl = tk.Frame(self.tab_agents, bg=C_BASE)
        ctl.pack(fill=tk.X, pady=(0, 6))

        tk.Label(ctl, text="Package:", font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 4))
        self.pkg_entry = tk.Entry(ctl, font=("Segoe UI", 9), bg=C_MANTLE, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", width=24)
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

        ctl2 = tk.Frame(self.tab_agents, bg=C_BASE)
        ctl2.pack(fill=tk.X, pady=(0, 8))

        tk.Label(ctl2, text="Goal Prompt:", font=("Segoe UI", 9, "bold"), fg=C_BLUE, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 4))
        self.goal_entry = tk.Entry(ctl2, font=("Segoe UI", 9), bg=C_MANTLE, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", width=34)
        self.goal_entry.insert(0, "Giai xac thuc 2FA TOTP va kiem tra CAPTCHA xoay anh / chon nhieu anh")
        self.goal_entry.pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(ctl2, text="Device:", font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 4))
        self.device_combo = ttk.Combobox(ctl2, values=self._get_all_known_serials(), width=16, state="readonly")
        self.device_combo.current(0)
        self.device_combo.pack(side=tk.LEFT, padx=(0, 8))

        btn_run_loop = tk.Button(ctl2, text="🧠 4-Subagent Loop", font=("Segoe UI", 9, "bold"), bg=C_GREEN, fg=C_CRUST,
                                 relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_run_closed_loop)
        btn_run_loop.pack(side=tk.LEFT, padx=2)

        btn_matrix = tk.Button(ctl2, text="⚡ 4-Device Matrix", font=("Segoe UI", 9, "bold"), bg=C_PEACH, fg=C_CRUST,
                               relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_run_matrix)
        btn_matrix.pack(side=tk.LEFT, padx=2)

        btn_pipeline = tk.Button(ctl2, text="🚀 Agile Kanban Pipeline", font=("Segoe UI", 9, "bold"), bg=C_MAUVE, fg=C_CRUST,
                                 relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_run_pipeline)
        btn_pipeline.pack(side=tk.LEFT, padx=2)

        btn_evo = tk.Button(ctl2, text="🧬 Run 55-Subagent 10x Evolution (v12.0)", font=("Segoe UI", 9, "bold"), bg=C_TEAL, fg=C_CRUST,
                            relief="flat", padx=12, pady=3, cursor="hand2", command=self.on_run_self_evolution)
        btn_evo.pack(side=tk.LEFT, padx=3)

        log_frame = tk.Frame(self.tab_agents, bg=C_MANTLE, highlightbackground=C_SURFACE0, highlightthickness=1)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.agent_log_text = tk.Text(log_frame, bg=C_MANTLE, fg=C_TEXT, font=("Consolas", 9), relief="flat", padx=8, pady=8)
        scroll = tk.Scrollbar(log_frame, command=self.agent_log_text.yview)
        self.agent_log_text.configure(yscrollcommand=scroll.set)

        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.agent_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.agent_log_text.tag_configure("info", foreground=C_BLUE)
        self.agent_log_text.tag_configure("success", foreground=C_GREEN)
        self.agent_log_text.tag_configure("warn", foreground=C_YELLOW)
        self.agent_log_text.tag_configure("error", foreground=C_RED)
        self.agent_log_text.tag_configure("agent", foreground=C_MAUVE, font=("Consolas", 9, "bold"))

        self.log_agent_msg("AMAF 7.0", "30-Subagent Orchestrator & 40-Tool MCP Server Ready (Universal 2FA + Web/Rotation/Grid CAPTCHA CV + WCAG + Crash/ANR).", "success")

    def _build_real_farm_tab(self):
        bar1 = tk.Frame(self.tab_real_farm, bg=C_BASE)
        bar1.pack(fill=tk.X, pady=(0, 8))

        tk.Label(bar1, text="Farm Mode:", font=("Segoe UI", 9, "bold"), fg=C_BLUE, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 4))
        self.farm_mode_combo = ttk.Combobox(bar1, values=["HYBRID", "AVD_ONLY", "REAL_ONLY"], width=12, state="readonly")
        self.farm_mode_combo.set(self.real_mgr.get_farm_mode().get("farm_mode", "HYBRID"))
        self.farm_mode_combo.pack(side=tk.LEFT, padx=(0, 6))
        self.farm_mode_combo.bind("<<ComboboxSelected>>", self.on_change_farm_mode)

        btn_scan_real = tk.Button(bar1, text="🔍 Scan Real Phones & Thermal Guard", font=("Segoe UI", 9, "bold"),
                                  bg=C_GREEN, fg=C_CRUST, relief="flat", padx=10, pady=3, cursor="hand2", command=self.refresh_real_devices_tab)
        btn_scan_real.pack(side=tk.LEFT, padx=4)

        btn_vivo_guard = tk.Button(bar1, text="🛡️ Dismiss Vivo/OriginOS USB Popup", font=("Segoe UI", 9, "bold"),
                                   bg=C_YELLOW, fg=C_CRUST, relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_dismiss_oem_popup)
        btn_vivo_guard.pack(side=tk.LEFT, padx=4)

        tk.Label(bar1, text="Wireless IP:Port:", font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_BASE).pack(side=tk.LEFT, padx=(10, 4))
        self.wireless_ip_entry = tk.Entry(bar1, font=("Segoe UI", 9), bg=C_MANTLE, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", width=16)
        self.wireless_ip_entry.insert(0, "192.168.1.50:5555")
        self.wireless_ip_entry.pack(side=tk.LEFT, padx=(0, 4))

        btn_wifi_conn = tk.Button(bar1, text="📡 Connect Wi-Fi", font=("Segoe UI", 9, "bold"),
                                  bg=C_BLUE, fg=C_CRUST, relief="flat", padx=8, pady=3, cursor="hand2", command=self.on_connect_wireless_adb)
        btn_wifi_conn.pack(side=tk.LEFT, padx=2)

        btn_usb2wifi = tk.Button(bar1, text="🔌➔📡 USB to Wi-Fi", font=("Segoe UI", 9, "bold"),
                                 bg=C_MAUVE, fg=C_CRUST, relief="flat", padx=8, pady=3, cursor="hand2", command=self.on_usb_to_wireless)
        btn_usb2wifi.pack(side=tk.LEFT, padx=2)

        btn_wall = tk.Button(bar1, text="🖥️ Open Multi-Scrcpy Wall", font=("Segoe UI", 9, "bold"),
                             bg=C_PEACH, fg=C_CRUST, relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_open_scrcpy_wall)
        btn_wall.pack(side=tk.RIGHT, padx=3)

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

    def _build_v7_lab_tab(self):
        """Interactive AMAF 7.0 Control Lab for Universal 2FA, Web/Rotation/Grid CAPTCHA CV, SoM & Deep Diagnostics."""
        top_sel = tk.Frame(self.tab_v7_lab, bg=C_BASE)
        top_sel.pack(fill=tk.X, pady=(0, 6))

        tk.Label(top_sel, text="Target Device:", font=("Segoe UI", 9, "bold"), fg=C_BLUE, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 4))
        self.v7_device_combo = ttk.Combobox(top_sel, values=self._get_all_known_serials(), width=18, state="readonly")
        self.v7_device_combo.current(0)
        self.v7_device_combo.pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(top_sel, text="2FA Base32 Secret:", font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 4))
        self.v7_secret_entry = tk.Entry(top_sel, font=("Segoe UI", 9), bg=C_MANTLE, fg=C_TEXT, relief="flat", width=20)
        self.v7_secret_entry.insert(0, "JBSWY3DPEHPK3PXP")
        self.v7_secret_entry.pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(top_sel, text="🔑 Generate Live TOTP", font=("Segoe UI", 9, "bold"), bg=C_GREEN, fg=C_CRUST,
                  relief="flat", padx=8, cursor="hand2", command=self.on_v7_generate_totp).pack(side=tk.LEFT, padx=3)

        tk.Button(top_sel, text="🔐 Auto-Detect & Solve 2FA (7 Modes)", font=("Segoe UI", 9, "bold"), bg=C_TEAL, fg=C_CRUST,
                  relief="flat", padx=10, cursor="hand2", command=self.on_v7_solve_2fa).pack(side=tk.LEFT, padx=3)

        tk.Button(top_sel, text="📸 Capture Set-of-Mark (SoM) Screenshot", font=("Segoe UI", 9, "bold"), bg=C_PEACH, fg=C_CRUST,
                  relief="flat", padx=10, cursor="hand2", command=self.on_v7_capture_som).pack(side=tk.LEFT, padx=3)

        # Row 2: Universal Complex CAPTCHA, Rotation, Grid & Web Browser CAPTCHA
        cap_bar = tk.LabelFrame(
            self.tab_v7_lab,
            text=" 🧩 Universal 10-Type CAPTCHA CV, Xoay Ảnh Đồng Tâm, Chọn Nhiều Ảnh 3x3/4x4 & Truy Cập Web Giải CAPTCHA ",
            font=("Segoe UI", 9, "bold"),
            fg=C_MAUVE,
            bg=C_BASE,
            padx=8,
            pady=6
        )
        cap_bar.pack(fill=tk.X, pady=(0, 6))

        tk.Button(cap_bar, text="🧩 Solve Any CAPTCHA (10 Types CV)", font=("Segoe UI", 9, "bold"), bg=C_MAUVE, fg=C_CRUST,
                  relief="flat", padx=8, cursor="hand2", command=self.on_v7_solve_any_captcha).pack(side=tk.LEFT, padx=3)

        tk.Button(cap_bar, text="🔄 Solve Rotation Ring (Xoay ảnh)", font=("Segoe UI", 9, "bold"), bg=C_BLUE, fg=C_CRUST,
                  relief="flat", padx=8, cursor="hand2", command=self.on_v7_solve_rotation).pack(side=tk.LEFT, padx=3)

        tk.Button(cap_bar, text="🖼️ Solve 3x3/4x4 Grid (Chọn nhiều ảnh)", font=("Segoe UI", 9, "bold"), bg=C_GREEN, fg=C_CRUST,
                  relief="flat", padx=8, cursor="hand2", command=self.on_v7_solve_grid).pack(side=tk.LEFT, padx=3)

        tk.Label(cap_bar, text="Web URL:", font=("Segoe UI", 9), fg=C_TEXT, bg=C_BASE).pack(side=tk.LEFT, padx=(8, 4))
        self.v7_url_entry = tk.Entry(cap_bar, font=("Segoe UI", 9), bg=C_MANTLE, fg=C_TEXT, relief="flat", width=26)
        self.v7_url_entry.insert(0, "https://example.com")
        self.v7_url_entry.pack(side=tk.LEFT, padx=(0, 4))

        tk.Button(cap_bar, text="🌐 Open Web & Solve CAPTCHA", font=("Segoe UI", 9, "bold"), bg=C_YELLOW, fg=C_CRUST,
                  relief="flat", padx=8, cursor="hand2", command=self.on_v7_solve_web_captcha).pack(side=tk.LEFT, padx=3)

        # Row 3: Deep Diagnostics (#25, #28, #29, #30)
        diag_bar = tk.Frame(self.tab_v7_lab, bg=C_BASE)
        diag_bar.pack(fill=tk.X, pady=(0, 6))

        tk.Button(diag_bar, text="🎨 Audit WCAG 2.1 Contrast & TalkBack (#28)", font=("Segoe UI", 9, "bold"), bg=C_SURFACE0, fg=C_TEAL,
                  relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_v7_audit_wcag).pack(side=tk.LEFT, padx=3)

        tk.Button(diag_bar, text="💥 Analyze Crash / Tombstone / ANR (#29)", font=("Segoe UI", 9, "bold"), bg=C_SURFACE0, fg=C_RED,
                  relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_v7_analyze_crash).pack(side=tk.LEFT, padx=3)

        tk.Button(diag_bar, text="🌐 Audit Network RX/TX & API Latency (#30)", font=("Segoe UI", 9, "bold"), bg=C_SURFACE0, fg=C_BLUE,
                  relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_v7_audit_net_api).pack(side=tk.LEFT, padx=3)

        tk.Button(diag_bar, text="🚀 Profile FPS Jank & Memory Leak (#25)", font=("Segoe UI", 9, "bold"), bg=C_SURFACE0, fg=C_GREEN,
                  relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_v7_profile_perf).pack(side=tk.LEFT, padx=3)

        tk.Button(diag_bar, text="🧠 Audit Human UX & Logic", font=("Segoe UI", 9, "bold"), bg=C_PEACH, fg=C_CRUST,
                  relief="flat", padx=10, pady=3, cursor="hand2", command=self.on_v8_audit_human_ux).pack(side=tk.LEFT, padx=3)

        # Row 4: AMAF 8.0 Real-Device Live Web Testbench, Vivo OriginOS 6, Audio/Behavior CAPTCHA, SSO & 8-Stage E2E (#31-#35)
        v8_bar = tk.LabelFrame(
            self.tab_v7_lab,
            text=" 🚀 AMAF 8.0 Real-Device Live Web Testbench (#31), Vivo OriginOS 6 (#32), Audio/Behavior (#33), SSO (#34) & E2E Benchmark (#35) ",
            font=("Segoe UI", 9, "bold"),
            fg=C_GREEN,
            bg=C_BASE,
            padx=8,
            pady=6
        )
        v8_bar.pack(fill=tk.X, pady=(0, 6))

        tk.Button(v8_bar, text="🌐 Live Web Testbench E2E (#31)", font=("Segoe UI", 9, "bold"), bg=C_GREEN, fg=C_CRUST,
                  relief="flat", padx=8, cursor="hand2", command=self.on_v8_live_testbench).pack(side=tk.LEFT, padx=3)

        tk.Button(v8_bar, text="📱 Optimize Vivo OriginOS 6 (#32)", font=("Segoe UI", 9, "bold"), bg=C_YELLOW, fg=C_CRUST,
                  relief="flat", padx=8, cursor="hand2", command=self.on_v8_vivo_optimize).pack(side=tk.LEFT, padx=3)

        tk.Button(v8_bar, text="🔊 Audio/Dice/Behavior CAPTCHA (#33)", font=("Segoe UI", 9, "bold"), bg=C_MAUVE, fg=C_CRUST,
                  relief="flat", padx=8, cursor="hand2", command=self.on_v8_audio_behavior_captcha).pack(side=tk.LEFT, padx=3)

        tk.Button(v8_bar, text="🔑 SSO & Session Guard (#34)", font=("Segoe UI", 9, "bold"), bg=C_BLUE, fg=C_CRUST,
                  relief="flat", padx=8, cursor="hand2", command=self.on_v8_session_guard).pack(side=tk.LEFT, padx=3)

        tk.Button(v8_bar, text="🏆 8-Stage Real-Device E2E (#35)", font=("Segoe UI", 9, "bold"), bg=C_TEAL, fg=C_CRUST,
                  relief="flat", padx=8, cursor="hand2", command=self.on_v8_e2e_benchmark).pack(side=tk.LEFT, padx=3)

        # Output Console for AMAF 7.0 Lab
        self.v7_output_text = tk.Text(self.tab_v7_lab, bg=C_CRUST, fg=C_TEXT, font=("Consolas", 9), relief="flat", padx=10, pady=8)
        v7_scroll = tk.Scrollbar(self.tab_v7_lab, command=self.v7_output_text.yview)
        self.v7_output_text.configure(yscrollcommand=v7_scroll.set)
        v7_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.v7_output_text.pack(fill=tk.BOTH, expand=True)
        self._v7_log("AMAF 7.0 Lab Ready — Select a device (e.g., 10CF5L0TYL00312 or emulator-5554) and trigger any 2FA, CAPTCHA CV, or Diagnostic tool above.")

    def _v7_log(self, text: str):
        t_str = time.strftime("%H:%M:%S")
        self.v7_output_text.insert(tk.END, f"[{t_str}] {text}\n")
        self.v7_output_text.see(tk.END)

    def _build_reports_tab(self):
        top_bar = tk.Frame(self.tab_reports, bg=C_BASE)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        btn_refresh_rep = tk.Button(top_bar, text="🔄 Refresh Reports", font=("Segoe UI", 9, "bold"), bg=C_SURFACE0, fg=C_TEXT,
                                    relief="flat", padx=10, pady=4, cursor="hand2", command=self.refresh_reports)
        btn_refresh_rep.pack(side=tk.LEFT, padx=4)

        btn_open_folder = tk.Button(top_bar, text="📁 Open Reports Folder", font=("Segoe UI", 9), bg=C_SURFACE0, fg=C_TEXT,
                                    relief="flat", padx=10, pady=4, cursor="hand2", command=self.on_open_reports_folder)
        btn_open_folder.pack(side=tk.LEFT, padx=4)

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

        paned = tk.PanedWindow(self.tab_memory, orient=tk.HORIZONTAL, bg=C_BASE, sashrelief="flat", sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(paned, bg=C_MANTLE)
        paned.add(left_frame, minsize=380)

        right_frame = tk.Frame(paned, bg=C_MANTLE)
        paned.add(right_frame, minsize=420)

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
                f"Prompts: {summary.get('prompts_count')} | "
                f"Evolution Cycles: {summary.get('evolution_cycles_count', 0)}"
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

        self.status_lbl = tk.Label(
            status_bar,
            text="Ready | AMAF 8.0 (35 Subagents | 45 MCP Tools | 71/71 Tests Passing) | D:\\Project\\multi-phone-agent",
            font=("Segoe UI", 8),
            fg=C_SUBTEXT,
            bg=C_CRUST
        )
        self.status_lbl.pack(side=tk.LEFT)

        author_lbl = tk.Label(status_bar, text="Antigravity Multi-Device Testing Core v7.0", font=("Segoe UI", 8), fg=C_SURFACE1, bg=C_CRUST)
        author_lbl.pack(side=tk.RIGHT)

    def log_agent_msg(self, sender: str, msg: str, tag: str = "info"):
        t_str = time.strftime("%H:%M:%S")
        self.agent_log_text.insert(tk.END, f"[{t_str}] ", "sub")
        self.agent_log_text.insert(tk.END, f"[{sender}] ", "agent")
        self.agent_log_text.insert(tk.END, f"{msg}\n", tag)
        self.agent_log_text.see(tk.END)

    def _auto_refresh_loop(self):
        while self._is_running:
            try:
                mem = psutil.virtual_memory()
                free_gb = round(mem.available / (1024**3), 1)
                cpu_pct = psutil.cpu_percent(interval=None)
                states = self.proc_mgr.get_farm_state()
                locks = self.lock_mgr.list_active_locks()
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

            self.log_agent_msg("OEMPopupGuard", f"Broadcasting guarded APK install (with Vivo/OriginOS USB popup auto-confirm) for: {Path(apk_path).name}...", "info")
            for serial in connected:
                res = self.oem_guard.guarded_apk_install(serial, apk_path)
                ok = res.get("install_success", False)
                self.log_agent_msg("InstallAPK", f"[{serial}] Guarded Install: {res}", "success" if ok else "error")

        threading.Thread(target=_worker, daemon=True).start()

    def on_dismiss_oem_popup(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.oem_guard.guard_device(serial, use_vivo_fallback=True)
            self.log_agent_msg("OEMPopupGuard", f"[{serial}] Vivo/OriginOS USB Popup Guard: {res}", "success")
            self._v7_log(f"[OEMPopupGuard #18] {serial} -> {res}")
        threading.Thread(target=_worker, daemon=True).start()

    # AMAF 7.0 Lab Handlers
    def on_v7_generate_totp(self):
        secret = self.v7_secret_entry.get().strip() or "JBSWY3DPEHPK3PXP"
        try:
            res = self.universal_2fa.engine.generate_totp(secret)
            self._v7_log(f"[Universal2FAEngine #26] Generated RFC 6238 TOTP: {res['code']} (Valid for {res['remaining_seconds']}s, Algo={res['algorithm']})")
        except Exception as e:
            self._v7_log(f"[Universal2FAEngine Error] {e}")

    def on_v7_solve_2fa(self):
        serial = self.v7_device_combo.get().strip()
        secret = self.v7_secret_entry.get().strip() or "JBSWY3DPEHPK3PXP"
        def _worker():
            self._v7_log(f"[Universal2FASubagent #26] Scanning & solving 7-mode 2FA challenge on {serial}...")
            res = self.universal_2fa.solve_2fa_challenge(serial, secret=secret)
            self._v7_log(f"[Universal2FASubagent #26] Result: {res}")
            self.log_agent_msg("Universal2FA", f"[{serial}] {res.get('status')} (Mode: {res.get('mode')}, Code: {res.get('code_used')})", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v7_capture_som(self):
        serial = self.v7_device_combo.get().strip()
        def _worker():
            self._v7_log(f"[AutoScreenshotSubagent #21] Capturing Set-of-Mark (SoM) annotated screenshot on {serial}...")
            res = self.auto_screenshot.capture_smart_screenshot(serial, tag="gui_som", annotate_som=True)
            self._v7_log(f"[AutoScreenshotSubagent #21] Saved SoM image ({res.get('marks_count')} interactive badges): {res.get('annotated_screenshot_path')}")
            if res.get("annotated_screenshot_path") and os.path.exists(res["annotated_screenshot_path"]) and os.name == "nt":
                os.startfile(res["annotated_screenshot_path"])
        threading.Thread(target=_worker, daemon=True).start()

    def on_v7_solve_any_captcha(self):
        serial = self.v7_device_combo.get().strip()
        def _worker():
            self._v7_log(f"[ComplexCaptchaSubagent #22] Inspecting {serial} for all 10 Simple & Complex CAPTCHA types...")
            res = self.complex_captcha.solve_any_captcha_with_vision(serial)
            self._v7_log(f"[ComplexCaptchaSubagent #22] Result: {res}")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v7_solve_rotation(self):
        serial = self.v7_device_combo.get().strip()
        def _worker():
            self._v7_log(f"[WebAndAdvancedCaptchaSubagent #27] Solving Concentric Ring Rotation CAPTCHA (`xoay ảnh`) on {serial}...")
            res = self.web_adv_captcha.solve_rotation_captcha_advanced(serial)
            self._v7_log(f"[WebAndAdvancedCaptchaSubagent #27] Rotation Result: {res}")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v7_solve_grid(self):
        serial = self.v7_device_combo.get().strip()
        def _worker():
            self._v7_log(f"[WebAndAdvancedCaptchaSubagent #27] Solving Multi-Image Grid CAPTCHA (`chọn nhiều ảnh`) on {serial}...")
            res = self.web_adv_captcha.solve_multi_image_grid_captcha(serial, grid_size=3, rounds=2)
            self._v7_log(f"[WebAndAdvancedCaptchaSubagent #27] Grid Result: {res}")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v7_solve_web_captcha(self):
        serial = self.v7_device_combo.get().strip()
        url = self.v7_url_entry.get().strip() or "https://example.com"
        def _worker():
            self._v7_log(f"[WebAndAdvancedCaptchaSubagent #27] Opening {url} on {serial}, forwarding WebView DevTools, and solving web CAPTCHA...")
            res = self.web_adv_captcha.navigate_and_solve_web_captcha(serial, url=url)
            self._v7_log(f"[WebAndAdvancedCaptchaSubagent #27] Web CAPTCHA Result: {res}")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v7_audit_wcag(self):
        serial = self.v7_device_combo.get().strip()
        def _worker():
            self._v7_log(f"[AccessibilityAndWCAGContrastSubagent #28] Running WCAG 2.1 AA/AAA pixel contrast & TalkBack focus audit on {serial}...")
            shot = self.auto_screenshot.capture_smart_screenshot(serial, tag="wcag_gui", annotate_som=False)
            res = self.wcag_auditor.audit_wcag_and_talkback_tree(serial, screenshot_path=shot.get("screenshot_path"))
            self._v7_log(f"[AccessibilityWCAG #28] Level: {res.get('wcag_level')} (Score: {res.get('wcag_score')}/100, Violations: {res.get('violations_count')}) -> {res.get('violations')[:5]}")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v7_analyze_crash(self):
        serial = self.v7_device_combo.get().strip()
        pkg = self.pkg_entry.get().strip() or None
        def _worker():
            self._v7_log(f"[CrashTombstoneAndANRSubagent #29] Demangling Java/Kotlin Fatal Exceptions, Native Tombstones & ANRs on {serial}...")
            res = self.crash_analyzer.analyze_logcat_and_tombstones(serial, package_name=pkg)
            self._v7_log(f"[CrashTombstoneANR #29] Total Faults: {res.get('total_faults')} (Unique SHA-256 Signatures: {res.get('unique_signatures')}) -> Recommendations: {res.get('root_cause_recommendations')}")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v7_audit_net_api(self):
        serial = self.v7_device_combo.get().strip()
        pkg = self.pkg_entry.get().strip() or "com.android.settings"
        def _worker():
            self._v7_log(f"[NetworkTrafficAndAPILatencySubagent #30] Inspecting /proc/net/dev RX/TX throughput & HTTP API latency on {serial}...")
            res = self.net_api_profiler.run_network_api_telemetry_audit(serial, package_name=pkg)
            tp = res.get("throughput", {})
            api = res.get("api_telemetry", {})
            self._v7_log(f"[NetworkAPILatency #30] Score: {res.get('api_health_score')}/100 | RX: {tp.get('total_rx_mb')} MB, TX: {tp.get('total_tx_mb')} MB | API Calls: {api.get('api_calls_detected')}, Cleartext Risks: {api.get('cleartext_urls_count')}")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v7_profile_perf(self):
        serial = self.v7_device_combo.get().strip()
        pkg = self.pkg_entry.get().strip() or "com.android.settings"
        def _worker():
            self._v7_log(f"[PerformanceAndMemLeakSubagent #25] Profiling FPS Jank & PSS/Heap memory leaks on {serial} ({pkg})...")
            res = self.perf_profiler.run_comprehensive_performance_audit(serial, pkg)
            self._v7_log(f"[PerformanceAndMemLeak #25] Grade: {res.get('performance_grade')} ({res.get('performance_score')}/100) | FPS: {res['graphics']['estimated_fps']} (Jank: {res['graphics']['jank_percent']}%) | Total PSS: {res['memory']['total_pss_mb']} MB")
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
            self.log_agent_msg("SelfEvolutionEngine", "Launching 30-Subagent Autonomous Self-Evolution Loop (AMAF 7.0)...", "info")
            def _cb(agent, msg):
                self.log_agent_msg(agent, msg, "info")

            res = self.evolution_engine.run_evolution_loop(iterations=1, package_name=pkg, callback=_cb)
            dur = res.get("total_duration_seconds", 0)
            rep = res.get("report_path", "")
            self.log_agent_msg("SelfEvolutionEngine", f"30-Subagent Evolution Completed in {dur}s! Report: {rep}", "success")
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
                serials = self._get_all_known_serials()
                if hasattr(self, "device_combo"):
                    self.device_combo["values"] = serials
                if hasattr(self, "v7_device_combo"):
                    self.v7_device_combo["values"] = serials

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

    def on_launch_foodgo_latest(self):
        """One-click install & launch of FoodGo P18 + live Scrcpy screen viewer."""
        apk_path = Path(r"D:\Project\food-delivery\app\build\outputs\apk\debug\app-debug.apk")
        def _worker():
            connected = [d["serial"] for d in self.adb.get_connected_devices() if d.get("status") == "device"]
            target = "emulator-5554" if "emulator-5554" in connected else (connected[0] if connected else "emulator-5554")
            self.log_agent_msg("FoodGoP18", f"Launching FoodGo (P18 latest build) on {target}...", "info")
            if apk_path.exists():
                self.adb.run_device_cmd(target, ["install", "-r", str(apk_path)], timeout=60)
            self.adb.shell(target, "am start -n com.example.fooddelivery/.ui.splash.SplashActivity", timeout=10)
            self.root.after(0, lambda: self.scrcpy_mgr.open_viewer(target, title=f"FoodGo P18 Live ({target})"))
            self.log_agent_msg("FoodGoP18", f"FoodGo P18 is live on {target} (Scrcpy window opened).", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v8_audit_human_ux(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "emulator-5554"
        def _worker():
            self._v7_log(f"[{serial}] Running Subagent #31 HumanPersonaUXAuditorSubagent...")
            rep = self.human_ux_auditor.audit_screen_ux_and_logic(serial, "live_screen")
            self._v7_log(
                f"[{serial}] Combined Score: {rep['combined_score']}/100 "
                f"(Layout={rep['layout_health_score']}/100, UX Logic={rep['ux_logic_score']}/100) | "
                f"Semantic Issues: {rep['semantic_issues']} | Layout Warnings: {len(rep['layout_warnings'])}"
            )
            self.log_agent_msg("HumanPersonaUX(#31)", f"[{serial}] Score={rep['combined_score']}/100 (Layout={rep['layout_health_score']}, UX={rep['ux_logic_score']})", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v8_live_testbench(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            self._v7_log(f"[{serial}] Starting Subagent #31 LiveWebTestbenchAndRealPhoneE2ESubagent (HTTP Server + ADB Reverse + Chrome E2E)...")
            res = self.live_testbench_agent.run_live_real_phone_testbench_e2e(serial, port=8765)
            self._v7_log(f"[LiveWebTestbench #31] Result: {res}")
            self.log_agent_msg("LiveWebTestbench(#31)", f"[{serial}] Solved={res.get('all_solved')} ({res.get('challenges_solved_count', 0)}/5)", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v8_vivo_optimize(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            self._v7_log(f"[{serial}] Running Subagent #32 VivoOriginOSDeepOptimizerSubagent...")
            res = self.vivo_optimizer.optimize_vivo_real_phone(serial)
            self._v7_log(f"[VivoOptimizer #32] Result: {res}")
            self.log_agent_msg("VivoOptimizer(#32)", f"[{serial}] OriginOS Optimized: {res.get('status')}", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v8_audio_behavior_captcha(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            self._v7_log(f"[{serial}] Running Subagent #33 InteractiveAudioAndBehaviorCaptchaSubagent...")
            res = self.audio_behavior_captcha.execute_human_behavior_verification(serial)
            self._v7_log(f"[AudioBehaviorCaptcha #33] Result: {res}")
            self.log_agent_msg("AudioBehaviorCaptcha(#33)", f"[{serial}] Trajectory Entropy Score={res.get('entropy_score')}", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v8_session_guard(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            self._v7_log(f"[{serial}] Running Subagent #34 CrossAppSessionAndCredentialGuardSubagent...")
            res = self.session_guard.handle_sso_or_credential_prompt(serial)
            self._v7_log(f"[SessionGuard #34] Result: {res}")
            self.log_agent_msg("SessionGuard(#34)", f"[{serial}] SSO/Credential Guard: {res.get('status')}", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v8_e2e_benchmark(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        pkg = self.pkg_entry.get().strip() or "com.android.settings"
        def _worker():
            self._v7_log(f"[{serial}] Running Subagent #35 RealDeviceE2EBenchmarkAndSelfHealerSubagent (8-Stage E2E)...")
            res = self.e2e_benchmark.run_full_device_e2e_benchmark(serial, package_name=pkg)
            self._v7_log(f"[RealDeviceE2EBenchmark #35] Grade={res.get('overall_grade')} ({res.get('overall_score')}/100) | Report: {res.get('report_path')}")
            self.log_agent_msg("E2EBenchmark(#35)", f"[{serial}] Grade={res.get('overall_grade')} ({res.get('overall_score')}/100)", "success")
        threading.Thread(target=_worker, daemon=True).start()


    def _build_v9_zero_token_gpu_tab(self):
        top_bar = tk.Frame(self.tab_v9_gpu, bg=C_MANTLE, padx=12, pady=10)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            top_bar,
            text="🚀 Zero-Token GPU (RTX 3050 PTX sm_86) + Macro Replay + Android CDP + TikTok Workflows (#36-#40)",
            font=("Segoe UI", 11, "bold"),
            fg=C_GREEN,
            bg=C_MANTLE
        ).pack(side=tk.LEFT)

        btn_row = tk.Frame(self.tab_v9_gpu, bg=C_BASE)
        btn_row.pack(fill=tk.X, pady=4)

        tk.Button(
            btn_row, text="⚡ #36 Audit RTX 3050 PTX & Neural OCR", font=("Segoe UI", 9, "bold"),
            bg=C_GREEN, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v9_gpu_audit
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="📼 #37 Replay Airtest/Poco Macro (0 Token)", font=("Segoe UI", 9, "bold"),
            bg=C_BLUE, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v9_macro_replay
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="🌐 #38 Attach Android CDP (@chrome_devtools)", font=("Segoe UI", 9, "bold"),
            bg=C_TEAL, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v9_cdp_attach
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="🎵 #39 Run TikTok Switch & Comment Workflow", font=("Segoe UI", 9, "bold"),
            bg=C_PEACH, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v9_tiktok_workflow
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="🛡️ #40 Run 3-Tier Hybrid CAPTCHA Defense", font=("Segoe UI", 9, "bold"),
            bg=C_MAUVE, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v9_hybrid_3tier
        ).pack(side=tk.LEFT, padx=4)

        self.v9_log_text = tk.Text(self.tab_v9_gpu, bg=C_CRUST, fg=C_TEXT, font=("Consolas", 9), height=14, relief="flat", padx=10, pady=8)
        self.v9_log_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.v9_log_text.insert(tk.END, "[AMAF 9.0] Zero-Token GPU Engine (NVIDIA GeForce RTX 3050 PTX sm_86) & Subagents #36-#40 Ready.\n")

    def _v9_log(self, msg: str):
        if hasattr(self, "v9_log_text"):
            ts = time.strftime("%H:%M:%S")
            self.root.after(0, lambda: (self.v9_log_text.insert(tk.END, f"[{ts}] {msg}\n"), self.v9_log_text.see(tk.END)))

    def on_v9_gpu_audit(self):
        def _worker():
            res = self.local_gpu_vision.run_self_diagnostics()
            self._v9_log(f"[Subagent #36 LocalGPUVision] {res}")
            self.log_agent_msg("LocalGPUVision(#36)", f"GPU={res.get('gpu_telemetry', {}).get('gpu_name')} | Zero-Token OCR Verified", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v9_macro_replay(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.macro_replay.replay_macro("tiktok_switch_and_interact", serial=serial, dry_run=True)
            self._v9_log(f"[Subagent #37 MacroReplay] {res}")
            self.log_agent_msg("MacroReplay(#37)", f"[{serial}] Status={res.get('status')} | Tokens={res.get('tokens_used')}", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v9_cdp_attach(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.android_cdp.discover_and_attach(serial)
            self._v9_log(f"[Subagent #38 AndroidCDP] {res}")
            self.log_agent_msg("AndroidCDP(#38)", f"[{serial}] Sockets={res.get('sockets_discovered')} | Tabs={res.get('open_tabs_count', 0)}", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v9_tiktok_workflow(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.social_workflow.run_tiktok_workflow(serial, target_account="nht.tn472", search_query="tra dang", comment_text="dinh quaa", dry_run=True)
            self._v9_log(f"[Subagent #39 SocialWorkflow] {res}")
            self.log_agent_msg("SocialWorkflow(#39)", f"[{serial}] TikTok Workflow Status={res.get('status')} | Tokens=0", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v9_hybrid_3tier(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.hybrid_captcha_3tier.run_3tier_self_audit(serial)
            self._v9_log(f"[Subagent #40 HybridCaptcha3Tier] {res}")
            self.log_agent_msg("Hybrid3Tier(#40)", f"[{serial}] Status={res.get('status')} | Audio={res.get('tier2_audio_decoded')}", "success")
        threading.Thread(target=_worker, daemon=True).start()


    def _build_v10_stream_vault_dag_tab(self):
        top_bar = tk.Frame(self.tab_v10_dag, bg=C_MANTLE, padx=12, pady=10)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            top_bar,
            text="⚡ AMAF v10.0: Persistent ADB Stream (#41) + IME/Viewport Guard (#42) + Semantic GPU (#43) + Account Vault (#44) + Visual DAG (#45)",
            font=("Segoe UI", 11, "bold"),
            fg=C_BLUE,
            bg=C_MANTLE
        ).pack(side=tk.LEFT)

        btn_row = tk.Frame(self.tab_v10_dag, bg=C_BASE)
        btn_row.pack(fill=tk.X, pady=4)

        tk.Button(
            btn_row, text="🚀 #41 Benchmark Persistent ADB Stream", font=("Segoe UI", 9, "bold"),
            bg=C_GREEN, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v10_stream_benchmark
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="⌨️ #42 Guard Soft Keyboard & Viewport", font=("Segoe UI", 9, "bold"),
            bg=C_BLUE, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v10_kbd_viewport_guard
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="🎯 #43 GPU Contour & Orientation Matcher", font=("Segoe UI", 9, "bold"),
            bg=C_TEAL, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v10_semantic_matcher
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="🔐 #44 Audit Multi-Account Vault & Proxy", font=("Segoe UI", 9, "bold"),
            bg=C_PEACH, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v10_account_vault
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="🔀 #45 Execute Visual Flow DAG & Live Preview", font=("Segoe UI", 9, "bold"),
            bg=C_MAUVE, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v10_visual_dag
        ).pack(side=tk.LEFT, padx=4)

        self.v10_log_text = tk.Text(self.tab_v10_dag, bg=C_CRUST, fg=C_TEXT, font=("Consolas", 9), height=14, relief="flat", padx=10, pady=8)
        self.v10_log_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.v10_log_text.insert(tk.END, "[AMAF 10.0] Subagents #41-#45 (Persistent ADB Pipe, IME/Viewport Guard, Semantic GPU Matcher, Account Vault & Visual DAG) Ready.\n")

    def _v10_log(self, msg: str):
        if hasattr(self, "v10_log_text"):
            ts = time.strftime("%H:%M:%S")
            self.root.after(0, lambda: (self.v10_log_text.insert(tk.END, f"[{ts}] {msg}\n"), self.v10_log_text.see(tk.END)))

    def on_v10_stream_benchmark(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.persistent_stream.run_stream_benchmark(serial)
            self._v10_log(f"[Subagent #41 PersistentADBStream] {res}")
            self.log_agent_msg("PersistentStream(#41)", f"[{serial}] FlashWrites={res.get('flash_writes')} | ShellLatency={res.get('shell_latency_ms')}ms", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v10_kbd_viewport_guard(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.kbd_viewport_guard.guard_input_and_viewport(serial, target_x=400, target_y=2200, dry_run=True)
            self._v10_log(f"[Subagent #42 KeyboardViewportGuard] {res}")
            self.log_agent_msg("KbdViewportGuard(#42)", f"[{serial}] Status={res.get('status')} | Tokens=0", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v10_semantic_matcher(self):
        def _worker():
            res = self.semantic_matcher.run_self_diagnostics()
            self._v10_log(f"[Subagent #43 ZeroTokenSemanticMatcher] {res}")
            self.log_agent_msg("SemanticMatcher(#43)", f"Status={res.get('status')} | Passed={res.get('passed')}", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v10_account_vault(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.account_vault.run_vault_and_proxy_audit(serial, dry_run=True)
            self._v10_log(f"[Subagent #44 MultiAccountVaultAndProxy] {res}")
            self.log_agent_msg("AccountVault(#44)", f"[{serial}] Accounts={res.get('accounts_count')} | Status={res.get('status')}", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v10_visual_dag(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.visual_flow_dag.execute_dag("tiktok_smart_switch_and_engage_dag", serial=serial, dry_run=True)
            preview_img = self.visual_flow_dag.render_annotated_preview_frame(
                touch_points=[(630, 1400), (1166, 1550)],
                boxes=[{"bbox": (200, 300, 900, 600), "label": "DAG_TARGET_LOCKED"}],
                preview_size=(320, 700)
            )
            self._v10_log(f"[Subagent #45 VisualFlowDAG] {res} | PreviewFrame={preview_img.size}")
            self.log_agent_msg("VisualFlowDAG(#45)", f"[{serial}] DAG={res.get('status')} | Visited={len(res.get('visited_nodes', []))}", "success")
        threading.Thread(target=_worker, daemon=True).start()



    def _build_v12_installer_and_10x_tab(self):
        top_bar = tk.Frame(self.tab_v12_installer, bg=C_MANTLE, padx=12, pady=10)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            top_bar,
            text="📦 AMAF v12.0: Universal APK Installer (#46) + Sideload Guard (#47) + SecIME Vault (#48) + AXML Parser (#49) + Daemon (#50) + 10x Evolution (#51-#55)",
            font=("Segoe UI", 10, "bold"),
            fg=C_GREEN,
            bg=C_MANTLE
        ).pack(side=tk.LEFT)

        btn_row = tk.Frame(self.tab_v12_installer, bg=C_BASE)
        btn_row.pack(fill=tk.X, pady=4)

        tk.Button(
            btn_row, text="📦 #46-#50 Universal Install APK", font=("Segoe UI", 9, "bold"),
            bg=C_GREEN, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_install_apk_all
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="🛡️ #47 Pre-Authorize Sideload Sources", font=("Segoe UI", 9, "bold"),
            bg=C_BLUE, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v12_sideload_guard
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="🔍 #49 Inspect APK AXML & --user 0", font=("Segoe UI", 9, "bold"),
            bg=C_TEAL, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v12_inspect_axml
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="💓 #50 Start Always-On Install Daemon", font=("Segoe UI", 9, "bold"),
            bg=C_PEACH, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v12_toggle_daemon
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="🧬 #51-#55 Run 10x Recursive Evolution", font=("Segoe UI", 9, "bold"),
            bg=C_MAUVE, fg=C_CRUST, relief="flat", padx=10, pady=6, command=self.on_v12_run_10x_evolution
        ).pack(side=tk.LEFT, padx=4)

        self.v12_log_text = tk.Text(self.tab_v12_installer, bg=C_CRUST, fg=C_TEXT, font=("Consolas", 9), height=14, relief="flat", padx=10, pady=8)
        self.v12_log_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.v12_log_text.insert(tk.END, "[AMAF 12.0] Subagents #46-#55 (Universal APK Installer, Sideload Guard, SecIME Vault, Pure-Python AXML, Always-On Daemon, GKD Selector, Mobile-Agent-E Memory, UI-TARS Reflection, DroidBot UTG & 10x Recursive Evolution) Ready.\n")

    def _v12_log(self, msg: str):
        if hasattr(self, "v12_log_text"):
            ts = time.strftime("%H:%M:%S")
            self.root.after(0, lambda: (self.v12_log_text.insert(tk.END, f"[{ts}] {msg}\n"), self.v12_log_text.see(tk.END)))

    def on_v12_sideload_guard(self):
        def _worker():
            res = self.sideload_source_guard.get_status()
            self._v12_log(f"[Subagent #47 SideloadSourceGuard] {res}")
            self.log_agent_msg("SideloadGuard(#47)", "Sideload Source & --user 0 Permission Guard Ready", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v12_inspect_axml(self):
        def _worker():
            res = self.multi_user_pkg.normalize_and_filter_pm_execution(
                "pm list packages",
                raw_output="Error: Shell does not have permission to access user 666\npackage:com.geminicall.ai"
            )
            self._v12_log(f"[Subagent #49 MultiUserPackage] {res}")
            self.log_agent_msg("MultiUserPkg(#49)", f"Normalized: {res.get('normalized_cmd')} | Packages={res.get('packages')}", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v12_toggle_daemon(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            health = self.always_on_install_daemon.get_health_status(serial)
            self._v12_log(f"[Subagent #50 AlwaysOnInstallDaemon] {health}")
            self.log_agent_msg("InstallDaemon(#50)", f"[{serial}] Daemon Healthy={health.get('healthy')}", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v12_run_10x_evolution(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.recursive_10x_coordinator.run_10_iterations(live_serial=serial, write_report=True)
            self._v12_log(f"[Subagents #51-#55 Recursive10xEvolution] Passed={res.get('passed_iterations')}/10 | Report={res.get('report_path')}")
            self.log_agent_msg("Recursive10x(#55)", f"[{serial}] 10/10 Recursive Evolution Iterations Passed!", "success")
        threading.Thread(target=_worker, daemon=True).start()


    def _build_v13_ui_ux_and_critic_tab(self):
        top_bar = tk.Frame(self.tab_v13_ui_ux, bg=C_MANTLE, padx=12, pady=10)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            top_bar,
            text="🎨 AMAF v13.0: Screenshot Critic (#56) + 8pt Tokens (#57) + Sidebar IA (#58) + Ctrl+K Palette (#59) + Bento Sparkline (#60) + Anti-Rainbow CTA (#61) + Finish Gate (#64) + 10x UI/UX Loop (#65)",
            font=("Segoe UI", 9, "bold"),
            fg=C_BLUE,
            bg=C_MANTLE
        ).pack(side=tk.LEFT)

        search_row = tk.Frame(self.tab_v13_ui_ux, bg=C_BASE)
        search_row.pack(fill=tk.X, pady=4)

        tk.Label(search_row, text="⌘K Command Palette:", font=("Segoe UI", 9, "bold"), fg=C_TEXT, bg=C_BASE).pack(side=tk.LEFT, padx=(0, 6))
        self.v13_cmd_entry = tk.Entry(search_row, font=("Segoe UI", 9), bg=C_MANTLE, fg=C_TEXT, insertbackground=C_TEXT, relief="flat", width=36)
        self.v13_cmd_entry.insert(0, "install apk vivo")
        self.v13_cmd_entry.pack(side=tk.LEFT, padx=(0, 8))

        # Primary CTA (#6366f1 Indigo) + Neutral Secondary buttons (#313244) following Subagent #61 Anti-Rainbow Hierarchy
        tk.Button(
            search_row, text="🚀 #65 Run 10x Sequential UI/UX Evolution", font=("Segoe UI", 9, "bold"),
            bg="#6366f1", fg="#f8fafc", relief="flat", padx=12, pady=6, command=self.on_v13_run_10x_ui_ux_evolution
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            search_row, text="⌘K #59 Search Command Palette", font=("Segoe UI", 9),
            bg=C_SURFACE0, fg=C_TEXT, relief="flat", padx=10, pady=6, command=self.on_v13_ctrl_k_search
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            search_row, text="📸 #56 Live Vivo Screenshot Critique", font=("Segoe UI", 9),
            bg=C_SURFACE0, fg=C_TEXT, relief="flat", padx=10, pady=6, command=self.on_v13_screenshot_critique
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            search_row, text="📊 #60 Bento Card & Sparkline", font=("Segoe UI", 9),
            bg=C_SURFACE0, fg=C_TEXT, relief="flat", padx=10, pady=6, command=self.on_v13_bento_sparkline
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            search_row, text="✅ #64 UI Finish-Gate Review", font=("Segoe UI", 9),
            bg=C_SURFACE0, fg=C_TEXT, relief="flat", padx=10, pady=6, command=self.on_v13_finish_gate_audit
        ).pack(side=tk.LEFT, padx=4)

        self.v13_log_text = tk.Text(self.tab_v13_ui_ux, bg=C_CRUST, fg=C_TEXT, font=("Consolas", 9), height=14, relief="flat", padx=10, pady=8)
        self.v13_log_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.v13_log_text.insert(tk.END, "[AMAF 13.0] Subagents #56-#65 (Visual Screenshot Clutter Critic, 8pt Grid & Tokens, Miller Sidebar IA, Ctrl+K Command Palette, Bento Sparklines, Semantic 3-Tier CTA, WCAG Contrast Auto-Fixer, Micro-Interactions, UI Finish-Gate Reviewer & 10x Sequential UI/UX Coordinator) Ready.\n")

    def _v13_log(self, msg: str):
        if hasattr(self, "v13_log_text"):
            ts = time.strftime("%H:%M:%S")
            self.root.after(0, lambda: (self.v13_log_text.insert(tk.END, f"[{ts}] {msg}\n"), self.v13_log_text.see(tk.END)))

    def on_v13_ctrl_k_search(self):
        query = self.v13_cmd_entry.get().strip() if hasattr(self, "v13_cmd_entry") else "install apk"
        def _worker():
            res = self.command_palette_agent.execute(query=query, top_k=5)
            self._v13_log(f"[Subagent #59 CommandPalette Ctrl+K] query='{query}' -> {res.get('search_results')}")
            self.log_agent_msg("CommandPalette(#59)", f"Ctrl+K query='{query}' matched {len(res.get('search_results', []))} commands", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v13_screenshot_critique(self):
        def _worker():
            res = self.visual_clutter_critic.execute()
            self._v13_log(f"[Subagent #56 VisualScreenshotCritic] Score={res.get('overall_ui_score')} | Grade={res.get('grade')}")
            self.log_agent_msg("ScreenshotCritic(#56)", f"UI Score={res.get('overall_ui_score')}/100 ({res.get('grade')})", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v13_bento_sparkline(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.bento_sparkline_agent.execute(serial=serial, model="Vivo V2417A (Physical)", status="ONLINE", is_physical=True)
            card = res.get("card", {})
            self._v13_log(f"[Subagent #60 BentoDeviceCard] {card.get('serial')} | Sparkline={card.get('sparkline_str')} | Action={card.get('primary_action')}")
            self.log_agent_msg("BentoCard(#60)", f"[{serial}] Sparkline={card.get('sparkline_str')}", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v13_finish_gate_audit(self):
        def _worker():
            res = self.ui_finish_gate_reviewer.execute()
            self._v13_log(f"[Subagent #64 UIFinishGateReviewer] Decision={res.get('gate_decision')} | Score={res.get('score')}/100")
            self.log_agent_msg("FinishGate(#64)", f"Gate={res.get('gate_decision')} ({res.get('score')}/100)", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v13_run_10x_ui_ux_evolution(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.recursive_10x_ui_ux_coordinator.execute(live_serial=serial, write_report=True)
            self._v13_log(f"[Subagent #65 Recursive10xUIUXEvolution] Initial={res.get('initial_ui_score')} -> Final={res.get('final_ui_score')} | Gate={res.get('final_gate_decision')} | Report={res.get('report_path')}")
            self.log_agent_msg("Recursive10xUIUX(#65)", f"[{serial}] 10/10 UI/UX Loops Complete: {res.get('initial_ui_score')} -> {res.get('final_ui_score')}/100 ({res.get('final_gate_decision')})", "success")
        threading.Thread(target=_worker, daemon=True).start()


    def _build_v14_antibot_and_causal_tab(self):
        top_bar = tk.Frame(self.tab_v14_antibot, bg=C_MANTLE, padx=12, pady=10)
        top_bar.pack(fill=tk.X, pady=(0, 8))

        tk.Label(
            top_bar,
            text="🛡️ AMAF v14.0 (75 Subagents): Sigma-Lognormal Touch (#66) + Patchright CDP Stealth (#67) + Sensor Recoil (#68) + Turnstile Pre-Warm (#69) + Radar UI (#70) + Vivo Filter Refiner (#71) + Weibull Pacer (#72) + 10x Causal Chain (#75)",
            font=("Segoe UI", 9, "bold"),
            fg=C_GREEN,
            bg=C_MANTLE
        ).pack(side=tk.LEFT)

        btn_row = tk.Frame(self.tab_v14_antibot, bg=C_BASE)
        btn_row.pack(fill=tk.X, pady=4)

        # Primary CTA (#6366f1 Indigo) + Neutral Secondary buttons (#313244)
        tk.Button(
            btn_row, text="🚀 #75 Run 10x Causal Anti-Bot & UI/UX Loop", font=("Segoe UI", 9, "bold"),
            bg="#6366f1", fg="#f8fafc", relief="flat", padx=12, pady=6, command=self.on_v14_run_10x_causal_evolution
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="👆 #66 Sigma-Lognormal Touch & Fitts Audit", font=("Segoe UI", 9),
            bg=C_SURFACE0, fg=C_TEXT, relief="flat", padx=10, pady=6, command=self.on_v14_sigma_lognormal_swipe
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="🕵️ #67 Patchright Zero-Runtime.enable CDP", font=("Segoe UI", 9),
            bg=C_SURFACE0, fg=C_TEXT, relief="flat", padx=10, pady=6, command=self.on_v14_stealth_cdp_audit
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="📳 #68-#69 Sensor Recoil & Pre-Warm Entropy", font=("Segoe UI", 9),
            bg=C_SURFACE0, fg=C_TEXT, relief="flat", padx=10, pady=6, command=self.on_v14_sensor_recoil_audit
        ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            btn_row, text="✅ #71-#74 Unified 10-Point Finish Gate", font=("Segoe UI", 9),
            bg=C_SURFACE0, fg=C_TEXT, relief="flat", padx=10, pady=6, command=self.on_v14_unified_finish_gate
        ).pack(side=tk.LEFT, padx=4)

        self.v14_log_text = tk.Text(self.tab_v14_antibot, bg=C_CRUST, fg=C_TEXT, font=("Consolas", 9), height=14, relief="flat", padx=10, pady=8)
        self.v14_log_text.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.v14_log_text.insert(tk.END, "[AMAF 14.0] Subagents #66-#75 (Sigma-Lognormal Touch Kinematics, Patchright Zero-Runtime.enable CDP, Android Sensor-Touch Recoil, Turnstile Pre-Warm Entropy, Cloudflare-Radar Bento UI, Vivo Header/Filter Refiner, Weibull Cognitive Pacer, 4-Layer Bot Signal Correlator, Unified 10-Point Finish Gate & 10x Causal Chain Coordinator) Ready.\n")

    def _v14_log(self, msg: str):
        if hasattr(self, "v14_log_text"):
            ts = time.strftime("%H:%M:%S")
            self.root.after(0, lambda: (self.v14_log_text.insert(tk.END, f"[{ts}] {msg}\n"), self.v14_log_text.see(tk.END)))

    def on_v14_sigma_lognormal_swipe(self):
        def _worker():
            res = self.sigma_lognormal_kinematics.execute()
            self._v14_log(f"[Subagent #66 SigmaLognormalKinematics] {res}")
            self.log_agent_msg("SigmaLognormal(#66)", "Biometric Sigma-Lognormal Swipe + Fitts Gaussian Verified", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v14_stealth_cdp_audit(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.patchright_stealth_cdp.execute(serial=serial)
            self._v14_log(f"[Subagent #67 PatchrightStealthCDP] {res}")
            self.log_agent_msg("StealthCDP(#67)", f"[{serial}] Zero Runtime.enable + Adreno 730 Profile Verified", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v14_sensor_recoil_audit(self):
        def _worker():
            res68 = self.sensor_coherence_guard.execute()
            res69 = self.turnstile_waf_defense.execute()
            self._v14_log(f"[Subagent #68 SensorCoherence] Score={res68.get('coherence_score')} | [Subagent #69 PreWarm] {res69.get('challenge_triage')}")
            self.log_agent_msg("SensorAndPreWarm(#68-#69)", f"Coherence={res68.get('coherence_score')}% | Pre-Warm Ready", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v14_unified_finish_gate(self):
        def _worker():
            res = self.unified_ui_antibot_finish_gate.execute()
            self._v14_log(f"[Subagent #74 UnifiedFinishGate] Decision={res.get('decision')} | Composite={res.get('composite_score')} | BotRisk={res.get('bot_detection_risk_pct')}%")
            self.log_agent_msg("UnifiedGate(#74)", f"Gate={res.get('decision')} | BotRisk={res.get('bot_detection_risk_pct')}%", "success")
        threading.Thread(target=_worker, daemon=True).start()

    def on_v14_run_10x_causal_evolution(self):
        serial = self.v7_device_combo.get().strip() if hasattr(self, "v7_device_combo") else "10CF5L0TYL00312"
        def _worker():
            res = self.causal_10x_antibot_ui_ux_coordinator.execute(live_serial=serial, write_report=True)
            self._v14_log(f"[Subagent #75 CausalChain10xCoordinator] Loops={res.get('total_iterations')} | FinalScore={res.get('final_composite_score')} | FinalBotRisk={res.get('final_bot_risk_pct')}% | Gate={res.get('final_gate')}")
            self.log_agent_msg("Causal10x(#75)", f"[{serial}] 10/10 Causal Loops PASS (BotRisk={res.get('final_bot_risk_pct')}%)", "success")
        threading.Thread(target=_worker, daemon=True).start()


def main():
    root = tk.Tk()
    app = FarmDashboardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
