"""
Model Context Protocol (MCP) Server 2.0 for Android Multi-Agent Farm (AMAF 5.0).
Allows any AI Agent (Antigravity, Cursor, Claude Code, Kilo Code, ARTEMIS, OpenCode)
to discover, lease, observe, navigate, broadcast group actions, manage real physical phones,
orchestrate multi-app testing flows, crawl UI state graphs, execute human-like Cubic Bezier gestures,
auto-dismiss Vivo/OriginOS/MIUI USB installation popups, solve CAPTCHAs, and trigger 20-subagent self-evolution loops.
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
from mcp_bridge.artemis_bridge import ArtemisBridge
from config.farm_config import DEFAULT_FARM_DEVICES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)
logger = logging.getLogger("AndroidFarmMCP")


class AndroidFarmMCPServer:
    """Standard Model Context Protocol Server 2.0 (28 Tools) for Hybrid Real & Virtual Multi-App Farm."""

    def __init__(self):
        self.adb = ADBWrapper()
        self.hardware = HardwareSimulator(self.adb)
        self.otp_service = MockOTPService(self.hardware)
        self.real_mgr = RealDeviceManager(self.adb)
        self.broadcaster = GroupControlBroadcaster(self.adb, self.real_mgr)
        self.multi_app_mgr = MultiAppAutomationManager(self.adb, self.real_mgr, self.broadcaster, self.otp_service)
        self.human_engine = HumanTouchEngine(self.adb, self.real_mgr)
        self.oem_watcher = OEMPopupWatcher(self.adb)
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
        self.lock_mgr = DeviceLockManager()
        self.bridge = ArtemisBridge()
        self.tools = self._register_tools()

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
                        "serial": {"type": "string", "description": "Device serial (e.g. emulator-5554 or R58M... or 192.168.1.50:5555)"},
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
                "description": "Trigger the 20-Subagent Autonomous Self-Evolution Engine (Worktree Audit -> Scout -> Vivo/OEM Guard -> Multi-App Discovery -> Human Touch & CAPTCHA Check -> Multi-App Flow + Notetaker + Action Reflector -> UI Graph Crawler -> 48dp Visual QA -> Kanban Pipeline -> Prompt Evolution).",
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
            }
        ]

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

            else:
                return {"success": False, "error": f"Unknown tool: {name}"}

        except Exception as e:
            logger.exception("Error executing tool %s: %s", name, e)
            return {"success": False, "error": str(e)}

    def run_stdio(self):
        """Standard JSON-RPC 2.0 I/O loop."""
        logger.info("Android Multi-Agent Farm MCP Server 2.0 (AMAF 5.0 - 28 Tools) started on stdio.")
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
                                "version": "5.0.0"
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
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": json.dumps(output, ensure_ascii=False, indent=2)
                                }
                            ]
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
