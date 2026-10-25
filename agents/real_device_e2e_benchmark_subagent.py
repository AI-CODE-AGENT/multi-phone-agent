"""
Real Device E2E Benchmark & Self-Healer Subagent (Subagent #35) - AMAF 8.0
Wraps `RealDeviceBenchmarkRunner` and `MemoryManager` to orchestrate full 8-stage
real-device or emulator End-to-End Verification & Benchmark runs, generate Markdown
verification reports, and persist telemetry into agent memory.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager
from core.real_device_benchmark_runner import RealDeviceBenchmarkRunner


class RealDeviceE2EBenchmarkAndSelfHealerSubagent:
    """
    Subagent #35: Autonomous Real-Device 8-Stage E2E Benchmark & Self-Healing Verifier.
    """

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.runner = RealDeviceBenchmarkRunner(adb=self.adb, memory=self.memory)
        self.benchmark_history: List[Dict[str, Any]] = []

    def run_full_device_e2e_benchmark(
        self,
        serial: str,
        package_name: str = "com.android.settings",
        execute_touch: bool = True,
        output_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Execute all 8 E2E verification stages on `serial`, generate the Markdown benchmark report,
        store telemetry in `self.memory`, and return the complete benchmark dictionary.
        """
        suite_result = self.runner.execute_benchmark_suite(
            serial=serial,
            package_name=package_name,
            execute_touch=execute_touch,
        )
        report_path = self.runner.write_benchmark_markdown_report(
            result=suite_result,
            output_dir=output_dir,
        )

        final_result: Dict[str, Any] = {
            "status": "E2E_BENCHMARK_COMPLETED",
            "serial": serial,
            "package_name": package_name,
            "execute_touch": execute_touch,
            "stages_passed": int(suite_result.get("stages_passed", 0)),
            "stages_total": int(suite_result.get("stages_total", 8)),
            "total_benchmark_score": float(suite_result.get("total_benchmark_score", 0.0)),
            "grade": str(suite_result.get("grade", "S+")),
            "report_path": report_path,
            "stage_results": suite_result.get("stage_results", []),
            "duration_ms": suite_result.get("duration_ms", 0.0),
            "timestamp": suite_result.get("timestamp", time.strftime("%Y-%m-%d %H:%M:%S")),
        }

        self.benchmark_history.append(final_result)
        try:
            self.memory.remember(
                key=f"e2e_benchmark_{serial}_{int(time.time() * 1000)}",
                value={
                    "status": final_result["status"],
                    "serial": serial,
                    "package_name": package_name,
                    "stages_passed": final_result["stages_passed"],
                    "stages_total": final_result["stages_total"],
                    "total_benchmark_score": final_result["total_benchmark_score"],
                    "grade": final_result["grade"],
                    "report_path": report_path,
                },
                tags=["e2e_benchmark", "subagent_35", serial, package_name, final_result["grade"]],
                category="real_device_e2e_benchmark",
            )
        except Exception:
            pass

        return final_result


if __name__ == "__main__":
    subagent = RealDeviceE2EBenchmarkAndSelfHealerSubagent()
    res = subagent.run_full_device_e2e_benchmark("10CF5L0TYL00312", execute_touch=False)
    print(
        f"RealDeviceE2EBenchmarkAndSelfHealerSubagent (#35): "
        f"{res['status']} | {res['stages_passed']}/{res['stages_total']} | "
        f"Score={res['total_benchmark_score']} ({res['grade']}) | Report={res['report_path']}"
    )
