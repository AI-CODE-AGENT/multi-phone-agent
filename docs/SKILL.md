---
name: android-multi-agent-farm
description: Master skill for AI Agents to control, test, broadcast, orchestrate multi-app flows, crawl UI graphs, and self-evolve mobile applications across Hybrid Real Physical Android Phones and 4 Ultra-Light Headless Android 15 Emulators via MCP Server 2.0 (24 Tools), REST API, or Python SDK.
---

# Android Multi-Agent Farm (AMAF 4.0) — Hybrid Real Phone Farm, Multi-App Automation & 16-Subagent Self-Evolution Skill

Use this skill whenever an AI agent needs to interact with, test, debug, or orchestrate mobile applications across **multiple physical Android phones (USB & Wireless TCP/IP)** and **4 Ultra-Lightweight Headless Android 15 Emulators (`emulator-5554` to `emulator-5560`)**.

---

## 1. Architecture Overview (AMAF 4.0)

1. **Hybrid Real + Virtual Device Pool (`core/real_device_manager.py`)**:
   - Supports switching dynamically between `HYBRID` (4 Headless AVDs + N Real Phones), `AVD_ONLY`, and `REAL_ONLY` modes.
   - **Wireless ADB Provisioning**: Switch USB phones to TCP/IP (`adb tcpip 5555` -> `adb connect <IP>:5555`) with persistent auto-reconnect.
   - **Battery & Thermal Protection Guard**: Continuously monitors `dumpsys battery` temperature (°C) and level (%). Automatically dims display brightness (`15/255`), disables system animations (`0.0x`), and triggers `dumpsys battery unplug` cooling when temperature reaches `>= 42.0°C`.
2. **Synchronized Group Control Broadcaster (`core/group_control_broadcaster.py`)**:
   - Broadcasts tap, swipe, text input, hardware keys, app launches, and shell commands across N devices concurrently (`ThreadPoolExecutor`).
   - **Normalized Coordinate Scaling**: Automatically scales normalized coordinates `(0.0..1.0)` or reference `720x1600` coordinates to each target phone's real resolution (`1080x2400`, `1440x3200`, etc.).
3. **Multi-App Testing Automation (`core/multi_app_manager.py`)**:
   - **Package Discovery & Launcher Resolution**: Lists 3rd-party/system packages (`pm list packages -3`) and resolves main activities.
   - **Permission Auto-Grant & Clean State**: Batch-grants runtime permissions (`pm grant`) and overlay (`SYSTEM_ALERT_WINDOW`), clears app state (`pm clear`), and snapshots/restores checkpoints.
   - **Deep Link Routing & Maestro-Style Flows**: Launches Deep Links (`am start -W -a android.intent.action.VIEW -d <uri>`) with launch latency telemetry, and executes declarative multi-app step flows across 1 or N phones simultaneously.
4. **16 Specialized Subagents & Self-Evolution Loop (`agents/self_evolution_engine.py`)**:
   - `#1 PlannerSubagent`, `#2 OperatorSubagent`, `#3 VisionPerceptionSubagent`, `#4 SelfHealingSubagent` (6-Tier Recovery), `#5 AuditorSubagent`, `#6 SecurityAuditorSubagent` (OWASP Mobile Top 10), `#7 PromptOptimizerSubagent`, `#8 CodeImproverSubagent`, `#9 RegressionVerifierSubagent`, `#10 RealDeviceScoutSubagent`, `#11 GroupSyncSubagent`, `#12 ExperienceMinerSubagent`, `#13 CrossAppNotetakerSubagent` (Cross-app OTP/Order/URL/Clipboard bridge), `#14 ActionReflectorSubagent` (Pre/Post UI state transition verifier), `#15 MultiAppCrawlerSubagent` (DroidBot/Fastbot UI state-graph explorer), and `#16 WorktreeCoordinatorSubagent` (Git worktree isolation).

---

## 2. All 24 MCP Tools (`mcp_bridge/android_farm_mcp_server.py`)

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
| 11 | `android_run_kanban_task` | Execute end-to-end Kanban task lifecycle with autonomous Subagents. |
| 12 | `android_discover_real_devices` | Scan physical phones (USB/Wi-Fi), inspect battery/temp, or switch `set_farm_mode` (`HYBRID`, `AVD_ONLY`, `REAL_ONLY`). |
| 13 | `android_connect_wireless_adb` | Convert USB phone to Wi-Fi ADB (`usb_to_wireless`) or connect to `IP:Port` (`connect_ip`). |
| 14 | `android_group_broadcast` | Synchronously broadcast `tap`, `swipe`, `text`, `key`, `launch_app`, or `shell` across `ALL`, `REAL_ONLY`, or `AVD_ONLY` devices with resolution scaling. |
| 15 | `android_device_health_guard` | Apply thermal & battery guard and animation optimization on a real phone. |
| 16 | `android_run_self_evolution_loop` | Trigger the 16-Subagent Autonomous Self-Evolution Engine. |
| 17 | `android_mine_experience_macros` | Query or list distilled Macro-Action shortcuts from `ExperienceMinerSubagent`. |
| 18 | `android_open_multi_scrcpy_wall` | Open a tiled desktop grid of Scrcpy windows for all online phones. |
| 19 | `android_manage_git_worktree` | Create, list, commit, or merge isolated Git feature worktrees (`D:\Project\multi-phone-agent-worktrees\<slug>`) for Subagent feature development. |
| 20 | `android_list_installed_apps` | List installed 3rd-party or system packages on a target device. |
| 21 | `android_app_state_control` | `grant_permissions`, `clear_data`, `snapshot`, or `restore` app state. |
| 22 | `android_open_deep_link` | Route Deep Link / App Link URIs (`am start -W`) and measure launch latency (`TotalTime` ms). |
| 23 | `android_run_multi_app_flow` | Run Maestro-style declarative multi-app workflows across 1 or N phones with `CrossAppNotetakerSubagent`. |
| 24 | `android_crawl_app_graph` | Explore UI state transition graphs across one or multiple apps via `MultiAppCrawlerSubagent`. |

---

## 3. Repository & Git Worktree Locations
- **Main Repository (`main`)**: `D:\Project\multi-phone-agent` (`https://github.com/tan21072005/multi-phone-agent`)
- **Subagent Isolated Worktrees**: `D:\Project\multi-phone-agent-worktrees\<feature-slug>`
- **MCP Server Entrypoint**: `D:\Project\multi-phone-agent\mcp_bridge\android_farm_mcp_server.py`
