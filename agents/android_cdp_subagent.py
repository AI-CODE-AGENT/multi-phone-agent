"""
Subagent #38: Android Chrome DevTools Protocol (CDP) Hardware Bridge Subagent (AMAF v9.0)

Wraps `AndroidCDPBridge` to provide zero-token DOM/WebView/Mini-Program inspection
via Android's internal Abstract Unix Domain Sockets (`@chrome_devtools_remote` and
`@JsEngine_*_devtools_remote`) paired with physical hardware touch injection
(`HumanTouchEngine` / `input swipe`) so `navigator.webdriver` remains `false` / `undefined`.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.android_cdp_bridge import AndroidCDPBridge
from core.human_touch_engine import HumanTouchEngine
from core.memory_manager import MemoryManager


class AndroidCDPSubagent:
    """
    Subagent #38: Bridges desktop Python directly to Android Chrome / WebView / Mini-App
    DevTools sockets (`@chrome_devtools_remote`, `@JsEngine_*_devtools_remote`) for
    100% deterministic DOM coordinate extraction and zero-flag physical touch execution.
    """

    SUBAGENT_ID = 38
    SUBAGENT_NAME = "AndroidCDPSubagent"

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
        touch_engine: Optional[HumanTouchEngine] = None,
        bridge: Optional[AndroidCDPBridge] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory
        self.touch_engine = touch_engine or HumanTouchEngine(adb=self.adb)
        self.bridge = bridge or AndroidCDPBridge(adb=self.adb, touch_engine=self.touch_engine)

    def discover_and_attach(
        self,
        serial: str,
        local_port: int = 9229,
        raw_unix_override: Optional[str] = None,
        mock_tabs_response: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Discovers active DevTools sockets on `serial`, forwards the primary socket to a
        local TCP port, and lists all debuggable browser/WebView tabs.
        """
        sockets = self.bridge.discover_devtools_sockets(
            serial=serial,
            raw_unix_override=raw_unix_override,
        )
        primary_socket = sockets[0] if sockets else "chrome_devtools_remote"

        forwarded = False
        active_port = local_port
        if sockets or mock_tabs_response is not None:
            if mock_tabs_response is None:
                forwarded = self.bridge.forward_socket(
                    serial=serial,
                    local_port=local_port,
                    socket_name=primary_socket,
                )
                active_port = self.bridge.active_forwards.get(
                    f"{serial}:{primary_socket}",
                    local_port,
                )
            else:
                forwarded = True

        tabs = self.bridge.list_open_tabs(
            local_port=active_port,
            mock_tabs_response=mock_tabs_response,
        )

        report = {
            "status": "CDP_BRIDGE_ATTACHED" if (forwarded and tabs) else "CDP_SOCKETS_INSPECTED",
            "subagent_id": self.SUBAGENT_ID,
            "subagent_name": self.SUBAGENT_NAME,
            "serial": serial,
            "discovered_sockets": sockets,
            "sockets_discovered": sockets,
            "primary_socket": primary_socket,
            "forwarded": forwarded,
            "local_port": active_port,
            "open_tabs": tabs,
            "tab_count": len(tabs),
            "tokens_used": 0,
            "timestamp": time.time(),
        }
        self._remember(serial, "discover_and_attach", report)
        return report

    def inspect_and_tap_via_cdp(
        self,
        serial: str,
        selector_or_type: str = "auto",
        screen_size: Tuple[int, int] = (1260, 2800),
        perform_tap: bool = True,
        mock_tabs: Optional[List[Dict[str, Any]]] = None,
        mock_eval_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Locates a CAPTCHA widget or DOM element via read-only CDP `Runtime.evaluate`,
        converts its CSS coordinates into physical Android screen coordinates, and optionally
        taps it via the physical `HumanTouchEngine` so `navigator.webdriver` stays clean.
        """
        if perform_tap:
            res = self.bridge.tap_dom_element_physically(
                serial=serial,
                selector=selector_or_type,
                touch_engine=self.touch_engine,
                screen_size=screen_size,
                mock_tabs=mock_tabs,
                mock_eval_result=mock_eval_result,
            )
        else:
            loc = self.bridge.locate_captcha_or_element_via_cdp(
                serial=serial,
                selector_or_type=selector_or_type,
                screen_size=screen_size,
                mock_tabs=mock_tabs,
                mock_eval_result=mock_eval_result,
            )
            res = {
                "status": loc.get("status", "ELEMENT_LOCATED"),
                "serial": serial,
                "selector": selector_or_type,
                "matched_type": loc.get("matched_type"),
                "phys_x": loc.get("phys_x", 0),
                "phys_y": loc.get("phys_y", 0),
                "bounds": loc.get("bounds"),
                "location": loc,
                "tap_result": None,
                "webdriver_clean": not bool(loc.get("navigator_webdriver", False)),
                "tokens_used": 0,
            }

        res["subagent_id"] = self.SUBAGENT_ID
        res["subagent_name"] = self.SUBAGENT_NAME
        res["tokens_used"] = 0
        self._remember(serial, f"inspect_and_tap:{selector_or_type}", res)
        return res

    def _remember(self, serial: str, action: str, payload: Dict[str, Any]) -> None:
        if self.memory is None or not hasattr(self.memory, "remember"):
            return
        try:
            self.memory.remember(
                content=f"[Subagent #38 AndroidCDPSubagent] {action} on {serial} -> {payload.get('status')}",
                tags=["android_cdp_subagent", "cdp", serial],
                metadata=payload,
            )
        except TypeError:
            try:
                self.memory.remember(
                    key=f"cdp_{serial}_{int(time.time() * 1000)}",
                    value=payload,
                    tags=["android_cdp_subagent", "cdp", serial],
                    category="android_cdp_bridge",
                )
            except Exception:
                pass
        except Exception:
            pass
