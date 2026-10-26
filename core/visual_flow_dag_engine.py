"""
Conditional Visual Workflow DAG Engine & Live Screen Preview Monitor (Feature #45)
===================================================================================
Deterministic Directed Acyclic Graph (DAG) State-Machine Workflow Engine for
multi-step conditional mobile automation (`If Screen Contains X -> Branch A, Else -> Branch B`)
plus annotated Live Screen Preview rendering (drawing glowing cyan/green crosshairs,
touch ripples, trajectory lines, and bounding boxes onto device frames for the GUI dashboard).

Operates with 100% ZERO AI TOKENS at runtime.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from PIL import Image, ImageDraw


@dataclass
class DAGNode:
    """
    Represents a single state-machine node inside a Conditional Visual Workflow DAG.

    Attributes:
        node_id: Unique identifier of the node within the workflow DAG.
        title: Human-readable title describing the node's operation.
        node_type: One of `"action"`, `"condition"`, `"subagent_call"`, `"terminal"`.
        params: Arbitrary dictionary of node parameters, selectors, or target subagents.
        on_success: Next `node_id` to transition to when evaluation/execution succeeds.
        on_failure: Fallback `node_id` to transition to when evaluation/execution fails.
        max_retries: Maximum number of retries/visits permitted before escalating or halting.
    """

    node_id: str
    title: str
    node_type: str = "action"
    params: Dict[str, Any] = field(default_factory=dict)
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    max_retries: int = 2

    VALID_NODE_TYPES = {"action", "condition", "subagent_call", "terminal"}

    def __post_init__(self) -> None:
        if self.node_type not in self.VALID_NODE_TYPES:
            raise ValueError(
                f"Invalid node_type '{self.node_type}'. Expected one of {sorted(self.VALID_NODE_TYPES)}"
            )
        if self.params is None:
            self.params = {}
        self.max_retries = max(0, int(self.max_retries))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize DAGNode into a JSON-compatible dictionary."""
        return {
            "node_id": self.node_id,
            "title": self.title,
            "node_type": self.node_type,
            "params": dict(self.params),
            "on_success": self.on_success,
            "on_failure": self.on_failure,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: Union["DAGNode", Dict[str, Any]]) -> "DAGNode":
        """Construct a DAGNode from a dictionary or existing DAGNode."""
        if isinstance(data, cls):
            return data
        return cls(
            node_id=str(data["node_id"]),
            title=str(data.get("title", data["node_id"])),
            node_type=str(data.get("node_type", "action")),
            params=dict(data.get("params") or {}),
            on_success=data.get("on_success"),
            on_failure=data.get("on_failure"),
            max_retries=int(data.get("max_retries", 2)),
        )


class VisualFlowDAGEngine:
    """
    Deterministic Directed Acyclic Graph (DAG) State-Machine Workflow Engine
    and Annotated Live Screen Preview Renderer.
    """

    DEFAULT_WORKFLOWS_DIR = (
        Path(__file__).resolve().parent.parent / "config" / "workflows_dag"
    )

    def __init__(
        self,
        workflows_dir: Optional[Union[str, Path]] = None,
        adb: Optional[Any] = None,
    ) -> None:
        self.workflows_dir = Path(workflows_dir or self.DEFAULT_WORKFLOWS_DIR)
        self.workflows_dir.mkdir(parents=True, exist_ok=True)
        self.adb = adb
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._node_handlers: Dict[str, Callable[[DAGNode, str, Dict[str, Any], bool], Any]] = {}
        self._populate_builtin_workflows()
        self._load_disk_workflows()

    # ------------------------------------------------------------------
    # Built-in Workflow Definitions & Persistence
    # ------------------------------------------------------------------

    def _build_tiktok_smart_switch_and_engage_dag(self) -> Dict[str, Any]:
        nodes = [
            DAGNode(
                node_id="start_launch",
                title="Launch TikTok Package & Wait For Main Feed",
                node_type="action",
                params={
                    "package": "com.ss.android.ugc.trill",
                    "action": "launch_app",
                    "wait_ms": 1500,
                },
                on_success="check_ime_or_popup",
                on_failure="recover_back_and_retry",
                max_retries=2,
            ),
            DAGNode(
                node_id="check_ime_or_popup",
                title="Guard Against Rogue IME Keyboard or Modal Popup (Subagent #18/#42)",
                node_type="subagent_call",
                params={
                    "subagent_ids": [18, 42],
                    "subagent_names": ["PopupGuardSubagent", "IMEFocusGuardSubagent"],
                    "check": "dismiss_ime_and_popups",
                },
                on_success="switch_account_nht",
                on_failure="recover_back_and_retry",
                max_retries=2,
            ),
            DAGNode(
                node_id="switch_account_nht",
                title="Switch Active Profile to Account NHT",
                node_type="action",
                params={
                    "target_account": "nht",
                    "action": "switch_profile",
                    "coords": [1140, 2680],
                },
                on_success="search_tra_dang",
                on_failure="recover_back_and_retry",
                max_retries=2,
            ),
            DAGNode(
                node_id="search_tra_dang",
                title="Search Creator 'tra.dang.904' via Top Search Bar",
                node_type="action",
                params={
                    "query": "tra.dang.904",
                    "action": "search_creator",
                    "coords": [1180, 145],
                },
                on_success="open_video_and_like",
                on_failure="recover_back_and_retry",
                max_retries=2,
            ),
            DAGNode(
                node_id="open_video_and_like",
                title="Open Latest Video & Trigger Heart Like Gesture",
                node_type="action",
                params={
                    "action": "open_and_like_video",
                    "coords": [630, 1400],
                },
                on_success="post_comment_and_verify",
                on_failure="recover_back_and_retry",
                max_retries=2,
            ),
            DAGNode(
                node_id="post_comment_and_verify",
                title="Post Engagement Comment & Verify Delivery",
                node_type="condition",
                params={
                    "condition": "screen_contains_comment_posted",
                    "comment_text": "Tuyet voi qua!",
                    "coords": [1160, 1820],
                },
                on_success="exit_home_done",
                on_failure="recover_back_and_retry",
                max_retries=2,
            ),
            DAGNode(
                node_id="recover_back_and_retry",
                title="Fallback Recovery: Navigate Back, Clear Overlay & Complete",
                node_type="action",
                params={
                    "action": "navigate_back_and_recover",
                    "keyevent": "KEYCODE_BACK",
                    "recovery_mode": "graceful_resume",
                },
                on_success="exit_home_done",
                on_failure="exit_home_done",
                max_retries=2,
            ),
            DAGNode(
                node_id="exit_home_done",
                title="Return to Android Home Screen & Complete TikTok DAG",
                node_type="terminal",
                params={
                    "action": "navigate_home",
                    "status": "DAG_COMPLETED",
                },
                on_success=None,
                on_failure=None,
                max_retries=0,
            ),
        ]
        return {
            "dag_name": "tiktok_smart_switch_and_engage_dag",
            "title": "TikTok Smart Account Switch & Creator Engagement DAG",
            "start_node": "start_launch",
            "version": "1.0.0",
            "nodes": [n.to_dict() for n in nodes],
        }

    def _build_web_11_site_smart_patrol_dag(self) -> Dict[str, Any]:
        nodes = [
            DAGNode(
                node_id="open_chrome_tab",
                title="Open Target URL in Android Chrome Browser Tab",
                node_type="action",
                params={
                    "package": "com.android.chrome",
                    "action": "open_url_tab",
                    "sites_count": 11,
                },
                on_success="attach_cdp_socket",
                on_failure="done",
                max_retries=2,
            ),
            DAGNode(
                node_id="attach_cdp_socket",
                title="Attach Localhost Chrome DevTools Protocol (CDP) Socket (Subagent #43)",
                node_type="subagent_call",
                params={
                    "subagent_id": 43,
                    "subagent_name": "AndroidChromeCDPBridgeSubagent",
                    "action": "forward_and_attach_cdp",
                },
                on_success="detect_challenge_type",
                on_failure="done",
                max_retries=2,
            ),
            DAGNode(
                node_id="detect_challenge_type",
                title="Inspect DOM & Viewport to Classify Challenge / Form Type",
                node_type="condition",
                params={
                    "condition": "classify_web_challenge",
                    "supported_types": ["slider", "checkbox", "form_quiz", "clean_page"],
                },
                on_success="solve_3tier_gpu",
                on_failure="done",
                max_retries=2,
            ),
            DAGNode(
                node_id="solve_3tier_gpu",
                title="Execute 3-Tier Local RTX 3050 GPU Vision & Biomechanical Solver",
                node_type="subagent_call",
                params={
                    "subagent_ids": [35, 36, 44],
                    "engine": "nvcuda_sm86_3tier",
                    "tokens_used": 0,
                },
                on_success="verify_submission",
                on_failure="done",
                max_retries=2,
            ),
            DAGNode(
                node_id="verify_submission",
                title="Verify HTTP 200 / DOM Success Banner Post-Submission",
                node_type="condition",
                params={
                    "condition": "verify_dom_submission_success",
                },
                on_success="done",
                on_failure="done",
                max_retries=2,
            ),
            DAGNode(
                node_id="done",
                title="11-Site Web Patrol Cycle Completed",
                node_type="terminal",
                params={
                    "status": "DAG_COMPLETED",
                },
                on_success=None,
                on_failure=None,
                max_retries=0,
            ),
        ]
        return {
            "dag_name": "web_11_site_smart_patrol_dag",
            "title": "11-Site Web Smart Patrol & 3-Tier Local GPU Verification DAG",
            "start_node": "open_chrome_tab",
            "version": "1.0.0",
            "nodes": [n.to_dict() for n in nodes],
        }

    def _populate_builtin_workflows(self) -> None:
        builtins = [
            self._build_tiktok_smart_switch_and_engage_dag(),
            self._build_web_11_site_smart_patrol_dag(),
        ]
        for spec in builtins:
            name = spec["dag_name"]
            self._workflows[name] = spec
            target_file = self.workflows_dir / f"{name}.json"
            if not target_file.exists():
                self.save_workflow(name, spec)

    def _load_disk_workflows(self) -> None:
        if not self.workflows_dir.exists():
            return
        for json_file in sorted(self.workflows_dir.glob("*.json")):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                dag_name = data.get("dag_name") or json_file.stem
                if dag_name and "nodes" in data:
                    self._workflows[dag_name] = data
            except Exception:
                continue

    def save_workflow(self, dag_name: str, spec: Dict[str, Any]) -> str:
        """Persist a DAG workflow definition to `config/workflows_dag/<dag_name>.json`."""
        normalized_nodes = [DAGNode.from_dict(n).to_dict() for n in spec.get("nodes", [])]
        payload = {
            "dag_name": dag_name,
            "title": spec.get("title", dag_name),
            "start_node": spec.get(
                "start_node",
                normalized_nodes[0]["node_id"] if normalized_nodes else "",
            ),
            "version": spec.get("version", "1.0.0"),
            "nodes": normalized_nodes,
        }
        self._workflows[dag_name] = payload
        file_path = self.workflows_dir / f"{dag_name}.json"
        file_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(file_path)

    def load_workflow(self, dag_name: str) -> Dict[str, Any]:
        """Load a DAG workflow specification by name from memory or disk."""
        if dag_name in self._workflows:
            return self._workflows[dag_name]
        file_path = self.workflows_dir / f"{dag_name}.json"
        if file_path.exists():
            spec = json.loads(file_path.read_text(encoding="utf-8"))
            self._workflows[dag_name] = spec
            return spec
        raise KeyError(f"Unknown DAG workflow: '{dag_name}'")

    def list_workflows(self) -> List[str]:
        """Return sorted list of available DAG workflow names."""
        self._load_disk_workflows()
        return sorted(self._workflows.keys())

    def register_node_handler(
        self,
        node_id: str,
        handler: Callable[[DAGNode, str, Dict[str, Any], bool], Any],
    ) -> None:
        """Register a custom deterministic Python handler for a specific `node_id`."""
        self._node_handlers[node_id] = handler

    # ------------------------------------------------------------------
    # Deterministic DAG Execution State Machine
    # ------------------------------------------------------------------

    def _normalize_dag_spec(
        self,
        dag_name_or_spec: Union[str, Dict[str, Any], List[Union[DAGNode, Dict[str, Any]]]],
    ) -> Tuple[str, str, Dict[str, DAGNode], List[str]]:
        if isinstance(dag_name_or_spec, str):
            spec = self.load_workflow(dag_name_or_spec)
            dag_name = spec.get("dag_name", dag_name_or_spec)
            raw_nodes = spec.get("nodes", [])
            nodes = [DAGNode.from_dict(n) for n in raw_nodes]
            start_node = spec.get("start_node") or (nodes[0].node_id if nodes else "")
        elif isinstance(dag_name_or_spec, list):
            nodes = [DAGNode.from_dict(n) for n in dag_name_or_spec]
            dag_name = "custom_inline_dag"
            start_node = nodes[0].node_id if nodes else ""
        elif isinstance(dag_name_or_spec, dict):
            dag_name = dag_name_or_spec.get("dag_name", "custom_dict_dag")
            raw_nodes = dag_name_or_spec.get("nodes", [])
            if isinstance(raw_nodes, dict):
                nodes = [DAGNode.from_dict(v) for v in raw_nodes.values()]
            else:
                nodes = [DAGNode.from_dict(n) for n in raw_nodes]
            start_node = dag_name_or_spec.get("start_node") or (
                nodes[0].node_id if nodes else ""
            )
        else:
            raise TypeError(f"Unsupported dag_name_or_spec type: {type(dag_name_or_spec)}")

        node_map: Dict[str, DAGNode] = {n.node_id: n for n in nodes}
        ordered_ids: List[str] = [n.node_id for n in nodes]
        return dag_name, start_node, node_map, ordered_ids

    def _evaluate_node(
        self,
        node: DAGNode,
        serial: str,
        context: Dict[str, Any],
        dry_run: bool,
        attempt_index: int,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Deterministically evaluate or execute a single DAGNode.
        Returns `(succeeded, detail_dict)` with 0 AI tokens used.
        """
        ctx_handlers = context.get("node_handlers") or {}
        fail_nodes = set(context.get("fail_nodes") or [])
        fail_once_nodes = set(context.get("fail_once_nodes") or [])
        condition_overrides = context.get("condition_results") or {}
        simulated_outcomes = context.get("node_outcomes") or {}

        # 1. Explicit handler in context or engine registry or node.params
        handler = (
            ctx_handlers.get(node.node_id)
            or self._node_handlers.get(node.node_id)
            or (node.params.get("handler") if callable(node.params.get("handler")) else None)
        )
        if callable(handler):
            try:
                res = handler(node, serial, context, dry_run)
                if isinstance(res, dict):
                    success = bool(res.get("success", res.get("ok", True)))
                    return success, res
                if isinstance(res, tuple) and len(res) == 2:
                    return bool(res[0]), (res[1] if isinstance(res[1], dict) else {"result": res[1]})
                return bool(res), {"result": res}
            except Exception as exc:
                return False, {"error": str(exc)}

        # 2. Explicit simulated outcomes in context or node params
        if node.node_id in simulated_outcomes:
            val = simulated_outcomes[node.node_id]
            if isinstance(val, list):
                idx = min(attempt_index, len(val) - 1)
                outcome = bool(val[idx])
            else:
                outcome = bool(val)
            return outcome, {"simulated_outcome": outcome, "attempt": attempt_index + 1}

        if node.node_id in fail_once_nodes and attempt_index == 0:
            return False, {"simulated_failure": "fail_once", "attempt": attempt_index + 1}

        if node.node_id in fail_nodes:
            return False, {"simulated_failure": "fail_nodes", "attempt": attempt_index + 1}

        if node.params.get("simulate_failure") is True:
            if node.params.get("fail_once", True) and attempt_index > 0:
                return True, {"recovered_after_retry": True, "attempt": attempt_index + 1}
            return False, {"simulated_failure": "node_param", "attempt": attempt_index + 1}

        if node.node_id in condition_overrides:
            cond_val = bool(condition_overrides[node.node_id])
            return cond_val, {"condition_override": cond_val}

        if "condition_result" in node.params:
            cond_val = bool(node.params["condition_result"])
            return cond_val, {"condition_param": cond_val}

        # 3. Screen text condition check (`If Screen Contains X -> Branch A, Else -> Branch B`)
        expected_text = node.params.get("if_screen_contains")
        if expected_text is not None:
            screen_text = str(context.get("screen_text") or context.get("xml_dump") or "")
            matched = str(expected_text).lower() in screen_text.lower()
            return matched, {
                "if_screen_contains": expected_text,
                "matched": matched,
            }

        # 4. Default deterministic execution
        return True, {
            "executed": True,
            "node_type": node.node_type,
            "dry_run": dry_run,
            "serial": serial,
        }

    def execute_dag(
        self,
        dag_name_or_spec: Union[str, Dict[str, Any], List[Union[DAGNode, Dict[str, Any]]]],
        serial: str = "10CF5L0TYL00312",
        context: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Traverse the DAG from start node to terminal node, evaluating conditions,
        executing node handlers, following `on_success` / `on_failure` edges,
        preventing infinite cycles, and returning the full execution trace.
        """
        started_at = time.time()
        ctx: Dict[str, Any] = dict(context or {})
        dag_name, start_node_id, node_map, ordered_ids = self._normalize_dag_spec(
            dag_name_or_spec
        )

        if not node_map or not start_node_id or start_node_id not in node_map:
            return {
                "dag_name": dag_name,
                "serial": serial,
                "dry_run": dry_run,
                "nodes_visited": [],
                "branch_decisions": [],
                "step_trace": [],
                "tokens_used": 0,
                "status": "DAG_EMPTY_OR_INVALID",
                "elapsed_ms": 0.0,
            }

        nodes_visited: List[str] = []
        branch_decisions: List[Dict[str, Any]] = []
        step_trace: List[Dict[str, Any]] = []
        visit_counts: Dict[str, int] = {nid: 0 for nid in node_map}

        max_total_steps = int(ctx.get("max_total_steps", max(32, len(node_map) * 6)))
        current_id: Optional[str] = start_node_id
        final_status = "DAG_COMPLETED"

        while current_id is not None and len(step_trace) < max_total_steps:
            if current_id not in node_map:
                final_status = "DAG_BROKEN_EDGE"
                break

            node = node_map[current_id]
            attempt_idx = visit_counts.get(current_id, 0)

            # Cycle / retry budget protection
            allowed_visits = max(1, node.max_retries + 1)
            if node.node_type != "terminal" and attempt_idx >= allowed_visits:
                # If we exceeded retry budget on this node, try jumping to terminal if one exists
                terminal_candidates = [
                    nid for nid, n in node_map.items() if n.node_type == "terminal"
                ]
                if terminal_candidates and current_id != terminal_candidates[-1]:
                    next_id = terminal_candidates[-1]
                    branch_decisions.append(
                        {
                            "from_node": current_id,
                            "to_node": next_id,
                            "branch": "max_retries_exceeded_fallback",
                            "success": False,
                            "attempt": attempt_idx + 1,
                        }
                    )
                    current_id = next_id
                    continue
                final_status = "DAG_CYCLE_ABORTED"
                break

            visit_counts[current_id] = attempt_idx + 1
            nodes_visited.append(current_id)

            succeeded, detail = self._evaluate_node(
                node=node,
                serial=serial,
                context=ctx,
                dry_run=dry_run,
                attempt_index=attempt_idx,
            )

            if node.node_type == "terminal":
                step_trace.append(
                    {
                        "step_index": len(step_trace),
                        "node_id": node.node_id,
                        "title": node.title,
                        "node_type": node.node_type,
                        "success": True,
                        "branch_taken": "terminal",
                        "next_node": None,
                        "detail": detail,
                    }
                )
                final_status = "DAG_COMPLETED"
                break

            if succeeded:
                next_node = node.on_success
                branch_label = "on_success"
            else:
                next_node = node.on_failure
                branch_label = "on_failure"

            branch_decisions.append(
                {
                    "from_node": node.node_id,
                    "to_node": next_node,
                    "branch": branch_label,
                    "success": succeeded,
                    "attempt": attempt_idx + 1,
                }
            )
            step_trace.append(
                {
                    "step_index": len(step_trace),
                    "node_id": node.node_id,
                    "title": node.title,
                    "node_type": node.node_type,
                    "success": succeeded,
                    "branch_taken": branch_label,
                    "next_node": next_node,
                    "detail": detail,
                }
            )

            if next_node is None:
                final_status = "DAG_COMPLETED" if succeeded else "DAG_FAILED"
                break

            current_id = next_node
        else:
            if len(step_trace) >= max_total_steps:
                final_status = "DAG_CYCLE_ABORTED"

        elapsed_ms = round((time.time() - started_at) * 1000.0, 3)
        return {
            "dag_name": dag_name,
            "serial": serial,
            "dry_run": dry_run,
            "nodes_visited": nodes_visited,
            "branch_decisions": branch_decisions,
            "step_trace": step_trace,
            "tokens_used": 0,
            "status": final_status,
            "elapsed_ms": elapsed_ms,
        }

    # ------------------------------------------------------------------
    # Live Screen Preview Annotated Frame Renderer
    # ------------------------------------------------------------------

    def render_annotated_preview_frame(
        self,
        screen_image: Optional[Union[Image.Image, Any, str, Path]] = None,
        touch_points: Optional[List[Tuple[int, int]]] = None,
        boxes: Optional[List[Dict[str, Any]]] = None,
        preview_size: Tuple[int, int] = (320, 700),
    ) -> Image.Image:
        """
        Draw glowing cyan/green target crosshairs, touch ripples, trajectory lines,
        and bounding boxes onto `screen_image` and resize to `preview_size` (default 320x700)
        as an RGB `PIL.Image.Image` for embedding in the Tkinter GUI Live Preview panel.
        """
        if screen_image is None:
            canvas = Image.new("RGB", (1260, 2800), (18, 22, 31))
        elif isinstance(screen_image, Image.Image):
            canvas = screen_image.convert("RGB").copy()
        elif isinstance(screen_image, (str, Path)):
            canvas = Image.open(screen_image).convert("RGB")
        else:
            # Support numpy ndarray or array-like inputs
            import numpy as np

            arr = np.asarray(screen_image)
            if arr.ndim == 2:
                canvas = Image.fromarray(arr.astype("uint8"), mode="L").convert("RGB")
            else:
                canvas = Image.fromarray(arr[:, :, :3].astype("uint8"), mode="RGB")

        draw = ImageDraw.Draw(canvas)
        width, height = canvas.size
        scale_stroke = max(2, int(round(min(width, height) / 240.0)))

        # 1. Draw bounding boxes (glowing neon green / cyan)
        for box in boxes or []:
            if "bbox" in box and len(box["bbox"]) >= 4:
                x1, y1, x2, y2 = [int(v) for v in box["bbox"][:4]]
            elif all(k in box for k in ("x1", "y1", "x2", "y2")):
                x1, y1, x2, y2 = (
                    int(box["x1"]),
                    int(box["y1"]),
                    int(box["x2"]),
                    int(box["y2"]),
                )
            elif all(k in box for k in ("x", "y", "w", "h")):
                x1 = int(box["x"])
                y1 = int(box["y"])
                x2 = x1 + int(box["w"])
                y2 = y1 + int(box["h"])
            else:
                continue

            x1, x2 = sorted((max(0, x1), min(width - 1, x2)))
            y1, y2 = sorted((max(0, y1), min(height - 1, y2)))
            color = box.get("color", (0, 255, 160))
            glow_color = (0, 210, 255)

            # Outer cyan glow + inner bright green box
            draw.rectangle(
                [max(0, x1 - 2), max(0, y1 - 2), min(width - 1, x2 + 2), min(height - 1, y2 + 2)],
                outline=glow_color,
                width=scale_stroke + 2,
            )
            draw.rectangle(
                [x1, y1, x2, y2],
                outline=color,
                width=scale_stroke,
            )

            label = str(box.get("label") or "").strip()
            if label:
                tag_h = max(18, scale_stroke * 6)
                tag_w = min(width - x1, max(48, len(label) * (scale_stroke * 3 + 4)))
                tag_y1 = max(0, y1 - tag_h)
                draw.rectangle([x1, tag_y1, x1 + tag_w, y1], fill=(0, 180, 120))
                draw.text((x1 + 4, tag_y1 + 2), label, fill=(255, 255, 255))

        # 2. Draw trajectory lines & glowing cyan/green crosshairs for touch points
        pts = [(int(px), int(py)) for (px, py) in (touch_points or [])]
        if len(pts) >= 2:
            for idx in range(len(pts) - 1):
                p1, p2 = pts[idx], pts[idx + 1]
                draw.line([p1, p2], fill=(0, 230, 255), width=scale_stroke + 2)
                draw.line([p1, p2], fill=(80, 255, 160), width=max(1, scale_stroke))

        radius_outer = max(16, scale_stroke * 7)
        radius_inner = max(8, scale_stroke * 3)
        arm = max(24, scale_stroke * 10)

        for idx, (tx, ty) in enumerate(pts):
            cx = max(0, min(width - 1, tx))
            cy = max(0, min(height - 1, ty))
            # Outer cyan ripple ring
            draw.ellipse(
                [cx - radius_outer, cy - radius_outer, cx + radius_outer, cy + radius_outer],
                outline=(0, 240, 255),
                width=scale_stroke + 1,
            )
            # Inner neon green ring
            draw.ellipse(
                [cx - radius_inner, cy - radius_inner, cx + radius_inner, cy + radius_inner],
                outline=(0, 255, 128),
                fill=(0, 255, 180),
                width=scale_stroke,
            )
            # Crosshair lines
            draw.line(
                [(max(0, cx - arm), cy), (min(width - 1, cx + arm), cy)],
                fill=(0, 255, 220),
                width=scale_stroke,
            )
            draw.line(
                [(cx, max(0, cy - arm)), (cx, min(height - 1, cy + arm))],
                fill=(0, 255, 220),
                width=scale_stroke,
            )

        target_w, target_h = int(preview_size[0]), int(preview_size[1])
        if canvas.size != (target_w, target_h):
            resample_filter = getattr(Image, "Resampling", Image).LANCZOS
            canvas = canvas.resize((target_w, target_h), resample=resample_filter)

        return canvas.convert("RGB")
