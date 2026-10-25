# Feature Worktree: Multi-App Automation Manager

- **Subagent Owner**: `MultiAppManagerSubagent`
- **Worktree Path**: `D:/Project/multi-phone-agent-worktrees/multi-app-manager`
- **Branch**: `feat/multi-app-manager`
- **Core Module**: `core/multi_app_manager.py` (`MultiAppAutomationManager`)
- **Capabilities**:
  - Installed package discovery (`list_installed_apps`) with offline fallback (`com.android.settings`, `com.android.chrome`, `com.google.android.apps.messaging`) and launcher activity resolution (`resolve_launcher_activity`).
  - Automated runtime permissions & `SYSTEM_ALERT_WINDOW` appops granting (`grant_all_runtime_permissions`) and app data clearing (`clear_app_data`).
  - Persistent app state snapshotting (`snapshot_app_state`) and restoration (`restore_app_state`) stored in `config/app_state_snapshots.json`.
  - Deep link intent launching with `TotalTime` launch latency telemetry (`open_deep_link`) and unredacted active notification parsing (`get_active_notifications`).
  - Maestro-inspired declarative multi-app flow execution (`run_declarative_multi_app_flow`) supporting `launchApp`, `clearState`, `grantPermissions`, `openLink`, `tapOn`, `inputText` (with `$NOTE:<key>` interpolation), `assertVisible`, `switchApp`, `injectMockOtp`, and `extractNote`.
