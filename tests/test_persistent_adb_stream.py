"""
Unit tests for Feature #41: Persistent ADB Shell Pipe & Fast Frame Streamer
(`core/persistent_adb_stream_engine.py` & `agents/persistent_adb_stream_subagent.py`).
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.persistent_adb_stream_subagent import PersistentADBStreamSubagent
from core.persistent_adb_stream_engine import (
    PersistentADBShellSession,
    PersistentADBStreamEngine,
)


class _FakePipeProcess:
    """Deterministic fake `subprocess.Popen` pipe for testing `__AMAF_EOF_$?__` framing."""

    def __init__(self, stdout_lines: list[str], exit_code: int = 0) -> None:
        self.written_commands: list[str] = []
        self._lines = list(stdout_lines) + [f"__AMAF_EOF_{exit_code}__\n"]
        self._closed = False
        self.stdin = MagicMock()
        self.stdin.write.side_effect = self._on_write
        self.stdout = MagicMock()
        self.stdout.readline.side_effect = self._on_readline
        self.stderr = MagicMock()

    def _on_write(self, data: str) -> int:
        self.written_commands.append(data)
        return len(data)

    def _on_readline(self) -> str:
        if self._lines:
            return self._lines.pop(0)
        return ""

    def poll(self):
        return None if not self._closed else 0

    def terminate(self) -> None:
        self._closed = True

    def wait(self, timeout: float = 0.5) -> int:
        self._closed = True
        return 0

    def kill(self) -> None:
        self._closed = True


def test_persistent_shell_command_framing_and_eof_parsing() -> None:
    """Verify `execute_fast_cmd` writes `__AMAF_EOF_$?__` and parses output + exit code."""
    fake_proc = _FakePipeProcess(
        stdout_lines=["package:com.android.settings\n", "amaf_ready\n"],
        exit_code=0,
    )
    session = PersistentADBShellSession(serial="10CF5L0TYL00312", auto_connect=False)
    with patch.object(session, "_spawn_process", return_value=fake_proc):
        result = session.execute_fast_cmd("pm list packages settings")

    assert result["status"] == "OK"
    assert result["mode"] == "PERSISTENT_PIPE"
    assert result["exit_code"] == 0
    assert result["tokens_used"] == 0
    assert result["framed_cmd"] == "pm list packages settings; echo __AMAF_EOF_$?__"
    assert "package:com.android.settings" in result["output"]
    assert "amaf_ready" in result["output"]
    assert "__AMAF_EOF_" not in result["output"]
    assert fake_proc.written_commands == ["pm list packages settings; echo __AMAF_EOF_$?__\n"]
    session.close()


def test_persistent_shell_nonzero_exit_code_parsing() -> None:
    """Verify non-zero exit code (`__AMAF_EOF_127__`) is accurately parsed as ERROR."""
    fake_proc = _FakePipeProcess(
        stdout_lines=["sh: unknown_cmd: not found\n"],
        exit_code=127,
    )
    session = PersistentADBShellSession(serial="10CF5L0TYL00312", auto_connect=False)
    with patch.object(session, "_spawn_process", return_value=fake_proc):
        result = session.execute_fast_cmd("unknown_cmd")

    assert result["status"] == "ERROR"
    assert result["exit_code"] == 127
    assert result["tokens_used"] == 0
    assert "not found" in result["output"]
    session.close()


def test_compound_batch_pipeline_and_execute_touch_burst() -> None:
    """Verify `execute_touch_burst` builds a single compound shell pipeline with `tokens_used == 0`."""
    fake_proc = _FakePipeProcess(stdout_lines=[], exit_code=0)
    engine = PersistentADBStreamEngine()
    session = engine.get_session("10CF5L0TYL00312")

    actions = [
        {"type": "tap", "x": 540, "y": 1200},
        {"type": "swipe", "x1": 540, "y1": 1800, "x2": 540, "y2": 600, "duration_ms": 180},
        {"type": "key", "keycode": 4},
    ]

    with patch.object(session, "_spawn_process", return_value=fake_proc):
        burst_res = engine.execute_touch_burst(
            serial="10CF5L0TYL00312",
            actions=actions,
            delay_ms=40,
        )

    expected_compound = (
        "input tap 540 1200 ; sleep 0.04 ; "
        "input swipe 540 1800 540 600 180 ; sleep 0.04 ; "
        "input keyevent 4"
    )
    assert burst_res["status"] == "OK"
    assert burst_res["commands_count"] == 3
    assert burst_res["actions_count"] == 3
    assert burst_res["compound_cmd"] == expected_compound
    assert burst_res["tokens_used"] == 0
    assert fake_proc.written_commands == [f"{expected_compound}; echo __AMAF_EOF_$?__\n"]
    engine.close_all()


def test_fast_tap_and_fast_swipe_zero_tokens() -> None:
    """Verify `fast_tap` and `fast_swipe` execute through the persistent session with 0 tokens."""
    fake_proc = _FakePipeProcess(stdout_lines=["\n"], exit_code=0)
    engine = PersistentADBStreamEngine()
    session = engine.get_session("emulator-5554")

    with patch.object(session, "_spawn_process", return_value=fake_proc):
        tap_res = engine.fast_tap("emulator-5554", 320, 640)
        assert tap_res["status"] == "OK"
        assert tap_res["action"] == "tap"
        assert tap_res["x"] == 320
        assert tap_res["y"] == 640
        assert tap_res["tokens_used"] == 0

    fake_proc2 = _FakePipeProcess(stdout_lines=["\n"], exit_code=0)
    with patch.object(session, "_spawn_process", return_value=fake_proc2):
        session.close()
        swipe_res = engine.fast_swipe("emulator-5554", 100, 900, 100, 200, duration_ms=160)
        assert swipe_res["status"] == "OK"
        assert swipe_res["action"] == "swipe"
        assert swipe_res["duration_ms"] == 160
        assert swipe_res["tokens_used"] == 0

    assert engine.close_all() == 1


def test_stream_ram_screenshot_in_memory_and_synthetic_fallback() -> None:
    """Verify `stream_ram_screenshot` returns a valid PIL.Image with `flash_writes == 0`."""
    engine = PersistentADBStreamEngine()

    # 1. Mock `subprocess.run` returning valid PNG bytes from `exec-out screencap -p`
    sample_img = Image.new("RGB", (1260, 2800), color=(40, 90, 160))
    buf = io.BytesIO()
    sample_img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    mock_completed = MagicMock()
    mock_completed.returncode = 0
    mock_completed.stdout = png_bytes

    with patch("core.persistent_adb_stream_engine.subprocess.run", return_value=mock_completed):
        res = engine.stream_ram_screenshot("10CF5L0TYL00312", resize_to=(360, 800))

    assert res["status"] == "STREAM_OK"
    assert res["source"] == "exec-out"
    assert isinstance(res["image"], Image.Image)
    assert res["width"] == 360
    assert res["height"] == 800
    assert res["bytes_len"] == len(png_bytes)
    assert res["flash_writes"] == 0
    assert res["tokens_used"] == 0

    # 2. Verify synthetic 1260x2800 fallback when device is offline
    mock_offline = MagicMock()
    mock_offline.returncode = 1
    mock_offline.stdout = b""

    with patch("core.persistent_adb_stream_engine.subprocess.run", return_value=mock_offline):
        fallback_res = engine.stream_ram_screenshot("OFFLINE_SERIAL", resize_to=None)

    assert fallback_res["status"] == "STREAM_OK"
    assert fallback_res["source"] == "synthetic_fallback"
    assert isinstance(fallback_res["image"], Image.Image)
    assert (fallback_res["width"], fallback_res["height"]) == (1260, 2800)
    assert fallback_res["flash_writes"] == 0
    assert fallback_res["tokens_used"] == 0


def test_persistent_adb_stream_subagent_benchmark_and_preview() -> None:
    """Verify Subagent #41 (`PersistentADBStreamSubagent`) benchmark and live preview."""
    subagent = PersistentADBStreamSubagent()
    assert subagent.SUBAGENT_ID == 41
    assert subagent.SUBAGENT_NAME == "PersistentADBStreamSubagent"

    bench = subagent.run_stream_benchmark(serial="10CF5L0TYL00312")
    assert bench["subagent_id"] == 41
    assert bench["subagent_name"] == "PersistentADBStreamSubagent"
    assert bench["status"] == "BENCHMARK_OK"
    assert bench["flash_writes"] == 0
    assert bench["tokens_used"] == 0
    assert bench["frame_width"] > 0
    assert bench["frame_height"] > 0

    preview = subagent.capture_live_preview_frame(
        serial="10CF5L0TYL00312",
        preview_size=(360, 800),
    )
    assert preview["status"] == "STREAM_OK"
    assert isinstance(preview["image"], Image.Image)
    assert (preview["width"], preview["height"]) == (360, 800)
    assert preview["flash_writes"] == 0
    assert preview["tokens_used"] == 0

    subagent.close()
