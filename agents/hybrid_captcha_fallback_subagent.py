"""
Subagent #40: Hybrid 3-Tier CAPTCHA Defense & Audio/API Fallback Subagent
=========================================================================
Wraps HybridCaptchaDefenseBridge to orchestrate:
- Tier 1: Zero-Token Local GPU/CV + CDP DOM + Bezier Touch
- Tier 2: Zero-Token Local STFT/CNN-CTC Audio Speech Decoder
- Tier 3: Optional Developer Sandbox Token Bridge (2Captcha / CapSolver / Anti-Captcha)
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.hybrid_captcha_defense_bridge import HybridCaptchaDefenseBridge


class HybridCaptchaFallbackSubagent:
    """Subagent #40: 3-Tier Hybrid CAPTCHA Defense & Audio/API Fallback Specialist."""

    SUBAGENT_ID = 40
    SUBAGENT_NAME = "HybridCaptchaFallbackSubagent"

    def __init__(self, adb: Any = None, memory: Any = None, confidence_threshold: float = 0.75):
        self.adb = adb
        self.memory = memory
        self.bridge = HybridCaptchaDefenseBridge(confidence_threshold=confidence_threshold)

    def solve_challenge_with_3tier_defense(
        self,
        serial: str = "10CF5L0TYL00312",
        challenge_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = dict(challenge_payload or {"type": "checkbox", "screen_size": (1260, 2800)})
        payload.setdefault("serial", serial)
        res = self.bridge.solve_captcha_3tier(payload)
        res["subagent_id"] = self.SUBAGENT_ID
        res["subagent_name"] = self.SUBAGENT_NAME
        res["serial"] = serial
        return res

    def run_3tier_self_audit(self, serial: str = "10CF5L0TYL00312") -> Dict[str, Any]:
        """Run a full 3-tier diagnostic verification across visual, audio, and token tiers."""
        t1 = self.solve_challenge_with_3tier_defense(serial, {"type": "checkbox"})
        t2 = self.solve_challenge_with_3tier_defense(
            serial, {"type": "audio", "expected_digits": "5924"}
        )
        t3 = self.solve_challenge_with_3tier_defense(
            serial, {"type": "token_api", "provider": "capsolver", "force_tier": 3}
        )
        summary = self.bridge.get_telemetry_summary()
        return {
            "status": "HYBRID_3TIER_READY",
            "subagent_id": self.SUBAGENT_ID,
            "serial": serial,
            "tier1_status": t1.get("status"),
            "tier2_audio_decoded": t2.get("transcription"),
            "tier3_provider": t3.get("provider"),
            "telemetry": summary,
        }
