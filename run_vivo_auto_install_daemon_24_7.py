"""
24/7 Persistent Auto-Install & OEM Popup Watcher Service (`run_vivo_auto_install_daemon_24_7.py`)
Automatically detects `PackageInterceptActivity` / OEM security dialogs on Vivo OriginOS (`10CF5L0TYL00312`)
and any connected Android phone, ticks 'Tôi đã hiểu kết quả phát hiện rủi ro của ứng dụng' (`input tap`),
and clicks 'Tiếp tục cài đặt' 100% automatically whenever ANY `adb install` or on-device APK install occurs.
"""

import os
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.adb_wrapper import ADBWrapper
from core.oem_popup_watcher import OEMPopupWatcher
from core.always_on_install_daemon import INSTALLER_WINDOW_TOKENS


LOG_FILE = PROJECT_ROOT / "logs" / "vivo_24_7_auto_install_daemon.log"


def log_msg(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def is_installer_window(focus_str: str) -> bool:
    if not focus_str:
        return False
    low = focus_str.lower()
    return any(tok in low for tok in INSTALLER_WINDOW_TOKENS)


def run_24_7_daemon(poll_interval_sec: float = 0.40) -> None:
    adb = ADBWrapper()
    watcher = OEMPopupWatcher(adb=adb)
    log_msg("🚀 Started 24/7 Persistent Vivo OriginOS Auto-Install & Checkbox Watcher Service...")

    last_device_scan_ts = 0.0
    cached_serials = ["10CF5L0TYL00312"]

    while True:
        try:
            now = time.time()
            if now - last_device_scan_ts >= 3.0:
                devices = adb.get_connected_devices()
                online = [d["serial"] for d in devices if d.get("status") == "device" and d.get("serial")]
                if online:
                    cached_serials = online
                last_device_scan_ts = now

            for serial in cached_serials:
                focus_out = adb.shell(
                    serial,
                    "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'",
                    timeout=3,
                ) or ""
                if is_installer_window(focus_out):
                    res = watcher.scan_and_dismiss_oem_popup(
                        serial,
                        use_vivo_coordinate_fallback=False,
                    )
                    if res.get("status") in ("POPUP_DISMISSED", "POPUP_DISMISSED_FALLBACK"):
                        log_msg(
                            f"✅ [{serial}] Auto-Handled Installer Dialog: status={res.get('status')} | "
                            f"checkbox_ticked={res.get('checkbox_ticked')} ({res.get('checkbox_info')}) | "
                            f"button={res.get('matched_label')} @ {res.get('tapped_coords')}"
                        )
                        # Brief settle pause after dismissing dialog so package installer transitions cleanly
                        time.sleep(0.8)
        except KeyboardInterrupt:
            log_msg("🛑 24/7 Watcher stopped by user.")
            break
        except Exception as exc:
            log_msg(f"⚠️ Watcher loop warning: {exc}")

        time.sleep(poll_interval_sec)


if __name__ == "__main__":
    run_24_7_daemon()
