"""
Auditor & Code Improvement Subagent
Analyzes test runs, monitors performance bottlenecks, and synthesizes actionable code fixes.
"""

import sys
import time
import re
from typing import Dict, List, Optional, Any
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.farm_config import REPORTS_DIR
from core.adb_wrapper import ADBWrapper


class AuditorSubagent:
    """Audits session logs, categorizes defects, and generates engineering recommendations."""

    def __init__(self, serial: str, adb: Optional[ADBWrapper] = None):
        self.serial = serial
        self.adb = adb or ADBWrapper()
        self.reports_dir = REPORTS_DIR

    def audit_run(
        self,
        package_name: str,
        trajectory: List[Dict[str, Any]],
        duration_seconds: float
    ) -> Dict[str, Any]:
        """
        Produce a full audit of an execution trajectory.
        """
        crashes = self.adb.get_logcat_crashes(self.serial, lines=80)
        has_fatal = "FATAL EXCEPTION" in crashes or "NullPointerException" in crashes

        # Calculate latency stats
        latencies = [step.get("latency_ms", 0) for step in trajectory if "latency_ms" in step]
        avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0.0
        slow_steps = [s for s in trajectory if s.get("latency_ms", 0) > 1500]

        recommendations = self.generate_engineering_recommendations(crashes, slow_steps)

        audit_result = {
            "serial": self.serial,
            "package": package_name,
            "duration_s": duration_seconds,
            "total_steps": len(trajectory),
            "avg_latency_ms": avg_latency,
            "slow_steps_count": len(slow_steps),
            "has_fatal_crashes": has_fatal,
            "crash_excerpt": crashes[:400] if crashes else None,
            "recommendations": recommendations
        }

        # Save Markdown Audit Memo
        self._write_audit_markdown(audit_result, trajectory)
        return audit_result

    def generate_engineering_recommendations(self, crashes: str, slow_steps: List[Dict[str, Any]]) -> List[str]:
        """Generate concrete code improvement recommendations based on failure telemetry."""
        recs = []
        if crashes:
            if "NullPointerException" in crashes:
                match = re.search(r"at ([\w\.\$]+\([\w\.]+:\d+\))", crashes)
                loc = f" at `{match.group(1)}`" if match else ""
                recs.append(f"**Fix NullPointerException{loc}**: Thêm null-check hoặc Kotlin safe-call (`?.`) trước khi gọi phương thức.")
            if "SQLiteException" in crashes:
                recs.append("**Database Migration Fix**: Cơ sở dữ liệu SQLite gặp xung đột phiên bản, kiểm tra Room / SQLiteOpenHelper migration scripts.")
            if "OutOfMemory" in crashes:
                recs.append("**Memory Leak Fix**: Kiểm tra giải phóng Bitmap / Texture hoặc rò rỉ Activity reference trong static contexts.")
            if "ANR in" in crashes:
                recs.append("**Thread Optimization**: Tác vụ I/O nặng đang chạy trên Main UI Thread, hãy chuyển sang `Dispatchers.IO` (Coroutines) hoặc `RxJava/Schedulers`.")

        if slow_steps:
            recs.append(f"**UI Responsiveness**: Có {len(slow_steps)} bước giao diện mất trên 1.5s để phản hồi. Cần tối ưu render hoặc thêm Skeleton Loading.")

        if not recs:
            recs.append("**Clean Execution**: Không phát hiện crash hoặc bottleneck nghiêm trọng. Ứng dụng đáp ứng tốt tiêu chuẩn ổn định.")

        return recs

    def _write_audit_markdown(self, audit: Dict[str, Any], trajectory: List[Dict[str, Any]]):
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename = self.reports_dir / f"AUDIT_{self.serial}_{timestamp}.md"

        rec_md = "\n".join([f"- {r}" for r in audit["recommendations"]])
        steps_md = "\n".join([f"1. **{s.get('action')}**: {s.get('detail')} ({s.get('latency_ms', 0)}ms)" for s in trajectory])

        content = f"""# [Audit Report] Mobile Test Trajectory & Performance Analysis

**Device:** `{audit['serial']}`  
**Target Package:** `{audit['package']}`  
**Duration:** `{audit['duration_s']}s` | **Total Steps:** `{audit['total_steps']}`  
**Average UI Latency:** `{audit['avg_latency_ms']}ms`  
**Crash Detected:** `{'YES (CRITICAL)' if audit['has_fatal_crashes'] else 'NO (STABLE)'}`  

---

## 1. De Xuat Cai Tien Ma Nguon (Code Improvements)
{rec_md}

---

## 2. Nhat Ky Cac Buoc Thuc Thi (Execution Trajectory)
{steps_md if steps_md else '*(Chua co buoc thao tac)*'}

---

## 3. Logcat Crash Excerpt
```
{audit['crash_excerpt'] or '*(Khong co crash he thong)*'}
```
"""
        filename.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    auditor = AuditorSubagent("emulator-5554")
    print("AuditorSubagent initialized.")
