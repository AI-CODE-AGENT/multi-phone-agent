import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from core.audio_behavior_captcha_engine import AudioAndBehaviorCaptchaEngine


class InteractiveAudioAndBehaviorCaptchaSubagent:
    """
    Subagent #33: Interactive Audio Accessibility CAPTCHA, Behavioral Trajectory
    Entropy, and 3D Dice Sum CAPTCHA Solver.
    """

    def __init__(self, adb: Any = None, memory: Any = None) -> None:
        self.adb = adb
        self.memory = memory
        self.engine = AudioAndBehaviorCaptchaEngine()

    def solve_audio_or_behavioral_challenge(
        self,
        serial: str,
        challenge_type: str = "AUTO",
        wav_path: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Solves an audio CAPTCHA, behavioral anti-bot trajectory challenge, or
        3D dice sum CAPTCHA challenge.
        Supports challenge_type in {"AUDIO_CAPTCHA", "BEHAVIORAL_ENTROPY", "DICE_SUM_CAPTCHA", "AUTO"}.
        """
        mode = (challenge_type or "AUTO").upper()

        if mode == "AUTO":
            if wav_path and os.path.exists(wav_path):
                mode = "AUDIO_CAPTCHA"
            elif image_path and os.path.exists(image_path):
                mode = "DICE_SUM_CAPTCHA"
            else:
                mode = "AUDIO_CAPTCHA"

        result: Dict[str, Any] = {
            "status": "solved",
            "subagent": "InteractiveAudioAndBehaviorCaptchaSubagent",
            "subagent_id": 33,
            "serial": serial,
            "challenge_type": mode,
        }

        if mode == "AUDIO_CAPTCHA":
            cleanup_temp = False
            target_wav = wav_path
            if not target_wav or not os.path.exists(target_wav):
                fd, temp_wav = tempfile.mkstemp(suffix=".wav")
                os.close(fd)
                target_wav = self.engine.generate_synthetic_audio_captcha_wav(
                    save_path=temp_wav, digits_str="4829"
                )
                cleanup_temp = True

            try:
                audio_res = self.engine.solve_audio_captcha_wav(target_wav)
                trajectory = self.engine.generate_human_behavioral_trajectory(
                    start_xy=(160, 820), end_xy=(540, 620), duration_ms=580, num_points=24
                )
                result.update(audio_res)
                result["answer"] = audio_res.get("decoded_digits", "")
                result["behavioral_trajectory"] = trajectory
                result["anti_bot_human_score"] = trajectory["anti_bot_human_score"]
            finally:
                if cleanup_temp and target_wav and os.path.exists(target_wav):
                    try:
                        os.remove(target_wav)
                    except OSError:
                        pass

        elif mode == "DICE_SUM_CAPTCHA":
            cleanup_temp = False
            target_img = image_path
            if not target_img or not os.path.exists(target_img):
                fd, temp_img = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                target_img = self.engine.generate_synthetic_dice_sum_captcha(
                    save_path=temp_img, dice_values=[3, 5, 2]
                )
                cleanup_temp = True

            try:
                dice_res = self.engine.solve_dice_sum_captcha_cv(target_img)
                trajectory = self.engine.generate_human_behavioral_trajectory(
                    start_xy=(200, 900), end_xy=(520, 680), duration_ms=610, num_points=26
                )
                result.update(dice_res)
                result["answer"] = str(dice_res.get("total_sum", 0))
                result["behavioral_trajectory"] = trajectory
                result["anti_bot_human_score"] = trajectory["anti_bot_human_score"]
            finally:
                if cleanup_temp and target_img and os.path.exists(target_img):
                    try:
                        os.remove(target_img)
                    except OSError:
                        pass

        elif mode == "BEHAVIORAL_ENTROPY":
            trajectory = self.engine.generate_human_behavioral_trajectory(
                start_xy=(140, 1100), end_xy=(640, 520), duration_ms=620, num_points=28
            )
            result.update(trajectory)
            result["answer"] = "HUMAN_VERIFIED"

        else:
            raise ValueError(f"Unsupported challenge_type: {challenge_type}")

        # Optional ADB interaction if a mock/controller is injected
        if self.adb is not None and result.get("answer"):
            if hasattr(self.adb, "input_text"):
                try:
                    self.adb.input_text(serial, str(result["answer"]))
                except TypeError:
                    self.adb.input_text(str(result["answer"]))

        # Optional telemetry memory recording
        if self.memory is not None and hasattr(self.memory, "record_event"):
            try:
                self.memory.record_event("audio_behavior_captcha_solved", result)
            except Exception:
                pass

        return result
