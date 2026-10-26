"""
Core UI/UX Navigation, Command Palette & Bento Device Card Engines (#58, #59, #60).

Zero-AI-Token deterministic UI/UX architecture engines for Multi-Phone Agent Farm:
- Engine #58 (`SidebarNavigationAndIAEngine`): Miller's-Law 5-Workspace Left Sidebar
  Information Architecture replacing 8+ cramped horizontal tabs and mapping all 65 Subagents
  with Hick's Law cognitive load reduction (> 60%).
- Engine #59 (`CommandPaletteAndProgressiveDisclosureEngine`): Raycast / Linear / VS Code
  style `Ctrl+K` / `⌘K` fuzzy Command Palette indexing all 65 Subagents + 30+ quick actions,
  plus Progressive Disclosure toolbar splitter (`1 Primary CTA` + `<= 3 Secondary` + `Overflow Drawer`).
- Engine #60 (`BentoDeviceCardAndSparklineEngine`): SonicCloud / OpenSTF / Vercel Analytics
  inspired Bento Device Card view-model builder & Unicode/SVG telemetry sparkline renderer.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _strip_accents(text: str) -> str:
    """Normalize Vietnamese/Unicode diacritics for fast zero-token fuzzy search."""
    if not text:
        return ""
    text = text.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn").lower()


# ==============================================================================
# ENGINE #58: SidebarNavigationAndIAEngine
# ==============================================================================


@dataclass(frozen=True)
class WorkspaceNode:
    """Represents one of the 5 Miller's-Law-compliant Left Sidebar Workspaces."""

    workspace_id: str
    title: str
    icon: str
    shortcut: str
    description: str
    subagent_ids: List[int]
    primary_features: List[str]
    badge_color: str = "#38bdf8"


class SidebarNavigationAndIAEngine:
    """
    Engine #58: Information Architecture & Left Sidebar Router.

    Solves the "Horizontal Tab Overflow & Illogical Grouping" defect by organizing
    all 65 Subagents and features into 5 logical, Miller's-Law-compliant (5 ± 2)
    Sidebar Workspaces instead of 8+ cramped horizontal tabs or 65 top-level buttons.
    """

    LEGACY_TOP_LEVEL_CHOICE_COUNT: int = 65
    LEGACY_HORIZONTAL_TAB_COUNT: int = 9

    def __init__(self) -> None:
        self._workspaces: Dict[str, WorkspaceNode] = self._build_workspaces()
        self._active_workspace_id: str = "fleet_overview"

    @staticmethod
    def _build_workspaces() -> Dict[str, WorkspaceNode]:
        """Build the 5 canonical Miller's-Law-compliant Sidebar Workspaces covering #1..#65."""
        nodes = [
            WorkspaceNode(
                workspace_id="fleet_overview",
                title="📱 Fleet & Real Phones",
                icon="📱",
                shortcut="Alt+1",
                description=(
                    "Virtual AVD Grid, Real Phone Farm (Vivo V2417A), Multi-Scrcpy Wall, "
                    "and Group Broadcast."
                ),
                subagent_ids=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 42],
                primary_features=[
                    "Virtual AVD Grid",
                    "Real Phone Farm (Vivo V2417A)",
                    "Multi-Scrcpy Wall",
                    "Group Broadcast",
                ],
                badge_color="#10b981",
            ),
            WorkspaceNode(
                workspace_id="automation_evolution",
                title="🤖 AI Loops & 10x Evolution",
                icon="🤖",
                shortcut="Alt+2",
                description=(
                    "65-Subagent Self-Evolution, 10x Recursive Evolution (#51-#55), "
                    "UI/UX 10x Evolution (#56-#65), Kanban Pipeline, Visual Flow DAG (#45)."
                ),
                subagent_ids=[
                    16, 17, 18, 19, 20, 21, 35, 37, 39, 45,
                    51, 52, 53, 54, 55,
                    56, 57, 58, 59, 60, 61, 62, 63, 64, 65,
                ],
                primary_features=[
                    "65-Subagent Self-Evolution",
                    "10x Recursive Evolution (#51-#55)",
                    "UI/UX 10x Evolution (#56-#65)",
                    "Kanban Pipeline",
                    "Visual Flow DAG (#45)",
                ],
                badge_color="#8b5cf6",
            ),
            WorkspaceNode(
                workspace_id="security_captcha_lab",
                title="🔐 Security, 2FA & CAPTCHA",
                icon="🔐",
                shortcut="Alt+3",
                description=(
                    "Universal 7-Mode 2FA (#26), 13+ Type CAPTCHA CV (#22, #27, #33, #40), "
                    "Live Web Testbench (#31), Session & Vault Guard (#34, #44)."
                ),
                subagent_ids=[22, 23, 24, 26, 27, 31, 32, 33, 34, 40, 44],
                primary_features=[
                    "Universal 7-Mode 2FA (#26)",
                    "13+ Type CAPTCHA CV (#22, #27, #33, #40)",
                    "Live Web Testbench (#31)",
                    "Session & Vault Guard (#34, #44)",
                ],
                badge_color="#f59e0b",
            ),
            WorkspaceNode(
                workspace_id="gpu_stream_diagnostics",
                title="⚡ GPU, Stream & Diagnostics",
                icon="⚡",
                shortcut="Alt+4",
                description=(
                    "RTX 3050 Zero-Token Vision/OCR (#36, #43), Persistent ADB Stream (#41), "
                    "Android CDP (#38), WCAG/Crash/Network/FPS (#25, #28, #29, #30)."
                ),
                subagent_ids=[25, 28, 29, 30, 36, 38, 41, 43],
                primary_features=[
                    "RTX 3050 Zero-Token Vision/OCR (#36, #43)",
                    "Persistent ADB Stream (#41)",
                    "Android CDP (#38)",
                    "WCAG/Crash/Network/FPS (#25, #28, #29, #30)",
                ],
                badge_color="#06b6d4",
            ),
            WorkspaceNode(
                workspace_id="apk_installer_memory",
                title="📦 APK Installer & Memory",
                icon="📦",
                shortcut="Alt+5",
                description=(
                    "Universal Multi-Stage APK Installer (#46), Sideload Guard (#47), "
                    "Vivo SecIME Vault (#48), Pure-Python AXML (#49), Always-On Daemon (#50), "
                    "Codebase Memory & Defect Reports."
                ),
                subagent_ids=[46, 47, 48, 49, 50],
                primary_features=[
                    "Universal Multi-Stage APK Installer (#46)",
                    "Sideload Guard (#47)",
                    "Vivo SecIME Vault (#48)",
                    "Pure-Python AXML (#49)",
                    "Always-On Daemon (#50)",
                    "Codebase Memory & Defect Reports",
                ],
                badge_color="#ec4899",
            ),
        ]
        return {node.workspace_id: node for node in nodes}

    def list_workspaces(self) -> List[Dict[str, Any]]:
        """Return ordered list of all 5 Sidebar Workspaces as serializable dictionaries."""
        result: List[Dict[str, Any]] = []
        for ws_id, node in self._workspaces.items():
            result.append(
                {
                    "workspace_id": node.workspace_id,
                    "title": node.title,
                    "icon": node.icon,
                    "shortcut": node.shortcut,
                    "description": node.description,
                    "subagent_ids": list(node.subagent_ids),
                    "subagent_count": len(node.subagent_ids),
                    "primary_features": list(node.primary_features),
                    "badge_color": node.badge_color,
                    "is_active": ws_id == self._active_workspace_id,
                }
            )
        return result

    def get_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Retrieve a specific workspace by ID."""
        if workspace_id not in self._workspaces:
            raise KeyError(f"Unknown workspace_id: {workspace_id!r}")
        node = self._workspaces[workspace_id]
        return {
            "workspace_id": node.workspace_id,
            "title": node.title,
            "icon": node.icon,
            "shortcut": node.shortcut,
            "description": node.description,
            "subagent_ids": list(node.subagent_ids),
            "subagent_count": len(node.subagent_ids),
            "primary_features": list(node.primary_features),
            "badge_color": node.badge_color,
            "is_active": workspace_id == self._active_workspace_id,
        }

    def select_workspace(self, workspace_id: str) -> Dict[str, Any]:
        """Switch active sidebar workspace and return updated routing state."""
        if workspace_id not in self._workspaces:
            raise KeyError(f"Cannot route to unknown workspace_id: {workspace_id!r}")
        self._active_workspace_id = workspace_id
        return self.get_workspace(workspace_id)

    def locate_subagent_workspace(self, subagent_id: int) -> Dict[str, Any]:
        """Find which of the 5 Sidebar Workspaces hosts `subagent_id` (1..65)."""
        for ws_id, node in self._workspaces.items():
            if subagent_id in node.subagent_ids:
                return {
                    "subagent_id": subagent_id,
                    "workspace_id": ws_id,
                    "workspace_title": node.title,
                    "shortcut": node.shortcut,
                }
        raise ValueError(f"Subagent #{subagent_id} is not mapped to any workspace (valid: 1..65)")

    def verify_complete_65_subagent_coverage(self) -> Dict[str, Any]:
        """Verify that all 65 Subagents (#1..#65) are uniquely mapped across the 5 workspaces."""
        all_ids: List[int] = []
        for node in self._workspaces.values():
            all_ids.extend(node.subagent_ids)
        expected = set(range(1, 66))
        actual = set(all_ids)
        missing = sorted(expected - actual)
        duplicates = sorted({x for x in all_ids if all_ids.count(x) > 1})
        return {
            "workspace_count": len(self._workspaces),
            "total_mapped_subagents": len(actual),
            "expected_subagents": 65,
            "missing_subagents": missing,
            "duplicate_subagents": duplicates,
            "millers_law_compliant": 3 <= len(self._workspaces) <= 7,
            "complete_65_coverage": (len(missing) == 0 and len(duplicates) == 0 and len(actual) == 65),
        }

    def cognitive_load_reduction_pct(
        self,
        flat_choices: int = LEGACY_TOP_LEVEL_CHOICE_COUNT,
        workspace_choices: int = 5,
    ) -> float:
        """
        Compute Hick's Law cognitive load / decision time reduction percentage.

        Under Hick-Hyman Law, decision entropy for scanning `N` ungrouped controls vs
        scanning `W` progressive-disclosure workspaces (`W = 5`) scales with
        log2(N + 1) and linear visual scan cost:
            Effective flat complexity = N * log2(N + 1)
            Effective grouped complexity = W * log2(W + 1) + (N / W) * log2((N / W) + 1)
        Returns percentage reduction (> 60.0%).
        """
        if flat_choices <= workspace_choices or workspace_choices <= 0:
            return 0.0

        flat_cost = flat_choices * math.log2(flat_choices + 1)
        avg_group_size = flat_choices / float(workspace_choices)
        progressive_cost = (
            workspace_choices * math.log2(workspace_choices + 1)
            + avg_group_size * math.log2(avg_group_size + 1)
        )
        reduction = ((flat_cost - progressive_cost) / flat_cost) * 100.0
        return round(max(0.0, min(99.9, reduction)), 2)


# ==============================================================================
# ENGINE #59: CommandPaletteAndProgressiveDisclosureEngine
# ==============================================================================


@dataclass(frozen=True)
class CommandPaletteEntry:
    """Single searchable item in the `Ctrl+K` / `⌘K` Command Palette."""

    command_id: str
    title: str
    category_badge: str
    shortcut_hint: str
    handler_name: str
    workspace_id: str
    subagent_id: Optional[int] = None
    keywords: List[str] = field(default_factory=list)


class CommandPaletteAndProgressiveDisclosureEngine:
    """
    Engine #59: Raycast / Linear / VS Code `Ctrl+K` Fuzzy Command Palette
    & Progressive Disclosure Engine.

    - Indexes all 65 Subagents (#1..#65) and 32+ quick actions with Vietnamese & English
      aliases, category badges, shortcut hints, and handler names.
    - Performs zero-token fuzzy search (`search_commands(query, limit=8)`).
    - Enforces Progressive Disclosure on any toolbar (`enforce_progressive_disclosure`)
      so no toolbar ever exceeds `1 Primary CTA` + `<= 3 Secondary Buttons` + `Overflow Drawer`.
    """

    SHORTCUT_TRIGGER = "Ctrl+K"

    # Dedicated high-value metadata for Subagents #1..#65
    SUBAGENT_CATALOG: Dict[int, Dict[str, Any]] = {
        1: {"name": "AVD Fleet Provisioner", "ws": "fleet_overview", "kw": ["avd", "emulator", "virtual", "create"]},
        2: {"name": "ADB Device Discovery & Health", "ws": "fleet_overview", "kw": ["adb", "devices", "usb", "serial"]},
        3: {"name": "Multi-Scrcpy Matrix Controller", "ws": "fleet_overview", "kw": ["scrcpy", "mirror", "screen", "wall"]},
        4: {"name": "Group Broadcast Input Synchronizer", "ws": "fleet_overview", "kw": ["broadcast", "sync", "group", "tap"]},
        5: {"name": "Vivo V2417A Real Phone Bridge", "ws": "fleet_overview", "kw": ["vivo", "v2417a", "real phone", "physical", "dien thoai that"]},
        6: {"name": "Proxy & APN Per-Device Router", "ws": "fleet_overview", "kw": ["proxy", "socks5", "vpn", "ip", "apn"]},
        7: {"name": "Device Fingerprint & Props Spoofer", "ws": "fleet_overview", "kw": ["imei", "fingerprint", "build.prop", "spoof"]},
        8: {"name": "Battery & Thermal Guard", "ws": "fleet_overview", "kw": ["battery", "thermal", "temperature", "pin", "nhiet do"]},
        9: {"name": "Storage & Cache Hygiene Cleaner", "ws": "fleet_overview", "kw": ["storage", "cache", "clean", "don rac"]},
        10: {"name": "Audio & Microphone Loopback", "ws": "fleet_overview", "kw": ["audio", "mic", "sound", "am thanh"]},
        11: {"name": "GPS & Mock Location Trajectory", "ws": "fleet_overview", "kw": ["gps", "location", "vi tri", "mock"]},
        12: {"name": "Clipboard & File Push/Pull Sync", "ws": "fleet_overview", "kw": ["clipboard", "push", "pull", "file"]},
        13: {"name": "Screen Orientation & Resolution Governor", "ws": "fleet_overview", "kw": ["rotation", "dpi", "resolution", "xoay man hinh"]},
        14: {"name": "Real Phone USB Auto-Reconnect", "ws": "fleet_overview", "kw": ["usb", "reconnect", "vivo", "ket noi"]},
        15: {"name": "Fleet Snapshot & Restore Manager", "ws": "fleet_overview", "kw": ["snapshot", "backup", "restore", "sao luu"]},
        16: {"name": "TikTok Autonomous Warmup & Scroll", "ws": "automation_evolution", "kw": ["tiktok", "scroll", "luot tiktok", "warmup", "nuoi nick"]},
        17: {"name": "Social Account Onboarding Flow", "ws": "automation_evolution", "kw": ["login", "register", "dang nhap", "social", "account"]},
        18: {"name": "Kanban Task Queue Scheduler", "ws": "automation_evolution", "kw": ["kanban", "queue", "scheduler", "lich trinh"]},
        19: {"name": "Natural Bezier Touch Humanizer", "ws": "automation_evolution", "kw": ["bezier", "swipe", "human", "touch", "vuot"]},
        20: {"name": "Smart Retry & Incident Recovery", "ws": "automation_evolution", "kw": ["retry", "recovery", "incident", "tu phuc hoi"]},
        21: {"name": "Multi-App Workflow Sequencer", "ws": "automation_evolution", "kw": ["workflow", "sequence", "multi-app", "kich ban"]},
        22: {"name": "Slider Puzzle CAPTCHA CV Solver", "ws": "security_captcha_lab", "kw": ["captcha", "slider", "keo hinh", "puzzle", "cv"]},
        23: {"name": "Anti-Bot Telemetry Evasion Guard", "ws": "security_captcha_lab", "kw": ["antibot", "evasion", "stealth", "chong quet"]},
        24: {"name": "Permission Dialog Auto-Granter", "ws": "security_captcha_lab", "kw": ["permission", "grant", "allow", "cap quyen"]},
        25: {"name": "WCAG Contrast & Accessibility Auditor", "ws": "gpu_stream_diagnostics", "kw": ["wcag", "accessibility", "contrast", "kiem thu"]},
        26: {"name": "Universal 7-Mode 2FA & OTP Extractor", "ws": "security_captcha_lab", "kw": ["2fa", "otp", "totp", "sms", "authenticator", "ma xac thuc"]},
        27: {"name": "3D Rotation & Object CAPTCHA Solver", "ws": "security_captcha_lab", "kw": ["captcha", "rotation", "xoay anh", "3d", "object"]},
        28: {"name": "ANR & Crash Tombstone Inspector", "ws": "gpu_stream_diagnostics", "kw": ["crash", "anr", "logcat", "tombstone", "loi ung dung"]},
        29: {"name": "Network Latency & Packet Inspector", "ws": "gpu_stream_diagnostics", "kw": ["network", "ping", "latency", "packet", "mang"]},
        30: {"name": "Frame Pacing & 60FPS Jank Profiler", "ws": "gpu_stream_diagnostics", "kw": ["fps", "jank", "frame", "gpu", "muot"]},
        31: {"name": "Live Web CAPTCHA & 2FA Testbench", "ws": "security_captcha_lab", "kw": ["testbench", "captcha", "2fa", "web", "live test"]},
        32: {"name": "SMS & Notification Listener Guard", "ws": "security_captcha_lab", "kw": ["sms", "notification", "tin nhan", "otp"]},
        33: {"name": "Grid Selection & Icon CAPTCHA Solver", "ws": "security_captcha_lab", "kw": ["captcha", "grid", "icon", "recaptcha", "hcaptcha", "turnstile"]},
        34: {"name": "Encrypted Credential & Cookie Vault", "ws": "security_captcha_lab", "kw": ["vault", "cookie", "session", "token", "bao mat"]},
        35: {"name": "Self-Evolving Rule Synthesizer", "ws": "automation_evolution", "kw": ["self-evolution", "synthesize", "tu tien hoa"]},
        36: {"name": "RTX 3050 CUDA PTX Vision Engine", "ws": "gpu_stream_diagnostics", "kw": ["rtx 3050", "cuda", "ptx", "gpu", "vision", "sm_86"]},
        37: {"name": "Zero-Token UI Hierarchy Grounder", "ws": "automation_evolution", "kw": ["uiautomator", "xml", "hierarchy", "grounding"]},
        38: {"name": "Android Chrome DevTools Protocol (CDP)", "ws": "gpu_stream_diagnostics", "kw": ["cdp", "webview", "chrome", "devtools"]},
        39: {"name": "Autonomous State Machine Explorer", "ws": "automation_evolution", "kw": ["fsm", "state machine", "explorer", "kham pha"]},
        40: {"name": "13+ Type Universal CAPTCHA Orchestrator", "ws": "security_captcha_lab", "kw": ["captcha", "13 type", "universal captcha", "giai captcha"]},
        41: {"name": "Persistent Sub-15ms ADB Frame Streamer", "ws": "gpu_stream_diagnostics", "kw": ["stream", "adb stream", "screencap", "low latency"]},
        42: {"name": "Multi-Phone Farm Load Balancer", "ws": "fleet_overview", "kw": ["load balancer", "farm", "cluster", "phan tai"]},
        43: {"name": "Zero-Token GPU OCR & Text Locator", "ws": "gpu_stream_diagnostics", "kw": ["ocr", "text", "gpu ocr", "doc chu", "rtx 3050"]},
        44: {"name": "Session Hijack & Token Expiry Watchdog", "ws": "security_captcha_lab", "kw": ["session", "expiry", "watchdog", "token"]},
        45: {"name": "Visual Flow DAG Pipeline Builder", "ws": "automation_evolution", "kw": ["dag", "visual flow", "pipeline", "node graph"]},
        46: {"name": "Universal Multi-Stage APK Installer", "ws": "apk_installer_memory", "kw": ["apk", "install", "cai dat apk", "xapk", "apks", "split apk", "#46"]},
        47: {"name": "Android Sideload & Play Protect Guard", "ws": "apk_installer_memory", "kw": ["sideload", "play protect", "allow install", "cap quyen cai apk", "#47"]},
        48: {"name": "Vivo V2417A SecIME Password Vault", "ws": "apk_installer_memory", "kw": ["vivo", "secime", "password", "mat khau vivo", "v2417a", "#48"]},
        49: {"name": "Pure-Python AXML Manifest Parser", "ws": "apk_installer_memory", "kw": ["axml", "manifest", "package name", "apk parser", "#49"]},
        50: {"name": "Always-On APK Folder Watchdog Daemon", "ws": "apk_installer_memory", "kw": ["daemon", "watchdog", "auto install", "tu dong cai apk", "#50"]},
        51: {"name": "10x Recursive Gap & Bottleneck Miner", "ws": "automation_evolution", "kw": ["10x", "recursive", "bottleneck", "evolution", "tien hoa 10x", "#51"]},
        52: {"name": "10x Subagent Code & Prompt Mutator", "ws": "automation_evolution", "kw": ["10x", "mutator", "code evolution", "#52"]},
        53: {"name": "10x Pareto Frontier Benchmark Judge", "ws": "automation_evolution", "kw": ["10x", "pareto", "benchmark", "judge", "#53"]},
        54: {"name": "10x Cross-Device Knowledge Distiller", "ws": "automation_evolution", "kw": ["10x", "distiller", "knowledge", "#54"]},
        55: {"name": "10x Autonomous Master Evolution Loop", "ws": "automation_evolution", "kw": ["10x", "master loop", "recursive evolution", "tu tien hoa", "#55"]},
        56: {"name": "UI/UX 10x Heuristic & Clutter Auditor", "ws": "automation_evolution", "kw": ["ui ux", "heuristic", "nielsen", "clutter", "giao dien", "#56"]},
        57: {"name": "UI/UX Design Token & Dark Theme Engine", "ws": "automation_evolution", "kw": ["ui ux", "design token", "dark mode", "theme", "mau sac", "#57"]},
        58: {"name": "Sidebar Navigation & IA Router", "ws": "automation_evolution", "kw": ["ui ux", "sidebar", "navigation", "information architecture", "menu", "#58"]},
        59: {"name": "Ctrl+K Command Palette & Progressive Disclosure", "ws": "automation_evolution", "kw": ["ui ux", "ctrl+k", "command palette", "progressive disclosure", "tim kiem", "#59"]},
        60: {"name": "Bento Device Card & Sparkline Renderer", "ws": "automation_evolution", "kw": ["ui ux", "bento", "device card", "sparkline", "the thiet bi", "#60"]},
        61: {"name": "Log Drawer & Collapsible Inspector", "ws": "automation_evolution", "kw": ["ui ux", "log drawer", "console", "inspector", "#61"]},
        62: {"name": "Empty State & Guided Onboarding Wizard", "ws": "automation_evolution", "kw": ["ui ux", "empty state", "onboarding", "huong dan", "#62"]},
        63: {"name": "Toast Notification & Action Undo Manager", "ws": "automation_evolution", "kw": ["ui ux", "toast", "notification", "undo", "thong bao", "#63"]},
        64: {"name": "Keyboard Shortcut & Focus Ring Manager", "ws": "automation_evolution", "kw": ["ui ux", "keyboard", "shortcut", "phim tat", "a11y", "#64"]},
        65: {"name": "UI/UX 10x Master Polish & Verification Gate", "ws": "automation_evolution", "kw": ["ui ux", "10x", "polish", "finish gate", "hoan thien giao dien", "#65"]},
    }

    QUICK_ACTIONS: List[Dict[str, Any]] = [
        {"id": "act_install_apk", "title": "Install APK / XAPK on Selected Phones", "badge": "APK", "shortcut": "Ctrl+Shift+I", "handler": "handle_install_apk", "ws": "apk_installer_memory", "kw": ["cai dat apk", "install apk", "xapk", "sideload", "#46"]},
        {"id": "act_vivo_connect", "title": "Connect & Unlock Vivo V2417A Real Phone", "badge": "Vivo", "shortcut": "Ctrl+Shift+V", "handler": "handle_vivo_connect", "ws": "fleet_overview", "kw": ["vivo", "v2417a", "real phone", "dien thoai that", "secime"]},
        {"id": "act_mirror_scrcpy", "title": "Mirror Device Screen via Scrcpy", "badge": "Fleet", "shortcut": "Ctrl+M", "handler": "handle_mirror_scrcpy", "ws": "fleet_overview", "kw": ["scrcpy", "mirror", "man hinh", "view"]},
        {"id": "act_start_headless", "title": "Start Headless AVD Instance", "badge": "Fleet", "shortcut": "Ctrl+Shift+H", "handler": "handle_start_headless", "ws": "fleet_overview", "kw": ["headless", "avd", "start", "khoi dong"]},
        {"id": "act_group_broadcast", "title": "Toggle Group Broadcast Sync across Farm", "badge": "Fleet", "shortcut": "Ctrl+B", "handler": "handle_group_broadcast", "ws": "fleet_overview", "kw": ["broadcast", "sync", "dong bo", "group"]},
        {"id": "act_tiktok_warmup", "title": "Run TikTok Autonomous Warmup Loop", "badge": "AI Loop", "shortcut": "Ctrl+T", "handler": "handle_tiktok_warmup", "ws": "automation_evolution", "kw": ["tiktok", "luot tiktok", "warmup", "nuoi nick", "video"]},
        {"id": "act_run_10x_evolution", "title": "Run 10x Recursive Self-Evolution (#51-#55)", "badge": "10x Evolution", "shortcut": "Ctrl+E", "handler": "handle_10x_evolution", "ws": "automation_evolution", "kw": ["10x", "evolution", "recursive", "tu tien hoa", "#55"]},
        {"id": "act_run_ui_ux_10x", "title": "Audit & Polish UI/UX 10x Architecture (#56-#65)", "badge": "UI/UX 10x", "shortcut": "Ctrl+U", "handler": "handle_ui_ux_10x", "ws": "automation_evolution", "kw": ["ui ux", "10x", "giao dien", "thiet ke", "bento", "sidebar", "#65"]},
        {"id": "act_solve_captcha", "title": "Trigger 13-Type Zero-Token CAPTCHA Solver", "badge": "CAPTCHA", "shortcut": "Ctrl+Shift+C", "handler": "handle_solve_captcha", "ws": "security_captcha_lab", "kw": ["captcha", "giai captcha", "slider", "grid", "rotation", "#40"]},
        {"id": "act_extract_2fa", "title": "Extract 7-Mode 2FA / OTP Code Now", "badge": "2FA", "shortcut": "Ctrl+Shift+2", "handler": "handle_extract_2fa", "ws": "security_captcha_lab", "kw": ["2fa", "otp", "totp", "sms", "authenticator", "ma xac thuc", "#26"]},
        {"id": "act_open_testbench", "title": "Launch Live Web CAPTCHA & 2FA Testbench", "badge": "Security", "shortcut": "Ctrl+Shift+T", "handler": "handle_open_testbench", "ws": "security_captcha_lab", "kw": ["testbench", "web", "captcha", "2fa", "#31"]},
        {"id": "act_gpu_ocr_scan", "title": "Run RTX 3050 CUDA Zero-Token OCR Scan", "badge": "GPU", "shortcut": "Ctrl+Shift+O", "handler": "handle_gpu_ocr_scan", "ws": "gpu_stream_diagnostics", "kw": ["gpu", "rtx 3050", "ocr", "vision", "cuda", "#43"]},
        {"id": "act_adb_stream_bench", "title": "Benchmark Persistent ADB Frame Stream", "badge": "Stream", "shortcut": "Ctrl+Shift+S", "handler": "handle_adb_stream_bench", "ws": "gpu_stream_diagnostics", "kw": ["stream", "fps", "adb", "benchmark", "#41"]},
        {"id": "act_inspect_cdp", "title": "Attach Android Chrome DevTools (CDP)", "badge": "Diagnostics", "shortcut": "Ctrl+Shift+D", "handler": "handle_inspect_cdp", "ws": "gpu_stream_diagnostics", "kw": ["cdp", "webview", "chrome", "debug", "#38"]},
        {"id": "act_check_wcag", "title": "Run WCAG 2.1 AA Contrast & Layout Audit", "badge": "UI/UX", "shortcut": "Alt+W", "handler": "handle_check_wcag", "ws": "gpu_stream_diagnostics", "kw": ["wcag", "contrast", "ui ux", "accessibility", "#25"]},
        {"id": "act_parse_axml", "title": "Inspect APK Manifest via Pure-Python AXML", "badge": "APK", "shortcut": "Alt+A", "handler": "handle_parse_axml", "ws": "apk_installer_memory", "kw": ["axml", "manifest", "apk", "package", "#49"]},
        {"id": "act_toggle_apk_daemon", "title": "Toggle Always-On APK Watchdog Daemon", "badge": "APK", "shortcut": "Alt+D", "handler": "handle_toggle_apk_daemon", "ws": "apk_installer_memory", "kw": ["daemon", "watchdog", "apk", "auto install", "#50"]},
        {"id": "act_vivo_secime_vault", "title": "Configure Vivo SecIME Install Password Vault", "badge": "Vivo", "shortcut": "Alt+V", "handler": "handle_vivo_secime_vault", "ws": "apk_installer_memory", "kw": ["vivo", "secime", "password", "cai dat apk", "#48"]},
        {"id": "act_goto_fleet", "title": "Go to Workspace: 📱 Fleet & Real Phones", "badge": "Navigation", "shortcut": "Alt+1", "handler": "handle_nav_fleet", "ws": "fleet_overview", "kw": ["workspace", "fleet", "phone", "vivo", "avd"]},
        {"id": "act_goto_automation", "title": "Go to Workspace: 🤖 AI Loops & 10x Evolution", "badge": "Navigation", "shortcut": "Alt+2", "handler": "handle_nav_automation", "ws": "automation_evolution", "kw": ["workspace", "10x", "ai loop", "ui ux", "kanban"]},
        {"id": "act_goto_security", "title": "Go to Workspace: 🔐 Security, 2FA & CAPTCHA", "badge": "Navigation", "shortcut": "Alt+3", "handler": "handle_nav_security", "ws": "security_captcha_lab", "kw": ["workspace", "security", "2fa", "captcha"]},
        {"id": "act_goto_gpu", "title": "Go to Workspace: ⚡ GPU, Stream & Diagnostics", "badge": "Navigation", "shortcut": "Alt+4", "handler": "handle_nav_gpu", "ws": "gpu_stream_diagnostics", "kw": ["workspace", "gpu", "rtx 3050", "stream", "ocr"]},
        {"id": "act_goto_apk", "title": "Go to Workspace: 📦 APK Installer & Memory", "badge": "Navigation", "shortcut": "Alt+5", "handler": "handle_nav_apk", "ws": "apk_installer_memory", "kw": ["workspace", "apk", "cai dat apk", "memory"]},
        {"id": "act_clean_cache", "title": "Clean Storage & App Cache on All Devices", "badge": "Fleet", "shortcut": "Ctrl+Shift+Del", "handler": "handle_clean_cache", "ws": "fleet_overview", "kw": ["clean", "cache", "don rac", "storage"]},
        {"id": "act_export_defect_report", "title": "Export Codebase Memory & Defect Report", "badge": "Memory", "shortcut": "Ctrl+Shift+R", "handler": "handle_export_report", "ws": "apk_installer_memory", "kw": ["report", "memory", "defect", "bao cao"]},
        {"id": "act_open_flow_dag", "title": "Open Visual Flow DAG Editor", "badge": "AI Loop", "shortcut": "Ctrl+G", "handler": "handle_open_dag", "ws": "automation_evolution", "kw": ["dag", "flow", "visual", "pipeline", "#45"]},
        {"id": "act_reboot_adb", "title": "Restart ADB Server & Re-enumerate USB", "badge": "Fleet", "shortcut": "Ctrl+Alt+R", "handler": "handle_reboot_adb", "ws": "fleet_overview", "kw": ["adb", "restart", "usb", "reset"]},
        {"id": "act_spoof_props", "title": "Randomize Device Fingerprint & IMEI", "badge": "Security", "shortcut": "Ctrl+Shift+F", "handler": "handle_spoof_props", "ws": "fleet_overview", "kw": ["fingerprint", "imei", "spoof", "device"]},
        {"id": "act_set_proxy", "title": "Assign SOCKS5 Proxy to Selected Devices", "badge": "Network", "shortcut": "Ctrl+Shift+P", "handler": "handle_set_proxy", "ws": "fleet_overview", "kw": ["proxy", "socks5", "ip", "vpn"]},
        {"id": "act_toggle_dark_theme", "title": "Toggle Dark Mode / High-Contrast Slate Theme", "badge": "UI/UX", "shortcut": "Ctrl+Shift+L", "handler": "handle_toggle_theme", "ws": "automation_evolution", "kw": ["ui ux", "theme", "dark mode", "giao dien"]},
        {"id": "act_open_log_drawer", "title": "Toggle Bottom Collapsible Log Drawer", "badge": "Diagnostics", "shortcut": "Ctrl+`", "handler": "handle_toggle_logs", "ws": "gpu_stream_diagnostics", "kw": ["log", "console", "drawer", "ui ux"]},
        {"id": "act_stop_all_tasks", "title": "Emergency Stop All Running Phone Tasks", "badge": "Safety", "shortcut": "Esc", "handler": "handle_emergency_stop", "ws": "fleet_overview", "kw": ["stop", "kill", "dung lai", "emergency"]},
    ]

    def __init__(self) -> None:
        self._entries: List[CommandPaletteEntry] = self._build_index()

    def _build_index(self) -> List[CommandPaletteEntry]:
        entries: List[CommandPaletteEntry] = []

        # 1. Index all 65 Subagents (#1..#65)
        for sa_id in range(1, 66):
            meta = self.SUBAGENT_CATALOG[sa_id]
            entries.append(
                CommandPaletteEntry(
                    command_id=f"subagent_{sa_id:02d}",
                    title=f"Subagent #{sa_id}: {meta['name']}",
                    category_badge=f"Subagent #{sa_id}",
                    shortcut_hint=f"#{sa_id}",
                    handler_name=f"invoke_subagent_{sa_id:02d}",
                    workspace_id=meta["ws"],
                    subagent_id=sa_id,
                    keywords=[f"#{sa_id}", f"subagent {sa_id}", f"agent {sa_id}"] + list(meta["kw"]),
                )
            )

        # 2. Index 32+ Quick Actions
        for act in self.QUICK_ACTIONS:
            entries.append(
                CommandPaletteEntry(
                    command_id=act["id"],
                    title=act["title"],
                    category_badge=act["badge"],
                    shortcut_hint=act["shortcut"],
                    handler_name=act["handler"],
                    workspace_id=act["ws"],
                    subagent_id=None,
                    keywords=list(act["kw"]),
                )
            )
        return entries

    @property
    def total_indexed_commands(self) -> int:
        """Total commands in the palette (65 Subagents + 32 Quick Actions = 97)."""
        return len(self._entries)

    def search_commands(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """
        Fast, zero-token fuzzy search across all 65 Subagents and 30+ Quick Actions.

        Scores exact subagent number (`#46`, `#55`, `#65`), exact prefix, substring match,
        token overlap, and Vietnamese/English alias matching (`cai dat apk`, `vivo`, `10x`,
        `ui ux`, `tiktok`, `2fa`, `captcha`).
        """
        limit = max(1, int(limit))
        norm_q = _strip_accents(query.strip())

        if not norm_q:
            return [self._serialize_entry(e, score=100.0) for e in self._entries[:limit]]

        q_tokens = [tok for tok in norm_q.replace("/", " ").replace("-", " ").split() if tok]
        scored: List[tuple[float, int, CommandPaletteEntry]] = []

        for idx, entry in enumerate(self._entries):
            score = self._score_entry(entry, norm_q, q_tokens)
            if score > 0.0:
                scored.append((score, -idx, entry))

        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [self._serialize_entry(entry, score=round(score, 2)) for score, _, entry in scored[:limit]]

    @staticmethod
    def _score_entry(
        entry: CommandPaletteEntry,
        norm_q: str,
        q_tokens: List[str],
    ) -> float:
        title_norm = _strip_accents(entry.title)
        badge_norm = _strip_accents(entry.category_badge)
        kw_norms = [_strip_accents(k) for k in entry.keywords]
        haystack = " ".join([title_norm, badge_norm, entry.command_id.lower()] + kw_norms)

        score = 0.0

        # Direct subagent number check (e.g. "#46", "46", "#65")
        if entry.subagent_id is not None:
            sa_tag = f"#{entry.subagent_id}"
            if norm_q == sa_tag or norm_q == str(entry.subagent_id):
                score += 250.0
            elif sa_tag in norm_q.split():
                score += 180.0

        # Exact keyword match
        for kw in kw_norms:
            if norm_q == kw:
                score += 160.0
            elif kw.startswith(norm_q):
                score += 95.0
            elif norm_q in kw:
                score += 65.0

        # Title prefix / substring match
        if title_norm.startswith(norm_q):
            score += 120.0
        elif norm_q in title_norm:
            score += 80.0

        # Multi-token intersection scoring
        if q_tokens:
            matched_tokens = 0
            for tok in q_tokens:
                if entry.subagent_id is not None and tok == f"#{entry.subagent_id}":
                    matched_tokens += 1
                    score += 90.0
                elif any(tok == kw for kw in kw_norms):
                    matched_tokens += 1
                    score += 45.0
                elif tok in haystack:
                    matched_tokens += 1
                    score += 30.0
            if matched_tokens == len(q_tokens):
                score += 50.0
            elif matched_tokens == 0:
                return 0.0

        return score

    @staticmethod
    def _serialize_entry(entry: CommandPaletteEntry, score: float) -> Dict[str, Any]:
        return {
            "command_id": entry.command_id,
            "title": entry.title,
            "category_badge": entry.category_badge,
            "shortcut_hint": entry.shortcut_hint,
            "handler_name": entry.handler_name,
            "workspace_id": entry.workspace_id,
            "subagent_id": entry.subagent_id,
            "keywords": list(entry.keywords),
            "score": score,
        }

    def enforce_progressive_disclosure(
        self,
        toolbar_actions: List[Dict[str, Any]],
        max_visible_primary: int = 1,
        max_visible_secondary: int = 3,
    ) -> Dict[str, Any]:
        """
        Split a cluttered N-button toolbar into:
          - `primary_cta`: at most `max_visible_primary` (default 1) Primary CTA button
          - `secondary_buttons`: at most `max_visible_secondary` (default 3) Secondary buttons
          - `overflow_drawer_items`: all remaining actions moved into the `⋯ More / Ctrl+K` drawer
        Guarantees zero visual button clutter across all headers and device bars.
        """
        max_pri = max(0, int(max_visible_primary))
        max_sec = max(0, int(max_visible_secondary))

        if not toolbar_actions:
            return {
                "primary_cta": [],
                "secondary_buttons": [],
                "overflow_drawer_items": [],
                "total_input_actions": 0,
                "visible_button_count": 0,
                "overflow_count": 0,
                "command_palette_shortcut": self.SHORTCUT_TRIGGER,
                "is_clutter_free": True,
            }

        # Sort only if explicit priority is given while preserving stable order
        indexed = list(enumerate(toolbar_actions))
        explicit_primaries = [
            item for item in indexed if bool(item[1].get("is_primary", False))
        ]
        others = [
            item for item in indexed if not bool(item[1].get("is_primary", False))
        ]
        ordered = [act for _, act in (explicit_primaries + others)]

        primary_cta = ordered[:max_pri]
        secondary_buttons = ordered[max_pri : max_pri + max_sec]
        overflow_drawer_items = ordered[max_pri + max_sec :]

        visible_count = len(primary_cta) + len(secondary_buttons)
        return {
            "primary_cta": primary_cta,
            "secondary_buttons": secondary_buttons,
            "overflow_drawer_items": overflow_drawer_items,
            "total_input_actions": len(toolbar_actions),
            "visible_button_count": visible_count,
            "overflow_count": len(overflow_drawer_items),
            "command_palette_shortcut": self.SHORTCUT_TRIGGER,
            "is_clutter_free": visible_count <= (max_pri + max_sec),
        }


# ==============================================================================
# ENGINE #60: BentoDeviceCardAndSparklineEngine
# ==============================================================================


class BentoDeviceCardAndSparklineEngine:
    """
    Engine #60: Bento Device Card & Telemetry Sparkline Renderer.

    Inspired by `SonicCloudOrg/sonic-client`, `OpenSTF`, and `Vercel Analytics`.
    Replaces cramped 5-rainbow-button device rows with clean Bento cards featuring:
      - `first_read_title` (e.g. `"Vivo V2417A (Physical)"` or `"Pixel 6 AVD #1"`)
      - `status_pill` (`"ONLINE • READY"`, semantic color `#10b981`)
      - `primary_action` (single primary button: `"Mirror Scrcpy"` or `"Start Headless"`)
      - `secondary_icon_actions` (compact icon buttons instead of 5 full-width rainbow buttons)
      - `sparkline_svg_points` and Unicode sparkline (`"▂▃▄▅▆▇▆▅"`) for CPU/RAM/FPS/Battery.
    """

    UNICODE_TICKS = "▁▂▃▄▅▆▇█"

    STATUS_PALETTE: Dict[str, Dict[str, str]] = {
        "online": {"label": "ONLINE • READY", "color": "#10b981", "bg": "rgba(16, 185, 129, 0.14)"},
        "busy": {"label": "ONLINE • BUSY", "color": "#38bdf8", "bg": "rgba(56, 189, 248, 0.14)"},
        "installing": {"label": "ONLINE • INSTALLING APK", "color": "#8b5cf6", "bg": "rgba(139, 92, 246, 0.14)"},
        "warning": {"label": "WARNING • THERMAL/AUTH", "color": "#f59e0b", "bg": "rgba(245, 158, 11, 0.14)"},
        "offline": {"label": "OFFLINE • STOPPED", "color": "#64748b", "bg": "rgba(100, 116, 139, 0.14)"},
        "error": {"label": "ERROR • DISCONNECTED", "color": "#ef4444", "bg": "rgba(239, 68, 68, 0.14)"},
    }

    def render_unicode_sparkline(self, values: List[float]) -> str:
        """Render a compact 8-level Unicode sparkline (e.g. `'▂▃▄▅▆▇▆▅'`) from telemetry samples."""
        if not values:
            return "▁▁▁▁▁▁▁▁"
        clean = [float(v) for v in values]
        lo = min(clean)
        hi = max(clean)
        span = hi - lo
        if span <= 1e-9:
            mid_idx = min(len(self.UNICODE_TICKS) - 1, max(0, int(round((lo / 100.0) * 7))))
            return self.UNICODE_TICKS[mid_idx] * len(clean)

        chars: List[str] = []
        max_tick = len(self.UNICODE_TICKS) - 1
        for val in clean:
            norm = (val - lo) / span
            tick_idx = int(round(norm * max_tick))
            tick_idx = max(0, min(max_tick, tick_idx))
            chars.append(self.UNICODE_TICKS[tick_idx])
        return "".join(chars)

    def render_svg_sparkline_points(
        self,
        values: List[float],
        width: int = 120,
        height: int = 28,
        padding: int = 2,
    ) -> str:
        """Compute SVG `<polyline points="...">` string for smooth Vercel-style telemetry sparklines."""
        if not values:
            y_mid = height / 2.0
            return f"0,{y_mid:.1f} {width},{y_mid:.1f}"

        clean = [float(v) for v in values]
        if len(clean) == 1:
            clean = [clean[0], clean[0]]

        lo = min(clean)
        hi = max(clean)
        span = hi - lo if (hi - lo) > 1e-9 else 1.0
        usable_w = max(1.0, float(width - 2 * padding))
        usable_h = max(1.0, float(height - 2 * padding))

        pts: List[str] = []
        n = len(clean)
        for i, val in enumerate(clean):
            x = padding + (i / float(n - 1)) * usable_w
            norm = (val - lo) / span if (hi - lo) > 1e-9 else 0.5
            y = padding + (1.0 - norm) * usable_h
            pts.append(f"{x:.1f},{y:.1f}")
        return " ".join(pts)

    def build_bento_device_card_model(self, device_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw device state dict into a clean Bento Device Card view-model.
        """
        serial = str(device_info.get("serial", "emulator-5554"))
        model_name = str(device_info.get("model", "")).strip()
        is_physical = bool(
            device_info.get("is_physical", False)
            or ("vivo" in model_name.lower())
            or ("v2417a" in model_name.lower())
            or (not serial.startswith("emulator-") and not serial.startswith("avd-"))
        )
        raw_status = str(device_info.get("status", "online")).lower().strip()
        status_meta = self.STATUS_PALETTE.get(raw_status, self.STATUS_PALETTE["online"])

        if not model_name:
            model_name = "Vivo V2417A" if is_physical else "Pixel 6 AVD #1"

        if is_physical and "(Physical)" not in model_name:
            first_read_title = f"{model_name} (Physical)"
        else:
            first_read_title = model_name

        is_online = raw_status in ("online", "busy", "installing", "ready")
        if is_online:
            primary_action = {
                "action_id": "mirror_scrcpy",
                "label": "Mirror Scrcpy",
                "icon": "🖥️",
                "style": "primary_accent",
                "serial": serial,
            }
        else:
            primary_action = {
                "action_id": "start_headless",
                "label": "Start Headless",
                "icon": "▶️",
                "style": "primary_emerald",
                "serial": serial,
            }

        # Compact icon-only secondary actions instead of 5 full-width rainbow buttons
        secondary_icon_actions = [
            {"action_id": "install_apk", "icon": "📦", "tooltip": "Install APK (#46)", "serial": serial},
            {"action_id": "open_shell", "icon": "⌨️", "tooltip": "ADB Shell / Log Drawer", "serial": serial},
            {"action_id": "more_menu", "icon": "⋯", "tooltip": "More Actions (Ctrl+K)", "serial": serial},
        ]

        cpu_series = list(device_info.get("cpu_history", [22, 28, 35, 42, 38, 50, 46, 34]))
        fps_series = list(device_info.get("fps_history", [58, 60, 60, 59, 60, 60, 59, 60]))
        ram_pct = float(device_info.get("ram_pct", 48.0))
        battery_pct = int(device_info.get("battery_pct", 92))
        fps_current = int(fps_series[-1]) if fps_series else 60

        return {
            "serial": serial,
            "is_physical": is_physical,
            "first_read_title": first_read_title,
            "status_pill": {
                "text": status_meta["label"],
                "color": status_meta["color"],
                "background": status_meta["bg"],
                "raw_status": raw_status,
            },
            "primary_action": primary_action,
            "secondary_icon_actions": secondary_icon_actions,
            "sparkline_unicode": self.render_unicode_sparkline(cpu_series),
            "sparkline_svg_points": self.render_svg_sparkline_points(cpu_series),
            "fps_sparkline_unicode": self.render_unicode_sparkline(fps_series),
            "telemetry_summary": {
                "cpu_current_pct": float(cpu_series[-1]) if cpu_series else 0.0,
                "ram_pct": ram_pct,
                "fps": fps_current,
                "battery_pct": battery_pct,
            },
            "rainbow_button_clutter_eliminated": True,
        }
