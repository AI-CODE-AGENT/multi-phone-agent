"""
OEM Popup Guard Subagent (Subagent #18)
Autonomous guardian that wraps OEMPopupWatcher and MemoryManager to detect, dismiss,
and remember OEM security / USB installation popups (Vivo OriginOS, Xiaomi HyperOS/MIUI,
OPPO/Realme ColorOS, Samsung OneUI, and Google Play Protect).
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager
from core.oem_popup_watcher import OEMPopupWatcher


class OEMPopupGuardSubagent:
    """
    Subagent #18: Guards real Android devices against blocking OEM security overlays
    and USB APK installation prompts while persisting dismissal telemetry into MemoryManager.
    """

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        watcher: Optional[OEMPopupWatcher] = None,
        memory: Optional[MemoryManager] = None
    ):
        if isinstance(watcher, MemoryManager) and memory is None:
            memory = watcher
            watcher = None
        self.adb = adb or ADBWrapper()
        self.watcher = watcher or OEMPopupWatcher(self.adb)
        self.memory = memory or MemoryManager()

    def guard_device(
        self,
        serial: str,
        use_vivo_fallback: bool = False
    ) -> Dict[str, Any]:
        """
        Scan a target device for OEM security / permission popups, auto-dismiss if found,
        and record the dismissal into MemoryManager.
        """
        res = self.watcher.scan_and_dismiss_oem_popup(
            serial=serial,
            use_vivo_coordinate_fallback=use_vivo_fallback
        )
        if res.get("status") in ("POPUP_DISMISSED", "POPUP_DISMISSED_FALLBACK"):
            self.memory.remember(
                key=f"oem_popup_{serial}_{int(time.time() * 1000)}",
                value=res,
                tags=["oem_popup", "security_dialog", serial, res.get("method", "unknown")],
                category="oem_popup_guard",
                metadata={
                    "serial": serial,
                    "matched_label": res.get("matched_label"),
                    "tapped_coords": res.get("tapped_coords"),
                }
            )
        return res

    def guarded_apk_install(
        self,
        serial: str,
        apk_path: str,
        timeout: int = 90
    ) -> Dict[str, Any]:
        """
        Install an APK on `serial` with background OEM popup auto-confirmation enabled,
        persisting any dismissed dialogs into MemoryManager.
        """
        install_res = self.watcher.install_apk_with_oem_guard(
            serial=serial,
            apk_path=apk_path,
            timeout=timeout
        )
        self.memory.remember(
            key=f"oem_guarded_install_{serial}_{int(time.time())}",
            value=install_res,
            tags=["oem_popup", "apk_install", serial],
            category="oem_popup_guard",
            metadata={
                "serial": serial,
                "apk_path": apk_path,
                "success": install_res.get("success", False),
                "popups_auto_clicked": install_res.get("popups_auto_clicked", 0),
            }
        )
        return install_res


if __name__ == "__main__":
    subagent = OEMPopupGuardSubagent()
    print("OEMPopupGuardSubagent (#18) ready.")
