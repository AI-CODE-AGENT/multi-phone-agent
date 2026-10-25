# Human Touch Engine & Subagent #17 (`feat/human-touch-engine`)

## Overview
Implements biomechanical touch and gesture synthesis inspired by Google DeepMind `android_env`, `google-research/android_world`, `sarperavci/human_mouse`, and Fitts's Law motor-control modeling.

## Key Components

### 1. `core/human_touch_engine.py` (`HumanTouchEngine`)
- **Fitts's Law Gaussian Micro-Jitter (`apply_gaussian_jitter`)**: Adds `(random.gauss(0, sigma), random.gauss(0, sigma))` offsets around target coordinates and clamps within element bounds (with a 4px safety margin) or screen resolution bounds.
- **Minimum-Jerk Cubic Bézier Trajectory (`generate_bezier_trajectory`)**: Generates human trajectories with two randomized control points (`cp1`, `cp2`), an ease-in/ease-out minimum-jerk velocity profile (`t_eased = 3*t^2 - 2*t^3`), and optional human overshoot + micro-correction settle points when distance > 40px.
- **Rootless Finger-Dwell Tap (`human_tap`)**: Supports normalized `[0.0, 1.0]` coordinate scaling via `RealDeviceManager.get_device_resolution()`, applies Gaussian jitter, and executes a micro-swipe touch pressure window (`input swipe jx jy jx±1 jy±1 dwell`) compatible with all Android OEM ROMs (including Vivo OriginOS) without root.
- **Biomechanical Bézier Swipe (`human_bezier_swipe`)**: Dispatches a chained `input motionevent DOWN ... MOVE ... UP` gesture and automatically falls back to multi-segment Bézier `input swipe` commands if `motionevent` is unsupported on the target ROM.
- **Slider Puzzle CAPTCHA Drag (`human_slider_drag`)**: Performs an 18-step Cubic Bézier drag with vertical hand drift (`±3px`), overshoot, and settle correction.
- **Burst Cadence Typing (`human_type_text`)**: Types text in human bursts with natural inter-keystroke delays.

### 2. `agents/human_touch_subagent.py` (`HumanTouchSubagent` — Subagent #17)
- Wraps `HumanTouchEngine` and `MemoryManager`.
- Provides `execute_human_action(serial, action_spec)` supporting `tap`, `bezier_swipe`, `slider_drag`, and `type_text`, recording biomechanical gesture telemetry in `MemoryManager`.
