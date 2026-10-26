"""
Conditional Visual Workflow DAG & Live Screen Preview Monitor Subagent (Subagent #45)
=====================================================================================
Wraps `VisualFlowDAGEngine` and `MemoryManager` to build, persist, inspect, and
execute conditional visual workflow DAGs (`If Screen Contains X -> Branch A, Else -> Branch B`)
and render live annotated screen preview frames (glowing crosshairs, touch ripples,
trajectory lines, and bounding boxes) with ZERO AI TOKENS at runtime.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager
from core.visual_flow_dag_engine import DAGNode, VisualFlowDAGEngine


class VisualFlowBuilderAndLiveMonitorSubagent:
    """
    Subagent #45: Conditional Visual Workflow DAG Engine & Live Screen Preview Monitor.
    """

    SUBAGENT_ID = 45
    SUBAGENT_NAME = "VisualFlowBuilderAndLiveMonitorSubagent"

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        engine: Optional[VisualFlowDAGEngine] = None,
        memory: Optional[MemoryManager] = None,
        workflows_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        if isinstance(engine, MemoryManager) and memory is None:
            memory = engine
            engine = None
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.engine = engine or VisualFlowDAGEngine(
            workflows_dir=workflows_dir, adb=self.adb
        )

    def list_workflows(self) -> List[str]:
        """List all available DAG workflow names (including built-ins)."""
        return self.engine.list_workflows()

    def load_workflow(self, dag_name: str) -> Dict[str, Any]:
        """Load a DAG workflow specification by name."""
        return self.engine.load_workflow(dag_name)

    def save_workflow(self, dag_name: str, spec: Dict[str, Any]) -> str:
        """Persist a custom DAG workflow specification to `config/workflows_dag/`."""
        path = self.engine.save_workflow(dag_name, spec)
        self.memory.remember(
            key=f"dag_saved_{dag_name}_{int(time.time() * 1000)}",
            value={"dag_name": dag_name, "path": path, "subagent": self.SUBAGENT_NAME},
            tags=["visual_flow_dag", "save_workflow", dag_name],
            category="dag_telemetry",
        )
        return path

    def register_node_handler(
        self,
        node_id: str,
        handler: Callable[[DAGNode, str, Dict[str, Any], bool], Any],
    ) -> None:
        """Register a custom deterministic Python handler for a specific `node_id`."""
        self.engine.register_node_handler(node_id, handler)

    def execute_dag(
        self,
        dag_name_or_spec: Union[str, Dict[str, Any], List[Union[DAGNode, Dict[str, Any]]]],
        serial: str = "10CF5L0TYL00312",
        context: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute a conditional DAG workflow and persist zero-token telemetry in `MemoryManager`.
        """
        res = self.engine.execute_dag(
            dag_name_or_spec=dag_name_or_spec,
            serial=serial,
            context=context,
            dry_run=dry_run,
        )
        telemetry = {
            **res,
            "subagent": self.SUBAGENT_NAME,
            "subagent_id": self.SUBAGENT_ID,
            "tokens_used": 0,
        }
        dag_label = str(res.get("dag_name", "custom_dag"))
        self.memory.remember(
            key=f"dag_exec_{dag_label}_{serial}_{int(time.time() * 1000)}",
            value=telemetry,
            tags=["visual_flow_dag", dag_label, serial],
            category="dag_telemetry",
        )
        return telemetry

    def render_annotated_preview_frame(
        self,
        screen_image: Optional[Union[Image.Image, Any, str, Path]] = None,
        touch_points: Optional[List[Tuple[int, int]]] = None,
        boxes: Optional[List[Dict[str, Any]]] = None,
        preview_size: Tuple[int, int] = (320, 700),
    ) -> Image.Image:
        """
        Render live screen preview with glowing cyan/green target crosshairs,
        trajectory lines, and bounding boxes resized to `preview_size`.
        """
        return self.engine.render_annotated_preview_frame(
            screen_image=screen_image,
            touch_points=touch_points,
            boxes=boxes,
            preview_size=preview_size,
        )


# Convenient alias
VisualFlowDAGSubagent = VisualFlowBuilderAndLiveMonitorSubagent


if __name__ == "__main__":
    sub = VisualFlowBuilderAndLiveMonitorSubagent()
    print(f"{sub.SUBAGENT_NAME} (#{sub.SUBAGENT_ID}) initialized. Built-in DAGs: {sub.list_workflows()}")
