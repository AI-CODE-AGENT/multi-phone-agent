# Feature Worktree: Mobile-Agent-E Action Reflector Subagent (#14)

- **Subagent Owner**: `ActionReflectorSubagent`
- **Worktree Path**: `D:/Project/multi-phone-agent-worktrees/action-reflector`
- **Branch**: `feat/action-reflector`
- **Capabilities**: Pre/post-action UI transition verification, deterministic SHA-256 UI structural hashing (`ui_hash`), blocking permission & ANR/crash dialog detection, unexpected package switch verification, and stuck-screen detection (`NO_CHANGE_STUCK`).

## Overview

`ActionReflectorSubagent` (Subagent #14) implements the Mobile-Agent-E Action Reflector pattern for closed-loop mobile UI automation:
1. **`compute_ui_signature(xml_content, foreground_app)`**: Parses UIAutomator XML (with regex fallback) to count nodes, clickable elements, and text labels, computes a deterministic SHA-256 `ui_hash`, and flags permission or crash/ANR dialogs.
2. **`capture_state_snapshot(serial)`**: Queries the foreground app (`dumpsys window` / `dumpsys activity`) and dumps the live UIAutomator hierarchy to snapshot the device screen state.
3. **`reflect_on_action(serial, action, before_state, after_state, expected_package)`**: Compares `before_state` and `after_state` to classify the outcome (`CRASH_OR_ANR_DETECTED`, `PERMISSION_DIALOG_BLOCKED`, `UNEXPECTED_APP_SWITCH`, `NO_CHANGE_STUCK`, or `PROGRESS_VERIFIED`) and recommends the next recovery or continuation step.
