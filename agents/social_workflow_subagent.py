"""
Multi-App Social & Trust-Building Workflow Subagent (Subagent #39) - AMAF 9.0
Wraps `SocialWorkflowEngine` and `MemoryManager` to execute 100% Zero-Token
TikTok Multi-Account Engagement Workflows (`com.ss.android.ugc.trill`) and
11+ Website CAPTCHA & Anti-Bot Benchmark Patrols across physical Android devices
(e.g., Vivo V2417A `10CF5L0TYL00312` `1260x2800`) and emulators.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager
from core.social_workflow_engine import SocialWorkflowEngine


class SocialWorkflowSubagent:
    """
    Subagent #39: Autonomous Zero-Token Multi-App Social & Trust-Building Workflow Subagent.
    """

    SUBAGENT_ID = 39
    SUBAGENT_NAME = "SocialWorkflowSubagent"

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
        engine: Optional[SocialWorkflowEngine] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.engine = engine or SocialWorkflowEngine(adb=self.adb)
        self.workflow_history: List[Dict[str, Any]] = []

    def run_tiktok_account_switch_and_engage(
        self,
        serial: str,
        target_account: str = "nht.tn472",
        search_query: str = "tra dang",
        comment_text: str = "dinh quaa",
        dry_run: bool = False,
        resolution: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the 6-step Zero-Token TikTok account switch, search, watch, like,
        and comment workflow via `SocialWorkflowEngine` and record telemetry in memory.
        """
        res = self.engine.run_tiktok_account_switch_and_engage(
            serial=serial,
            target_account=target_account,
            search_query=search_query,
            comment_text=comment_text,
            dry_run=dry_run,
            resolution=resolution,
        )
        res["subagent_id"] = self.SUBAGENT_ID
        res["subagent_name"] = self.SUBAGENT_NAME
        self.workflow_history.append(res)

        try:
            self.memory.remember(
                key=f"tiktok_workflow_{serial}_{int(time.time() * 1000)}",
                value={
                    "status": res["status"],
                    "serial": serial,
                    "target_account": target_account,
                    "search_query": search_query,
                    "comment_text": comment_text,
                    "steps_completed": res["steps_completed"],
                    "tokens_used": res["tokens_used"],
                },
                tags=["social_workflow", "subagent_39", "tiktok", serial, target_account],
                category="social_workflow_engine",
            )
        except Exception:
            pass

        return res

    def run_tiktok_workflow(
        self,
        serial: str,
        target_account: str = "nht.tn472",
        search_query: str = "tra dang",
        comment_text: str = "dinh quaa",
        dry_run: bool = False,
        resolution: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        """Alias for `run_tiktok_account_switch_and_engage` used by Orchestrator & GUI."""
        return self.run_tiktok_account_switch_and_engage(
            serial=serial,
            target_account=target_account,
            search_query=search_query,
            comment_text=comment_text,
            dry_run=dry_run,
            resolution=resolution,
        )

    def run_full_11_website_captcha_patrol(
        self,
        serial: str,
        websites: Optional[List[str]] = None,
        dry_run: bool = False,
        include_extended_antibot: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute the 11+ Website CAPTCHA & Anti-Bot Benchmark Patrol in Chrome with
        0 AI tokens via `SocialWorkflowEngine` and record telemetry in memory.
        """
        res = self.engine.run_full_11_website_captcha_patrol(
            serial=serial,
            websites=websites,
            dry_run=dry_run,
            include_extended_antibot=include_extended_antibot,
        )
        res["subagent_id"] = self.SUBAGENT_ID
        res["subagent_name"] = self.SUBAGENT_NAME
        self.workflow_history.append(res)

        try:
            self.memory.remember(
                key=f"captcha_patrol_{serial}_{int(time.time() * 1000)}",
                value={
                    "status": res["status"],
                    "serial": serial,
                    "websites_total": res["websites_total"],
                    "websites_solved": res["websites_solved"],
                    "tokens_used": res["tokens_used"],
                },
                tags=["social_workflow", "subagent_39", "captcha_patrol", serial],
                category="social_workflow_engine",
            )
        except Exception:
            pass

        return res

    def run_tiktok_workflow(
        self,
        serial: str,
        target_account: str = "nht.tn472",
        search_query: str = "tra dang",
        comment_text: str = "dinh quaa",
        dry_run: bool = False,
        resolution: Optional[Tuple[int, int]] = None,
    ) -> Dict[str, Any]:
        """Alias for `run_tiktok_account_switch_and_engage` used by Orchestrator & GUI."""
        return self.run_tiktok_account_switch_and_engage(
            serial=serial,
            target_account=target_account,
            search_query=search_query,
            comment_text=comment_text,
            dry_run=dry_run,
            resolution=resolution,
        )

    def execute_combined_social_and_captcha_workflow(
        self,
        serial: str,
        target_account: str = "nht.tn472",
        search_query: str = "tra dang",
        comment_text: str = "dinh quaa",
        websites: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Run both the TikTok multi-account engagement workflow and the 11-website
        CAPTCHA benchmark patrol in a single deterministic Zero-Token session.
        """
        tiktok_res = self.run_tiktok_account_switch_and_engage(
            serial=serial,
            target_account=target_account,
            search_query=search_query,
            comment_text=comment_text,
            dry_run=dry_run,
        )
        patrol_res = self.run_full_11_website_captcha_patrol(
            serial=serial,
            websites=websites,
            dry_run=dry_run,
        )
        total_tokens = int(tiktok_res.get("tokens_used", 0)) + int(patrol_res.get("tokens_used", 0))
        return {
            "status": "COMBINED_SOCIAL_AND_CAPTCHA_COMPLETED",
            "subagent_id": self.SUBAGENT_ID,
            "subagent_name": self.SUBAGENT_NAME,
            "serial": serial,
            "tokens_used": total_tokens,
            "tiktok_workflow": tiktok_res,
            "captcha_patrol": patrol_res,
        }


if __name__ == "__main__":
    sub = SocialWorkflowSubagent()
    out = sub.execute_combined_social_and_captcha_workflow(
        serial="10CF5L0TYL00312",
        dry_run=True,
    )
    print(
        f"SocialWorkflowSubagent (#39): {out['status']} | "
        f"TikTok Steps={out['tiktok_workflow']['steps_completed']}/6 | "
        f"Websites={out['captcha_patrol']['websites_solved']}/{out['captcha_patrol']['websites_total']} | "
        f"Tokens={out['tokens_used']}"
    )
