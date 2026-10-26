"""
Always-On Install Daemon & CLI Subagent (Subagent #50)
Wraps `AlwaysOnInstallDaemon` and `MemoryManager` to provide zero-token background
APK installation popup guarding, heartbeat health telemetry, and 1-click CLI execution.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager
from core.always_on_install_daemon import AlwaysOnInstallDaemon


class AlwaysOnInstallDaemonAndCLISubagent:
    """
    Subagent #50: Manages per-device `AlwaysOnInstallDaemon` instances, monitors
    daemon heartbeats, and executes 1-click APK installations with automatic OEM
    security popup & risk checkbox dismissal.
    """

    SUBAGENT_ID = 50
    SUBAGENT_NAME = "AlwaysOnInstallDaemonAndCLISubagent"

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
        default_serial: str = "10CF5L0TYL00312",
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.default_serial = default_serial
        self.daemons: Dict[str, AlwaysOnInstallDaemon] = {}

    def get_or_create_daemon(
        self,
        serial: Optional[str] = None,
        poll_interval_sec: float = 0.8,
        max_idle_timeout_sec: float = 300.0,
    ) -> AlwaysOnInstallDaemon:
        """Retrieve or initialize an `AlwaysOnInstallDaemon` for the target device serial."""
        target_serial = serial or self.default_serial
        if target_serial not in self.daemons:
            self.daemons[target_serial] = AlwaysOnInstallDaemon(
                serial=target_serial,
                adb=self.adb,
                poll_interval_sec=poll_interval_sec,
                max_idle_timeout_sec=max_idle_timeout_sec,
            )
        return self.daemons[target_serial]

    def start_daemon(
        self,
        serial: Optional[str] = None,
        poll_interval_sec: float = 0.8,
        max_idle_timeout_sec: float = 300.0,
        force_full_scan: bool = False,
    ) -> Dict[str, Any]:
        """Start the Always-On Install Watcher Daemon on `serial`."""
        daemon = self.get_or_create_daemon(
            serial=serial,
            poll_interval_sec=poll_interval_sec,
            max_idle_timeout_sec=max_idle_timeout_sec,
        )
        res = daemon.start(force_full_scan=force_full_scan)
        self.memory.remember(
            key=f"always_on_daemon_start_{daemon.serial}_{int(time.time() * 1000)}",
            value=res,
            tags=["always_on_daemon", "apk_install", daemon.serial],
            category="always_on_install_daemon",
        )
        return res

    def stop_daemon(self, serial: Optional[str] = None) -> Dict[str, Any]:
        """Stop the Always-On Install Watcher Daemon on `serial`."""
        daemon = self.get_or_create_daemon(serial=serial)
        res = daemon.stop()
        self.memory.remember(
            key=f"always_on_daemon_stop_{daemon.serial}_{int(time.time() * 1000)}",
            value=res,
            tags=["always_on_daemon", "apk_install", daemon.serial],
            category="always_on_install_daemon",
        )
        return res

    def run_single_tick(
        self,
        serial: Optional[str] = None,
        force_full_scan: bool = False,
    ) -> Dict[str, Any]:
        """Execute a single watcher tick on `serial`."""
        daemon = self.get_or_create_daemon(serial=serial)
        return daemon.run_single_tick(force_full_scan=force_full_scan)

    def get_health_status(self, serial: Optional[str] = None) -> Dict[str, Any]:
        """Inspect daemon health and heartbeat status for `serial`."""
        daemon = self.get_or_create_daemon(serial=serial)
        return daemon.get_health_status()

    def install_apk(
        self,
        apk_path: str,
        serial: Optional[str] = None,
        extra_flags: Optional[List[str]] = None,
        timeout_sec: int = 90,
    ) -> Dict[str, Any]:
        """
        Install an APK using `AlwaysOnInstallDaemon.install_apk_with_daemon` and
        persist installation telemetry in `MemoryManager`.
        """
        daemon = self.get_or_create_daemon(serial=serial)
        res = daemon.install_apk_with_daemon(
            apk_path=apk_path,
            extra_flags=extra_flags,
            timeout_sec=timeout_sec,
        )
        self.memory.remember(
            key=f"always_on_install_{daemon.serial}_{int(time.time() * 1000)}",
            value=res,
            tags=["always_on_daemon", "apk_install", daemon.serial],
            category="always_on_install_daemon",
            metadata={
                "serial": daemon.serial,
                "apk_path": apk_path,
                "success": res.get("success", False),
                "popups_dismissed": res.get("popups_dismissed", 0),
                "checkboxes_ticked": res.get("checkboxes_ticked", 0),
            },
        )
        return res


if __name__ == "__main__":
    agent = AlwaysOnInstallDaemonAndCLISubagent()
    print(f"{agent.SUBAGENT_NAME} (#{agent.SUBAGENT_ID}) initialized.")
