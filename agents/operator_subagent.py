"""
Operator Subagent
Executes plan milestones with precision, manages mock OTP auto-delivery, and coordinates hardware events.
"""

import sys
import time
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.hardware_simulator import HardwareSimulator
from core.mock_otp_service import MockOTPService
from agents.device_lock_manager import DeviceLockManager


class OperatorSubagent:
    """Device Operator that interacts with ADB and integrates mock hardware/telecom events."""

    def __init__(
        self,
        agent_id: str,
        serial: str,
        adb: Optional[ADBWrapper] = None,
        hardware: Optional[HardwareSimulator] = None,
        mock_otp: Optional[MockOTPService] = None,
        lock_mgr: Optional[DeviceLockManager] = None
    ):
        self.agent_id = agent_id
        self.serial = serial
        self.adb = adb or ADBWrapper()
        self.hardware = hardware or HardwareSimulator(self.adb)
        self.mock_otp = mock_otp or MockOTPService(self.hardware)
        self.lock_mgr = lock_mgr or DeviceLockManager()

    def execute_step(self, step: Dict[str, Any], elements: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Execute a single milestone action.
        Returns execution result dictionary with status and metrics.
        """
        action = step.get("action", "").lower()
        start_t = time.time()
        result = {"action": action, "status": "unknown", "detail": ""}

        if action == "launch":
            pkg = step.get("package")
            ok = self.adb.launch_app(self.serial, pkg)
            result["status"] = "success" if ok else "failed"
            result["detail"] = f"Launched {pkg}"
            time.sleep(2.0)

        elif action == "tap":
            locator = step.get("locator", "")
            elems = elements or self.adb.parse_ui_elements(self.adb.dump_ui_hierarchy(self.serial))
            target = self._find_element_by_locator(elems, locator)
            if target and target.get("bounds"):
                c = target["bounds"]
                self.adb.tap(self.serial, c["center_x"], c["center_y"])
                result["status"] = "success"
                result["detail"] = f"Tapped {locator} at ({c['center_x']}, {c['center_y']})"
            else:
                result["status"] = "element_not_found"
                result["detail"] = f"Could not find element matching '{locator}'"

        elif action == "input":
            locator = step.get("locator", "")
            text_val = step.get("text", "")
            elems = elements or self.adb.parse_ui_elements(self.adb.dump_ui_hierarchy(self.serial))
            target = self._find_element_by_locator(elems, locator) if locator else None
            if target and target.get("bounds"):
                c = target["bounds"]
                self.adb.tap(self.serial, c["center_x"], c["center_y"])
                time.sleep(0.3)
            self.adb.input_text(self.serial, text_val)
            result["status"] = "success"
            result["detail"] = f"Entered text '{text_val}' into '{locator}'"

        elif action == "mock_otp_flow":
            phone = step.get("phone", "0941189263")
            # 1. Generate & deliver OTP locally (0 VND carrier cost)
            code = self.mock_otp.generate_otp(phone)
            ok, msg = self.mock_otp.deliver_mock_sms_to_device(self.serial, phone, code)
            time.sleep(1.0)

            # 2. Enter OTP into active input field
            elems = self.adb.parse_ui_elements(self.adb.dump_ui_hierarchy(self.serial))
            otp_input = None
            for e in elems:
                cls_name = e.get("class", "").lower()
                res_id = (e.get("resource_id") or "").lower()
                txt = (e.get("text") or "").lower()
                if "edittext" in cls_name or "otp" in res_id or "code" in res_id or "otp" in txt:
                    otp_input = e
                    break

            if otp_input and otp_input.get("bounds"):
                c = otp_input["bounds"]
                self.adb.tap(self.serial, c["center_x"], c["center_y"])
                time.sleep(0.3)

            self.adb.input_text(self.serial, code)
            result["status"] = "success"
            result["detail"] = f"Delivered & Auto-filled Mock OTP {code} for {phone} (0 VND SMS Cost)"

        elif action == "biometrics":
            ok, msg = self.hardware.touch_fingerprint(self.serial)
            result["status"] = "success" if ok else "failed"
            result["detail"] = f"Biometric fingerprint sensor triggered: {msg}"

        elif action == "gps":
            lat = float(step.get("lat", 10.776889))
            lng = float(step.get("lng", 106.700806))
            ok, msg = self.hardware.set_gps_location(self.serial, lat, lng)
            result["status"] = "success" if ok else "failed"
            result["detail"] = f"GPS set to ({lat}, {lng})"

        elif action == "scroll":
            direction = step.get("direction", "down")
            if direction == "down":
                self.adb.swipe(self.serial, 360, 1100, 360, 400, 350)
            else:
                self.adb.swipe(self.serial, 360, 400, 360, 1100, 350)
            result["status"] = "success"
            result["detail"] = f"Scrolled {direction}"

        result["latency_ms"] = round((time.time() - start_t) * 1000, 1)
        return result

    def _find_element_by_locator(self, elements: List[Dict[str, Any]], locator_pattern: str) -> Optional[Dict[str, Any]]:
        """Match element by exact or regex pipe separated keywords."""
        patterns = [p.strip().lower() for p in locator_pattern.split("|")]
        for el in elements:
            txt = (el.get("text") or "").lower()
            desc = (el.get("content_desc") or "").lower()
            res_id = (el.get("resource_id") or "").lower()

            for pat in patterns:
                if pat == txt or pat in txt or pat in desc or pat in res_id:
                    return el
        return None


if __name__ == "__main__":
    op = OperatorSubagent("Test_Operator", "emulator-5554")
    print("OperatorSubagent initialized.")
