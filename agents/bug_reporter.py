"""
Bug Reporter & Evidence Collector
Generates structured Markdown defect reports with screenshots, UI dumps, and crash stack traces.
"""

import json
import time
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.farm_config import REPORTS_DIR


class BugReporter:
    def __init__(self, reports_dir: Optional[Path] = None):
        self.reports_dir = reports_dir or REPORTS_DIR
        self.screenshots_dir = self.reports_dir / "screenshots"
        self.dumps_dir = self.reports_dir / "dumps"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.dumps_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(
        self,
        title: str,
        serial: str,
        package_name: str,
        error_type: str,
        error_message: str,
        step_history: List[Dict[str, Any]],
        stack_trace: str = "",
        screenshot_path: Optional[str] = None,
        ui_dump_xml: Optional[str] = None
    ) -> str:
        """
        Generate a Markdown bug report file and return the report filepath.
        """
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        report_id = f"BUG_{serial}_{timestamp}"
        report_file = self.reports_dir / f"{report_id}.md"

        steps_md = ""
        for i, step in enumerate(step_history, 1):
            action = step.get("action", "unknown")
            target = step.get("target", "")
            status = step.get("status", "done")
            steps_md += f"{i}. **{action}** on `{target}` -> status: `{status}`\n"

        if not steps_md:
            steps_md = "*(Chua co buoc thao tac nao)*\n"

        stack_md = f"```\n{stack_trace}\n```" if stack_trace else "*(Khong co stacktrace he thong)*"

        screenshot_md = ""
        if screenshot_path and os.path.exists(screenshot_path):
            screenshot_md = f"![Screenshot Evidence]({screenshot_path})\n"

        content = f"""# [Bug Report] {title}

**Report ID:** `{report_id}`  
**Thoi gian phat hien:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`  
**Thiet bi:** `{serial}`  
**Ung dung (Package):** `{package_name}`  
**Phan loai loi:** `{error_type}`  

---

## 1. Mo Ta Loi & Nguyen Nhan
> **Thong bao:** {error_message}

{screenshot_md}

---

## 2. Cac Buoc Tai Hien (Reproduction Steps)
{steps_md}

---

## 3. Logcat Crash / Stacktrace
{stack_md}

---

## 4. De Xuat Khac Phuc (Self-Healing Recommendation)
- Kiem tra lai cac phan tu giao dien hoac quyen he thong tuong ung voi buoc cuoi cung.
- Xem lai logcat phia tren de xac dinh dong code gay crash (`NullPointerException`, `ANR`, v.v.).
"""

        report_file.write_text(content, encoding="utf-8")

        # Also save JSON metadata
        json_file = self.reports_dir / f"{report_id}.json"
        meta = {
            "report_id": report_id,
            "title": title,
            "serial": serial,
            "package_name": package_name,
            "error_type": error_type,
            "error_message": error_message,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "screenshot": screenshot_path,
            "report_path": str(report_file)
        }
        json_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")

        return str(report_file)

    def list_reports(self) -> List[Dict[str, Any]]:
        """List all generated bug reports."""
        reports = []
        for jf in self.reports_dir.glob("BUG_*.json"):
            try:
                reports.append(json.loads(jf.read_text(encoding="utf-8")))
            except Exception:
                pass
        return sorted(reports, key=lambda x: x.get("created_at", ""), reverse=True)


if __name__ == "__main__":
    reporter = BugReporter()
    print("Reports dir:", reporter.reports_dir)
    print("Found existing reports:", len(reporter.list_reports()))
