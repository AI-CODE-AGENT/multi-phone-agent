"""
Model Context Protocol (MCP) Server 2.0 for Android Multi-Agent Farm (AMAF 8.0).
Allows any AI Agent (Antigravity, Cursor, Claude Code, Kilo Code, ARTEMIS, OpenCode)
to discover, lease, observe, navigate, broadcast group actions, manage real physical phones,
orchestrate multi-app testing flows, crawl UI state graphs, execute human-like Cubic Bezier gestures,
auto-dismiss Vivo/OriginOS/MIUI USB installation popups, optimize Vivo OriginOS 6 (1260x2800) hardware,
launch a Live Interactive Web Testbench over `adb reverse`, solve all 13+ CAPTCHAs (Concentric Ring Rotation,
Multi-Image Grids, Web Browser/WebView, Audio PCM FFT, Behavioral Entropy, 3D Dice Sum), automate 7-mode 2FA/MFA,
classify cross-app auth states, audit WCAG 2.1 contrast, demangle Java/Native/ANR stack traces, inspect network API latency,
run 8-Stage Real-Device E2E Benchmarks, and trigger 35-subagent self-evolution loops.
Implements JSON-RPC 2.0 over standard I/O (stdio) with zero external dependencies.
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.adb_wrapper import ADBWrapper
from core.hardware_simulator import HardwareSimulator
from core.mock_otp_service import MockOTPService
from core.real_device_manager import RealDeviceManager
from core.group_control_broadcaster import GroupControlBroadcaster
from core.multi_app_manager import MultiAppAutomationManager
from core.human_touch_engine import HumanTouchEngine
from core.oem_popup_watcher import OEMPopupWatcher
from core.universal_apk_installer_engine import UniversalAPKInstallerEngine
from core.scrcpy_manager import ScrcpyManager
from core.memory_manager import MemoryManager
from core.git_worktree_manager import GitWorktreeManager
from agents.device_lock_manager import DeviceLockManager
from agents.experience_miner_subagent import ExperienceMinerSubagent
from agents.cross_app_notetaker_subagent import CrossAppNotetakerSubagent
from agents.action_reflector_subagent import ActionReflectorSubagent
from agents.multi_app_crawler_subagent import MultiAppCrawlerSubagent
from agents.human_touch_subagent import HumanTouchSubagent
from agents.oem_popup_guard_subagent import OEMPopupGuardSubagent
from agents.captcha_solver_subagent import CaptchaSolverSubagent
from agents.network_visual_qa_subagent import NetworkAndVisualQASubagent
from agents.auto_screenshot_subagent import AutoScreenshotSubagent
from agents.complex_captcha_subagent import ComplexCaptchaSubagent
from agents.deeplink_qr_scanner_subagent import DeepLinkAndQRScannerSubagent
from agents.clipboard_biometric_subagent import ClipboardAndBiometricHookSubagent
from agents.performance_memleak_subagent import PerformanceAndMemLeakSubagent
from agents.universal_2fa_subagent import Universal2FASubagent
from agents.web_and_advanced_captcha_subagent import WebAndAdvancedCaptchaSubagent
from agents.accessibility_wcag_subagent import AccessibilityAndWCAGContrastSubagent
from agents.crash_tombstone_anr_subagent import CrashTombstoneAndANRSubagent
from agents.network_api_latency_subagent import NetworkTrafficAndAPILatencySubagent
from agents.live_web_testbench_e2e_subagent import LiveWebTestbenchAndRealPhoneE2ESubagent
from agents.vivo_originos_optimizer_subagent import VivoOriginOSDeepOptimizerSubagent
from agents.audio_behavior_captcha_subagent import InteractiveAudioAndBehaviorCaptchaSubagent
from agents.session_credential_guard_subagent import CrossAppSessionAndCredentialGuardSubagent
from agents.real_device_e2e_benchmark_subagent import RealDeviceE2EBenchmarkAndSelfHealerSubagent
from agents.multi_screen_responsive_subagent import (
    MultiScreenViewportMatrixSubagent,
    ResponsiveDOMAndXMLCriticSubagent,
    SynchronizedMultiDeviceMirrorSubagent,
    VisualMultiScreenGridComposerSubagent,
    AutoFixLayoutPatchSynthesizerSubagent,
)
from agents.autonomous_qa_tester_subagent import (
    AutonomousTestPlanGeneratorSubagent,
    BoundaryAndMonkeyFuzzTesterSubagent,
    ZeroHumanQASignOffOracleSubagent,
    MCPVisionAndTestRunnerBridgeSubagent,
    Causal10xResponsiveQACoordinatorSubagent,
)
from agents.cross_platform_os_matrix_subagent import (
    DesktopOSViewportMatrixSubagent,
    AppleiOSAndiPadOSViewportSubagent,
    HarmonyOSAndOriginOSContinuitySubagent,
    AlternativeAndPrivacyMobileOSSubagent,
    KaiOSAndSmartTV10FootUISubagent,
    UniversalSafeAreaAndWindowChromeSubagent,
    CrossPlatform6FrameworkPatchSubagent,
    Visual25OSMatrixPosterComposerSubagent,
    UniversalZeroHumanCrossPlatformQAOracleSubagent,
    Causal10xCrossPlatformPromptEvolverSubagent,
)
from agents.dual_theme_and_balanced_layout_subagent import (
    DualThemeLightDarkTokenSubagent,
    VisualBalanceAndWhitespaceCriticSubagent,
    WebsiteTemplateGalleryBenchmarkSubagent,
    DualThemeSideBySideEvidenceComposerSubagent,
    UniversalDualThemeFinishGateOracleSubagent,
    Causal10xDualThemeAndLayoutEvolverSubagent,
)
from mcp_bridge.artemis_bridge import ArtemisBridge
from config.farm_config import DEFAULT_FARM_DEVICES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)
logger = logging.getLogger("AndroidFarmMCP")


class AndroidFarmMCPServer:
    """Standard Model Context Protocol Server 2.0 (55 Tools) for Hybrid Real & Virtual Multi-OS & Multi-App Farm (AMAF 16.0)."""

    def __init__(self):
        self.adb = ADBWrapper()
        self.hardware = HardwareSimulator(self.adb)
        self.otp_service = MockOTPService(self.hardware)
        self.real_mgr = RealDeviceManager(self.adb)
        self.broadcaster = GroupControlBroadcaster(self.adb, self.real_mgr)
        self.multi_app_mgr = MultiAppAutomationManager(self.adb, self.real_mgr, self.broadcaster, self.otp_service)
        self.human_engine = HumanTouchEngine(self.adb, self.real_mgr)
        self.oem_watcher = OEMPopupWatcher(self.adb)
        self.universal_installer = UniversalAPKInstallerEngine()
        self.scrcpy_mgr = ScrcpyManager()
        self.memory = MemoryManager()
        self.worktree_mgr = GitWorktreeManager()
        self.exp_miner = ExperienceMinerSubagent(self.memory)
        self.notetaker = CrossAppNotetakerSubagent(self.adb, self.memory)
        self.reflector = ActionReflectorSubagent(self.adb, self.memory)
        self.crawler = MultiAppCrawlerSubagent(self.adb, self.memory)
        self.human_subagent = HumanTouchSubagent(self.adb, self.memory)
        self.oem_guard = OEMPopupGuardSubagent(self.adb, self.memory)
        self.captcha_solver = CaptchaSolverSubagent(self.adb, self.memory)
        self.net_visual_qa = NetworkAndVisualQASubagent(self.adb, self.memory)
        self.auto_screenshot = AutoScreenshotSubagent(self.adb, self.memory)
        self.complex_captcha = ComplexCaptchaSubagent(self.adb, self.memory, solver=self.captcha_solver)
        self.deeplink_qr = DeepLinkAndQRScannerSubagent(self.adb, self.memory)
        self.clipboard_bio = ClipboardAndBiometricHookSubagent(self.adb, self.memory)
        self.perf_profiler = PerformanceAndMemLeakSubagent(self.adb, self.memory)
        self.universal_2fa = Universal2FASubagent(self.adb, self.memory)
        self.web_adv_captcha = WebAndAdvancedCaptchaSubagent(self.adb, self.memory, solver=self.captcha_solver)
        self.wcag_auditor = AccessibilityAndWCAGContrastSubagent(self.adb, self.memory)
        self.crash_analyzer = CrashTombstoneAndANRSubagent(self.adb, self.memory)
        self.net_api_profiler = NetworkTrafficAndAPILatencySubagent(self.adb, self.memory)
        self.live_testbench = LiveWebTestbenchAndRealPhoneE2ESubagent(self.adb, self.memory)
        self.vivo_optimizer = VivoOriginOSDeepOptimizerSubagent(self.adb, self.memory)
        self.audio_behavior_captcha = InteractiveAudioAndBehaviorCaptchaSubagent(self.adb, self.memory)
        self.session_guard = CrossAppSessionAndCredentialGuardSubagent(self.adb, self.memory)
        self.e2e_benchmark = RealDeviceE2EBenchmarkAndSelfHealerSubagent(self.adb, self.memory)
        self.responsive_matrix = MultiScreenViewportMatrixSubagent(self.adb, self.memory)
        self.responsive_critic = ResponsiveDOMAndXMLCriticSubagent(self.adb, self.memory)
        self.sync_mirror = SynchronizedMultiDeviceMirrorSubagent(self.adb, self.memory)
        self.qa_plan_gen = AutonomousTestPlanGeneratorSubagent(self.adb, self.memory)
        self.qa_fuzzer = BoundaryAndMonkeyFuzzTesterSubagent(self.adb, self.memory)
        self.qa_oracle = ZeroHumanQASignOffOracleSubagent(self.adb, self.memory)
        self.qa_10x_evolver = Causal10xResponsiveQACoordinatorSubagent(self.adb, self.memory)
        self.desktop_os_matrix = DesktopOSViewportMatrixSubagent(self.adb, self.memory)
        self.ios_ipados_matrix = AppleiOSAndiPadOSViewportSubagent(self.adb, self.memory)
        self.harmony_origin_matrix = HarmonyOSAndOriginOSContinuitySubagent(self.adb, self.memory)
        self.alt_mobile_matrix = AlternativeAndPrivacyMobileOSSubagent(self.adb, self.memory)
        self.kaios_tv_matrix = KaiOSAndSmartTV10FootUISubagent(self.adb, self.memory)
        self.safe_area_chrome = UniversalSafeAreaAndWindowChromeSubagent(self.adb, self.memory)
        self.six_framework_patcher = CrossPlatform6FrameworkPatchSubagent(self.adb, self.memory)
        self.os25_poster_composer = Visual25OSMatrixPosterComposerSubagent(self.adb, self.memory)
        self.os25_qa_oracle = UniversalZeroHumanCrossPlatformQAOracleSubagent(self.adb, self.memory)
        self.os25_causal_10x = Causal10xCrossPlatformPromptEvolverSubagent(self.adb, self.memory)
        self.dual_theme_token_subagent = DualThemeLightDarkTokenSubagent()
        self.visual_balance_critic = VisualBalanceAndWhitespaceCriticSubagent()
        self.template_benchmark_subagent = WebsiteTemplateGalleryBenchmarkSubagent()
        self.dual_theme_poster_subagent = DualThemeSideBySideEvidenceComposerSubagent()
        self.dual_theme_finish_gate = UniversalDualThemeFinishGateOracleSubagent()
        self.dual_theme_causal_10x = Causal10xDualThemeAndLayoutEvolverSubagent()
        self.lock_mgr = DeviceLockManager()
        self.bridge = ArtemisBridge()
        self.tools = self._register_tools()

    def list_tools(self) -> List[Dict[str, Any]]:
        return self.tools

    def _register_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "android_list_devices",
                "description": "List all online Android farm devices (both 4 Headless AVDs and optional Physical Real Phones) with lease status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {
                            "type": "string",
                            "description": "Optional calling agent ID to check lease ownership."
                        }
                    }
                }
            },
            {
                "name": "android_lease_device",
                "description": "Acquire an exclusive lease lock on a specific device serial (e.g. emulator-5554 or real phone USB/IP serial) to prevent test collisions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Device serial (e.g. emulator-5554 or 10CF5L0TYL00312)"},
                        "agent_id": {"type": "string", "description": "Unique identifier of the calling agent"},
                        "task_name": {"type": "string", "description": "Name or goal of the testing task"},
                        "lease_seconds": {"type": "integer", "description": "Lease duration in seconds (default 300)"}
                    },
                    "required": ["serial", "agent_id", "task_name"]
                }
            },
            {
                "name": "android_release_device",
                "description": "Release an exclusive lease lock on a device when the agent finishes testing.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Device serial"},
                        "agent_id": {"type": "string", "description": "Unique identifier of the calling agent"}
                    },
                    "required": ["serial", "agent_id"]
                }
            },
            {
                "name": "android_get_screen_state",
                "description": "Capture current screenshot path and dump parsed UI hierarchy (all clickable text elements, resource IDs, and bounds).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_tap_element",
                "description": "Tap an element on screen using either absolute coordinates (x, y) or text label search.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "x": {"type": "integer", "description": "X coordinate in pixels"},
                        "y": {"type": "integer", "description": "Y coordinate in pixels"},
                        "text": {"type": "string", "description": "Optional text to search and tap automatically"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_input_text",
                "description": "Type text or numbers into the currently focused input field on the device.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "text": {"type": "string", "description": "Text or numbers to type"}
                    },
                    "required": ["serial", "text"]
                }
            },
            {
                "name": "android_press_key",
                "description": "Simulate Android physical or soft key press (BACK, HOME, ENTER, APP_SWITCH, VOLUME_UP, VOLUME_DOWN).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "key": {"type": "string", "enum": ["BACK", "HOME", "ENTER", "APP_SWITCH", "VOLUME_UP", "VOLUME_DOWN"], "description": "Key name to press"}
                    },
                    "required": ["serial", "key"]
                }
            },
            {
                "name": "android_mock_otp",
                "description": "Zero-cost (0 VND) Mock OTP management. Works on both AVDs (simulated SMS) and Real Phones (broadcast + clipboard injection).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["generate", "inject_sms", "verify", "get_history"], "description": "Mock OTP action"},
                        "serial": {"type": "string", "description": "Target device serial (required for inject_sms)"},
                        "phone_number": {"type": "string", "description": "Target phone number (e.g. 0941189263)"},
                        "code": {"type": "string", "description": "Code to verify (for action='verify')"}
                    },
                    "required": ["action", "phone_number"]
                }
            },
            {
                "name": "android_touch_fingerprint",
                "description": "Trigger simulated biometric fingerprint authentication to pass biometric prompts.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "fingerprint_id": {"type": "integer", "description": "Fingerprint ID (default 1)"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_set_gps",
                "description": "Spoof GPS geo-coordinates on the device (e.g. Landmark 81 Saigon: 10.7951, 106.7218).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "latitude": {"type": "number", "description": "Latitude coordinate"},
                        "longitude": {"type": "number", "description": "Longitude coordinate"}
                    },
                    "required": ["serial", "latitude", "longitude"]
                }
            },
            {
                "name": "android_run_kanban_task",
                "description": "Execute a high-level task through the autonomous pipeline (Planner -> Operator -> Vision -> Healer -> Auditor -> CodeImprover -> RegressionVerifier -> ExperienceMiner).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_title": {"type": "string", "description": "Clear title of the testing/automation task"},
                        "task_description": {"type": "string", "description": "Detailed step-by-step goal or assertion"},
                        "device_serial": {"type": "string", "description": "Optional assigned device serial (e.g. emulator-5554 or real phone serial)"}
                    },
                    "required": ["task_title", "task_description"]
                }
            },
            {
                "name": "android_discover_real_devices",
                "description": "Scan and profile all connected physical Android phones (USB & Wireless TCP/IP) with manufacturer, model, resolution, battery %, and temperature (°C), or switch farm_mode (HYBRID, AVD_ONLY, REAL_ONLY).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "set_farm_mode": {
                            "type": "string",
                            "enum": ["HYBRID", "AVD_ONLY", "REAL_ONLY"],
                            "description": "Optional mode switch for optional Real Phone Farm."
                        },
                        "auto_reconnect_wireless": {
                            "type": "boolean",
                            "description": "Whether to auto-reconnect known wireless ADB endpoints first."
                        }
                    }
                }
            },
            {
                "name": "android_connect_wireless_adb",
                "description": "Switch a USB-connected real phone to Wireless ADB over TCP/IP (port 5555) or connect directly to a remote phone IP:Port.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["connect_ip", "usb_to_wireless", "disconnect"],
                            "description": "Wireless ADB operation"
                        },
                        "ip_or_serial": {
                            "type": "string",
                            "description": "Target IP address (e.g. 192.168.1.50) or USB serial (for usb_to_wireless)"
                        },
                        "port": {
                            "type": "integer",
                            "description": "TCP/IP ADB port (default 5555)"
                        }
                    },
                    "required": ["action", "ip_or_serial"]
                }
            },
            {
                "name": "android_group_broadcast",
                "description": "Synchronously control multiple real phones and emulators at the exact same time (tap, swipe, text, key, launch_app, shell) with automatic resolution scaling.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["tap", "swipe", "text", "key", "launch_app", "shell"],
                            "description": "Broadcast action type"
                        },
                        "group_filter": {
                            "type": "string",
                            "enum": ["ALL", "REAL_ONLY", "AVD_ONLY"],
                            "description": "Target device group filter when serials list is omitted"
                        },
                        "serials": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional explicit list of device serials"
                        },
                        "x": {"type": "number", "description": "Tap X or Swipe start X (pixel on 720x1600 or normalized 0.0-1.0)"},
                        "y": {"type": "number", "description": "Tap Y or Swipe start Y (pixel on 720x1600 or normalized 0.0-1.0)"},
                        "x2": {"type": "number", "description": "Swipe end X"},
                        "y2": {"type": "number", "description": "Swipe end Y"},
                        "text": {"type": "string", "description": "Text to broadcast, key name, package name, or shell command"}
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "android_device_health_guard",
                "description": "Inspect battery %, voltage, and temperature (°C) on a physical phone and apply thermal/screen-dimming protection.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target physical device serial"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_run_self_evolution_loop",
                "description": "Trigger the 35-Subagent Autonomous Self-Evolution Engine (Worktree Audit -> Scout -> Vivo OriginOS 6 Guard -> SoM Screenshot -> Multi-App Discovery -> Human Touch & 13+ Type CAPTCHA CV -> Universal 7-Mode 2FA & Session Guard -> Live Web Testbench E2E -> Multi-App Flow + Notetaker + Action Reflector -> UI Graph Crawler -> 48dp & WCAG 2.1 Audit -> Crash/ANR Demangler -> Network API Latency -> FPS/MemLeak -> Kanban Pipeline -> Prompt Evolution).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "iterations": {"type": "integer", "description": "Number of evolution cycles to run (default 1)"},
                        "package_name": {"type": "string", "description": "Target Android package (default com.android.settings)"}
                    }
                }
            },
            {
                "name": "android_mine_experience_macros",
                "description": "List or lookup reusable Macro-Action shortcuts distilled by ExperienceMinerSubagent (Mobile-Agent-E architecture).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "goal_query": {"type": "string", "description": "Optional goal text to match a specific macro shortcut"},
                        "package_name": {"type": "string", "description": "Optional package name (default com.android.settings)"}
                    }
                }
            },
            {
                "name": "android_open_multi_scrcpy_wall",
                "description": "Launch a tiled multi-device Scrcpy screen wall on the desktop for simultaneous visual monitoring of multiple real phones and AVDs.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serials": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of serials to display (defaults to all online devices)"
                        },
                        "cols": {"type": "integer", "description": "Number of grid columns (default 4)"}
                    }
                }
            },
            {
                "name": "android_manage_git_worktree",
                "description": "Create, list, commit, or merge isolated Git feature worktrees (`D:/Project/multi-phone-agent-worktrees/<slug>`) so each Subagent develops features in its own worktree.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["create", "list", "commit", "merge"],
                            "description": "Worktree management action"
                        },
                        "feature_slug": {"type": "string", "description": "Feature name/slug (e.g. real-phone-farm, group-control)"},
                        "subagent_name": {"type": "string", "description": "Owning subagent name"},
                        "commit_message": {"type": "string", "description": "Conventional commit message for commit action"},
                        "push_remote": {"type": "boolean", "description": "Push merged branch to origin (default true)"}
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "android_list_installed_apps",
                "description": "List installed third-party or system packages on a target device to support multi-application testing.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial (default emulator-5554)"},
                        "include_system": {"type": "boolean", "description": "Include system packages (default false)"}
                    }
                }
            },
            {
                "name": "android_app_state_control",
                "description": "Control application state for reproducible multi-app testing: clear app data, auto-grant runtime permissions, snapshot state, or restore state.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["grant_permissions", "clear_data", "snapshot", "restore"],
                            "description": "App state operation"
                        },
                        "serial": {"type": "string", "description": "Target device serial"},
                        "package_name": {"type": "string", "description": "Target Android package name"},
                        "label": {"type": "string", "description": "Optional checkpoint label for snapshot/restore"}
                    },
                    "required": ["action", "serial", "package_name"]
                }
            },
            {
                "name": "android_open_deep_link",
                "description": "Route a Deep Link or App Link URI (`https://...` or `customscheme://...`) on a device and measure launch latency in milliseconds.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "uri": {"type": "string", "description": "Deep link URI to open"},
                        "package_name": {"type": "string", "description": "Optional target package name"}
                    },
                    "required": ["serial", "uri"]
                }
            },
            {
                "name": "android_run_multi_app_flow",
                "description": "Execute a Maestro-style declarative multi-app workflow (`launchApp`, `clearState`, `grantPermissions`, `openLink`, `tapOn`, `inputText`, `assertVisible`, `switchApp`, `injectMockOtp`, `extractNote`) across one or multiple devices with CrossAppNotetaker support.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "steps": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Ordered list of declarative multi-app flow step objects"
                        },
                        "serials": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional target device serials"
                        }
                    },
                    "required": ["steps"]
                }
            },
            {
                "name": "android_crawl_app_graph",
                "description": "Run DroidBot/Fastbot-inspired UI state-graph exploration and optional Monkey burst across one or multiple Android applications.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial (default emulator-5554)"},
                        "package_name": {"type": "string", "description": "Single package name to crawl"},
                        "packages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of multiple packages to crawl sequentially"
                        },
                        "max_steps": {"type": "integer", "description": "Max exploration steps per app (default 3)"},
                        "run_monkey_burst": {"type": "boolean", "description": "Run fast monkey event burst (default false)"}
                    }
                }
            },
            {
                "name": "android_human_touch_action",
                "description": "Execute biometric human-like touch interactions (Gaussian-jitter dwell tap, Cubic Bezier curve swipe, slider drag with overshoot, or natural cadence typing).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "action": {
                            "type": "string",
                            "enum": ["tap", "bezier_swipe", "slider_drag", "type_text"],
                            "description": "Human-like touch action"
                        },
                        "x": {"type": "number", "description": "Start X coordinate (pixel or normalized 0..1)"},
                        "y": {"type": "number", "description": "Start Y coordinate (pixel or normalized 0..1)"},
                        "end_x": {"type": "integer", "description": "End X coordinate for bezier_swipe"},
                        "end_y": {"type": "integer", "description": "End Y coordinate for bezier_swipe"},
                        "distance_px": {"type": "integer", "description": "Horizontal drag distance in pixels for slider_drag"},
                        "text": {"type": "string", "description": "Text to type with human cadence"}
                    },
                    "required": ["serial", "action"]
                }
            },
            {
                "name": "android_oem_popup_guard",
                "description": "Auto-detect and click Vivo/OriginOS ('Tiếp tục cài đặt', 'Cho phép cài đặt qua USB'), Xiaomi MIUI/HyperOS, OPPO ColorOS, and Play Protect installation/consent dialogs, or install an APK with a background popup watcher.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "action": {
                            "type": "string",
                            "enum": ["scan_and_dismiss", "start_watcher", "stop_watcher", "guarded_install_apk"],
                            "description": "OEM popup guard action"
                        },
                        "apk_path": {"type": "string", "description": "Path to APK file when action='guarded_install_apk'"},
                        "use_vivo_fallback": {"type": "boolean", "description": "Use Vivo OriginOS bottom-sheet coordinate fallback when overlay hides XML nodes"}
                    },
                    "required": ["serial", "action"]
                }
            },
            {
                "name": "android_solve_captcha",
                "description": "Automatically detect and solve mobile CAPTCHA / verification challenges (Slider Puzzle with Cubic Bezier drag, Math/Text OCR, Checkbox challenge, or Image Grid).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "action": {
                            "type": "string",
                            "enum": ["detect", "solve"],
                            "description": "Whether to only detect or detect and solve the CAPTCHA"
                        },
                        "hint_distance_px": {"type": "integer", "description": "Optional explicit drag distance in pixels for Slider CAPTCHAs"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_network_and_visual_qa",
                "description": "Audit UI hierarchy against Google Material 48dp touch-target accessibility guidelines or verify app crash resilience across Wi-Fi network toggles.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "action": {
                            "type": "string",
                            "enum": ["layout_audit", "network_resilience"],
                            "description": "QA verification mode"
                        },
                        "package_name": {"type": "string", "description": "Target package name for network_resilience"}
                    },
                    "required": ["serial", "action"]
                }
            },
            {
                "name": "android_auto_screenshot_som",
                "description": "Capture smart screenshot, render Set-of-Mark (SoM) numbered visual grounding badges (#1, #2...), or crop and zoom a UI region (OmniParser / Mobile-Agent-v2 style).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "action": {
                            "type": "string",
                            "enum": ["capture_som", "crop_zoom", "locate_mark"],
                            "description": "Auto-screenshot & Set-of-Mark operation"
                        },
                        "mark_id": {"type": "integer", "description": "Set-of-Mark badge number to resolve"},
                        "bounds": {"type": "object", "description": "Bounds {x1,y1,x2,y2} for crop_zoom"},
                        "zoom_factor": {"type": "integer", "description": "Upscale zoom factor (default 2)"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_visual_template_match_and_diff",
                "description": "Run Airtest-style 2D Normalized Cross-Correlation (NCC) template matching or Maestro-style visual regression diffing (SSIM/PSNR/MAE + diff heatmap).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "action": {
                            "type": "string",
                            "enum": ["match_template", "compare_screenshots"],
                            "description": "Visual matching or regression diff operation"
                        },
                        "template_path": {"type": "string", "description": "Template PNG path for match_template"},
                        "baseline_path": {"type": "string", "description": "Baseline PNG path for compare_screenshots"},
                        "current_path": {"type": "string", "description": "Optional current screenshot PNG path"}
                    },
                    "required": ["serial", "action"]
                }
            },
            {
                "name": "android_solve_complex_captcha_cv",
                "description": "Universal Computer Vision CAPTCHA solver supporting all 10 simple & complex CAPTCHA types (Slider Sobel Gap, Rotation Polar Angle, Click-Order Blobs, Icon/Shape Outlier, Continuous Path Trace, Hold-Press Tremor, Audio Challenge, Opaque WebView Canvas, Math/OCR, Checkbox & Grid).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "action": {
                            "type": "string",
                            "enum": ["solve_any", "list_supported_types", "detect_sobel_gap", "estimate_rotation"],
                            "description": "Complex CAPTCHA CV operation"
                        },
                        "screenshot_path": {"type": "string", "description": "Optional screenshot path for CV analysis"},
                        "xml_override": {"type": "string", "description": "Optional XML hierarchy override"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_deeplink_and_qr_scanner",
                "description": "Automate Android App Links / Deep Link route fuzzing, detect camera QR viewfinder screens, generate synthetic QR codes, and inject ZXing/Camera QR/Barcode payloads.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "action": {
                            "type": "string",
                            "enum": ["open_deeplink", "fuzz_routes", "detect_scanner", "inject_qr"],
                            "description": "DeepLink or QR scanner operation"
                        },
                        "uri": {"type": "string", "description": "Deep link URI"},
                        "payload": {"type": "string", "description": "QR or Barcode payload string"},
                        "package_name": {"type": "string", "description": "Optional package name"}
                    },
                    "required": ["serial", "action"]
                }
            },
            {
                "name": "android_clipboard_biometric_and_notifications",
                "description": "Read/write/paste device clipboard, auto-extract OTPs from clipboard or notification shade, and trigger biometric fingerprint / PIN prompt authentication.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "action": {
                            "type": "string",
                            "enum": ["set_clipboard", "get_clipboard", "paste_clipboard", "biometric_auth", "inspect_notifications"],
                            "description": "Clipboard, biometric, or notification shade action"
                        },
                        "text": {"type": "string", "description": "Clipboard text to set"},
                        "finger_id": {"type": "integer", "description": "Fingerprint sensor ID (default 1)"},
                        "click_keyword": {"type": "string", "description": "Optional notification keyword to tap"}
                    },
                    "required": ["serial", "action"]
                }
            },
            {
                "name": "android_profile_performance_and_memleak",
                "description": "Profile real-time rendering FPS, Janky frames, P50/P90/P95/P99 latency (`dumpsys gfxinfo`), and PSS / Java Heap / Native Heap memory leak telemetry (`dumpsys meminfo`).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "package_name": {"type": "string", "description": "Target Android package name (default com.android.settings)"},
                        "action": {
                            "type": "string",
                            "enum": ["full_audit", "graphics_fps", "memory_leak"],
                            "description": "Performance profiling action (default full_audit)"
                        }
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_universal_2fa_automation",
                "description": "Automate all 7 complex 2FA/MFA modes: RFC 6238 TOTP (SHA1/SHA256/SHA512), RFC 4226 HOTP, 6-box Split-Digit OTP Entry, Authenticator Push Number-Matching ('Tap 84'), Cross-App Authenticator Switching, Passkey/WebAuthn, and Backup Recovery Codes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "action": {
                            "type": "string",
                            "enum": ["detect_and_solve", "generate_totp", "register_otpauth_uri", "list_accounts"],
                            "description": "Universal 2FA action"
                        },
                        "secret": {"type": "string", "description": "Base32 TOTP/HOTP secret (default JBSWY3DPEHPK3PXP)"},
                        "otpauth_uri": {"type": "string", "description": "otpauth://totp/... or otpauth://hotp/... URI"},
                        "account_id": {"type": "string", "description": "Registered account ID in 2FA vault"},
                        "push_target_number": {"type": "string", "description": "Optional target 2-digit number for Push Number-Matching"},
                        "authenticator_pkg": {"type": "string", "description": "Optional Authenticator app package for cross-app switching"},
                        "xml_override": {"type": "string", "description": "Optional UIAutomator XML override"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_solve_web_and_advanced_captcha",
                "description": "Solve Concentric Ring Image Rotation CAPTCHAs (`xoay ảnh`), Multi-Round 3x3 & 4x4 Multi-Image Grid Selection (`chọn nhiều ảnh`), and navigate to Web Browser/WebView URLs to solve web CAPTCHAs (`truy cập trang web giải capcha`).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "action": {
                            "type": "string",
                            "enum": ["solve_rotation_ring", "solve_multi_image_grid", "navigate_and_solve_web"],
                            "description": "Advanced/Web CAPTCHA operation"
                        },
                        "url": {"type": "string", "description": "Target web URL for navigate_and_solve_web"},
                        "screenshot_path": {"type": "string", "description": "Optional screenshot path"},
                        "grid_size": {"type": "integer", "description": "Grid dimension (3 for 3x3, 4 for 4x4)"},
                        "rounds": {"type": "integer", "description": "Number of dynamic replacement rounds (default 2)"},
                        "xml_override": {"type": "string", "description": "Optional UIAutomator XML override"}
                    },
                    "required": ["serial", "action"]
                }
            },
            {
                "name": "android_webview_devtools_bridge",
                "description": "Discover active Android WebView & Chrome DevTools UNIX domain sockets (`webview_devtools_remote_<pid>`, `chrome_devtools_remote`) and forward them to host TCP ports for DOM/CDP inspection.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "action": {
                            "type": "string",
                            "enum": ["discover_sockets", "forward_port"],
                            "description": "WebView DevTools bridge action"
                        },
                        "local_port": {"type": "integer", "description": "Local TCP port on host (default 9222)"},
                        "socket_name": {"type": "string", "description": "Socket name (default chrome_devtools_remote)"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_audit_wcag_accessibility",
                "description": "Audit Android UI screens against WCAG 2.1 AA/AAA color contrast ratios (`>= 4.5:1` / `>= 7.0:1`), TalkBack logical focus order, unlabeled interactive controls, and duplicate content descriptions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "screenshot_path": {"type": "string", "description": "Optional screenshot path for pixel luminance contrast check"},
                        "xml_override": {"type": "string", "description": "Optional UIAutomator XML override"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_analyze_crashes_and_anr",
                "description": "Parse and demangle Java/Kotlin Fatal Exceptions, Native C/C++ `SIGSEGV`/`SIGABRT` Tombstones, and `ANR in <pkg>` stack traces with deterministic SHA-256 deduplication and root-cause fix recommendations.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "package_name": {"type": "string", "description": "Optional package filter"},
                        "raw_logcat_override": {"type": "string", "description": "Optional raw logcat crash text override"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_audit_network_api_telemetry",
                "description": "Inspect `/proc/net/dev` RX/TX network throughput, parse HTTP/HTTPS API latency & status codes from logcat, and flag insecure `http://` cleartext endpoints.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "package_name": {"type": "string", "description": "Target package name (default com.android.settings)"},
                        "raw_logcat_override": {"type": "string", "description": "Optional logcat override"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_run_live_web_testbench_e2e",
                "description": "Start the Live Interactive Web CAPTCHA & 2FA Testbench Server on 127.0.0.1:8765, bind `adb reverse tcp:8765 tcp:8765`, open `/amaf-testbench` in the phone browser, and autonomously solve Concentric Rotation CAPTCHA, 3x3 Multi-Image Grid CAPTCHA, Slider Jigsaw CAPTCHA, RFC 6238 Live TOTP 2FA, and Push Number-Match 2FA.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial (e.g. 10CF5L0TYL00312)"},
                        "open_in_browser": {"type": "boolean", "description": "Open testbench URL in device browser (default true)"},
                        "execute_touch": {"type": "boolean", "description": "Execute physical touch gestures on device (default true)"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_optimize_vivo_originos_device",
                "description": "Inspect and optimize a Vivo / OriginOS 6 physical phone (such as Vivo V2417A 1260x2800): calibrate safe touch insets, enable USB stay-awake (`svc power stayon usb`), dismiss keyguard, and detect/dismiss Vivo security & USB install dialogs.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial (e.g. 10CF5L0TYL00312)"},
                        "keep_awake": {"type": "boolean", "description": "Keep screen awake over USB (default true)"},
                        "dismiss_keyguard": {"type": "boolean", "description": "Wake and dismiss keyguard (default true)"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_solve_audio_and_behavior_captcha",
                "description": "Solve Audio Accessibility CAPTCHAs via 16-bit PCM RMS + FFT spectral digit decoding, generate Fitts's Law minimum-jerk anti-bot human pointer trajectories, or solve 3D Dice Sum CAPTCHAs.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "challenge_type": {
                            "type": "string",
                            "enum": ["AUTO", "AUDIO_CAPTCHA", "BEHAVIORAL_ENTROPY", "DICE_SUM_CAPTCHA"],
                            "description": "Audio or behavioral CAPTCHA challenge type"
                        },
                        "wav_path": {"type": "string", "description": "Optional WAV file path for AUDIO_CAPTCHA"},
                        "image_path": {"type": "string", "description": "Optional PNG path for DICE_SUM_CAPTCHA"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_audit_session_and_credential_state",
                "description": "Classify current UI into deterministic auth states (`CAPTCHA_WALL`, `TWO_FACTOR_PROMPT`, `BIOMETRIC_PROMPT`, `OEM_SECURITY_DIALOG`, `LOGIN_CREDENTIALS_FORM`, `AUTHENTICATED_OR_GENERAL`), audit Android AccountManager/Autofill services, and extract deduplicated fresh OTPs.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial"},
                        "ui_xml_override": {"type": "string", "description": "Optional UI XML override"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_run_real_device_e2e_benchmark",
                "description": "Execute the 8-Stage Full-Stack Real-Device E2E Verification & Benchmark Suite on a connected physical phone (e.g. Vivo V2417A 10CF5L0TYL00312) or emulator and generate a Markdown evidence report.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial (e.g. 10CF5L0TYL00312)"},
                        "package_name": {"type": "string", "description": "Target package name (default com.android.settings)"},
                        "execute_touch": {"type": "boolean", "description": "Execute physical touch gestures (default true)"}
                    },
                    "required": ["serial"]
                }
            },
            {
                "name": "android_universal_install_apk",
                "description": "On-demand MCP tool (zero 24/7 background polling) to 100% automatically install an APK or dismiss Vivo OriginOS PackageInterceptActivity ('Tôi đã hiểu kết quả phát hiện rủi ro của ứng dụng' checkbox + 'Tiếp tục cài đặt' button). Runs a scoped popup watcher ONLY during the tool call and stops immediately upon completion.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Optional target device serial (auto-detects connected Vivo/Android device if omitted)"},
                        "apk_path": {"type": "string", "description": "Local path to the .apk file to install (leave empty if action='dismiss_active_dialog')"},
                        "action": {
                            "type": "string",
                            "enum": ["install_apk", "dismiss_active_dialog"],
                            "description": "Whether to install an APK with scoped OEM popup watcher or immediately dismiss an active install dialog on screen"
                        },
                        "grant_permissions": {"type": "boolean", "description": "Auto-grant runtime permissions (-g) during install (default true)"}
                    }
                }
            },
            {
                "name": "android_test_multi_screen_responsive",
                "description": "Test an Android app across multiple screen resolutions, densities, and orientations (Compact 720x1280, Standard 1080x2400, Vivo V2417A 1260x2800, Foldable 1812x2176, Tablet 1600x2560). Detects offscreen clipping, sibling overlap, text ellipsis, <48dp touch targets, and row misalignment, generates Android XML / Jetpack Compose / WebView CSS @media fixes, and returns a side-by-side comparison grid plus base64 images for Vision LLMs.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial (default 10CF5L0TYL00312)"},
                        "suite": {
                            "type": "string",
                            "enum": ["default_3", "phone_matrix", "full_5_screens"],
                            "description": "Preset screen suite to sweep (default full_5_screens)"
                        },
                        "profiles": {
                            "type": "array",
                            "items": {},
                            "description": "Optional custom list of profile IDs or {id, width, height, density_dpi} dicts"
                        },
                        "apply_hardware_wm": {
                            "type": "boolean",
                            "description": "If true, dynamically applies `adb shell wm size` and `wm density` per profile and resets in `finally` (default false for fast non-disruptive projection)"
                        },
                        "landscape": {"type": "boolean", "description": "Test in landscape orientation (default false)"},
                        "capture_screenshots": {"type": "boolean", "description": "Capture screenshots and return Vision LLM image blocks (default true)"}
                    }
                }
            },
            {
                "name": "android_run_autonomous_qa_tester",
                "description": "Zero-Human Autonomous QA Tester ('Thay thế hoàn toàn Tester'): Automatically discovers UI states, generates a 6-category Test Plan (Smoke, Multi-Screen Responsive, Actionability, Boundary Input Fuzzing, WCAG Accessibility, Crash/ANR), runs all 6 stages, compiles reproducible Bug Tickets (BUG-RESP/A11Y/CRASH) with Android XML/Compose/CSS fixes, and computes a 0..100 QA Readiness Verdict.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial (default 10CF5L0TYL00312)"},
                        "package_name": {"type": "string", "description": "Target Android package name (default com.android.settings)"},
                        "suite": {
                            "type": "string",
                            "enum": ["default_3", "phone_matrix", "full_5_screens"],
                            "description": "Responsive screen suite (default full_5_screens)"
                        },
                        "apply_hardware_wm": {"type": "boolean", "description": "Apply live `wm size`/`wm density` switches with `finally` reset (default false)"},
                        "capture_screenshots": {"type": "boolean", "description": "Capture multi-screen visual evidence (default true)"}
                    }
                }
            },
            {
                "name": "android_sync_multi_screen_action",
                "description": "Responsively-style synchronized interaction mirroring across multiple Android devices or screen resolutions using normalized [0.0 .. 1.0] coordinates (`norm_x`, `norm_y`) so a single tap, swipe, scroll, or text input maps accurately to 720p, 1080p, 1260p, Foldable, and Tablet screens simultaneously.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serials": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of target device serials (defaults to all online devices)"
                        },
                        "action_type": {
                            "type": "string",
                            "enum": ["tap", "swipe", "scroll", "input"],
                            "description": "Synchronized action to mirror"
                        },
                        "norm_x": {"type": "number", "description": "Normalized X coordinate in [0.0 .. 1.0]"},
                        "norm_y": {"type": "number", "description": "Normalized Y coordinate in [0.0 .. 1.0]"},
                        "norm_to_x": {"type": "number", "description": "Normalized end X for swipe/scroll in [0.0 .. 1.0]"},
                        "norm_to_y": {"type": "number", "description": "Normalized end Y for swipe/scroll in [0.0 .. 1.0]"},
                        "text": {"type": "string", "description": "Text to type when action_type='input'"},
                        "dry_run": {"type": "boolean", "description": "Compute coordinate mappings without dispatching ADB input"}
                    }
                }
            },
            {
                "name": "android_run_10x_responsive_qa_evolution",
                "description": "Execute the 10-Loop Causal Multi-Agent Evolution (`Loop 1` -> `Loop 10`) for Responsive Multi-Screen & Autonomous QA Testing, where each Loop n+1 strictly learns from Loop n's telemetry (`loop_n_plus_1.input_lesson == loop_n.learned_lesson`).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial (default 10CF5L0TYL00312)"},
                        "package_name": {"type": "string", "description": "Target package name (default com.android.settings)"}
                    }
                }
            },
            {
                "name": "android_list_cross_platform_os_profiles",
                "description": "List all 25 supported Cross-Platform Operating System & Form-Factor profiles across Desktop (Windows 11, macOS, ChromeOS, Ubuntu, Linux Mint, Fedora, Manjaro, Elementary OS, Zorin OS), Mobile (iOS 18 iPhone, iPadOS 18, Android 15, Vivo OriginOS, HarmonyOS & HarmonyOS NEXT, GrapheneOS, LineageOS, Ubuntu Touch, Sailfish OS, KaiOS), and Smart TV (LG webOS, Hisense VIDAA OS).",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "android_test_cross_platform_25os_matrix",
                "description": "Run Universal Zero-Human Cross-Platform Responsive & OS Safe-Area QA across up to 25 Operating Systems (Windows, macOS, ChromeOS, 6 Linux Distros, iOS, iPadOS, Android, OriginOS, HarmonyOS NEXT, GrapheneOS, LineageOS, Ubuntu Touch, Sailfish OS, KaiOS, LG webOS TV, Hisense VIDAA OS TV) and generate visual comparison poster + MCP Vision-LLM base64 image blocks.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Source device serial (default 10CF5L0TYL00312)"},
                        "suite": {
                            "type": "string",
                            "enum": ["full_25_os_matrix", "desktop_and_linux_11", "mobile_and_alt_os_12", "smart_tv_and_keypad_3", "representative_12_matrix"],
                            "description": "Cross-platform OS suite preset (default full_25_os_matrix)"
                        },
                        "profiles": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional explicit list of OS profile IDs or aliases"
                        }
                    }
                }
            },
            {
                "name": "android_audit_tv_and_kaios_spatial_navigation",
                "description": "Audit 10-Foot Smart TV (LG webOS, Hisense VIDAA OS) and Non-Touch Keypad (KaiOS 3.1) interfaces for SMPTE 5% title-safe overscan margins, >=24px 10-foot typography, KaiOS 36px 3-softkey bar collisions, and 100% LRUD (Left/Right/Up/Down) D-Pad Spatial Navigation focus graph reachability.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Source device serial (default 10CF5L0TYL00312)"}
                    }
                }
            },
            {
                "name": "android_generate_cross_platform_autofix_patches",
                "description": "Synthesize cross-platform auto-fix patches across 6 UI frameworks (Android XML, Jetpack Compose Multiplatform, Apple SwiftUI, Huawei HarmonyOS NEXT ArkTS, Desktop/Web CSS3, and Smart TV / KaiOS Spatial D-Pad Navigation).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "defect_code": {"type": "string", "description": "Defect code (e.g. SAFE_AREA_INSET_COLLISION, OFFSCREEN_CLIPPED_VIEW, DPAD_SPATIAL_FOCUS_UNREACHABLE)"},
                        "os_profile": {"type": "string", "description": "Target OS profile ID or alias (e.g. ios_iphone_16_pro_max, linux_ubuntu_gnome, harmonyos_next, webos, kaios)"},
                        "target_element": {"type": "string", "description": "Target UI element identifier"}
                    }
                }
            },
            {
                "name": "android_run_10x_cross_platform_causal_evolution",
                "description": "Execute the strict 10-Loop Causal Multi-OS Evolution (`Loop 1` -> `Loop 10`) across all 25 Operating Systems where for any loop n and constant a >= 0, Loop (n+a+1) strictly starts and rewrites its prompt only after Loop (n+a) completes and produces empirical telemetry (`started_at(n+a+1) > completed_at(n+a)` and `input_hash(n+a+1) == output_hash(n+a)`).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial (default 10CF5L0TYL00312)"}
                    }
                }
            },
            {
                "name": "android_switch_and_audit_dual_theme",
                "description": "Switch or audit AMAF v17.0 Dual-Theme (Light Mode ☀️ Daylight Alabaster vs Dark Mode 🌙 Obsidian Zinc) design tokens and verify WCAG AAA contrast ratios across all surfaces (`Subagent #96`).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string", "enum": ["LIGHT", "DARK"], "description": "Target theme mode (LIGHT or DARK)"}
                    }
                }
            },
            {
                "name": "android_audit_visual_balance_and_clutter",
                "description": "Audit GUI visual balance, tabless navigation, collapsible device drawer vertical savings (+45% stage height), 2x3 anti-rainbow button grids, and zero text truncation (`Subagents #97-#100`).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "theme_mode": {"type": "string", "enum": ["LIGHT", "DARK"], "description": "Theme mode to audit"}
                    }
                }
            },
            {
                "name": "android_benchmark_website_ui_templates",
                "description": "Benchmark layout proportions and anti-clutter rules against 12+ authoritative website & desktop UI templates (shadcn/ui, Tailwind UI, Vercel Geist, Linear, Stripe, Supabase, Tauri UI, Cruip, Creative Tim, Raycast, Mobbin, Collect UI) (`Subagent #101`).",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "android_render_dual_theme_evidence_posters",
                "description": "Compose the high-resolution side-by-side Light Mode ☀️ vs Dark Mode 🌙 visual comparison poster and verify the 12-point Dual-Theme Finish Gate (`Subagents #103-#104`).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "light_png_path": {"type": "string", "description": "Path to Light Mode screenshot"},
                        "dark_png_path": {"type": "string", "description": "Path to Dark Mode screenshot"}
                    }
                }
            },
            {
                "name": "android_run_10x_dual_theme_causal_evolution",
                "description": "Execute the strict 10-Loop Causal Dual-Theme & Anti-Clutter Evolution (`Loop 1` -> `Loop 10`) where Loop (n+a+1) strictly starts after Loop (n+a) finishes (`started_at(n+a+1) > completed_at(n+a)`) and rewrites its prompt from Loop (n+a) (`Subagent #105`).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "serial": {"type": "string", "description": "Target device serial (default 10CF5L0TYL00312)"},
                        "loops": {"type": "integer", "description": "Number of causal loops (default 10)"}
                    }
                }
            }
        ]

    def call_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        return self.handle_tool_call(name, args)

    def handle_tool_call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch tool calls to internal implementations."""
        try:
            if name == "android_list_devices":
                agent_id = args.get("agent_id", "External_Agent")
                devices = self.bridge.get_available_devices_for_agent(agent_id)
                return {
                    "success": True,
                    "farm_mode": self.real_mgr.get_farm_mode(),
                    "count": len(devices),
                    "devices": devices
                }

            elif name == "android_lease_device":
                serial = args["serial"]
                agent_id = args["agent_id"]
                task_name = args["task_name"]
                lease_sec = args.get("lease_seconds", 300)
                ok = self.bridge.lease_device(serial, agent_id, task_name, lease_sec)
                return {"success": ok, "serial": serial, "leased_to": agent_id, "duration": lease_sec}

            elif name == "android_release_device":
                serial = args["serial"]
                agent_id = args["agent_id"]
                ok = self.bridge.release_device(serial, agent_id)
                return {"success": ok, "serial": serial, "status": "released"}

            elif name == "android_get_screen_state":
                serial = args["serial"]
                screenshot_dir = PROJECT_ROOT / "reports" / "screenshots"
                screenshot_dir.mkdir(parents=True, exist_ok=True)
                safe_serial = serial.replace(":", "_")
                screenshot_file = str(screenshot_dir / f"screen_{safe_serial}.png")
                self.adb.capture_screenshot(serial, screenshot_file)
                ui_xml = self.adb.dump_ui_hierarchy(serial)
                ui_elements = self.adb.parse_ui_elements(ui_xml)
                w, h = self.real_mgr.get_device_resolution(serial)
                return {
                    "success": True,
                    "serial": serial,
                    "is_real_device": self.real_mgr.is_real_device(serial),
                    "resolution": f"{w}x{h}",
                    "screenshot_path": screenshot_file,
                    "element_count": len(ui_elements),
                    "elements": ui_elements[:50]
                }

            elif name == "android_tap_element":
                serial = args["serial"]
                if "x" in args and "y" in args:
                    x, y = int(args["x"]), int(args["y"])
                    self.adb.tap(serial, x, y)
                    return {"success": True, "x": x, "y": y}
                elif "text" in args:
                    text_query = args["text"].lower()
                    ui_xml = self.adb.dump_ui_hierarchy(serial)
                    elements = self.adb.parse_ui_elements(ui_xml)
                    matched = [e for e in elements if text_query in e.get("text", "").lower()]
                    if matched:
                        bounds = matched[0].get("bounds", {})
                        x = int(bounds.get("center_x", 0))
                        y = int(bounds.get("center_y", 0))
                        self.adb.tap(serial, x, y)
                        return {"success": True, "matched_text": matched[0]["text"], "tapped_at": [x, y]}
                    return {"success": False, "error": f"No element found matching text: {args['text']}"}
                return {"success": False, "error": "Must provide either (x, y) or text"}

            elif name == "android_input_text":
                serial = args["serial"]
                text = args["text"]
                self.adb.input_text(serial, text)
                return {"success": True, "typed_text": text}

            elif name == "android_press_key":
                serial = args["serial"]
                key = args["key"].upper()
                keymap = {
                    "BACK": 4, "HOME": 3, "ENTER": 66,
                    "APP_SWITCH": 187, "VOLUME_UP": 24, "VOLUME_DOWN": 25
                }
                keycode = keymap.get(key, 4)
                self.adb.press_key(serial, keycode)
                return {"success": True, "key": key, "keycode": keycode}

            elif name == "android_mock_otp":
                action = args["action"]
                phone = args["phone_number"]
                if action == "generate":
                    otp = self.otp_service.generate_otp(phone)
                    return {"success": True, "phone": phone, "otp_code": otp, "cost": "0 VND (Simulated)"}
                elif action == "inject_sms":
                    serial = args.get("serial", "emulator-5554")
                    code = args.get("code")
                    ok, msg = self.otp_service.deliver_mock_sms_to_device(serial, phone, code)
                    return {"success": ok, "phone": phone, "message": msg, "cost": "0 VND"}
                elif action == "verify":
                    code = args.get("code", "")
                    ok = self.otp_service.verify_otp(phone, code)
                    msg = "OTP matched successfully" if ok else "OTP invalid or expired"
                    return {"success": True, "phone": phone, "verified": ok, "message": msg}
                elif action == "get_history":
                    latest = self.otp_service.get_latest_otp(phone)
                    return {"success": True, "phone": phone, "latest_active_otp": latest}
                return {"success": False, "error": f"Unknown action: {action}"}

            elif name == "android_touch_fingerprint":
                serial = args["serial"]
                fid = args.get("fingerprint_id", 1)
                ok, msg = self.hardware.touch_fingerprint(serial, fid)
                return {"success": ok, "fingerprint_id": fid, "message": msg}

            elif name == "android_set_gps":
                serial = args["serial"]
                lat = float(args["latitude"])
                lng = float(args["longitude"])
                ok, msg = self.hardware.set_gps_location(serial, lat, lng)
                return {"success": ok, "latitude": lat, "longitude": lng, "message": msg}

            elif name == "android_run_kanban_task":
                title = args["task_title"]
                desc = args["task_description"]
                serial = args.get("device_serial", "emulator-5554")
                from agents.autonomous_pipeline_director import AutonomousPipelineDirector
                director = AutonomousPipelineDirector(self.adb, self.memory)
                result = director.run_autonomous_cycle(title, desc, serial)
                return {
                    "success": result.get("status") == "COMPLETED",
                    "task_id": result.get("card_id"),
                    "result": result
                }

            elif name == "android_discover_real_devices":
                if "set_farm_mode" in args:
                    self.real_mgr.set_farm_mode(args["set_farm_mode"])
                if args.get("auto_reconnect_wireless", False):
                    self.real_mgr.auto_reconnect_known_wireless()
                real_devs = self.real_mgr.discover_real_devices(include_unauthorized=True)
                return {
                    "success": True,
                    "farm_mode": self.real_mgr.get_farm_mode(),
                    "real_devices_count": len(real_devs),
                    "real_devices": real_devs
                }

            elif name == "android_connect_wireless_adb":
                action = args["action"]
                target = args["ip_or_serial"]
                port = int(args.get("port", 5555))
                if action == "connect_ip":
                    ok, msg = self.real_mgr.connect_wireless_device(target, port)
                elif action == "usb_to_wireless":
                    ok, msg = self.real_mgr.enable_wireless_adb(target, port)
                elif action == "disconnect":
                    ok, msg = self.real_mgr.disconnect_wireless_device(target)
                else:
                    return {"success": False, "error": f"Unknown wireless action: {action}"}
                return {"success": ok, "action": action, "target": target, "port": port, "message": msg}

            elif name == "android_group_broadcast":
                act = args["action"]
                serials = args.get("serials")
                gf = args.get("group_filter", "ALL")
                if act == "tap":
                    x = float(args.get("x", 360))
                    y = float(args.get("y", 800))
                    return self.broadcaster.broadcast_tap(x, y, serials=serials, group_filter=gf)
                elif act == "swipe":
                    x1 = float(args.get("x", 360))
                    y1 = float(args.get("y", 1100))
                    x2 = float(args.get("x2", 360))
                    y2 = float(args.get("y2", 400))
                    return self.broadcaster.broadcast_swipe(x1, y1, x2, y2, serials=serials, group_filter=gf)
                elif act == "text":
                    return self.broadcaster.broadcast_text(str(args.get("text", "")), serials=serials, group_filter=gf)
                elif act == "key":
                    return self.broadcaster.broadcast_key(str(args.get("text", "HOME")), serials=serials, group_filter=gf)
                elif act == "launch_app":
                    return self.broadcaster.broadcast_launch_app(str(args.get("text", "com.android.settings")), serials=serials, group_filter=gf)
                elif act == "shell":
                    return self.broadcaster.broadcast_shell(str(args.get("text", "getprop ro.product.model")), serials=serials, group_filter=gf)
                return {"success": False, "error": f"Unknown broadcast action: {act}"}

            elif name == "android_device_health_guard":
                serial = args["serial"]
                res = self.real_mgr.apply_real_phone_health_guard(serial)
                return {"success": True, **res}

            elif name == "android_run_self_evolution_loop":
                iterations = int(args.get("iterations", 1))
                pkg = args.get("package_name", "com.android.settings")
                from agents.self_evolution_engine import SelfEvolutionEngine
                engine = SelfEvolutionEngine(self.adb, self.memory)
                res = engine.run_evolution_loop(iterations=iterations, package_name=pkg)
                return {"success": True, **res}

            elif name == "android_mine_experience_macros":
                goal_q = args.get("goal_query")
                pkg = args.get("package_name", "com.android.settings")
                if goal_q:
                    macro = self.exp_miner.lookup_macro_for_goal(goal_q, pkg)
                    return {"success": True, "matched_macro": macro}
                macros = self.memory.list_macros()
                return {"success": True, "macros_count": len(macros), "macros": macros}

            elif name == "android_open_multi_scrcpy_wall":
                serials = args.get("serials") or self.broadcaster.resolve_target_serials(group_filter="ALL")
                cols = int(args.get("cols", 4))
                res = self.scrcpy_mgr.open_multi_device_wall(serials=serials, cols=cols)
                return {"success": True, **res}

            elif name == "android_manage_git_worktree":
                act = args["action"]
                slug = args.get("feature_slug", "subagent-feature")
                sub = args.get("subagent_name", "Subagent")
                if act == "create":
                    return self.worktree_mgr.create_feature_worktree(slug, subagent_name=sub)
                elif act == "list":
                    wts = self.worktree_mgr.list_worktrees()
                    return {"success": True, "count": len(wts), "worktrees": wts}
                elif act == "commit":
                    wt_path = self.worktree_mgr.worktrees_root / self.worktree_mgr.slugify_feature(slug)
                    msg = args.get("commit_message", f"feat({slug}): automated subagent update")
                    return self.worktree_mgr.commit_in_worktree(wt_path, msg, subagent_name=sub)
                elif act == "merge":
                    push = bool(args.get("push_remote", True))
                    return self.worktree_mgr.merge_worktree_to_main(slug, push_remote=push)
                return {"success": False, "error": f"Unknown worktree action: {act}"}

            elif name == "android_list_installed_apps":
                serial = args.get("serial", "emulator-5554")
                inc_sys = bool(args.get("include_system", False))
                res = self.multi_app_mgr.list_installed_apps(serial, include_system=inc_sys)
                return {"success": True, **res}

            elif name == "android_app_state_control":
                act = args["action"]
                serial = args["serial"]
                pkg = args["package_name"]
                label = args.get("label", "checkpoint_1")
                if act == "grant_permissions":
                    res = self.multi_app_mgr.grant_all_runtime_permissions(serial, pkg)
                elif act == "clear_data":
                    res = self.multi_app_mgr.clear_app_data(serial, pkg)
                elif act == "snapshot":
                    res = self.multi_app_mgr.snapshot_app_state(serial, pkg, label=label)
                elif act == "restore":
                    res = self.multi_app_mgr.restore_app_state(serial, pkg, label=label)
                else:
                    return {"success": False, "error": f"Unknown app state action: {act}"}
                return {"success": True, **res}

            elif name == "android_open_deep_link":
                serial = args["serial"]
                uri = args["uri"]
                pkg = args.get("package_name")
                res = self.multi_app_mgr.open_deep_link(serial, uri, package=pkg)
                return {"success": True, **res}

            elif name == "android_run_multi_app_flow":
                steps = args.get("steps", [])
                serials = args.get("serials")
                res = self.multi_app_mgr.run_declarative_multi_app_flow(flow_steps=steps, serials=serials)
                for k, v in res.get("shared_notes", {}).items():
                    self.notetaker.record_note(k, str(v), source_app="multi_app_flow")
                return {"success": True, **res}

            elif name == "android_crawl_app_graph":
                serial = args.get("serial", "emulator-5554")
                pkgs = args.get("packages")
                max_steps = int(args.get("max_steps", 3))
                monkey = bool(args.get("run_monkey_burst", False))
                if pkgs and isinstance(pkgs, list):
                    res = self.crawler.crawl_multiple_apps(serial, pkgs, steps_per_app=max_steps)
                else:
                    pkg = args.get("package_name", "com.android.settings")
                    res = self.crawler.crawl_application(serial, pkg, max_steps=max_steps, run_monkey_burst=monkey)
                return {"success": True, **res}

            elif name == "android_human_touch_action":
                serial = args["serial"]
                res = self.human_subagent.execute_human_action(serial, args)
                return {"success": True, **res}

            elif name == "android_oem_popup_guard":
                serial = args["serial"]
                act = args["action"]
                vivo_fb = bool(args.get("use_vivo_fallback", True))
                if act == "scan_and_dismiss":
                    res = self.oem_guard.guard_device(serial, use_vivo_fallback=vivo_fb)
                elif act == "start_watcher":
                    res = self.oem_watcher.start_background_watcher(serial, use_vivo_fallback=vivo_fb)
                elif act == "stop_watcher":
                    res = self.oem_watcher.stop_background_watcher(serial)
                elif act == "guarded_install_apk":
                    apk_path = args.get("apk_path", "")
                    res = self.oem_guard.guarded_apk_install(serial, apk_path)
                else:
                    return {"success": False, "error": f"Unknown oem_popup_guard action: {act}"}
                return {"success": True, **res}

            elif name == "android_solve_captcha":
                serial = args["serial"]
                act = args.get("action", "solve")
                if act == "detect":
                    res = self.captcha_solver.detect_captcha_challenge(serial)
                else:
                    res = self.captcha_solver.solve_captcha(
                        serial,
                        hint_distance_px=args.get("hint_distance_px")
                    )
                return {"success": True, **res}

            elif name == "android_network_and_visual_qa":
                serial = args["serial"]
                act = args["action"]
                if act == "layout_audit":
                    res = self.net_visual_qa.audit_ui_accessibility_and_layout(serial)
                else:
                    pkg = args.get("package_name", "com.android.settings")
                    res = self.net_visual_qa.run_network_resilience_check(serial, pkg)
                return {"success": True, **res}

            elif name == "android_auto_screenshot_som":
                serial = args["serial"]
                act = args.get("action", "capture_som")
                if act == "crop_zoom":
                    shot = args.get("screenshot_path") or self.auto_screenshot.capture_smart_screenshot(serial, annotate_som=False)["screenshot_path"]
                    bounds = args.get("bounds") or {"x1": 100, "y1": 200, "x2": 400, "y2": 500}
                    res = self.auto_screenshot.engine.crop_and_zoom_region(shot, bounds, zoom_factor=int(args.get("zoom_factor", 2)))
                elif act == "locate_mark":
                    res = self.auto_screenshot.locate_by_template_or_som(
                        serial,
                        mark_id=int(args.get("mark_id", 1)),
                        screenshot_path=args.get("screenshot_path"),
                        xml_override=args.get("xml_override")
                    )
                else:
                    res = self.auto_screenshot.capture_smart_screenshot(
                        serial,
                        tag=args.get("tag", "mcp_som"),
                        annotate_som=True,
                        xml_override=args.get("xml_override")
                    )
                return {"success": True, **res}

            elif name == "android_visual_template_match_and_diff":
                serial = args["serial"]
                act = args["action"]
                if act == "match_template":
                    res = self.auto_screenshot.locate_by_template_or_som(
                        serial,
                        template_path=args.get("template_path"),
                        screenshot_path=args.get("current_path")
                    )
                else:
                    res = self.auto_screenshot.visual_regression_check(
                        serial,
                        baseline_path=args.get("baseline_path", ""),
                        current_path=args.get("current_path")
                    )
                return {"success": True, **res}

            elif name == "android_solve_complex_captcha_cv":
                serial = args["serial"]
                act = args.get("action", "solve_any")
                if act == "list_supported_types":
                    types = self.complex_captcha.get_supported_captcha_types()
                    return {"success": True, "count": len(types), "supported_captcha_types": types}
                elif act == "detect_sobel_gap":
                    res = self.complex_captcha.cv_engine.detect_slider_gap_sobel(
                        args.get("screenshot_path", ""),
                        track_width=int(args.get("track_width", 520))
                    )
                    return {"success": True, **res}
                elif act == "estimate_rotation":
                    res = self.complex_captcha.cv_engine.estimate_rotation_angle(
                        args.get("screenshot_path"),
                        track_width=int(args.get("track_width", 520))
                    )
                    return {"success": True, **res}
                else:
                    res = self.complex_captcha.solve_any_captcha_with_vision(
                        serial,
                        xml_override=args.get("xml_override"),
                        screenshot_path=args.get("screenshot_path"),
                        auto_screenshot=bool(args.get("auto_screenshot", True))
                    )
                    return {"success": True, **res}

            elif name == "android_deeplink_and_qr_scanner":
                serial = args["serial"]
                act = args["action"]
                if act == "open_deeplink":
                    res = self.deeplink_qr.open_deep_link(serial, args.get("uri", "https://example.com"), args.get("package_name"))
                elif act == "fuzz_routes":
                    res = self.deeplink_qr.fuzz_deep_link_routes(serial, args.get("uri", "https://example.com/route"), package_name=args.get("package_name"))
                elif act == "detect_scanner":
                    res = self.deeplink_qr.detect_qr_scanner_screen(serial, xml_override=args.get("xml_override"))
                else:
                    res = self.deeplink_qr.inject_qr_or_barcode_payload(
                        serial,
                        payload=args.get("payload", "https://example.com/qr"),
                        format_type=args.get("format_type", "QR_CODE")
                    )
                return {"success": True, **res}

            elif name == "android_clipboard_biometric_and_notifications":
                serial = args["serial"]
                act = args["action"]
                if act == "set_clipboard":
                    res = self.clipboard_bio.set_clipboard(serial, args.get("text", ""))
                elif act == "get_clipboard":
                    res = self.clipboard_bio.get_clipboard(serial)
                elif act == "paste_clipboard":
                    res = self.clipboard_bio.paste_clipboard(serial)
                elif act == "biometric_auth":
                    res = self.clipboard_bio.authenticate_biometric(
                        serial,
                        finger_id=int(args.get("finger_id", 1)),
                        pin_fallback=str(args.get("pin_fallback", "1234")),
                        xml_override=args.get("xml_override")
                    )
                else:
                    res = self.clipboard_bio.inspect_and_interact_notifications(
                        serial,
                        click_keyword=args.get("click_keyword"),
                        expand_shade=bool(args.get("expand_shade", False)),
                        dumpsys_override=args.get("dumpsys_override")
                    )
                return {"success": True, **res}

            elif name == "android_profile_performance_and_memleak":
                serial = args["serial"]
                pkg = args.get("package_name", "com.android.settings")
                act = args.get("action", "full_audit")
                if act == "graphics_fps":
                    res = self.perf_profiler.profile_app_graphics_fps(serial, pkg)
                elif act == "memory_leak":
                    res = self.perf_profiler.profile_app_memory_and_leaks(serial, pkg)
                else:
                    res = self.perf_profiler.run_comprehensive_performance_audit(serial, pkg)
                return {"success": True, **res}

            elif name == "android_universal_2fa_automation":
                serial = args["serial"]
                act = args.get("action", "detect_and_solve")
                if act == "generate_totp":
                    res = self.universal_2fa.engine.generate_totp(
                        secret=args.get("secret", "JBSWY3DPEHPK3PXP"),
                        digits=int(args.get("digits", 6)),
                        period=int(args.get("period", 30)),
                        algorithm=str(args.get("algorithm", "SHA1"))
                    )
                elif act == "register_otpauth_uri":
                    res = self.universal_2fa.engine.register_otpauth_uri(args.get("otpauth_uri", ""))
                elif act == "list_accounts":
                    accts = self.universal_2fa.engine.list_accounts() if hasattr(self.universal_2fa.engine, "list_accounts") else []
                    res = {"accounts_count": len(accts), "accounts": accts}
                else:
                    res = self.universal_2fa.solve_2fa_challenge(
                        serial=serial,
                        secret=args.get("secret", "JBSWY3DPEHPK3PXP"),
                        account_id=args.get("account_id"),
                        push_target_number=args.get("push_target_number"),
                        authenticator_pkg=args.get("authenticator_pkg"),
                        xml_override=args.get("xml_override")
                    )
                return {"success": True, **res}

            elif name == "android_solve_web_and_advanced_captcha":
                serial = args["serial"]
                act = args["action"]
                if act == "solve_rotation_ring":
                    res = self.web_adv_captcha.solve_rotation_captcha_advanced(
                        serial=serial,
                        screenshot_path=args.get("screenshot_path"),
                        track_width=int(args.get("track_width", 520))
                    )
                elif act == "solve_multi_image_grid":
                    res = self.web_adv_captcha.solve_multi_image_grid_captcha(
                        serial=serial,
                        screenshot_path=args.get("screenshot_path"),
                        grid_size=int(args.get("grid_size", 3)),
                        rounds=int(args.get("rounds", 2))
                    )
                else:
                    res = self.web_adv_captcha.navigate_and_solve_web_captcha(
                        serial=serial,
                        url=args.get("url", "https://example.com"),
                        xml_override=args.get("xml_override"),
                        screenshot_path=args.get("screenshot_path"),
                        enable_cdp_forward=bool(args.get("enable_cdp_forward", True))
                    )
                return {"success": True, **res}

            elif name == "android_webview_devtools_bridge":
                serial = args["serial"]
                act = args.get("action", "discover_sockets")
                if act == "forward_port":
                    res = self.web_adv_captcha.engine.forward_webview_cdp_port(
                        self.adb,
                        serial=serial,
                        local_port=int(args.get("local_port", 9222)),
                        socket_name=args.get("socket_name", "chrome_devtools_remote")
                    )
                    return {"success": True, **res}
                else:
                    sockets = self.web_adv_captcha.engine.discover_webview_devtools_sockets(self.adb, serial)
                    return {"success": True, "serial": serial, "sockets_count": len(sockets), "sockets": sockets}

            elif name == "android_audit_wcag_accessibility":
                serial = args["serial"]
                res = self.wcag_auditor.audit_wcag_and_talkback_tree(
                    serial=serial,
                    xml_override=args.get("xml_override"),
                    screenshot_path=args.get("screenshot_path")
                )
                return {"success": True, **res}

            elif name == "android_analyze_crashes_and_anr":
                serial = args["serial"]
                res = self.crash_analyzer.analyze_logcat_and_tombstones(
                    serial=serial,
                    package_name=args.get("package_name"),
                    raw_logcat_override=args.get("raw_logcat_override")
                )
                return {"success": True, **res}

            elif name == "android_audit_network_api_telemetry":
                serial = args["serial"]
                res = self.net_api_profiler.run_network_api_telemetry_audit(
                    serial=serial,
                    package_name=args.get("package_name", "com.android.settings"),
                    raw_logcat_override=args.get("raw_logcat_override")
                )
                return {"success": True, **res}

            elif name == "android_run_live_web_testbench_e2e":
                serial = args["serial"]
                open_br = bool(args.get("open_in_browser", True))
                exec_t = bool(args.get("execute_touch", True))
                res = self.live_testbench.run_live_web_captcha_and_2fa_e2e(
                    serial=serial,
                    open_in_browser=open_br,
                    execute_touch=exec_t
                )
                return {"success": True, **res}

            elif name == "android_optimize_vivo_originos_device":
                serial = args["serial"]
                keep_awake = bool(args.get("keep_awake", True))
                dismiss_kg = bool(args.get("dismiss_keyguard", True))
                res = self.vivo_optimizer.inspect_and_optimize_vivo_device(
                    serial=serial,
                    keep_awake=keep_awake,
                    dismiss_keyguard=dismiss_kg
                )
                return {"success": True, **res}

            elif name == "android_solve_audio_and_behavior_captcha":
                serial = args["serial"]
                ctype = args.get("challenge_type", "AUTO")
                res = self.audio_behavior_captcha.solve_audio_or_behavioral_challenge(
                    serial=serial,
                    challenge_type=ctype,
                    wav_path=args.get("wav_path"),
                    image_path=args.get("image_path")
                )
                return {"success": True, **res}

            elif name == "android_audit_session_and_credential_state":
                serial = args["serial"]
                res = self.session_guard.audit_and_advance_auth_state(
                    serial=serial,
                    ui_xml_override=args.get("ui_xml_override")
                )
                return {"success": True, **res}

            elif name == "android_run_real_device_e2e_benchmark":
                serial = args["serial"]
                pkg = args.get("package_name", "com.android.settings")
                exec_t = bool(args.get("execute_touch", True))
                res = self.e2e_benchmark.run_full_device_e2e_benchmark(
                    serial=serial,
                    package_name=pkg,
                    execute_touch=exec_t
                )
                return {"success": True, **res}

            elif name == "android_universal_install_apk":
                serial = args.get("serial")
                if not serial:
                    online = self.adb.get_online_devices()
                    serial = online[0] if online else "10CF5L0TYL00312"
                apk_path = str(args.get("apk_path", "")).strip()
                act = args.get("action", "install_apk" if apk_path else "dismiss_active_dialog")
                if act == "dismiss_active_dialog" or not apk_path:
                    stage_res = self.universal_installer.execute_installer_step(self.adb, serial=serial)
                    oem_res = self.oem_watcher.scan_and_dismiss_once(serial, use_vivo_fallback=True)
                    return {
                        "success": True,
                        "mode": "dismiss_active_dialog",
                        "serial": serial,
                        "stage_result": stage_res,
                        "oem_result": oem_res,
                    }
                res = self.oem_guard.guarded_apk_install(serial=serial, apk_path=apk_path)
                return {"success": bool(res.get("success", res.get("installed", False))), **res}

            elif name == "android_test_multi_screen_responsive":
                serial = args.get("serial") or (self.adb.get_online_devices() or ["10CF5L0TYL00312"])[0]
                res = self.responsive_matrix.run_matrix_sweep(
                    serial=serial,
                    suite=args.get("suite", "full_5_screens"),
                    profiles=args.get("profiles"),
                    apply_hardware_wm=bool(args.get("apply_hardware_wm", False)),
                    landscape=bool(args.get("landscape", False)),
                    capture_screenshots=bool(args.get("capture_screenshots", True)),
                    xml_override=args.get("xml_override"),
                )
                return {"success": True, **res}

            elif name == "android_run_autonomous_qa_tester":
                serial = args.get("serial") or (self.adb.get_online_devices() or ["10CF5L0TYL00312"])[0]
                pkg = args.get("package_name", "com.android.settings")
                res = self.qa_oracle.run_autonomous_qa_tester(
                    serial=serial,
                    package_name=pkg,
                    suite=args.get("suite", "full_5_screens"),
                    profiles=args.get("profiles"),
                    apply_hardware_wm=bool(args.get("apply_hardware_wm", False)),
                    capture_screenshots=bool(args.get("capture_screenshots", True)),
                    xml_override=args.get("xml_override"),
                )
                return {"success": True, **res}

            elif name == "android_sync_multi_screen_action":
                serials = args.get("serials") or self.adb.get_online_devices() or ["10CF5L0TYL00312"]
                res = self.sync_mirror.mirror_action(
                    serials=serials,
                    action_type=args.get("action_type", "tap"),
                    norm_x=float(args.get("norm_x", 0.5)),
                    norm_y=float(args.get("norm_y", 0.5)),
                    norm_to_x=float(args.get("norm_to_x", 0.5)),
                    norm_to_y=float(args.get("norm_to_y", 0.25)),
                    text=str(args.get("text", "")),
                    dry_run=bool(args.get("dry_run", False)),
                )
                return {"success": True, **res}

            elif name == "android_run_10x_responsive_qa_evolution":
                serial = args.get("serial") or (self.adb.get_online_devices() or ["10CF5L0TYL00312"])[0]
                pkg = args.get("package_name", "com.android.settings")
                res = self.qa_10x_evolver.run_10x_causal_evolution(
                    serial=serial,
                    package_name=pkg,
                    xml_override=args.get("xml_override"),
                )
                return {"success": True, **res}

            elif name == "android_list_cross_platform_os_profiles":
                res = self.os25_poster_composer.list_all_25_os_profiles()
                return {"success": True, **res}

            elif name == "android_test_cross_platform_25os_matrix":
                serial = args.get("serial") or "10CF5L0TYL00312"
                res = self.os25_qa_oracle.execute(
                    serial=serial,
                    suite=args.get("suite", "full_25_os_matrix"),
                    profiles=args.get("profiles"),
                    xml_override=args.get("xml_override"),
                )
                return {"success": True, **res}

            elif name == "android_audit_tv_and_kaios_spatial_navigation":
                serial = args.get("serial") or "10CF5L0TYL00312"
                res = self.kaios_tv_matrix.execute(
                    serial=serial,
                    xml_override=args.get("xml_override"),
                )
                return {"success": True, **res}

            elif name == "android_generate_cross_platform_autofix_patches":
                res = self.six_framework_patcher.execute(
                    defect_code=args.get("defect_code", "SAFE_AREA_INSET_COLLISION"),
                    os_profile=args.get("os_profile", "ios_iphone_16_pro_max"),
                    target_element=args.get("target_element", "header_toolbar"),
                )
                return {"success": True, **res}

            elif name == "android_run_10x_cross_platform_causal_evolution":
                serial = args.get("serial") or "10CF5L0TYL00312"
                res = self.os25_causal_10x.execute(
                    serial=serial,
                    xml_override=args.get("xml_override"),
                )
                return {"success": True, **res}

            elif name == "android_switch_and_audit_dual_theme":
                res = self.dual_theme_token_subagent.execute(mode=args.get("mode", "LIGHT"))
                return {"success": True, **res}

            elif name == "android_audit_visual_balance_and_clutter":
                res = self.visual_balance_critic.execute(theme_mode=args.get("theme_mode", "DARK"))
                return {"success": True, **res}

            elif name == "android_benchmark_website_ui_templates":
                res = self.template_benchmark_subagent.execute()
                return {"success": True, **res}

            elif name == "android_render_dual_theme_evidence_posters":
                p_res = self.dual_theme_poster_subagent.execute(
                    light_png_path=args.get("light_png_path", ""),
                    dark_png_path=args.get("dark_png_path", ""),
                )
                fg_res = self.dual_theme_finish_gate.execute()
                return {"success": True, **p_res, "finish_gate": fg_res}

            elif name == "android_run_10x_dual_theme_causal_evolution":
                res = self.dual_theme_causal_10x.execute(
                    serial=args.get("serial", "10CF5L0TYL00312"),
                    loops=int(args.get("loops", 10)),
                )
                return {"success": True, **res}

            else:
                return {"success": False, "error": f"Unknown tool: {name}"}

        except Exception as e:
            logger.exception("Error executing tool %s: %s", name, e)
            return {"success": False, "error": str(e)}

    def run_stdio(self):
        """Standard JSON-RPC 2.0 I/O loop."""
        logger.info("Android Multi-Agent Farm MCP Server 2.0 (AMAF 16.0 - 55 Tools) started on stdio.")
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                req_id = req.get("id")
                method = req.get("method")
                params = req.get("params", {})

                if method == "initialize":
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {}},
                            "serverInfo": {
                                "name": "android-multi-agent-farm",
                                "version": "16.0.0"
                            }
                        }
                    }
                elif method == "tools/list":
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "tools": self.tools
                        }
                    }
                elif method == "tools/call":
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    output = self.handle_tool_call(tool_name, arguments)
                    mcp_images = output.pop("mcp_images", None) if isinstance(output, dict) else None
                    content_blocks = [
                        {
                            "type": "text",
                            "text": json.dumps(output, ensure_ascii=False, indent=2)
                        }
                    ]
                    if isinstance(mcp_images, list):
                        for img in mcp_images[:4]:
                            if isinstance(img, dict) and img.get("data"):
                                content_blocks.append(
                                    {
                                        "type": "image",
                                        "data": img["data"],
                                        "mimeType": img.get("mimeType", "image/jpeg"),
                                    }
                                )
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": content_blocks
                        }
                    }
                elif method == "ping":
                    res = {"jsonrpc": "2.0", "id": req_id, "result": {}}
                else:
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Method '{method}' not found"}
                    }
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()
            except Exception as e:
                err_res = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
                }
                sys.stdout.write(json.dumps(err_res) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    server = AndroidFarmMCPServer()
    server.run_stdio()
