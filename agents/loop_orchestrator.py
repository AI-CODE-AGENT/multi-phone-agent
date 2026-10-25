"""
Autonomous Loop Orchestrator
Coordinates Planner -> Operator -> Healer -> Auditor -> PromptOptimizer -> CodeImprover
in a complete Dev-QA-Self-Improvement loop with persistent MemoryManager.
"""

import sys
import time
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

# Force UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.hardware_simulator import HardwareSimulator
from core.mock_otp_service import MockOTPService
from core.memory_manager import MemoryManager
from agents.planner_subagent import PlannerSubagent
from agents.operator_subagent import OperatorSubagent
from agents.healing_subagent import SelfHealingSubagent
from agents.auditor_subagent import AuditorSubagent
from agents.prompt_optimizer_subagent import PromptOptimizerSubagent
from agents.code_improver_subagent import CodeImproverSubagent
from agents.device_lock_manager import DeviceLockManager


class LoopOrchestrator:
    """Manages the full Observe-Plan-Act-Heal-Audit-Improve-Patch loop on a target device."""

    def __init__(self, serial: str, adb: Optional[ADBWrapper] = None, memory: Optional[MemoryManager] = None):
        self.serial = serial
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.hardware = HardwareSimulator(self.adb)
        self.mock_otp = MockOTPService(self.hardware)
        self.lock_mgr = DeviceLockManager()

        # Initialize the Specialist Subagents
        self.planner = PlannerSubagent(agent_id=f"Planner_{serial}")
        self.operator = OperatorSubagent(
            agent_id=f"Operator_{serial}",
            serial=serial,
            adb=self.adb,
            hardware=self.hardware,
            mock_otp=self.mock_otp,
            lock_mgr=self.lock_mgr
        )
        self.healer = SelfHealingSubagent(serial=serial, adb=self.adb)
        self.auditor = AuditorSubagent(serial=serial, adb=self.adb)
        self.prompt_optimizer = PromptOptimizerSubagent(self.memory)
        self.code_improver = CodeImproverSubagent(self.memory)

        self._stop_requested = False

    def stop(self):
        """Abort active loop execution."""
        self._stop_requested = True

    def run_autonomous_loop(
        self,
        goal: str,
        package_name: str,
        callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Execute full autonomous closed-loop cycle:
        Plan -> Operate -> Heal (if needed) -> Audit -> Optimize Prompt -> Generate Patch (if needed).
        """
        self._stop_requested = False
        start_time = time.time()
        trajectory: List[Dict[str, Any]] = []
        healings: List[Dict[str, Any]] = []
        failures: List[Dict[str, Any]] = []

        # 1. Acquire Device Lock
        if not self.lock_mgr.acquire(self.serial, f"Loop_{self.serial}", f"Goal: {goal[:30]}", lease_seconds=600):
            return {"status": "error", "message": f"Device {self.serial} is locked by another agent session."}

        try:
            # 2. Phase 1: Planning
            if callback:
                callback("Planner", {"status": "planning", "goal": goal})
            plan = self.planner.create_plan_from_goal(goal, package_name)
            if callback:
                callback("Planner", {"status": "plan_ready", "milestones_count": len(plan), "plan": plan})

            # 3. Phase 2 & 3: Execution & Self-Healing Loop
            for step_idx, step in enumerate(plan, 1):
                if self._stop_requested:
                    break

                if callback:
                    callback("Operator", {"status": "executing", "step": step_idx, "action": step.get("action"), "milestone": step.get("milestone")})

                # Operator executes step
                res = self.operator.execute_step(step)

                # Check if failure needs Healing
                if res.get("status") == "element_not_found":
                    if callback:
                        callback("Healer", {"status": "diagnosing", "reason": res.get("detail")})

                    xml = self.adb.dump_ui_hierarchy(self.serial)
                    elements = self.adb.parse_ui_elements(xml)
                    healed, recovered_elem, msg = self.healer.attempt_recovery(step, elements)

                    if healed and recovered_elem and recovered_elem.get("bounds"):
                        # Re-execute action on healed element
                        c = recovered_elem["bounds"]
                        self.adb.tap(self.serial, c["center_x"], c["center_y"])
                        res["status"] = "healed_success"
                        res["detail"] = f"Recovered: {msg} at ({c['center_x']}, {c['center_y']})"
                        healings.append({"step": step_idx, "type": "fuzzy_match", "msg": msg})
                        if callback:
                            callback("Healer", {"status": "healed", "detail": res["detail"]})
                    else:
                        res["status"] = "unrecoverable_failure"
                        res["detail"] = msg
                        failures.append({"step": step_idx, "reason": msg})
                        if callback:
                            callback("Healer", {"status": "unrecovered", "detail": msg})

                trajectory.append(res)
                time.sleep(0.8)

            # 4. Phase 4: Auditing & Performance Profiling
            duration = round(time.time() - start_time, 2)
            if callback:
                callback("Auditor", {"status": "auditing"})
            audit_report = self.auditor.audit_run(package_name, trajectory, duration)
            if callback:
                callback("Auditor", {"status": "audit_complete", "report": audit_report})

            # 5. Phase 5: Self-Prompting & Prompt Optimization
            prompt_opt_result = None
            try:
                execution_feedback = {
                    "scenario": goal,
                    "failures": failures,
                    "healings": healings,
                    "avg_latency_ms": 320
                }
                prompt_opt_result = self.prompt_optimizer.analyze_and_optimize(
                    agent_type="operator",
                    current_prompt=f"Execute testing goal: {goal}",
                    execution_feedback=execution_feedback
                )
                if callback:
                    callback("PromptOptimizer", {
                        "status": "prompt_optimized",
                        "version": prompt_opt_result.get("version"),
                        "rationale": prompt_opt_result.get("rationale")
                    })
            except Exception as e:
                print(f"[LoopOrchestrator] Warning in prompt optimization: {e}", file=sys.stderr)

            # 6. Phase 6: Code Improver & Automated Patch Generation
            patch_result = None
            try:
                crashes = audit_report.get("crashes_detected", 0)
                recs = audit_report.get("recommendations", [])
                if crashes > 0 or failures:
                    defect = self.memory.record_defect(
                        defect_type="UI_OR_CRASH_DEFECT",
                        title=f"Defect during goal: {goal[:50]}",
                        serial=self.serial,
                        severity="MEDIUM" if not crashes else "HIGH",
                        context={"failures": failures, "recommendations": recs}
                    )
                    patch_result = self.code_improver.analyze_defect_and_propose_patch(defect)
                    if callback:
                        callback("CodeImprover", {
                            "status": "patch_created",
                            "defect_id": defect["defect_id"],
                            "patch_file": patch_result.get("patch_file"),
                            "summary": patch_result.get("summary")
                        })
            except Exception as e:
                print(f"[LoopOrchestrator] Warning in code improver: {e}", file=sys.stderr)

            # 7. Remember Run in Persistent Memory
            self.memory.remember(
                key=f"run_{self.serial}_{int(time.time())}",
                value={
                    "goal": goal,
                    "duration": duration,
                    "steps": len(trajectory),
                    "healed_count": len(healings),
                    "audit_summary": audit_report.get("markdown_path")
                },
                tags=["test_run", self.serial, package_name]
            )

            return {
                "status": "completed",
                "goal": goal,
                "serial": self.serial,
                "duration_seconds": duration,
                "steps_executed": len(trajectory),
                "trajectory": trajectory,
                "audit": audit_report,
                "prompt_optimization": prompt_opt_result,
                "code_patch": patch_result
            }

        finally:
            self.lock_mgr.release(self.serial, f"Loop_{self.serial}")


if __name__ == "__main__":
    orchestrator = LoopOrchestrator("emulator-5554")
    print("LoopOrchestrator initialized with 6 Subagents (Planner, Operator, Healer, Auditor, PromptOptimizer, CodeImprover).")
