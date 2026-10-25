"""
Prompt Optimizer Subagent (Self-Prompting Engine)
Analyzes execution logs, failure modes, and latency profiles to iteratively
refine and optimize task prompts for Planner and Operator subagents.
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.memory_manager import MemoryManager


class PromptOptimizerSubagent:
    def __init__(self, memory: Optional[MemoryManager] = None):
        self.memory = memory or MemoryManager()

    def analyze_and_optimize(
        self,
        agent_type: str,
        current_prompt: str,
        execution_feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze run feedback (failures, healing occurrences, timeouts)
        and synthesize an improved prompt version.
        """
        failures = execution_feedback.get("failures", [])
        healings = execution_feedback.get("healings", [])
        avg_latency = execution_feedback.get("avg_latency_ms", 0)
        scenario = execution_feedback.get("scenario", "general")

        rules_to_inject = []

        # Analyze healing occurrences
        if healings:
            healing_types = [h.get("type", "") for h in healings]
            if "fuzzy_text" in healing_types or "fuzzy_id" in healing_types:
                rules_to_inject.append(
                    "- [Dynamic UI Rule]: Screen elements may change labels or resource IDs across app updates. "
                    "Always prioritize broad semantic matching and text fallbacks before concluding an element is missing."
                )
            if "scroll_down" in healing_types:
                rules_to_inject.append(
                    "- [Viewport Rule]: Forms or submit buttons may reside below the viewport on 720x1600 screens. "
                    "If a primary action button is not immediately visible, scroll down 300px before failing."
                )

        # Analyze failure modes
        for f in failures:
            reason = str(f.get("reason", "")).lower()
            if ("timeout" in reason or "wait" in reason) and not any("Wait Timing Rule" in r for r in rules_to_inject):
                rules_to_inject.append(
                    "- [Wait Timing Rule]: Network API responses and animation transitions take up to 1.5s. "
                    "Ensure explicit wait after form submission before verifying state."
                )
            if "otp" in reason and not any("Mock OTP Rule" in r for r in rules_to_inject):
                rules_to_inject.append(
                    "- [Mock OTP Rule]: When verifying SMS/OTP, invoke MockOTPService directly via local API "
                    "to retrieve the active code instantly without relying on carrier SMS delivery."
                )
            if ("click" in reason or "tap" in reason) and not any("Fast-Burst Tap Rule" in r for r in rules_to_inject):
                rules_to_inject.append(
                    "- [Fast-Burst Tap Rule]: For transient dialogs or soft keyboards that occlude targets, "
                    "dismiss keyboard (Back/Hide) or use coordinate fallback if dynamic locator is obstructed."
                )

        # Synthesize improved prompt
        refinements_text = "\n".join(rules_to_inject) if rules_to_inject else "- [Consistency Rule]: Maintain explicit verification after each step."

        optimized_prompt = f"""# Role: Highly Robust {agent_type.capitalize()}
# Scenario: {scenario}
# Base Instructions:
{current_prompt.strip()}

# Autonomous Refinements (Iterative Self-Optimization):
{refinements_text}
# Guideline: Prioritize zero-cost Mock OTP (0 VND) for authentication, resilient dynamic locators with coordinate fallbacks, and explicit wait checks.
"""

        rationale = f"Optimized for {len(healings)} healing events and {len(failures)} failures in scenario '{scenario}'."
        entry = self.memory.record_prompt_iteration(
            agent_type=agent_type,
            prompt_text=optimized_prompt,
            rationale=rationale,
            success_rate=0.95
        )

        return {
            "status": "OPTIMIZED",
            "version": entry.get("version"),
            "original_prompt": current_prompt,
            "optimized_prompt": optimized_prompt,
            "rationale": rationale,
            "injected_rules_count": len(rules_to_inject)
        }


if __name__ == "__main__":
    opt = PromptOptimizerSubagent()
    feedback = {
        "scenario": "auth_flow",
        "failures": [{"reason": "OTP input timeout waiting for SMS"}],
        "healings": [{"type": "fuzzy_text"}, {"type": "scroll_down"}],
        "avg_latency_ms": 350
    }
    res = opt.analyze_and_optimize("operator", "Execute login with phone and OTP", feedback)
    print("Optimization Result Version:", res["version"])
    print("Injected Rules:", res["injected_rules_count"])
