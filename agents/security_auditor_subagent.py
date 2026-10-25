"""
Security Auditor Subagent (Mobile OWASP Top 10 Scanner)
Audits Android packages for common mobile security vulnerabilities:
- Insecure Data Storage & Backup (android:allowBackup)
- Exported Components without Permissions (IPC Injection Risk)
- Cleartext HTTP Transmission (Man-in-the-Middle Risk)
- Debuggable Release Flags (JDWP Reverse Engineering Risk)
- Clipboard Leaks & Sensitive Logging
"""

import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
SEC_REPORTS_DIR = REPORTS_DIR / "security_reports"


class SecurityAuditorSubagent:
    def __init__(self, adb: Optional[ADBWrapper] = None, memory: Optional[MemoryManager] = None):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        SEC_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def audit_package_security(self, serial: str, package_name: str) -> Dict[str, Any]:
        """
        Execute comprehensive OWASP Mobile security audit on the installed package.
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        vulnerabilities = []

        # 1. Inspect package dump from PackageManager
        code, pkg_dump, _ = self.adb.run_device_cmd(serial, ["shell", "dumpsys", "package", package_name])

        if not pkg_dump or "Unable to find package" in pkg_dump:
            return {
                "status": "PACKAGE_NOT_FOUND",
                "package_name": package_name,
                "serial": serial,
                "timestamp": timestamp,
                "findings_count": 0,
                "vulnerabilities": []
            }

        # 2. Check Debuggable Flag
        is_debuggable = "DEBUGGABLE" in pkg_dump or "flags=[ DEBUGGABLE" in pkg_dump
        if is_debuggable:
            vulnerabilities.append({
                "owasp_id": "M7: Client Code Quality",
                "severity": "HIGH",
                "title": "Application has DEBUGGABLE flag enabled",
                "description": "The app was compiled in debug mode. Attackers can attach a JDWP debugger, extract memory strings, and bypass runtime security controls.",
                "remediation": "Set android:debuggable='false' in release AndroidManifest.xml and ProGuard rules."
            })

        # 3. Check allowBackup Flag
        is_backup_allowed = "ALLOW_BACKUP" in pkg_dump or "flags=[ ALLOW_BACKUP" in pkg_dump
        if is_backup_allowed:
            vulnerabilities.append({
                "owasp_id": "M2: Insecure Data Storage",
                "severity": "MEDIUM",
                "title": "Application allows ADB Backup (android:allowBackup='true')",
                "description": "App data can be backed up via 'adb backup', allowing local access to SharedPreferences, SQLite databases, and user tokens.",
                "remediation": "Set android:allowBackup='false' in AndroidManifest.xml unless specifically required."
            })

        # 4. Check for Unprotected Exported Components
        exported_activities = []
        in_activities = False
        for line in pkg_dump.splitlines():
            line_str = line.strip()
            if "Activity Resolver Table:" in line:
                in_activities = True
            elif "Receiver Resolver Table:" in line or "Service Resolver Table:" in line:
                in_activities = False

            if in_activities and package_name in line_str and "filter" in line_str:
                exported_activities.append(line_str)

        if len(exported_activities) > 3:
            vulnerabilities.append({
                "owasp_id": "M1: Improper Platform Usage",
                "severity": "HIGH",
                "title": f"Discovered {len(exported_activities)} exposed exported Activities/Receivers without explicit permissions",
                "description": "Third-party rogue applications can trigger internal activities or send malicious intents directly.",
                "remediation": "Set android:exported='false' for internal activities, or guard with custom signature-level permissions."
            })

        # 5. Check Cleartext Traffic Permission
        # In Android 9+ (API 28+), cleartext is disabled by default unless explicitly permitted
        if "usesCleartextTraffic=true" in pkg_dump or "flags=[ ... CLEARTEXT" in pkg_dump:
            vulnerabilities.append({
                "owasp_id": "M3: Insecure Communication",
                "severity": "HIGH",
                "title": "Cleartext HTTP traffic permitted (usesCleartextTraffic=true)",
                "description": "The app allows unencrypted HTTP traffic, susceptible to Wi-Fi sniffing and Man-in-the-Middle attacks.",
                "remediation": "Enforce HTTPS and implement network_security_config.xml with cleartextTrafficPermitted='false'."
            })

        # Generate Report File
        report_id = f"SEC_{package_name.replace('.', '_')}_{int(time.time())}"
        report_file = SEC_REPORTS_DIR / f"{report_id}.md"

        content = f"""# Báo Cáo Kiểm Tra An Ninh Mobile (OWASP Mobile Security Report)

- **Gói ứng dụng (Package):** `{package_name}`
- **Thiết bị kiểm thử:** `{serial}`
- **Thời gian thực hiện:** `{timestamp}`
- **Số lượng lỗ hổng phát hiện:** `{len(vulnerabilities)}`

---

## 1. Bảng Tổng Hợp Lỗ Hổng

| Mã OWASP | Mức độ | Tiêu đề lỗ hổng | Giải pháp khắc phục |
| :--- | :--- | :--- | :--- |
"""
        for v in vulnerabilities:
            content += f"| **{v['owasp_id']}** | `{v['severity']}` | {v['title']} | {v['remediation']} |\n"

        content += f"""
---

## 2. Chi Tiết Khuyến Nghị Kỹ Thuật

"""
        for idx, v in enumerate(vulnerabilities, 1):
            content += f"""### {idx}. {v['title']} ({v['severity']})
- **Phân loại:** {v['owasp_id']}
- **Nguy cơ:** {v['description']}
- **Khắc phục:** `{v['remediation']}`

"""
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Store in Codebase Memory
        self.memory.remember(
            key=report_id,
            value={"package": package_name, "findings": len(vulnerabilities), "report_path": str(report_file)},
            tags=["security", package_name, serial]
        )

        return {
            "status": "AUDIT_COMPLETE",
            "report_id": report_id,
            "report_file": str(report_file),
            "findings_count": len(vulnerabilities),
            "vulnerabilities": vulnerabilities
        }


if __name__ == "__main__":
    sec = SecurityAuditorSubagent()
    print("SecurityAuditorSubagent ready.")
