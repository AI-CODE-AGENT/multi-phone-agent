"""
Autonomous Mobile Testing Agent
Implements Observe-Think-Act-Verify loop with self-healing element resolution and hardware injection.
"""

import time
import os
import sys
import random
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.hardware_simulator import HardwareSimulator
from agents.bug_reporter import BugReporter
from agents.device_lock_manager import DeviceLockManager


class AutonomousAgent:
    def __init__(
        self,
        agent_id: str,
        serial: str,
        adb: Optional[ADBWrapper] = None,
        hardware: Optional[HardwareSimulator] = None,
        reporter: Optional[BugReporter] = None,
        lock_mgr: Optional[DeviceLockManager] = None
    ):
        self.agent_id = agent_id
        self.serial = serial
        self.adb = adb or ADBWrapper()
        self.hardware = hardware or HardwareSimulator(self.adb)
        self.reporter = reporter or BugReporter()
        self.lock_mgr = lock_mgr or DeviceLockManager()

        self.step_history: List[Dict[str, Any]] = []
        self._stop_requested = False

    def stop(self):
        """Signal agent to abort current test execution."""
        self._stop_requested = True

    def find_element(self, elements: List[Dict[str, Any]], query: str) -> Optional[Dict[str, Any]]:
        """
        Self-healing element locator:
        1. Exact text match
        2. Case-insensitive contains text
        3. Content description match
        4. Resource ID match
        """
        q_lower = query.lower()

        # 1. Exact text match
        for el in elements:
            if el.get("text") == query:
                return el

        # 2. Case-insensitive text contains
        for el in elements:
            text = (el.get("text") or "").lower()
            if q_lower in text:
                return el

        # 3. Content description match
        for el in elements:
            desc = (el.get("content_desc") or "").lower()
            if q_lower in desc:
                return el

        # 4. Resource ID contains
        for el in elements:
            res_id = (el.get("resource_id") or "").lower()
            if q_lower in res_id:
                return el

        return None

    def handle_system_dialogs(self, elements: List[Dict[str, Any]]) -> bool:
        """Auto-handle common system permission prompts (Allow, OK, Continue)."""
        permission_keywords = ["allow", "while using the app", "only this time", "ok", "agree", "continue", "accept"]
        for kw in permission_keywords:
            el = self.find_element(elements, kw)
            if el and el.get("bounds"):
                center = el["bounds"]
                self.adb.tap(self.serial, center["center_x"], center["center_y"])
                time.sleep(1.0)
                return True
        return False

    def run_exploration(
        self,
        package_name: str,
        max_steps: int = 25,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Autonomously explore an installed application:
        Discovers screens, inputs forms, clicks interactive buttons, detects crashes.
        """
        self._stop_requested = False
        self.step_history = []

        # Acquire lock
        if not self.lock_mgr.acquire(self.serial, self.agent_id, f"Explore_{package_name}", lease_seconds=600):
            return {"status": "error", "message": f"Device {self.serial} is currently locked by another agent"}

        try:
            # 1. Launch target app
            self.adb.launch_app(self.serial, package_name)
            time.sleep(3.0)

            visited_signatures = set()
            crash_detected = False
            crash_report_path = None

            for step_num in range(1, max_steps + 1):
                if self._stop_requested:
                    break

                # A. Check for target app crashes in logcat (ignore uiautomator tool exceptions)
                crashes = self.adb.get_logcat_crashes(self.serial, lines=50)
                if crashes and "com.android.commands.uiautomator" not in crashes and (package_name in crashes or "FATAL EXCEPTION" in crashes):
                    crash_detected = True
                    # Take failure screenshot
                    ss_path = str(self.reporter.screenshots_dir / f"crash_{self.serial}_{int(time.time())}.png")
                    self.adb.capture_screenshot(self.serial, ss_path)
                    crash_report_path = self.reporter.generate_report(
                        title=f"Application Crash detected in {package_name}",
                        serial=self.serial,
                        package_name=package_name,
                        error_type="FATAL_CRASH",
                        error_message="Fatal crash or unhandled exception detected in logcat buffer.",
                        step_history=self.step_history,
                        stack_trace=crashes,
                        screenshot_path=ss_path
                    )
                    break

                # B. Dump UI hierarchy
                xml_dump = self.adb.dump_ui_hierarchy(self.serial)
                elements = self.adb.parse_ui_elements(xml_dump)

                # Check if system dialog blocked
                if self.handle_system_dialogs(elements):
                    self.step_history.append({"step": step_num, "action": "auto_allow_permission", "status": "handled"})
                    continue

                # C. Check if app was backgrounded
                curr_app = self.adb.get_current_app(self.serial)
                if curr_app.get("package") != package_name:
                    # Bring back
                    self.adb.launch_app(self.serial, package_name)
                    time.sleep(2.0)
                    xml_dump = self.adb.dump_ui_hierarchy(self.serial)
                    elements = self.adb.parse_ui_elements(xml_dump)

                # D. Pick action: Form fill or Tap
                clickable = [e for e in elements if e.get("clickable") and e.get("bounds")]
                edit_texts = [e for e in elements if "edittext" in e.get("class", "").lower() and e.get("bounds")]

                action_info = {}
                if edit_texts and random.random() < 0.6:
                    target_input = edit_texts[0]
                    center = target_input["bounds"]
                    self.adb.tap(self.serial, center["center_x"], center["center_y"])
                    time.sleep(0.5)
                    # Sample dummy input
                    sample_texts = ["test_user@example.com", "0901234567", "Password123!", "Nguyen Van A"]
                    val = random.choice(sample_texts)
                    self.adb.input_text(self.serial, val)
                    self.adb.press_key(self.serial, 66)  # Enter
                    action_info = {"step": step_num, "action": "input_text", "target": target_input.get("text") or target_input.get("resource_id"), "value": val}
                elif clickable:
                    # Choose a clickable element
                    target_btn = None
                    for c in clickable:
                        sig = f"{c.get('resource_id')}_{c.get('text')}"
                        if sig not in visited_signatures:
                            target_btn = c
                            visited_signatures.add(sig)
                            break
                    if not target_btn:
                        target_btn = random.choice(clickable)

                    center = target_btn["bounds"]
                    self.adb.tap(self.serial, center["center_x"], center["center_y"])
                    action_info = {
                        "step": step_num,
                        "action": "tap",
                        "target": target_btn.get("text") or target_btn.get("content_desc") or target_btn.get("resource_id") or "button",
                        "coords": (center["center_x"], center["center_y"])
                    }
                else:
                    # No clickable found, try swipe up or back
                    self.adb.swipe(self.serial, 360, 1200, 360, 400, 400)
                    action_info = {"step": step_num, "action": "scroll_down", "target": "screen"}

                action_info["status"] = "success"
                self.step_history.append(action_info)

                if callback:
                    callback(action_info)

                time.sleep(1.5)

            return {
                "status": "completed" if not crash_detected else "crashed",
                "steps_executed": len(self.step_history),
                "crash_detected": crash_detected,
                "report_file": crash_report_path,
                "history": self.step_history
            }
        finally:
            self.lock_mgr.release(self.serial, self.agent_id)

    def run_scenario(
        self,
        package_name: str,
        steps: List[Dict[str, Any]],
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Execute a deterministic or smart scenario with self-healing locators.
        Supports hardware simulation steps ('hardware_sms', 'hardware_fingerprint', 'hardware_gps').
        """
        self._stop_requested = False
        self.step_history = []

        if not self.lock_mgr.acquire(self.serial, self.agent_id, f"Scenario_{package_name}", lease_seconds=600):
            return {"status": "error", "message": f"Device {self.serial} is locked"}

        try:
            self.adb.launch_app(self.serial, package_name)
            time.sleep(2.5)

            for idx, step in enumerate(steps, 1):
                if self._stop_requested:
                    break

                action = step.get("action", "").lower()
                locator = step.get("locator", "")
                text_val = step.get("text", "")
                step_record = {"step": idx, "action": action, "locator": locator}

                # 1. Hardware Actions
                if action == "hardware_sms":
                    code = step.get("code", "123456")
                    ok, msg = self.hardware.send_quick_otp(self.serial, code)
                    step_record["status"] = "success" if ok else "failed"
                    step_record["detail"] = msg
                elif action == "hardware_fingerprint":
                    ok, msg = self.hardware.touch_fingerprint(self.serial, step.get("finger_id", 1))
                    step_record["status"] = "success" if ok else "failed"
                    step_record["detail"] = msg
                elif action == "hardware_gps":
                    lat = step.get("lat", 10.776889)
                    lng = step.get("lng", 106.700806)
                    ok, msg = self.hardware.set_gps_location(self.serial, lat, lng)
                    step_record["status"] = "success" if ok else "failed"
                # 2. UI Actions
                elif action in ["tap", "click"]:
                    xml = self.adb.dump_ui_hierarchy(self.serial)
                    elements = self.adb.parse_ui_elements(xml)
                    el = self.find_element(elements, locator)

                    # Self-healing: if not found, scroll down and retry
                    if not el:
                        self.adb.swipe(self.serial, 360, 1000, 360, 400, 400)
                        time.sleep(1.0)
                        xml = self.adb.dump_ui_hierarchy(self.serial)
                        elements = self.adb.parse_ui_elements(xml)
                        el = self.find_element(elements, locator)

                    if el and el.get("bounds"):
                        c = el["bounds"]
                        self.adb.tap(self.serial, c["center_x"], c["center_y"])
                        step_record["status"] = "success"
                    else:
                        step_record["status"] = "element_not_found"
                elif action in ["input", "type"]:
                    xml = self.adb.dump_ui_hierarchy(self.serial)
                    elements = self.adb.parse_ui_elements(xml)
                    el = self.find_element(elements, locator) if locator else None
                    if el and el.get("bounds"):
                        c = el["bounds"]
                        self.adb.tap(self.serial, c["center_x"], c["center_y"])
                        time.sleep(0.3)
                    self.adb.input_text(self.serial, text_val)
                    step_record["status"] = "success"
                elif action == "press_key":
                    key = step.get("keycode", 4)  # default Back
                    self.adb.press_key(self.serial, key)
                    step_record["status"] = "success"
                elif action == "wait":
                    dur = step.get("duration", 2)
                    time.sleep(dur)
                    step_record["status"] = "success"

                self.step_history.append(step_record)
                if callback:
                    callback(step_record)
                time.sleep(1.0)

            return {
                "status": "completed",
                "steps_executed": len(self.step_history),
                "history": self.step_history
            }
        finally:
            self.lock_mgr.release(self.serial, self.agent_id)


if __name__ == "__main__":
    print("AutonomousAgent initialized.")
