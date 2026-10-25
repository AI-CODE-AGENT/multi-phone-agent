# OEM Popup Watcher & Subagent #18 (`feat/oem-popup-watcher`)

## Overview
Real Android devices running Chinese and global OEM ROMs—especially **Vivo OriginOS / FuntouchOS**, **Xiaomi HyperOS / MIUI**, **OPPO / Realme ColorOS**, **Samsung OneUI**, and **Google Play Protect**—frequently intercept `adb install` and first-launch flows with modal security sheets (e.g. `"Tiếp tục cài đặt"`, `"Cho phép cài đặt qua USB"`, `"Install via USB"`). On Vivo OriginOS, the security overlay often masks button nodes from standard UIAutomator XML dumps.

## Key Components

### 1. `core/oem_popup_watcher.py` (`OEMPopupWatcher`)
- **`OEM_CONSENT_KEYWORDS`**: Multilingual dictionary of Vietnamese, English, and Chinese confirmation labels.
- **`OEM_SECURITY_PACKAGES`**: Package identifiers for Vivo, Xiaomi, OPPO/ColorOS, and Android package/permission controllers.
- **`VIVO_ORIGINOS_FALLBACK_BUTTON_COORDS`**: Normalized bottom-sheet coordinates `[(0.5, 0.88), (0.72, 0.90), (0.5, 0.92)]` scaled dynamically via `wm size` when UIAutomator dump hides security overlay nodes.
- **`scan_and_dismiss_oem_popup(serial, use_vivo_coordinate_fallback=False)`**: Dumps UI XML, checks `mCurrentFocus`, matches consent labels or OEM resource IDs, performs human-like micro-dwell touch swipes (`input swipe jx jy jx+1 jy+1 85`), and falls back to Vivo OriginOS bottom-sheet coordinates when appropriate.
- **`start_background_watcher` / `stop_background_watcher`**: Per-device background daemon threads that continuously clear OEM prompts.
- **`install_apk_with_oem_guard(serial, apk_path, timeout=90)`**: Wraps `adb -s <serial> install -r -g <apk_path>` inside an active background watcher (`interval_sec=0.6`, `use_vivo_fallback=True`).

### 2. `agents/oem_popup_guard_subagent.py` (`OEMPopupGuardSubagent` - Subagent #18)
- Integrates `OEMPopupWatcher` with `MemoryManager`.
- Exposes `guard_device(serial, use_vivo_fallback=False)` and `guarded_apk_install(serial, apk_path, timeout=90)`, recording all auto-confirmed popups and install telemetry into persistent codebase memory.
