"""
Macro Replay Subagent (Subagent #37)
Wraps `MacroRecorderEngine` and `MemoryManager` to record, resolve, and replay
multi-step UI action macros across heterogeneous Android devices (e.g., Vivo V2314A
1260x2800 and Android Emulators 1080x2400) with ZERO AI TOKENS at runtime.
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.human_touch_engine import HumanTouchEngine
from core.macro_recorder_engine import MacroRecorderEngine, MacroStep, VisualTemplate
from core.memory_manager import MemoryManager
from core.real_device_manager import RealDeviceManager


class MacroReplaySubagent:
    """
    Subagent #37: Action Macro Recorder & Self-Caching Replay Engine.
    Executes 0-token hybrid 3-stage resolution (Poco XML -> Airtest Visual Template -> Relative Scaling)
    and biomechanical replay via `HumanTouchEngine`.
    """

    SUBAGENT_ID = 37
    SUBAGENT_NAME = "MacroReplaySubagent#37"

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        engine: Optional[MacroRecorderEngine] = None,
        memory: Optional[MemoryManager] = None,
        macros_dir: Optional[Union[str, Path]] = None,
    ):
        if isinstance(engine, MemoryManager) and memory is None:
            memory = engine
            engine = None
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.engine = engine or MacroRecorderEngine(macros_dir=macros_dir, adb=self.adb)

    def start_recording(
        self,
        macro_name: str,
        resolution: Tuple[int, int] = (1260, 2800),
    ) -> Dict[str, Any]:
        """Start recording a new zero-token macro."""
        return self.engine.start_recording(macro_name=macro_name, resolution=resolution)

    def record_step(
        self,
        action_type: str,
        x: int = 0,
        y: int = 0,
        screen_image: Optional[Any] = None,
        xml_dump: Optional[str] = None,
        **kwargs: Any,
    ) -> MacroStep:
        """Record an action step with automatic XML selector extraction and 120x120 visual template crop."""
        return self.engine.record_step(
            action_type=action_type,
            x=x,
            y=y,
            screen_image=screen_image,
            xml_dump=xml_dump,
            **kwargs,
        )

    def save_macro(self, macro_name: Optional[str] = None) -> str:
        """Save the active macro to disk and log in agent memory."""
        saved_path = self.engine.save_macro(macro_name=macro_name)
        name = macro_name or self.engine._active_macro_name or "recorded_macro"
        self.memory.remember(
            key=f"macro_saved_{name}_{int(time.time() * 1000)}",
            value={"macro_name": name, "path": saved_path, "subagent": self.SUBAGENT_NAME},
            tags=["macro_recorder", "save_macro", name],
            category="macro_telemetry",
        )
        return saved_path

    def load_macro(self, macro_name: str) -> Dict[str, Any]:
        """Load a macro definition from disk or cache."""
        return self.engine.load_macro(macro_name=macro_name)

    def list_macros(self) -> List[str]:
        """List all available macros (including built-ins)."""
        return self.engine.list_macros()

    def resolve_step_coordinates(
        self,
        step: Union[MacroStep, Dict[str, Any]],
        target_resolution: Tuple[int, int],
        current_screen: Optional[Any] = None,
        current_xml: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve step coordinates using the 3-stage hybrid pipeline (0 AI tokens)."""
        return self.engine.resolve_step_coordinates(
            step=step,
            target_resolution=target_resolution,
            current_screen=current_screen,
            current_xml=current_xml,
        )

    def replay_macro(
        self,
        macro_name: str,
        serial: Optional[str] = None,
        dry_run: bool = False,
        touch_engine: Optional[HumanTouchEngine] = None,
        target_resolution: Optional[Tuple[int, int]] = None,
        current_screen: Optional[Any] = None,
        current_xml: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Replay a macro on `serial` (or in `dry_run=True` mode) with 0 AI tokens and persist telemetry."""
        res = self.engine.replay_macro(
            macro_name=macro_name,
            serial=serial,
            dry_run=dry_run,
            touch_engine=touch_engine,
            target_resolution=target_resolution,
            current_screen=current_screen,
            current_xml=current_xml,
        )
        telemetry = {
            **res,
            "subagent": self.SUBAGENT_NAME,
            "subagent_id": self.SUBAGENT_ID,
            "tokens_used": 0,
        }
        self.memory.remember(
            key=f"macro_replay_{macro_name}_{serial or 'dry_run'}_{int(time.time() * 1000)}",
            value=telemetry,
            tags=["macro_replay", macro_name, str(serial or "dry_run")],
            category="macro_telemetry",
        )
        return telemetry


if __name__ == "__main__":
    sub = MacroReplaySubagent()
    print(f"{sub.SUBAGENT_NAME} initialized. Available macros: {sub.list_macros()}")
