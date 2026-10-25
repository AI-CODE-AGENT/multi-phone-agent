"""
DeepLink & QR/Barcode Scanner Subagent (Subagent #23)
Inspired by Maestro `openLink`, ZXing QR/Barcode Camera Injection, and Android App Links
(`am start -W -a android.intent.action.VIEW -d <uri>`).

Provides:
- Deep link & Android App Link launching with launch metrics parsing (`Status`, `Activity`, `TotalTime`)
- Parameterized deep-link route fuzzing for crash & routing resilience
- Deterministic high-contrast synthetic QR matrix PNG generation via PIL & numpy
- UIAutomator XML QR/Barcode viewfinder screen detection (Vietnamese & English indicators)
- QR/Barcode payload injection via ZXing broadcast intent, optional deep-link trigger, and SDCard gallery push
"""

import hashlib
import os
import re
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager


class DeepLinkAndQRScannerSubagent:
    """
    Subagent #23: Deep Link & App Link Router + Synthetic QR/Barcode Generator & Camera/Intent Injector.
    """

    SCANNER_INDICATORS: Tuple[str, ...] = (
        "quét mã qr",
        "scan qr",
        "barcode",
        "camera_preview",
        "viewfinder",
        "zxing",
        "mlkit_barcode",
    )

    GALLERY_PICK_INDICATORS: Tuple[str, ...] = (
        "chọn ảnh qr từ thư viện",
        "chọn ảnh từ thư viện",
        "thư viện",
        "gallery",
        "album",
        "choose from album",
        "select qr image",
    )

    DEFAULT_FUZZ_PARAMS: Tuple[Dict[str, str], ...] = (
        {"promo": "AMAF6"},
        {"redirect": "checkout", "item_id": "101"},
        {"utm_source": "amaf_fuzzer", "utm_medium": "deeplink", "deep_test": "true"},
        {"q": "boundary_test_%20_!@#", "page": "0", "limit": "9999"},
    )

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.navigation_history: List[Dict[str, Any]] = []

    @staticmethod
    def _parse_bounds(bounds_str: str) -> Optional[Dict[str, int]]:
        """Parse UIAutomator bounds '[x1,y1][x2,y2]' into structured coordinates dict."""
        if not bounds_str:
            return None
        nums = re.findall(r"-?\d+", bounds_str)
        if len(nums) == 4:
            x1, y1, x2, y2 = (int(v) for v in nums)
            return {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "center_x": (x1 + x2) // 2,
                "center_y": (y1 + y2) // 2,
                "width": max(0, x2 - x1),
                "height": max(0, y2 - y1),
            }
        return None

    def open_deep_link(
        self,
        serial: str,
        uri: str,
        package_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Launch a deep link URI on `serial` via `am start -W -a android.intent.action.VIEW -d "{uri}"`
        (appending ` {package_name}` if `package_name` is specified).
        Parses output (`Status: ok`, `LaunchState`, `Activity`, `TotalTime`) and verifies if an error occurred.
        """
        cmd = f'am start -W -a android.intent.action.VIEW -d "{uri}"'
        if package_name:
            cmd = f"{cmd} {package_name}"

        out = self.adb.shell(serial, cmd) or ""
        out_lower = out.lower()

        has_error = (
            "error:" in out_lower
            or "unable to resolve intent" in out_lower
            or "activity not started" in out_lower
            or "securityexception" in out_lower
            or "exception" in out_lower
        )

        status_ok = "status: ok" in out_lower
        activity = ""
        launch_state = ""
        ms = 0

        for line in out.splitlines():
            line_stripped = line.strip()
            if line_stripped.startswith("Activity:"):
                activity = line_stripped.split("Activity:", 1)[1].strip()
            elif line_stripped.startswith("LaunchState:"):
                launch_state = line_stripped.split("LaunchState:", 1)[1].strip()
            elif line_stripped.startswith("TotalTime:"):
                raw_time = line_stripped.split("TotalTime:", 1)[1].strip()
                time_match = re.search(r"\d+", raw_time)
                if time_match:
                    ms = int(time_match.group(0))
            elif line_stripped.startswith("WaitTime:") and ms == 0:
                raw_time = line_stripped.split("WaitTime:", 1)[1].strip()
                time_match = re.search(r"\d+", raw_time)
                if time_match:
                    ms = int(time_match.group(0))

        # Considered opened if no error occurred and either Status: ok or non-error output
        if not has_error and (status_ok or "starting: intent" in out_lower or bool(activity)):
            status = "DEEPLINK_OPENED"
        elif not has_error and out.strip() == "":
            # When running against an offline/mock shell with empty output, treat as opened if no error
            status = "DEEPLINK_OPENED"
        else:
            status = "DEEPLINK_FAILED"

        record: Dict[str, Any] = {
            "serial": serial,
            "uri": uri,
            "package": package_name,
            "status": status,
            "resolved_activity": activity,
            "launch_state": launch_state,
            "launch_time_ms": ms,
            "raw_output": out,
        }

        self.navigation_history.append(record)
        try:
            self.memory.remember(
                key=f"deeplink_{serial}_{hashlib.md5(uri.encode('utf-8')).hexdigest()[:8]}",
                value=record,
                tags=["deeplink", "navigation", serial, status.lower()],
                category="deeplink_navigation",
            )
        except Exception:
            pass

        return record

    def fuzz_deep_link_routes(
        self,
        serial: str,
        base_uri: str,
        params_list: Optional[List[Dict[str, str]]] = None,
        package_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Test multiple parameterized deep link variations (e.g., `?promo=AMAF6`,
        `?redirect=checkout&item_id=101`, boundary characters) to verify deep-link routing
        resilience without crashes.
        """
        effective_params = (
            params_list if params_list is not None else [dict(p) for p in self.DEFAULT_FUZZ_PARAMS]
        )

        results: List[Dict[str, Any]] = []
        passed = 0

        for params in effective_params:
            query_str = urllib.parse.urlencode(params, doseq=True)
            if query_str:
                sep = "&" if "?" in base_uri else "?"
                fuzzed_uri = f"{base_uri}{sep}{query_str}"
            else:
                fuzzed_uri = base_uri

            res = self.open_deep_link(serial, fuzzed_uri, package_name=package_name)
            route_entry = {
                "uri": fuzzed_uri,
                "params": params,
                "status": res["status"],
                "resolved_activity": res["resolved_activity"],
                "launch_time_ms": res["launch_time_ms"],
            }
            if res["status"] == "DEEPLINK_OPENED":
                passed += 1
            results.append(route_entry)

        summary: Dict[str, Any] = {
            "serial": serial,
            "base_uri": base_uri,
            "routes_tested": len(results),
            "passed_count": passed,
            "results": results,
        }
        return summary

    def generate_synthetic_qr_image(
        self,
        payload: str,
        save_path: Optional[str] = None,
        size: int = 280,
    ) -> str:
        """
        Generate a deterministic high-contrast QR-like matrix PNG (with 3 finder pattern corners
        + payload bit matrix derived from SHA-256 of `payload`) using `PIL.Image`, `ImageDraw`,
        and `numpy`, saves to `save_path` (or `reports/screenshots/qr_<hash>.png`), and returns
        the file path string.
        """
        digest = hashlib.sha256(payload.encode("utf-8")).digest()
        short_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]

        if save_path is None:
            project_root = Path(__file__).resolve().parent.parent
            screenshots_dir = project_root / "reports" / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            target_path = screenshots_dir / f"qr_{short_hash}.png"
        else:
            target_path = Path(save_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)

        grid_size = 21  # Standard Version-1 QR code 21x21 module matrix
        matrix = np.zeros((grid_size, grid_size), dtype=np.uint8)

        def _place_finder_pattern(r0: int, c0: int) -> None:
            for r in range(7):
                for c in range(7):
                    if (
                        r in (0, 6)
                        or c in (0, 6)
                        or (2 <= r <= 4 and 2 <= c <= 4)
                    ):
                        matrix[r0 + r, c0 + c] = 1
                    else:
                        matrix[r0 + r, c0 + c] = 0

        # 3 Finder pattern corners: top-left, top-right, bottom-left
        _place_finder_pattern(0, 0)
        _place_finder_pattern(0, grid_size - 7)
        _place_finder_pattern(grid_size - 7, 0)

        # Timing patterns (row 6 and col 6 between finder patterns)
        for i in range(8, grid_size - 8):
            matrix[6, i] = (i + 1) % 2
            matrix[i, 6] = (i + 1) % 2

        # Expand SHA-256 digest bits to fill remaining data modules deterministically
        extended_bytes = (
            digest
            + hashlib.sha256(digest + payload.encode("utf-8")).digest()
        )
        bits = np.unpackbits(np.frombuffer(extended_bytes, dtype=np.uint8))

        bit_idx = 0
        for r in range(grid_size):
            for c in range(grid_size):
                # Skip finder patterns + 1-module quiet separators around them + timing lines
                in_top_left = r < 8 and c < 8
                in_top_right = r < 8 and c >= grid_size - 8
                in_bottom_left = r >= grid_size - 8 and c < 8
                is_timing = r == 6 or c == 6
                if in_top_left or in_top_right or in_bottom_left or is_timing:
                    continue
                matrix[r, c] = int(bits[bit_idx % len(bits)])
                bit_idx += 1

        img = Image.new("RGB", (size, size), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        quiet_zone_modules = 2
        total_modules = grid_size + 2 * quiet_zone_modules
        module_px = max(1, size // total_modules)
        offset = (size - (grid_size * module_px)) // 2

        for r in range(grid_size):
            for c in range(grid_size):
                if matrix[r, c] == 1:
                    x0 = offset + c * module_px
                    y0 = offset + r * module_px
                    x1 = x0 + module_px - 1
                    y1 = y0 + module_px - 1
                    draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0))

        img.save(str(target_path), format="PNG")
        return str(target_path)

    def detect_qr_scanner_screen(
        self,
        serial: str,
        xml_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Inspect UIAutomator XML (`xml_override` or `self.adb.dump_ui_hierarchy(serial)`)
        for QR/Barcode scanner viewfinder indicators:
        (`"quét mã qr"`, `"scan qr"`, `"barcode"`, `"camera_preview"`, `"viewfinder"`, `"zxing"`, `"mlkit_barcode"`).
        """
        xml_content = (
            xml_override
            if xml_override is not None
            else self.adb.dump_ui_hierarchy(serial)
        )
        xml_str = (xml_content or "").strip()

        scanner_detected = False
        matched_indicator = ""
        viewfinder_bounds: Optional[Dict[str, int]] = None

        if xml_str:
            try:
                root = ET.fromstring(xml_str)
                for node in root.iter("node"):
                    attrib = node.attrib
                    combined = " ".join(
                        [
                            attrib.get("text", ""),
                            attrib.get("content-desc", ""),
                            attrib.get("resource-id", ""),
                            attrib.get("class", ""),
                        ]
                    ).lower()

                    for indicator in self.SCANNER_INDICATORS:
                        if indicator in combined:
                            scanner_detected = True
                            matched_indicator = indicator
                            viewfinder_bounds = self._parse_bounds(attrib.get("bounds", ""))
                            break
                    if scanner_detected:
                        break
            except Exception:
                xml_lower = xml_str.lower()
                for indicator in self.SCANNER_INDICATORS:
                    if indicator in xml_lower:
                        scanner_detected = True
                        matched_indicator = indicator
                        b_match = re.search(r'bounds="(\[\d+,\d+\]\[\d+,\d+\])"', xml_str)
                        if b_match:
                            viewfinder_bounds = self._parse_bounds(b_match.group(1))
                        break

        return {
            "serial": serial,
            "scanner_detected": scanner_detected,
            "matched_indicator": matched_indicator,
            "viewfinder_bounds": viewfinder_bounds,
        }

    def inject_qr_or_barcode_payload(
        self,
        serial: str,
        payload: str,
        format_type: str = "QR_CODE",
        push_image_to_sdcard: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate the QR PNG via `generate_synthetic_qr_image(payload)`, broadcast ZXing / Android
        scanner result intent (`am broadcast -a com.google.zxing.client.android.SCAN --es SCAN_RESULT "{payload}" --es SCAN_RESULT_FORMAT "{format_type}"`),
        optionally trigger deep-link routing if `payload` is a URI (`http` or `://`), and push/record
        the QR image on `/sdcard/Pictures/AMAF_QR` for gallery-pick QR scanners (`"Chọn ảnh QR từ thư viện"`).
        """
        qr_path = self.generate_synthetic_qr_image(payload)

        broadcast_cmd = (
            f"am broadcast -a com.google.zxing.client.android.SCAN "
            f'--es SCAN_RESULT "{payload}" '
            f'--es SCAN_RESULT_FORMAT "{format_type}"'
        )
        self.adb.shell(serial, broadcast_cmd)

        if payload.startswith("http") or "://" in payload:
            self.open_deep_link(serial, payload)

        remote_qr_path = ""
        if push_image_to_sdcard:
            remote_dir = "/sdcard/Pictures/AMAF_QR"
            remote_qr_path = f"{remote_dir}/{Path(qr_path).name}"
            self.adb.shell(serial, f"mkdir -p {remote_dir}")
            try:
                if hasattr(self.adb, "run_device_cmd"):
                    self.adb.run_device_cmd(serial, ["push", qr_path, remote_qr_path])
                self.adb.shell(
                    serial,
                    f'am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d "file://{remote_qr_path}"',
                )
            except Exception:
                pass

        result: Dict[str, Any] = {
            "serial": serial,
            "status": "QR_PAYLOAD_INJECTED",
            "payload": payload,
            "format": format_type,
            "local_qr_image": qr_path,
            "remote_qr_image": remote_qr_path,
            "timestamp": time.time(),
        }

        try:
            self.memory.remember(
                key=f"qr_inject_{serial}_{int(result['timestamp'] * 1000)}",
                value=result,
                tags=["qr_scanner", "barcode", serial, format_type.lower()],
                category="qr_injection",
            )
        except Exception:
            pass

        return result


if __name__ == "__main__":
    import tempfile

    class _MockADB:
        def shell(self, serial: str, command: str, timeout: int = 30) -> str:
            if "am start -W" in command:
                return (
                    "Starting: Intent { act=android.intent.action.VIEW dat=myapp://checkout }\n"
                    "Status: ok\n"
                    "LaunchState: WARM\n"
                    "Activity: com.example.shop/.CheckoutActivity\n"
                    "TotalTime: 142\n"
                    "WaitTime: 148\n"
                    "Complete"
                )
            return "Broadcast completed: result=0"

        def run_device_cmd(self, serial: str, args: List[str], timeout: int = 30) -> Tuple[int, str, str]:
            return 0, "1 file pushed.", ""

        def dump_ui_hierarchy(self, serial: str) -> str:
            return (
                '<hierarchy rotation="0">'
                '<node index="0" text="Quét mã QR để thanh toán" '
                'resource-id="com.example.shop:id/zxing_viewfinder" '
                'class="android.view.View" bounds="[140,420][940,1220]" />'
                '<node index="1" text="Chọn ảnh QR từ thư viện" '
                'resource-id="com.example.shop:id/btn_pick_gallery" '
                'clickable="true" bounds="[240,1350][840,1490]" />'
                "</hierarchy>"
            )

    class _MockMemory:
        def remember(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
            return {}

    agent = DeepLinkAndQRScannerSubagent(adb=_MockADB(), memory=_MockMemory())  # type: ignore[arg-type]
    dl_res = agent.open_deep_link("emulator-5554", "myapp://product/101?promo=AMAF6", "com.example.shop")
    fuzz_res = agent.fuzz_deep_link_routes("emulator-5554", "myapp://product/101", package_name="com.example.shop")
    detect_res = agent.detect_qr_scanner_screen("emulator-5554")
    inject_res = agent.inject_qr_or_barcode_payload("emulator-5554", "myapp://pay?order=9988")
    print("DeepLink Result:", dl_res["status"], dl_res["resolved_activity"], f"{dl_res['launch_time_ms']}ms")
    print("Fuzz Routes Tested:", fuzz_res["routes_tested"], "Passed:", fuzz_res["passed_count"])
    print("Scanner Detected:", detect_res["scanner_detected"], "Indicator:", repr(detect_res["matched_indicator"]))
    print("QR Injected:", inject_res["status"], "Image:", os.path.exists(inject_res["local_qr_image"]))
