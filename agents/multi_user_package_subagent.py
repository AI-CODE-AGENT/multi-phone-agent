"""
Subagent #49: Multi-User Profile Normalizer & Pure-Python AXML APK Inspector Subagent
=====================================================================================
Wraps `MultiUserPackageEngine` to:
  1. Normalize `pm` / `cmd package` / `appops` commands with `--user 0` and strip
     Vivo OriginOS `user 666` (App Clone profile) `SecurityException` output lines.
  2. Parse compiled Android Binary XML (`AXML` `AndroidManifest.xml`) inside `.apk`
     files in pure Python without `aapt` or external binaries (0 AI tokens).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.multi_user_package_engine import MultiUserPackageEngine


class MultiUserProfileAndPackageSubagent:
    """
    Subagent #49: Ensures `--user 0` multi-user package command isolation against
    Vivo OriginOS `user 666` exceptions and extracts `.apk` binary manifest metadata
    in pure Python.
    """

    SUBAGENT_ID = 49
    SUBAGENT_NAME = "MultiUserProfileAndPackageSubagent"

    def __init__(
        self,
        adb: Any = None,
        memory: Any = None,
        default_user_id: int = 0,
    ) -> None:
        self.subagent_id = self.SUBAGENT_ID
        self.subagent_name = self.SUBAGENT_NAME
        self.adb = adb
        self.memory = memory
        self.default_user_id = int(default_user_id)
        self.engine = MultiUserPackageEngine()

    def normalize_and_filter_pm_execution(
        self,
        cmd: str,
        raw_output: str = "",
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Normalizes `cmd` to include `--user <user_id>` and strips any Vivo `user 666`
        `SecurityException` lines from `raw_output`.
        """
        uid = self.default_user_id if user_id is None else int(user_id)
        normalized_cmd = self.engine.normalize_pm_command(cmd, user_id=uid)

        executed_output = raw_output
        if not executed_output and self.adb is not None and hasattr(self.adb, "shell"):
            try:
                executed_output = str(self.adb.shell(normalized_cmd) or "")
            except Exception as exc:
                executed_output = str(exc)

        cleaned_output = self.engine.filter_user_666_errors(executed_output)
        packages: List[str] = [
            line.split("package:", 1)[1].strip()
            for line in cleaned_output.splitlines()
            if line.strip().startswith("package:")
        ]

        report = {
            "subagent_id": self.SUBAGENT_ID,
            "subagent_name": self.SUBAGENT_NAME,
            "status": "PM_COMMAND_NORMALIZED",
            "original_cmd": cmd,
            "normalized_cmd": normalized_cmd,
            "user_id": uid,
            "cleaned_output": cleaned_output,
            "packages": packages,
            "tokens_used": 0,
            "timestamp": time.time(),
        }

        if self.memory is not None and hasattr(self.memory, "remember"):
            try:
                self.memory.remember(
                    content=f"Subagent #49 normalized `{normalized_cmd}` ({len(packages)} packages)",
                    tags=["multi_user_pm", "user_0", "user_666_filter"],
                    metadata=report,
                )
            except Exception:
                pass

        return report

    def inspect_apk(self, apk_path: str | Path) -> Dict[str, Any]:
        """
        Extracts `package_name`, `permissions`, `activities`, `apk_size_bytes`,
        and `sha256_prefix` from `apk_path` in pure Python.
        """
        metadata = self.engine.extract_apk_metadata_pure_python(apk_path)
        report = {
            "subagent_id": self.SUBAGENT_ID,
            "subagent_name": self.SUBAGENT_NAME,
            "status": "APK_METADATA_EXTRACTED",
            **metadata,
            "timestamp": time.time(),
        }

        if self.memory is not None and hasattr(self.memory, "remember"):
            try:
                self.memory.remember(
                    content=(
                        f"Subagent #49 extracted APK {metadata['package_name']} "
                        f"({len(metadata['permissions'])} perms)"
                    ),
                    tags=["apk_parser", "axml", metadata["package_name"]],
                    metadata=report,
                )
            except Exception:
                pass

        return report


MultiUserPackageSubagent = MultiUserProfileAndPackageSubagent
