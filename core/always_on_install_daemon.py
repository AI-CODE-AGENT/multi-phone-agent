"""
Always-On Background APK Install Watcher Daemon (AMAF Iteration #7)
Inspired by openatx/uiautomator2 background watcher with a fast-path foreground window filter,
heartbeat telemetry, configurable idle timeout guard, and multi-OEM popup/checkbox auto-dismissal
(Vivo OriginOS / FuntouchOS, Xiaomi HyperOS / MIUI, OPPO / Realme ColorOS, Samsung OneUI, Play Protect).
"""

import os
import sys
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.oem_popup_watcher import OEMPopupWatcher

try:
    from core.universal_apk_installer_engine import UniversalAPKInstallerEngine
except ImportError:
    UniversalAPKInstallerEngine = None  # type: ignore

try:
    from core.sideload_source_guard_engine import SideloadSourceGuardEngine
except ImportError:
    SideloadSourceGuardEngine = None  # type: ignore


INSTALLER_WINDOW_TOKENS: List[str] = [
    "packageinstaller",
    "vivo.secime",
    "bbk.account",
    "permissioncontroller",
    "permissionmanager",
    "securitycenter",
    "manageexternalsources",
    "packageinterceptactivity",
    "safecenter",
    "appdetail",
    "installstaging",
    "uninstalleractivity",
    "grantpermissionsactivity",
]


class AlwaysOnInstallDaemon:
    """
    Per-device background APK installation & OEM security popup watcher daemon.
    Uses a fast-path `dumpsys window` check before triggering expensive `uiautomator dump`
    calls, tracks real-time heartbeat metrics, and enforces `max_idle_timeout_sec`.
    """

    def __init__(
        self,
        serial: str = "10CF5L0TYL00312",
        adb: Optional[ADBWrapper] = None,
        oem_watcher: Optional[OEMPopupWatcher] = None,
        poll_interval_sec: float = 0.8,
        max_idle_timeout_sec: float = 300.0,
        use_vivo_fallback: bool = True,
    ):
        self.serial = serial
        self.adb = adb or ADBWrapper()
        self.oem_watcher = oem_watcher or OEMPopupWatcher(self.adb)
        self.poll_interval_sec = max(0.05, float(poll_interval_sec))
        self.max_idle_timeout_sec = max(1.0, float(max_idle_timeout_sec))
        self.use_vivo_fallback = use_vivo_fallback

        # Optional sibling engines if present in workspace
        self.installer_engine = (
            UniversalAPKInstallerEngine(self.adb)
            if UniversalAPKInstallerEngine is not None
            else None
        )
        self.sideload_guard = (
            SideloadSourceGuardEngine(self.adb)
            if SideloadSourceGuardEngine is not None
            else None
        )

        # Heartbeat & telemetry tracking
        self.last_heartbeat_ts: float = 0.0
        self.started_at_ts: float = 0.0
        self.last_activity_ts: float = 0.0
        self.polls_completed: int = 0
        self.fast_path_skips: int = 0
        self.popups_dismissed: int = 0
        self.checkboxes_ticked: int = 0
        self.events_log: List[Dict[str, Any]] = []

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def get_foreground_window_info(self) -> str:
        """
        Query the current foreground window / activity via fast `dumpsys window` shell call
        or `adb.get_current_app`.
        """
        try:
            if hasattr(self.adb, "get_foreground_package"):
                pkg = self.adb.get_foreground_package(self.serial)
                if pkg:
                    return str(pkg)
        except Exception:
            pass

        out = self.adb.shell(
            self.serial,
            "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'",
            timeout=5,
        )
        return (out or "").strip()

    def is_installer_or_security_window(self, window_info: str) -> bool:
        """
        Return True if `window_info` matches any known Android package installer,
        OEM security center, unknown-sources settings, or permission dialog token.
        """
        if not window_info:
            return False
        lower_info = window_info.lower()
        return any(token in lower_info for token in INSTALLER_WINDOW_TOKENS)

    def run_single_tick(self, force_full_scan: bool = False) -> Dict[str, Any]:
        """
        Execute a single watcher tick:
        1. Update `last_heartbeat_ts` and `polls_completed`.
        2. Check foreground window via fast path unless `force_full_scan=True`.
        3. When matched (or forced), invoke `OEMPopupWatcher` (and optional `SideloadSourceGuardEngine`)
           to auto-tick risk checkboxes and click confirm buttons.
        """
        now = time.time()
        window_info = self.get_foreground_window_info()
        matched_window = self.is_installer_or_security_window(window_info)

        with self._lock:
            self.last_heartbeat_ts = now
            self.polls_completed += 1

        if not force_full_scan and not matched_window:
            with self._lock:
                self.fast_path_skips += 1
            return {
                "status": "FAST_PATH_SKIPPED",
                "serial": self.serial,
                "foreground_window": window_info,
                "heartbeat_ts": now,
                "polls_completed": self.polls_completed,
            }

        # Optional SideloadSourceGuardEngine check if ManageExternalSources is focused
        if (
            self.sideload_guard is not None
            and "manageexternalsources" in window_info.lower()
            and hasattr(self.sideload_guard, "auto_enable_unknown_source_switch")
        ):
            try:
                guard_res = self.sideload_guard.auto_enable_unknown_source_switch(self.serial)
                if guard_res.get("toggled"):
                    with self._lock:
                        self.popups_dismissed += 1
                        self.last_activity_ts = time.time()
                        self.events_log.append(guard_res)
                    return {
                        "status": "SIDELOAD_SWITCH_ENABLED",
                        "serial": self.serial,
                        "foreground_window": window_info,
                        "details": guard_res,
                        "heartbeat_ts": now,
                    }
            except Exception:
                pass

        scan_res = self.oem_watcher.scan_and_dismiss_oem_popup(
            serial=self.serial,
            use_vivo_coordinate_fallback=self.use_vivo_fallback and matched_window,
        )

        status = scan_res.get("status", "NO_POPUP_DETECTED")
        checkbox_ticked = bool(scan_res.get("checkbox_ticked", False))

        with self._lock:
            if checkbox_ticked:
                self.checkboxes_ticked += 1
            if status in ("POPUP_DISMISSED", "POPUP_DISMISSED_FALLBACK"):
                self.popups_dismissed += 1
                self.last_activity_ts = time.time()
                event_entry = {
                    "timestamp": time.time(),
                    "serial": self.serial,
                    "status": status,
                    "matched_label": scan_res.get("matched_label"),
                    "checkbox_ticked": checkbox_ticked,
                    "tapped_coords": scan_res.get("tapped_coords"),
                    "method": scan_res.get("method"),
                    "foreground_window": window_info,
                }
                self.events_log.append(event_entry)

        return {
            "status": status,
            "serial": self.serial,
            "foreground_window": window_info,
            "checkbox_ticked": checkbox_ticked,
            "matched_label": scan_res.get("matched_label"),
            "tapped_coords": scan_res.get("tapped_coords"),
            "heartbeat_ts": now,
            "polls_completed": self.polls_completed,
        }

    def start(self, force_full_scan: bool = False) -> Dict[str, Any]:
        """Start the background watcher daemon thread for `self.serial`."""
        if self._thread is not None and self._thread.is_alive():
            return {
                "status": "ALREADY_RUNNING",
                "serial": self.serial,
                "poll_interval_sec": self.poll_interval_sec,
                "max_idle_timeout_sec": self.max_idle_timeout_sec,
            }

        self._stop_event.clear()
        now = time.time()
        with self._lock:
            self.started_at_ts = now
            self.last_heartbeat_ts = now
            self.last_activity_ts = now

        def _daemon_loop():
            while not self._stop_event.is_set():
                try:
                    self.run_single_tick(force_full_scan=force_full_scan)
                except Exception:
                    with self._lock:
                        self.last_heartbeat_ts = time.time()

                # Idle timeout guard
                idle_sec = time.time() - self.last_activity_ts
                if idle_sec >= self.max_idle_timeout_sec:
                    self._stop_event.set()
                    break

                self._stop_event.wait(self.poll_interval_sec)

        self._thread = threading.Thread(
            target=_daemon_loop,
            name=f"AlwaysOnInstallDaemon-{self.serial}",
            daemon=True,
        )
        self._thread.start()

        return {
            "status": "DAEMON_STARTED",
            "serial": self.serial,
            "poll_interval_sec": self.poll_interval_sec,
            "max_idle_timeout_sec": self.max_idle_timeout_sec,
        }

    def stop(self) -> Dict[str, Any]:
        """Stop the background watcher daemon thread and return telemetry summary."""
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._thread = None

        return {
            "status": "DAEMON_STOPPED",
            "serial": self.serial,
            "polls_completed": self.polls_completed,
            "fast_path_skips": self.fast_path_skips,
            "popups_dismissed": self.popups_dismissed,
            "checkboxes_ticked": self.checkboxes_ticked,
            "events_count": len(self.events_log),
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Return daemon liveness, heartbeat freshness, and popup counters."""
        with self._lock:
            running = self._thread is not None and self._thread.is_alive()
            now = time.time()
            heartbeat_age_sec = (
                round(max(0.0, now - self.last_heartbeat_ts), 3)
                if self.last_heartbeat_ts > 0
                else None
            )
            idle_sec = (
                round(max(0.0, now - self.last_activity_ts), 3)
                if self.last_activity_ts > 0
                else 0.0
            )
            return {
                "serial": self.serial,
                "running": running,
                "healthy": running and (
                    heartbeat_age_sec is not None
                    and heartbeat_age_sec < max(5.0, self.poll_interval_sec * 4)
                ),
                "last_heartbeat_ts": self.last_heartbeat_ts,
                "heartbeat_age_sec": heartbeat_age_sec,
                "idle_sec": idle_sec,
                "max_idle_timeout_sec": self.max_idle_timeout_sec,
                "polls_completed": self.polls_completed,
                "fast_path_skips": self.fast_path_skips,
                "popups_dismissed": self.popups_dismissed,
                "checkboxes_ticked": self.checkboxes_ticked,
                "events_log": list(self.events_log),
            }

    def install_apk_with_daemon(
        self,
        apk_path: str,
        extra_flags: Optional[List[str]] = None,
        timeout_sec: int = 90,
    ) -> Dict[str, Any]:
        """
        Run a guarded APK installation with the Always-On Daemon active at high frequency,
        automatically ticking Vivo/Xiaomi/OPPO risk checkboxes and clicking confirm buttons.
        """
        if not os.path.exists(apk_path):
            return {
                "success": False,
                "serial": self.serial,
                "apk_path": apk_path,
                "error": f"APK file not found: {apk_path}",
                "popups_dismissed": 0,
                "checkboxes_ticked": 0,
            }

        before_popups = self.popups_dismissed
        before_checkboxes = self.checkboxes_ticked
        was_running = self._thread is not None and self._thread.is_alive()
        saved_interval = self.poll_interval_sec

        if not was_running:
            self.poll_interval_sec = min(self.poll_interval_sec, 0.35)
            self.start(force_full_scan=True)

        start_ts = time.time()
        try:
            flags = extra_flags if extra_flags is not None else ["-r", "-g"]
            cmd_args = ["install"] + list(flags) + [apk_path]
            code, out, err = self.adb.run_device_cmd(
                self.serial,
                cmd_args,
                timeout=timeout_sec,
            )
            combined = f"{out}\n{err}".strip()
            success = code == 0 and "Success" in combined

            # Fallback retry without -g if older Android / OEM rejects -g during install
            if not success and "-g" in flags and ("Unknown option" in combined or "SecurityException" in combined):
                fallback_flags = [f for f in flags if f != "-g"]
                code, out, err = self.adb.run_device_cmd(
                    self.serial,
                    ["install"] + fallback_flags + [apk_path],
                    timeout=timeout_sec,
                )
                combined = f"{out}\n{err}".strip()
                success = code == 0 and "Success" in combined
        finally:
            if not was_running:
                self.stop()
                self.poll_interval_sec = saved_interval

        elapsed_sec = round(time.time() - start_ts, 2)
        return {
            "success": success,
            "serial": self.serial,
            "apk_path": apk_path,
            "elapsed_sec": elapsed_sec,
            "popups_dismissed": max(0, self.popups_dismissed - before_popups),
            "checkboxes_ticked": max(0, self.checkboxes_ticked - before_checkboxes),
            "output": combined,
            "events_log": list(self.events_log),
        }
