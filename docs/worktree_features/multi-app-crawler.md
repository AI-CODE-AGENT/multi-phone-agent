# Feature Worktree: DroidBot & ByteDance Fastbot Multi-App UI State-Graph Crawler

- **Subagent Owner**: `MultiAppCrawlerSubagent` (Subagent #15)
- **Worktree Path**: `D:/Project/multi-phone-agent-worktrees/multi-app-crawler`
- **Branch**: `feat/multi-app-crawler`
- **Module**: `agents/multi_app_crawler_subagent.py`
- **Capabilities**:
  - Parses UIAutomator XML hierarchies (`extract_interactive_nodes`) to discover interactive elements with bounding boxes and center `(cx, cy)` coordinates.
  - Builds deterministic SHA-256 UI state-transition graphs (`states` and `edges`) during single-app (`crawl_application`) and multi-app (`crawl_multiple_apps`) exploration while filtering destructive UI actions (`Delete`, `Reset`, `Sign out`, `Power off`).
  - Supports optional Fastbot/Monkey event burst injection (`run_monkey_burst`) and automatic logcat crash/ANR detection (`FATAL EXCEPTION`, `ANR in <package>`).
