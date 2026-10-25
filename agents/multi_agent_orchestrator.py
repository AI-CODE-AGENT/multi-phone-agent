"""
Multi-Agent Orchestrator
Coordinates parallel autonomous testing across all 4 farm devices simultaneously.
"""

import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.farm_config import DEFAULT_FARM_DEVICES
from core.adb_wrapper import ADBWrapper
from core.hardware_simulator import HardwareSimulator
from agents.autonomous_agent import AutonomousAgent
from agents.device_lock_manager import DeviceLockManager
from agents.bug_reporter import BugReporter


class MultiAgentOrchestrator:
    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        lock_mgr: Optional[DeviceLockManager] = None,
        reporter: Optional[BugReporter] = None
    ):
        self.adb = adb or ADBWrapper()
        self.lock_mgr = lock_mgr or DeviceLockManager()
        self.reporter = reporter or BugReporter()
        self.hardware = HardwareSimulator(self.adb)

        # Map serial -> AutonomousAgent instance
        self.agents: Dict[str, AutonomousAgent] = {}
        for dev in DEFAULT_FARM_DEVICES:
            serial = dev["serial"]
            agent_id = f"Agent_{dev['name']}"
            self.agents[serial] = AutonomousAgent(
                agent_id=agent_id,
                serial=serial,
                adb=self.adb,
                hardware=self.hardware,
                reporter=self.reporter,
                lock_mgr=self.lock_mgr
            )

    def get_online_devices(self) -> List[str]:
        """Get list of online devices currently connected to ADB."""
        connected = [d["serial"] for d in self.adb.get_connected_devices() if d["status"] == "device"]
        return [d["serial"] for d in DEFAULT_FARM_DEVICES if d["serial"] in connected]

    def run_parallel_exploration(
        self,
        package_name: str,
        max_steps: int = 20,
        serials: Optional[List[str]] = None,
        log_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Run autonomous test exploration on all online devices simultaneously.
        """
        targets = serials or self.get_online_devices()
        if not targets:
            return {"status": "error", "message": "No farm devices are currently online."}

        start_time = time.time()
        results: Dict[str, Any] = {}

        def _worker(serial: str):
            agent = self.agents.get(serial)
            if not agent:
                return serial, {"status": "error", "message": f"No agent for {serial}"}

            def _step_cb(step_info: Dict[str, Any]):
                if log_callback:
                    log_callback(serial, step_info)

            res = agent.run_exploration(package_name, max_steps=max_steps, callback=_step_cb)
            return serial, res

        with ThreadPoolExecutor(max_workers=len(targets)) as executor:
            future_to_serial = {executor.submit(_worker, s): s for s in targets}
            for future in as_completed(future_to_serial):
                s = future_to_serial[future]
                try:
                    serial, data = future.result()
                    results[serial] = data
                except Exception as e:
                    results[s] = {"status": "exception", "error": str(e)}

        duration = round(time.time() - start_time, 2)
        return {
            "status": "completed",
            "duration_seconds": duration,
            "devices_tested": len(results),
            "results": results
        }

    def stop_all_agents(self):
        """Signal all running agents to stop their current tasks."""
        for agent in self.agents.values():
            agent.stop()


if __name__ == "__main__":
    orch = MultiAgentOrchestrator()
    print("MultiAgentOrchestrator initialized with 4 agents:")
    for s, a in orch.agents.items():
        print(f" - {s} -> {a.agent_id}")
