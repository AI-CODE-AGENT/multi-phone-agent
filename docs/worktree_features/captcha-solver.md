# Feature Worktree: CAPTCHA Solver Subagent (#19)

- **Subagent Owner**: `CaptchaSolverSubagent`
- **Worktree Path**: `D:/Project/multi-phone-agent-worktrees/captcha-solver`
- **Branch**: `feat/captcha-solver`
- **Capabilities**: Multi-class CAPTCHA detection (`SLIDER_PUZZLE`, `TEXT_MATH_OCR`, `CHECKBOX_CHALLENGE`, `IMAGE_GRID`, `NONE`), byte-entropy / deterministic slider gap offset estimation, 18-point Cubic Bézier human trajectory dragging with `+5px` overshoot and micro-settle correction, regex arithmetic solver, Gaussian-jittered 95ms dwell checkbox taps, and multi-tile image grid solving.

## Overview

`CaptchaSolverSubagent` (Subagent #19), inspired by `vsmutok/Puzzle-Captcha-Solver`, Google `android_world` M3A multimodal grounding, and Cubic Bézier human trajectories, provides closed-loop CAPTCHA detection and resolution:

1. **`detect_captcha_challenge(serial, xml_override)`**: Parses UIAutomator XML (with regex fallback) to classify active CAPTCHA challenges (`SLIDER_PUZZLE`, `TEXT_MATH_OCR`, `CHECKBOX_CHALLENGE`, `IMAGE_GRID`, or `NONE`) and extracts bounding boxes, slider track widths, arithmetic answers, or grid cell coordinates.
2. **`estimate_slider_gap_offset(serial, track_width, screenshot_path)`**: Computes a calibrated horizontal gap drag distance within `[int(track_width * 0.42), int(track_width * 0.78)]` (using byte-contrast entropy when a screenshot exists, or deterministic midpoint `int(track_width * 0.62)`).
3. **`_execute_bezier_slider_drag(serial, start_x, start_y, distance_px)`**: Synthesizes a 16-step Cubic Bézier curve with ease-in-out velocity, a `+5px` human overshoot (point 17), and a micro-correction settle back to `start_x + distance_px` (point 18), dispatched via chained `input motionevent DOWN/MOVE/UP` with swipe fallback.
4. **`solve_captcha(serial, xml_override, hint_distance_px)`**: Orchestrates detection and human-like execution across all four CAPTCHA modalities and records outcomes in `self.solve_history`.
