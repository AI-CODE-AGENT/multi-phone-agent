"""
Sideload Source & Runtime Permission Guard Subagent (Subagent #47).
Iteration #4 of the 10x Recursive Evolution Plan.

Wraps `SideloadSourceGuardEngine` to pre-authorize sideload host packages,
inspect and toggle `ManageExternalSourcesActivity` ("Allow from this source" /
"Cho phép từ nguồn này") screens, and auto-grant runtime and special appops permissions
with ZERO AI TOKENS at runtime.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.sideload_source_guard_engine import SideloadSourceGuardEngine


class SideloadSourceAndPermissionSubagent:
    """
    Subagent #47: Sideload Source Permission Guard & Runtime Auto-Grant Subagent.
    """

    SUBAGENT_ID = 47
    SUBAGENT_NAME = "SideloadSourceAndPermissionSubagent"

    def __init__(
        self,
        adb_wrapper: Any = None,
        engine: SideloadSourceGuardEngine | None = None,
        tap_settle_delay_s: float = 0.25,
    ) -> None:
        self.adb_wrapper = adb_wrapper
        self.engine = engine or SideloadSourceGuardEngine(tap_settle_delay_s=tap_settle_delay_s)
        self.history: list[dict[str, Any]] = []

    def _resolve_adb(self, adb_wrapper: Any = None) -> Any:
        target = adb_wrapper if adb_wrapper is not None else self.adb_wrapper
        if target is None:
            raise ValueError("An adb_wrapper instance must be provided to SideloadSourceAndPermissionSubagent.")
        return target

    def ensure_sideload_ready(
        self,
        adb_wrapper: Any = None,
        source_packages: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Pre-authorizes sideload host packages (`REQUEST_INSTALL_PACKAGES allow` on `--user 0`)
        so APK installations from Chrome, Zalo, File Explorer, Vivo Browser, or PackageInstaller
        do not get blocked by `ManageExternalSourcesActivity`.
        """
        adb = self._resolve_adb(adb_wrapper)
        result = self.engine.pre_authorize_sideload_sources(adb, source_packages=source_packages)
        record = {
            "subagent_id": self.SUBAGENT_ID,
            "operation": "ensure_sideload_ready",
            **result,
        }
        self.history.append(record)
        return record

    def inspect_and_toggle_sideload_screen(
        self,
        adb_wrapper: Any = None,
        xml_str: str | None = None,
    ) -> dict[str, Any]:
        """
        Inspects the current UI hierarchy (or provided `xml_str`) for the
        "Install unknown apps" / "Cho phép từ nguồn này" screen, toggles the switch
        if currently disabled, and sends `KEYCODE_BACK` (4) to return to the installer flow.
        """
        if xml_str is not None and adb_wrapper is None and self.adb_wrapper is None:
            # Pure XML inspection fallback if no adb_wrapper is attached
            analysis = self.engine.analyze_sideload_settings_xml(xml_str)
            record = {
                "subagent_id": self.SUBAGENT_ID,
                "operation": "inspect_and_toggle_sideload_screen",
                "handled": False,
                "action": "analyzed_only",
                "tapped": False,
                "back_sent": False,
                "analysis": analysis,
            }
            self.history.append(record)
            return record

        adb = self._resolve_adb(adb_wrapper)
        result = self.engine.handle_sideload_settings_screen(adb, xml_str=xml_str)
        record = {
            "subagent_id": self.SUBAGENT_ID,
            "operation": "inspect_and_toggle_sideload_screen",
            **result,
        }
        self.history.append(record)
        return record

    def grant_all_package_permissions(
        self,
        package_name: str,
        adb_wrapper: Any = None,
        permissions: list[str] | None = None,
        include_special_appops: bool = True,
    ) -> dict[str, Any]:
        """
        Auto-grants runtime permissions (`pm grant --user 0 <pkg> <perm>`) and
        special appops (`SYSTEM_ALERT_WINDOW`, `MANAGE_EXTERNAL_STORAGE`) for `package_name`.
        """
        adb = self._resolve_adb(adb_wrapper)
        result = self.engine.auto_grant_runtime_permissions(
            adb,
            package_name=package_name,
            permissions=permissions,
            include_special_appops=include_special_appops,
        )
        record = {
            "subagent_id": self.SUBAGENT_ID,
            "operation": "grant_all_package_permissions",
            **result,
        }
        self.history.append(record)
        return record

    def get_status(self) -> dict[str, Any]:
        """Return Subagent #47 operational telemetry and engine counters."""
        return {
            "subagent_id": self.SUBAGENT_ID,
            "subagent_name": self.SUBAGENT_NAME,
            "zero_ai_tokens": True,
            "stats": dict(self.engine.stats),
            "history_count": len(self.history),
            "default_sideload_sources": list(self.engine.DEFAULT_SIDELOAD_SOURCES),
        }
