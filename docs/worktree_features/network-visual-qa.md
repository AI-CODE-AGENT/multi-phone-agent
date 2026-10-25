# Feature Worktree: Network & Visual QA Subagent (#20)

- **Subagent Owner**: `NetworkAndVisualQASubagent`
- **Worktree Path**: `D:/Project/multi-phone-agent-worktrees/network-visual-qa`
- **Branch**: `feat/network-visual-qa`
- **Capabilities**: 48dp touch target sizing verification (`SMALL_TOUCH_TARGET`), missing accessibility label detection (`MISSING_ACCESSIBILITY_LABEL`), overlapping interactive sibling detection (`OVERLAPPING_CLICKABLES`), layout health scoring (`layout_health_score`), and Chaos Monkey Wi-Fi toggle network resilience verification (`NETWORK_RESILIENCE_VERIFIED`).

## Overview

`NetworkAndVisualQASubagent` (Subagent #20), inspired by Google Accessibility Scanner and Netflix Chaos Monkey, provides visual layout/accessibility auditing and network transition resilience checks for multi-app testing:
1. **`audit_ui_accessibility_and_layout(serial, xml_override=None)`**: Parses the UIAutomator XML hierarchy and inspects clickable elements (`clickable="true"`) for:
   - **Small Touch Target (`SMALL_TOUCH_TARGET`)**: Bounding box width `< 48` or height `< 48`.
   - **Missing Accessibility Label (`MISSING_ACCESSIBILITY_LABEL`)**: Both `text` and `content-desc` are empty on a clickable element.
   - **Overlapping Interactive Bounds (`OVERLAPPING_CLICKABLES`)**: Two clickable sibling elements overlap by `> 50%` of the smaller element's area.
   - Computes `layout_health_score` (`0..100`, starting at `100` and deducting `5` per warning, minimum `50`).
2. **`run_network_resilience_check(serial, package, toggle_wifi=True)`**: Tests application stability across brief network transitions (`svc wifi disable` followed immediately by `svc wifi enable`), launches/verifies `package`, and scans `logcat -d -t 60` for `FATAL EXCEPTION` or `ANR in {package}`.
