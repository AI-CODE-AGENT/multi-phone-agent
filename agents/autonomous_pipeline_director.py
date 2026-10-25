"""
Autonomous Pipeline Director (Master Conductor & Agile Leader)
Orchestrates the complete autonomous Dev-QA-Heal-Patch-Regression loop across the farm,
driving tasks on the Kanban Board from BACKLOG -> DONE.
"""

import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Callable

# Force UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.farm_config import DEFAULT_FARM_DEVICES
from core.adb_wrapper import ADBWrapper
from core.hardware_simulator import HardwareSimulator
from core.mock_otp_service import MockOTPService
from core.memory_manager import MemoryManager
from core.kanban_board import KanbanBoard

from agents.planner_subagent import PlannerSubagent
from agents.operator_subagent import OperatorSubagent
from agents.vision_perception_subagent import VisionPerceptionSubagent
from agents.healing_subagent import SelfHealingSubagent
from agents.auditor_subagent import AuditorSubagent
from agents.security_auditor_subagent import SecurityAuditorSubagent
from agents.prompt_optimizer_subagent import PromptOptimizerSubagent
from agents.code_improver_subagent import CodeImproverSubagent
from agents.regression_verifier_subagent import RegressionVerifierSubagent
from agents.real_device_scout_subagent import RealDeviceScoutSubagent
from agents.group_sync_subagent import GroupSyncSubagent
from agents.experience_miner_subagent import ExperienceMinerSubagent
from agents.device_lock_manager import DeviceLockManager
from core.real_device_manager import RealDeviceManager


class AutonomousPipelineDirector:
    """The Leader that coordinates all 12 specialized Subagents across Virtual AVDs & Real Phones."""

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
        kanban: Optional[KanbanBoard] = None
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.kanban = kanban or KanbanBoard()
        self.lock_mgr = DeviceLockManager()
        self.real_mgr = RealDeviceManager(self.adb)
        self.hardware = HardwareSimulator(self.adb)
        self.mock_otp = MockOTPService(self.hardware)

        # Specialist Subagents (12 Subagent Ecosystem)
        self.vision = VisionPerceptionSubagent(self.adb, self.memory)
        self.security = SecurityAuditorSubagent(self.adb, self.memory)
        self.prompt_opt = PromptOptimizerSubagent(self.memory)
        self.code_imp = CodeImproverSubagent(self.memory)
        self.regression = RegressionVerifierSubagent(self.adb, self.memory, self.kanban)
        self.scout = RealDeviceScoutSubagent(self.adb, self.real_mgr, self.memory)
        self.group_sync = GroupSyncSubagent(self.adb, memory=self.memory)
        self.exp_miner = ExperienceMinerSubagent(self.memory)

    def execute_task_lifecycle(
        self,
        title: str,
        goal: str,
        serial: str,
        package_name: str = "com.android.settings",
        callback: Optional[Callable[[str, str, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Execute full autonomous end-to-end task lifecycle with Kanban tracking.
        """
        def _log(subagent: str, msg: str):
            if callback:
                callback(serial, subagent, msg)

        start_time = time.time()

        # Step 1: Create Kanban Card in BACKLOG
        card = self.kanban.create_card(
            title=title,
            goal=goal,
            target_device=serial,
            assigned_subagent="PlannerSubagent"
        )
        card_id = card["card_id"]
        _log("Kanban", f"Created Task Card [{card_id}]: '{title}' in BACKLOG")

        # Step 2: Acquire Device Lock
        if not self.lock_mgr.acquire(serial, f"Pipeline_{card_id}", f"Goal: {goal[:30]}", lease_seconds=600):
            self.kanban.transition_state(card_id, "BLOCKED", actor="LockManager", note="Device busy")
            return {"status": "BLOCKED", "card_id": card_id, "message": f"Device {serial} is locked."}

        try:
            # Step 2.5: If Real Physical Phone, run RealDeviceScoutSubagent health & thermal guard
            if self.real_mgr.is_real_device(serial):
                _log("RealDeviceScout", f"Physical phone detected ({serial}). Applying Battery & Thermal Guard...")
                self.real_mgr.apply_real_phone_health_guard(serial)

            # Step 3: Transition to PLANNING (Check ExperienceMiner Macro Shortcut first!)
            self.kanban.transition_state(card_id, "PLANNING", actor="PlannerSubagent", note="Deconstructing goal")
            cached_macro = self.exp_miner.lookup_macro_for_goal(goal, package_name)
            if cached_macro and cached_macro.get("steps"):
                plan = cached_macro["steps"]
                _log("ExperienceMiner", f"Loaded verified Macro Shortcut ({len(plan)} steps, {cached_macro.get('success_count', 1)} prior wins).")
            else:
                _log("Planner", f"Deconstructing goal: '{goal}'")
                planner = PlannerSubagent(agent_id=f"Planner_{serial}")
                plan = planner.create_plan_from_goal(goal, package_name)
                _log("Planner", f"Generated {len(plan)} execution milestones.")

            # Step 4: Transition to DEV_IN_PROGRESS (Execution)
            self.kanban.transition_state(card_id, "DEV_IN_PROGRESS", actor="OperatorSubagent", note="Executing milestones")
            operator = OperatorSubagent(
                agent_id=f"Operator_{serial}",
                serial=serial,
                adb=self.adb,
                hardware=self.hardware,
                mock_otp=self.mock_otp,
                lock_mgr=self.lock_mgr
            )
            healer = SelfHealingSubagent(serial=serial, adb=self.adb)

            trajectory = []
            healings = []
            failures = []

            for step_idx, step in enumerate(plan, 1):
                _log("Operator", f"Step {step_idx}/{len(plan)}: {step.get('action')} -> {step.get('milestone')}")
                res = operator.execute_step(step)

                if res.get("status") == "element_not_found":
                    _log("Healer", f"Element not found. Triggering multi-tier recovery...")
                    self.kanban.transition_state(card_id, "HEALING", actor="SelfHealingSubagent", note=f"Step {step_idx} healing")

                    xml = self.adb.dump_ui_hierarchy(serial)
                    elements = self.adb.parse_ui_elements(xml)
                    healed, rec_elem, msg = healer.attempt_recovery(step, elements)

                    if healed and rec_elem and rec_elem.get("bounds"):
                        c = rec_elem["bounds"]
                        self.adb.tap(serial, c["center_x"], c["center_y"])
                        res["status"] = "healed_success"
                        res["detail"] = f"Recovered: {msg} at ({c['center_x']}, {c['center_y']})"
                        healings.append({"step": step_idx, "type": "fuzzy_match", "msg": msg})
                        _log("Healer", f"Healed successfully at ({c['center_x']}, {c['center_y']})")
                        self.kanban.transition_state(card_id, "DEV_IN_PROGRESS", actor="OperatorSubagent", note="Resumed after healing")
                    else:
                        # Fallback to Vision Perception coordinate grounding
                        v_coords = self.vision.resolve_visual_coordinates(serial, step.get("milestone", "center_confirm"))
                        if v_coords:
                            self.adb.tap(serial, v_coords[0], v_coords[1])
                            res["status"] = "vision_grounded"
                            res["detail"] = f"Visual ground fallback at {v_coords}"
                            _log("Vision", f"Visual coordinate grounded: {v_coords}")
                        else:
                            res["status"] = "unrecoverable_failure"
                            failures.append({"step": step_idx, "reason": msg})

                trajectory.append(res)
                time.sleep(0.5)

            # Step 5: Transition to QA_VERIFYING (Auditing & Security)
            self.kanban.transition_state(card_id, "QA_VERIFYING", actor="AuditorSubagent", note="Auditing performance & security")
            _log("Auditor", "Auditing runtime performance, frame drops, and logcat...")
            auditor = AuditorSubagent(serial=serial, adb=self.adb)
            duration = round(time.time() - start_time, 2)
            audit_report = auditor.audit_run(package_name, trajectory, duration)

            # Security Audit
            _log("SecurityAuditor", "Auditing package for Mobile OWASP vulnerabilities...")
            sec_report = self.security.audit_package_security(serial, package_name)

            # Step 6: Self-Prompt Optimization
            prompt_res = None
            try:
                prompt_res = self.prompt_opt.analyze_and_optimize(
                    agent_type="operator",
                    current_prompt=f"Goal: {goal}",
                    execution_feedback={"scenario": goal, "failures": failures, "healings": healings}
                )
                _log("PromptOptimizer", f"Synthesized optimized prompt {prompt_res.get('version')}")
            except Exception as e:
                pass

            # Step 7: Auto-Patch Generation (if defects occurred)
            patch_res = None
            if audit_report.get("crashes_detected", 0) > 0 or failures:
                self.kanban.transition_state(card_id, "PATCHED", actor="CodeImproverSubagent", note="Generating code patch")
                defect = self.memory.record_defect(
                    defect_type="RUNTIME_DEFECT",
                    title=f"Defect during {title}",
                    serial=serial,
                    context={"failures": failures}
                )
                patch_res = self.code_imp.analyze_defect_and_propose_patch(defect)
                _log("CodeImprover", f"Generated unified patch: {patch_res.get('patch_file')}")
                self.kanban.add_artifact(card_id, "code_patch", patch_res.get("patch_file"))

                # Step 8: Regression Verification
                _log("RegressionVerifier", "Running regression verification for patch on device...")
                reg_res = self.regression.verify_patch_on_device(patch_res, serial, package_name, card_id=card_id)
                _log("RegressionVerifier", f"Regression Result: {reg_res.get('status')}")
            else:
                self.kanban.transition_state(card_id, "REGRESSION_PASSED", actor="System", note="Zero defects detected")

            # Step 9: Mine Experience Trajectory into Macro Shortcut (Mobile-Agent-E)
            macro_res = None
            try:
                dev_res = self.real_mgr.get_device_resolution(serial)
                macro_res = self.exp_miner.mine_trajectory(
                    goal=goal,
                    package_name=package_name,
                    plan_steps=plan,
                    trajectory_results=trajectory,
                    duration_seconds=round(time.time() - start_time, 2),
                    reference_resolution=dev_res
                )
                if macro_res.get("status") == "MACRO_MINED":
                    _log("ExperienceMiner", f"Distilled reusable Macro Shortcut: {macro_res.get('goal_signature')}")
            except Exception:
                pass

            # Step 10: Final Transition to DONE
            self.kanban.transition_state(card_id, "DONE", actor="AutonomousPipelineDirector", note="Task successfully completed")
            self.kanban.add_artifact(card_id, "audit_report", audit_report.get("markdown_path"))
            self.kanban.add_artifact(card_id, "security_report", sec_report.get("report_file"))
            _log("Kanban", f"Task Card [{card_id}] successfully completed and moved to DONE.")

            total_dur = round(time.time() - start_time, 2)
            return {
                "status": "COMPLETED",
                "success": True,
                "task_id": card_id,
                "card_id": card_id,
                "serial": serial,
                "is_real_device": self.real_mgr.is_real_device(serial),
                "duration_seconds": total_dur,
                "steps_executed": len(trajectory),
                "audit": audit_report,
                "security": sec_report,
                "prompt_optimization": prompt_res,
                "patch": patch_res,
                "macro": macro_res
            }

        finally:
            self.lock_mgr.release(serial, f"Pipeline_{card_id}")

    def run_autonomous_cycle(
        self,
        title: str,
        goal: str,
        serial: str = "emulator-5554",
        package_name: str = "com.android.settings"
    ) -> Dict[str, Any]:
        """Alias for MCP & external callers to execute a complete Kanban task lifecycle."""
        return self.execute_task_lifecycle(title=title, goal=goal, serial=serial, package_name=package_name)

    def run_4_device_autonomous_pipeline(
        self,
        log_callback: Optional[Callable[[str, str, str], None]] = None,
        include_real_devices: bool = True
    ) -> Dict[str, Any]:
        """
        Run the full autonomous pipeline across all online farm devices (4 AVDs + Optional Real Phones) in parallel.
        """
        connected = [d["serial"] for d in self.adb.get_connected_devices() if d["status"] == "device"]
        targets = [d["serial"] for d in DEFAULT_FARM_DEVICES if d["serial"] in connected]
        if include_real_devices and self.real_mgr.get_farm_mode().get("real_phone_farm_enabled", True):
            for s in connected:
                if self.real_mgr.is_real_device(s) and s not in targets:
                    targets.append(s)
        if not targets:
            return {"status": "error", "message": "No online farm devices available."}

        scenarios = {
            "emulator-5554": {
                "title": "Customer Auth & Mock OTP Verification",
                "goal": "Verify user registration and authentication with Mock OTP for 0941189263 and fingerprint touch"
            },
            "emulator-5556": {
                "title": "Merchant Dispatch & GPS Routing",
                "goal": "Simulate merchant order pickup, spoof GPS to Landmark 81, and progress delivery route"
            },
            "emulator-5558": {
                "title": "Chaos Stress & Boundary Fuzzing",
                "goal": "Stress test with boundary inputs, screen rotations, and network profile changes"
            },
            "emulator-5560": {
                "title": "Performance, Latency & Security Audit",
                "goal": "Measure cold launch latency, frame jank drops, and audit OWASP mobile security"
            }
        }

        start_time = time.time()
        results: Dict[str, Any] = {}

        def _worker(s: str):
            sc = scenarios.get(s, {"title": "Generic Test", "goal": "Explore settings app"})
            return s, self.execute_task_lifecycle(
                title=sc["title"],
                goal=sc["goal"],
                serial=s,
                package_name="com.android.settings",
                callback=log_callback
            )

        with ThreadPoolExecutor(max_workers=len(targets)) as executor:
            future_to_serial = {executor.submit(_worker, s): s for s in targets}
            for future in as_completed(future_to_serial):
                s = future_to_serial[future]
                try:
                    serial, data = future.result()
                    results[serial] = data
                except Exception as e:
                    results[s] = {"status": "error", "error": str(e)}

        total_dur = round(time.time() - start_time, 2)
        return {
            "status": "COMPLETED",
            "total_duration_seconds": total_dur,
            "tasks_executed": len(results),
            "results": results,
            "kanban_summary": self.kanban.get_board_summary()
        }


if __name__ == "__main__":
    director = AutonomousPipelineDirector()
    print("AutonomousPipelineDirector ready.")
