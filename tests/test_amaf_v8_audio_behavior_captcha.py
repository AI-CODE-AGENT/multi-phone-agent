import os
import tempfile
import unittest

from agents.audio_behavior_captcha_subagent import (
    InteractiveAudioAndBehaviorCaptchaSubagent,
)
from core.audio_behavior_captcha_engine import AudioAndBehaviorCaptchaEngine


class TestAMAFV8AudioBehaviorCaptcha(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = AudioAndBehaviorCaptchaEngine()
        self.subagent = InteractiveAudioAndBehaviorCaptchaSubagent()
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_audio_captcha_wav_synth_and_fft_decode(self) -> None:
        wav_path = os.path.join(self.temp_dir.name, "captcha_4829.wav")
        saved = self.engine.generate_synthetic_audio_captcha_wav(
            save_path=wav_path, digits_str="4829", sample_rate=8000
        )
        self.assertTrue(os.path.exists(saved))

        res = self.engine.solve_audio_captcha_wav(saved)
        self.assertEqual(res["decoded_digits"], "4829")
        self.assertEqual(res["segments_count"], 4)
        self.assertGreaterEqual(res["confidence"], 0.95)
        self.assertEqual(res["method"], "pcm_rms_fft_digit_decoder")

    def test_human_behavioral_trajectory_minimum_jerk(self) -> None:
        traj = self.engine.generate_human_behavioral_trajectory(
            start_xy=(120, 960),
            end_xy=(640, 380),
            duration_ms=620,
            num_points=28,
        )
        self.assertEqual(traj["num_points"], 28)
        self.assertEqual(len(traj["points"]), 28)
        self.assertGreaterEqual(traj["anti_bot_human_score"], 0.92)
        self.assertLessEqual(traj["anti_bot_human_score"], 1.0)
        self.assertGreater(traj["velocity_variance"], 0.0)
        self.assertGreater(traj["curvature_entropy"], 0.0)
        self.assertAlmostEqual(traj["points"][0]["x"], 120.0, places=1)
        self.assertAlmostEqual(traj["points"][0]["y"], 960.0, places=1)
        self.assertAlmostEqual(traj["points"][-1]["x"], 640.0, places=1)
        self.assertAlmostEqual(traj["points"][-1]["y"], 380.0, places=1)

    def test_dice_sum_captcha_cv_solver(self) -> None:
        img_path = os.path.join(self.temp_dir.name, "dice_3_5_2.png")
        saved = self.engine.generate_synthetic_dice_sum_captcha(
            save_path=img_path, dice_values=[3, 5, 2]
        )
        self.assertTrue(os.path.exists(saved))

        res = self.engine.solve_dice_sum_captcha_cv(saved)
        self.assertEqual(res["dice_values"], [3, 5, 2])
        self.assertEqual(res["total_sum"], 10)
        self.assertEqual(res["method"], "numpy_pip_cluster_counter")

    def test_interactive_subagent_end_to_end_modes(self) -> None:
        wav_path = os.path.join(self.temp_dir.name, "subagent_audio.wav")
        self.engine.generate_synthetic_audio_captcha_wav(wav_path, digits_str="4829")

        res_audio = self.subagent.solve_audio_or_behavioral_challenge(
            serial="emulator-5554",
            challenge_type="AUDIO_CAPTCHA",
            wav_path=wav_path,
        )
        self.assertEqual(res_audio["status"], "solved")
        self.assertEqual(res_audio["decoded_digits"], "4829")
        self.assertEqual(res_audio["answer"], "4829")
        self.assertGreaterEqual(res_audio["anti_bot_human_score"], 0.92)

        img_path = os.path.join(self.temp_dir.name, "subagent_dice.png")
        self.engine.generate_synthetic_dice_sum_captcha(img_path, dice_values=[3, 5, 2])

        res_dice = self.subagent.solve_audio_or_behavioral_challenge(
            serial="emulator-5554",
            challenge_type="AUTO",
            image_path=img_path,
        )
        self.assertEqual(res_dice["challenge_type"], "DICE_SUM_CAPTCHA")
        self.assertEqual(res_dice["total_sum"], 10)
        self.assertEqual(res_dice["answer"], "10")

        res_behav = self.subagent.solve_audio_or_behavioral_challenge(
            serial="emulator-5554",
            challenge_type="BEHAVIORAL_ENTROPY",
        )
        self.assertEqual(res_behav["challenge_type"], "BEHAVIORAL_ENTROPY")
        self.assertGreaterEqual(res_behav["anti_bot_human_score"], 0.92)


if __name__ == "__main__":
    unittest.main()
