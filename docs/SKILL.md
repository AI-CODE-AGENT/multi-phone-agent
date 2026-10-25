---
name: android-multi-agent-farm
description: Master skill for AI Agents to control, test, broadcast, and self-evolve mobile applications across Hybrid Real Physical Android Phones and 4 Ultra-Light Headless Android 15 Emulators via MCP Server 2.0 (18 Tools), REST API, or Python SDK.
---

# Android Multi-Agent Farm (AMAF 3.0) — Hybrid Real Phone Farm, Group Broadcast & 12-Subagent Self-Evolution Skill

Use this skill whenever an AI agent needs to interact with, test, debug, or orchestrate mobile applications across **multiple physical Android phones (USB & Wireless TCP/IP)** and **4 Ultra-Lightweight Headless Android 15 Emulators (`emulator-5554` to `emulator-5560`)**.

---

## 1. Architecture Overview (AMAF 3.0)

1. **Hybrid Real + Virtual Device Pool (`core/real_device_manager.py`)**:
   - Supports switching dynamically between `HYBRID` (4 Headless AVDs + N Real Phones), `AVD_ONLY`, and `REAL_ONLY` modes.
   - **Wireless ADB Provisioning**: Switch USB phones to TCP/IP (`adb tcpip 5555` -> `adb connect <IP>:5555`) with persistent auto-reconnect.
   - **Battery & Thermal Protection Guard**: Continuously monitors `dumpsys battery` temperature (°C) and level (%). Automatically dims display brightness (`15/255`), disables system animations (`0.0x`), and triggers `dumpsys battery unplug` cooling when temperature reaches `>= 42.0°C`.
2. **Synchronized Group Control Broadcaster (`core/group_control_broadcaster.py`)**:
   - Broadcasts tap, swipe, text input, hardware keys, app launches, and shell commands across N devices concurrently (`ThreadPoolExecutor`).
   - **Normalized Coordinate Scaling**: Automatically scales normalized coordinates `(0.0..1.0)` or reference `720x1600` coordinates to each target phone's real resolution (`1080x2400`, `1440x3200`, etc.).
3. **Zero-Cost (0 VND) Mock OTP & Hardware Simulation (`core/mock_otp_service.py` & `core/hardware_simulator.py`)**:
   - **Virtual AVDs**: Injects simulated SMS via `adb emu sms send`.
   - **Physical Real Phones**: Automatically falls back to broadcasting `com.amaf.MOCK_OTP` Intent + setting the Android system clipboard (`cmd clipboard set-text`) with 0 VND carrier cost.
4. **12 Specialized Subagents & Self-Evolution Loop (`agents/self_evolution_engine.py`)**:
   - `PlannerSubagent`, `OperatorSubagent`, `VisionPerceptionSubagent`, `SelfHealingSubagent` (6-Tier Recovery), `AuditorSubagent`, `SecurityAuditorSubagent` (OWASP Mobile Top 10), `PromptOptimizerSubagent`, `CodeImproverSubagent`, `RegressionVerifierSubagent`, `RealDeviceScoutSubagent`, `GroupSyncSubagent`, and `ExperienceMinerSubagent` (Mobile-Agent-E Macro Shortcut distillation).

---

## 2. All 18 MCP Tools (`mcp_bridge/android_farm_mcp_server.py`)

| # | Tool Name | Purpose |
| :--- | :--- | :--- |
| 1 | `android_list_devices` | List all available AVDs and Real Phones with lease lock & battery status. |
| 2 | `android_lease_device` | Acquire an exclusive per-device mutex lock before running tests. |
| 3 | `android_release_device` | Release the device lock upon completion. |
| 4 | `android_get_screen_state` | Capture screenshot PNG + parsed UIAutomator XML elements & bounds. |
| 5 | `android_tap_element` | Tap by dynamic text search or `(x, y)` coordinates. |
| 6 | `android_input_text` | Input text into the focused field. |
| 7 | `android_press_key` | Press `HOME`, `BACK`, `ENTER`, `APP_SWITCH`, `VOLUME_UP`, `VOLUME_DOWN`. |
| 8 | `android_mock_otp` | `generate`, `inject_sms`, `verify`, or `get_history` (0 VND cost on AVD & Real Phone). |
| 9 | `android_touch_fingerprint` | Pass `BiometricPrompt` via fingerprint simulation. |
| 10 | `android_set_gps` | Spoof GPS coordinates (`latitude`, `longitude`). |
| 11 | `android_run_kanban_task` | Execute end-to-end Kanban task lifecycle with 12 Subagents. |
| 12 | `android_discover_real_devices` | Scan physical phones (USB/Wi-Fi), inspect battery/temp, or switch `set_farm_mode` (`HYBRID`, `AVD_ONLY`, `REAL_ONLY`). |
| 13 | `android_connect_wireless_adb` | Convert USB phone to Wi-Fi ADB (`usb_to_wireless`) or connect to `IP:Port` (`connect_ip`). |
| 14 | `android_group_broadcast` | Synchronously broadcast `tap`, `swipe`, `text`, `key`, `launch_app`, or `shell` across `ALL`, `REAL_ONLY`, or `AVD_ONLY` devices with resolution scaling. |
| 15 | `android_device_health_guard` | Apply thermal & battery guard and animation optimization on a real phone. |
| 16 | `android_run_self_evolution_loop` | Trigger the 12-Subagent Autonomous Self-Evolution Engine. |
| 17 | `android_mine_experience_macros` | Query or list distilled Macro-Action shortcuts from `ExperienceMinerSubagent`. |
| 18 | `android_open_multi_scrcpy_wall` | Open a tiled desktop grid of Scrcpy windows for all online phones. |
| 19 | `android_manage_git_worktree` | Create, list, commit, or merge isolated Git feature worktrees (`D:\Project\multi-phone-agent-worktrees\<slug>`) for Subagent feature development. |

---

## 3. Repository & Git Worktree Locations
- **Main Repository (`main`)**: `D:\Project\multi-phone-agent` (`https://github.com/tan21072005/multi-phone-agent`)
- **Subagent Isolated Worktrees**: `D:\Project\multi-phone-agent-worktrees\<feature-slug>`
- **MCP Server Entrypoint**: `D:\Project\multi-phone-agent\mcp_bridge\android_farm_mcp_server.py`
