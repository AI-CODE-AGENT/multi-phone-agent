---
name: android-multi-agent-farm
description: Master skill for AI Agents to control, test, broadcast, execute human-like Cubic Bezier gestures, solve CAPTCHAs, auto-bypass Vivo/OriginOS USB install popups, orchestrate multi-app flows, and self-evolve mobile applications across Hybrid Real Physical Android Phones and 4 Headless Android 15 Emulators via MCP Server 2.0 (28 Tools), REST API, or Python SDK.
---

# Android Multi-Agent Farm (AMAF 5.0) — Hybrid Real Phone Farm, Human-Like Touch, CAPTCHA Solver, Vivo/OriginOS Guard & 20-Subagent Skill

Use this skill whenever an AI agent needs to interact with, test, debug, or orchestrate mobile applications across **multiple physical Android phones (USB & Wireless TCP/IP)** and **4 Ultra-Lightweight Headless Android 15 Emulators (`emulator-5554` to `emulator-5560`)**.

---

## 1. Architecture Overview (AMAF 5.0)

1. **Human-Like Biometric Touch Engine (`core/human_touch_engine.py` & `agents/human_touch_subagent.py`)**:
   - Inspired by Google DeepMind `android_env`, `google-research/android_world`, and Fitts's Law biomechanics.
   - **Gaussian Jitter & Finger Dwell (`human_tap`)**: Samples natural $(x + \mathcal{N}(0, \sigma), y + \mathcal{N}(0, \sigma))$ within element bounds with a `55ms–130ms` finger press dwell.
   - **Cubic Bézier Curve Trajectory & Overshoot (`human_bezier_swipe`, `human_slider_drag`)**: Generates non-linear minimum-jerk curves with acceleration, deceleration, and `+3..8px` overshoot + micro-correction via `input motionevent DOWN/MOVE/UP` or multi-segment micro-swipes.
2. **Vivo/OriginOS, Xiaomi HyperOS & OPPO ColorOS Popup Auto-Guard (`core/oem_popup_watcher.py` & `agents/oem_popup_guard_subagent.py`)**:
   - Automatically detects and clicks `"Tiếp tục cài đặt"`, `"Cho phép cài đặt qua USB"`, `"Continue installing"`, `"Install via USB"`, `"Vẫn cài đặt"`, and `"Install anyway"` both during runtime and inside a concurrent background thread during `adb install -r`.
   - Includes normalized bottom-sheet coordinate fallback (`(0.5, 0.88)`, `(0.72, 0.90)`) when Vivo OriginOS security overlays hide buttons from UIAutomator XML dumps.
3. **Automated CAPTCHA & Verification Solver (`agents/captcha_solver_subagent.py`)**:
   - Automatically detects and solves `SLIDER_PUZZLE` (Cubic Bézier drag with overshoot), `TEXT_MATH_OCR` (arithmetic/code evaluation + human typing), `CHECKBOX_CHALLENGE` (Gaussian jitter + dwell tap), and `IMAGE_GRID` challenges.
4. **20 Specialized Subagents & Self-Evolution Loop (`agents/self_evolution_engine.py`)**:
   - `#1 PlannerSubagent`, `#2 OperatorSubagent`, `#3 VisionPerceptionSubagent`, `#4 SelfHealingSubagent`, `#5 AuditorSubagent`, `#6 SecurityAuditorSubagent`, `#7 PromptOptimizerSubagent`, `#8 CodeImproverSubagent`, `#9 RegressionVerifierSubagent`, `#10 RealDeviceScoutSubagent`, `#11 GroupSyncSubagent`, `#12 ExperienceMinerSubagent`, `#13 CrossAppNotetakerSubagent`, `#14 ActionReflectorSubagent`, `#15 MultiAppCrawlerSubagent`, `#16 WorktreeCoordinatorSubagent`, `#17 HumanTouchSubagent`, `#18 OEMPopupGuardSubagent`, `#19 CaptchaSolverSubagent`, and `#20 NetworkAndVisualQASubagent`.

---

## 2. All 28 MCP Tools (`mcp_bridge/android_farm_mcp_server.py`)

| # | Tool Name | Purpose |
| :--- | :--- | :--- |
| 1–11 | Core Farm & Hardware Tools | `android_list_devices`, `android_lease_device`, `android_release_device`, `android_get_screen_state`, `android_tap_element`, `android_input_text`, `android_press_key`, `android_mock_otp`, `android_touch_fingerprint`, `android_set_gps`, `android_run_kanban_task` |
| 12–19 | Real Phone Farm, Broadcast & Worktrees | `android_discover_real_devices`, `android_connect_wireless_adb`, `android_group_broadcast`, `android_device_health_guard`, `android_run_self_evolution_loop`, `android_mine_experience_macros`, `android_open_multi_scrcpy_wall`, `android_manage_git_worktree` |
| 20–24 | Multi-App Testing & UI Crawler | `android_list_installed_apps`, `android_app_state_control`, `android_open_deep_link`, `android_run_multi_app_flow`, `android_crawl_app_graph` |
| 25 | `android_human_touch_action` | Execute human-like `tap` (Gaussian jitter + dwell), `bezier_swipe`, `slider_drag`, or `type_text`. |
| 26 | `android_oem_popup_guard` | Auto-click Vivo/OriginOS (`"Tiếp tục cài đặt"`, `"Cho phép cài đặt qua USB"`) & MIUI/ColorOS popups or run `guarded_install_apk`. |
| 27 | `android_solve_captcha` | Detect and solve `SLIDER_PUZZLE`, `TEXT_MATH_OCR`, `CHECKBOX_CHALLENGE`, and `IMAGE_GRID` CAPTCHAs. |
| 28 | `android_network_and_visual_qa` | Audit UI against Google Material `48dp` touch-target accessibility guidelines and verify Wi-Fi network toggle resilience. |

---

## 3. Repository & Git Worktree Locations
- **Main Repository (`main`)**: `D:\Project\multi-phone-agent` (`https://github.com/tan21072005/multi-phone-agent`)
- **Subagent Isolated Worktrees**: `D:\Project\multi-phone-agent-worktrees\<feature-slug>`
- **MCP Server Entrypoint**: `D:\Project\multi-phone-agent\mcp_bridge\android_farm_mcp_server.py`
