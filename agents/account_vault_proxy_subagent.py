"""
Subagent #44: Multi-Account Vault, Rate-Limit Scheduler & Network Proxy Isolation Subagent
==========================================================================================
Wraps `MultiAccountVaultAndProxyEngine` to audit registered multi-app accounts
(`nht.tn472`, `wh0_am_i2342`, etc.), select the highest-trust ready account,
schedule anti-shadowban human-jitter cooldowns, and audit/configure per-device
Android HTTP proxy and IP isolation with zero AI tokens.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.account_vault_proxy_engine import MultiAccountVaultAndProxyEngine


class MultiAccountVaultAndProxySubagent:
    """
    Subagent #44: Orchestrates multi-account rotation, rate-limit scheduling,
    and per-device HTTP proxy / IP isolation auditing.
    """

    SUBAGENT_ID = 44
    SUBAGENT_NAME = "MultiAccountVaultAndProxySubagent"

    def __init__(
        self,
        vault_path: Optional[Path | str] = None,
        adb: Any = None,
        memory: Any = None,
    ) -> None:
        self.subagent_id = self.SUBAGENT_ID
        self.subagent_name = self.SUBAGENT_NAME
        self.adb = adb
        self.memory = memory
        self.engine = MultiAccountVaultAndProxyEngine(vault_path=vault_path)

    def run_vault_and_proxy_audit(
        self,
        serial: str = "10CF5L0TYL00312",
        platform: str = "tiktok",
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Audits the multi-account vault for `serial` and `platform`, selects the
        next ready account with the highest `trust_score`, and inspects the device's
        network proxy and IPv4 isolation status with 0 AI tokens.
        """
        ready_selection = self.engine.select_next_ready_account(
            platform=platform,
            serial=serial,
        )
        network_audit = self.engine.audit_device_network_isolation(
            serial=serial,
            dry_run=dry_run,
        )

        accounts_snapshot = [
            prof.to_dict() for prof in self.engine.accounts.values()
        ]

        report = {
            "status": "VAULT_AND_PROXY_AUDITED",
            "subagent_id": self.SUBAGENT_ID,
            "subagent_name": self.SUBAGENT_NAME,
            "serial": serial,
            "platform": platform,
            "ready_selection": ready_selection,
            "network_audit": network_audit,
            "accounts_count": len(accounts_snapshot),
            "accounts": accounts_snapshot,
            "dry_run": dry_run,
            "tokens_used": 0,
            "timestamp": time.time(),
        }

        if self.memory is not None and hasattr(self.memory, "remember"):
            try:
                self.memory.remember(
                    content=(
                        f"Subagent #44 audited {len(accounts_snapshot)} accounts on {serial}; "
                        f"ready={ready_selection.get('ready')}"
                    ),
                    tags=["account_vault", "proxy_isolation", serial, platform],
                    metadata=report,
                )
            except Exception:
                pass

        return report


AccountVaultProxySubagent = MultiAccountVaultAndProxySubagent

