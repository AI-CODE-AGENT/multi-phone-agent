"""
Subagent #41: PersistentADBStreamSubagent.

Wraps `PersistentADBStreamEngine` to provide zero-token persistent ADB shell
piping, compound touch bursts, and zero-flash-wear RAM screenshot streaming
for live preview and high-frequency farm automation.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.persistent_adb_stream_engine import PersistentADBStreamEngine


class PersistentADBStreamSubagent:
    """
    Subagent #41: Persistent ADB Shell Pipe & Fast Frame Streamer.
    Operates with ZERO AI tokens (`tokens_used == 0`) and zero `/sdcard/`
    flash writes (`flash_writes == 0`).
    """

    SUBAGENT_ID: int = 41
    SUBAGENT_NAME: str = "PersistentADBStreamSubagent"
    DEFAULT_SERIAL: str = "10CF5L0TYL00312"

    def __init__(self, adb_path: Optional[str] = None) -> None:
        self.engine = PersistentADBStreamEngine(adb_path=adb_path)

    def run_stream_benchmark(
        self,
        serial: str = DEFAULT_SERIAL,
    ) -> Dict[str, Any]:
        """
        Run a comprehensive benchmark of persistent shell command execution,
        compound touch burst pipelining, and RAM screenshot streaming.
        """
        t0 = time.perf_counter()

        # 1. Single persistent shell command ping
        session = self.engine.get_session(serial)
        ping_res = session.execute_fast_cmd("echo AMAF_PIPE_READY")

        # 2. Compound touch burst pipeline
        sample_burst: List[Dict[str, Any]] = [
            {"type": "tap", "x": 630, "y": 1400},
            {"type": "swipe", "x1": 630, "y1": 1800, "x2": 630, "y2": 900, "duration_ms": 150},
            {"type": "key", "keycode": 4},
        ]
        burst_res = self.engine.execute_touch_burst(
            serial=serial,
            actions=sample_burst,
            delay_ms=40,
        )

        # 3. Direct RAM frame stream (native resolution)
        frame_res = self.engine.stream_ram_screenshot(serial=serial, resize_to=None)

        total_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        return {
            "subagent_id": self.SUBAGENT_ID,
            "subagent_name": self.SUBAGENT_NAME,
            "status": "BENCHMARK_OK",
            "serial": serial,
            "ping_result": ping_res,
            "burst_result": burst_res,
            "stream_status": frame_res["status"],
            "frame_width": frame_res["width"],
            "frame_height": frame_res["height"],
            "bytes_len": frame_res["bytes_len"],
            "flash_writes": frame_res["flash_writes"],
            "shell_latency_ms": ping_res["latency_ms"],
            "stream_latency_ms": frame_res["latency_ms"],
            "total_benchmark_ms": total_ms,
            "tokens_used": 0,
        }

    def capture_live_preview_frame(
        self,
        serial: str = DEFAULT_SERIAL,
        preview_size: Tuple[int, int] = (360, 800),
    ) -> Dict[str, Any]:
        """
        Capture a RAM-streamed screenshot and resize it for the GUI Live Preview
        without touching `/sdcard/` flash storage.
        """
        stream_res = self.engine.stream_ram_screenshot(
            serial=serial,
            resize_to=preview_size,
        )
        return {
            "subagent_id": self.SUBAGENT_ID,
            "subagent_name": self.SUBAGENT_NAME,
            "status": stream_res["status"],
            "serial": serial,
            "source": stream_res["source"],
            "image": stream_res["image"],
            "width": stream_res["width"],
            "height": stream_res["height"],
            "preview_size": tuple(preview_size),
            "bytes_len": stream_res["bytes_len"],
            "flash_writes": stream_res["flash_writes"],
            "latency_ms": stream_res["latency_ms"],
            "tokens_used": 0,
        }

    def close(self) -> int:
        """Close all persistent ADB shell sessions managed by this subagent."""
        return self.engine.close_all()
