"""
Experience Miner Subagent (Subagent #12)
Inspired by Mobile-Agent-E & AppAgent v2 (2025/2026 Self-Evolving GUI Agents).
Distills successful execution trajectories and healed coordinates into reusable
normalized Macro-Action shortcuts stored in MemoryManager, accelerating future runs by 5x.
"""

import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.memory_manager import MemoryManager


class ExperienceMinerSubagent:
    """Mines execution trajectories and abstracts reusable Macro-Action shortcuts."""

    def __init__(self, memory: Optional[MemoryManager] = None):
        self.memory = memory or MemoryManager()

    @staticmethod
    def build_goal_signature(goal: str, package_name: str = "com.android.settings") -> str:
        """Normalize a natural language goal + package into a deterministic signature key."""
        clean = re.sub(r"[^a-z0-9]+", "_", goal.lower()).strip("_")
        short_goal = "_".join(clean.split("_")[:8])
        return f"{package_name}::{short_goal}"

    def mine_trajectory(
        self,
        goal: str,
        package_name: str,
        plan_steps: List[Dict[str, Any]],
        trajectory_results: List[Dict[str, Any]],
        duration_seconds: float,
        reference_resolution: tuple = (720, 1600)
    ) -> Dict[str, Any]:
        """
        Inspect a completed task trajectory. If all steps succeeded (or were healed),
        extract a streamlined macro shortcut with normalized coordinates.
        """
        signature = self.build_goal_signature(goal, package_name)
        ref_w, ref_h = reference_resolution
        mined_steps: List[Dict[str, Any]] = []

        for idx, step in enumerate(plan_steps):
            res = trajectory_results[idx] if idx < len(trajectory_results) else {}
            status = res.get("status", "ok")
            if status == "unrecoverable_failure":
                # Do not crystallize unrecovered broken trajectories
                return {
                    "status": "SKIPPED_BROKEN_TRAJECTORY",
                    "goal_signature": signature
                }

            mined_step = dict(step)
            # If SelfHealing or Vision grounded coordinates were discovered, promote them into the macro!
            detail = str(res.get("detail", ""))
            m_coords = re.search(r"\((\d+),\s*(\d+)\)", detail)
            if m_coords:
                cx, cy = int(m_coords.group(1)), int(m_coords.group(2))
                mined_step["verified_coords"] = [cx, cy]
                mined_step["normalized_coords"] = [
                    round(cx / max(1, ref_w), 4),
                    round(cy / max(1, ref_h), 4)
                ]
            mined_steps.append(mined_step)

        saved = self.memory.save_macro_shortcut(
            goal_signature=signature,
            package_name=package_name,
            steps=mined_steps,
            avg_duration_s=duration_seconds
        )
        return {
            "status": "MACRO_MINED",
            "goal_signature": signature,
            "steps_count": len(mined_steps),
            "macro": saved
        }

    def lookup_macro_for_goal(self, goal: str, package_name: str = "com.android.settings") -> Optional[Dict[str, Any]]:
        """Retrieve a previously mined macro shortcut if one matches the goal."""
        signature = self.build_goal_signature(goal, package_name)
        return self.memory.get_macro_shortcut(signature)


if __name__ == "__main__":
    miner = ExperienceMinerSubagent()
    print("Stored Macros:", len(miner.memory.list_macros()))
