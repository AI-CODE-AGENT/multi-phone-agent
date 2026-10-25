"""
Vivo OriginOS Deep Optimizer Subagent (Subagent #32)
Specialized hardware & OS optimizer for Vivo / OriginOS devices (such as Vivo V2417A / PD2417
running OriginOS 6 at 1260x2800, 560 dpi). Performs deep telemetry inspection, touch inset
calibration, USB awake & keyguard dismissal, and OriginOS system interception detection/bypass.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager
from core.vivo_originos_engine import VivoOriginOSEngine


class VivoOriginOSDeepOptimizerSubagent:
    """
    Subagent #32: Deep hardware & OS telemetry inspector and runtime optimizer
    for Vivo OriginOS devices (V2417A / PD2417 @ 1260x2800, 560 dpi) and other OEM skins.
    """

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.engine = VivoOriginOSEngine()

    def inspect_and_optimize_vivo_device(
        self,
        serial: str,
        keep_awake: bool = True,
        dismiss_keyguard: bool = True
    ) -> Dict[str, Any]:
        """
        Query Vivo/OriginOS hardware & window properties, apply stay-awake and keyguard
        optimizations, dump UI hierarchy XML to inspect & handle Vivo security/USB popups,
        and persist the telemetry profile into MemoryManager.
        """
        model_prop = self.adb.shell(serial, "getprop ro.product.model")
        os_prop = self.adb.shell(serial, "getprop ro.vivo.os.build.display.id")
        device_prop = self.adb.shell(serial, "getprop ro.product.device")
        size_raw = self.adb.shell(serial, "wm size")
        density_raw = self.adb.shell(serial, "wm density")
        window_raw = self.adb.shell(serial, "dumpsys window")

        props_combined = (
            f"[ro.product.model]: [{model_prop.strip()}]\n"
            f"[ro.product.device]: [{device_prop.strip()}]\n"
            f"[ro.vivo.os.build.display.id]: [{os_prop.strip()}]"
        )

        telemetry = self.engine.parse_originos_telemetry(
            props_raw=props_combined,
            size_raw=size_raw,
            density_raw=density_raw,
            window_raw=window_raw
        )

        optimizations_applied: List[str] = []
        if keep_awake:
            self.adb.shell(serial, "svc power stayon usb")
            self.adb.shell(serial, "input keyevent 224")
            optimizations_applied.extend(["svc power stayon usb", "input keyevent 224"])

        if dismiss_keyguard:
            self.adb.shell(serial, "wm dismiss-keyguard")
            optimizations_applied.append("wm dismiss-keyguard")

        ui_xml = ""
        if hasattr(self.adb, "dump_ui_hierarchy"):
            try:
                ui_xml = self.adb.dump_ui_hierarchy(serial) or ""
            except Exception:
                ui_xml = ""

        interception_check = self.engine.detect_vivo_system_interceptions(ui_xml)

        report = {
            "status": "VIVO_ORIGINOS_OPTIMIZED",
            "serial": serial,
            "telemetry": telemetry,
            "interception_check": interception_check,
            "optimizations_applied": optimizations_applied,
        }

        if self.memory is not None and hasattr(self.memory, "remember"):
            try:
                self.memory.remember(
                    key=f"vivo_originos_opt_{serial}_{int(time.time() * 1000)}",
                    value=report,
                    tags=["vivo", "originos", "optimizer", serial],
                    category="vivo_originos_optimizer",
                    metadata={
                        "serial": serial,
                        "model": telemetry.get("model"),
                        "os_display_id": telemetry.get("os_display_id"),
                        "interception_detected": interception_check.get("interception_detected", False),
                    }
                )
            except Exception:
                pass

        return report


if __name__ == "__main__":
    subagent = VivoOriginOSDeepOptimizerSubagent()
    print("VivoOriginOSDeepOptimizerSubagent (#32) ready.")
