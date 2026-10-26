"""
Unit Tests for Feature #45: Conditional Visual Workflow DAG Engine & Live Screen Preview Monitor
================================================================================================
Tests:
  1. Built-in DAG loading (`tiktok_smart_switch_and_engage_dag` and `web_11_site_smart_patrol_dag`).
  2. Conditional branching & fallback recovery: verifying that when a node returns failure,
     execution automatically routes to the `on_failure` recovery node (`recover_back_and_retry`)
     and completes (`status == "DAG_COMPLETED"`, `tokens_used == 0`).
  3. `render_annotated_preview_frame` producing a `(320, 700)` RGB `PIL.Image` with drawn
     touch crosshairs, trajectory lines, and bounding boxes.
  4. `VisualFlowBuilderAndLiveMonitorSubagent` (Subagent #45) integration and telemetry.
"""

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.visual_flow_dag_subagent import VisualFlowBuilderAndLiveMonitorSubagent
from core.visual_flow_dag_engine import DAGNode, VisualFlowDAGEngine


def test_dag_node_dataclass_and_serialization():
    node = DAGNode(
        node_id="check_login",
        title="Check if user is logged in",
        node_type="condition",
        params={"if_screen_contains": "Profile"},
        on_success="open_feed",
        on_failure="login_flow",
        max_retries=3,
    )
    as_dict = node.to_dict()
    assert as_dict["node_id"] == "check_login"
    assert as_dict["node_type"] == "condition"
    assert as_dict["max_retries"] == 3

    reconstructed = DAGNode.from_dict(as_dict)
    assert reconstructed == node

    with pytest.raises(ValueError):
        DAGNode(node_id="bad", title="Bad Node", node_type="invalid_type")


def test_builtin_dags_loaded_and_saved():
    engine = VisualFlowDAGEngine()
    workflows = engine.list_workflows()
    assert "tiktok_smart_switch_and_engage_dag" in workflows
    assert "web_11_site_smart_patrol_dag" in workflows

    tiktok_spec = engine.load_workflow("tiktok_smart_switch_and_engage_dag")
    tiktok_node_ids = [n["node_id"] for n in tiktok_spec["nodes"]]
    for expected_id in [
        "start_launch",
        "check_ime_or_popup",
        "switch_account_nht",
        "search_tra_dang",
        "open_video_and_like",
        "post_comment_and_verify",
        "recover_back_and_retry",
        "exit_home_done",
    ]:
        assert expected_id in tiktok_node_ids

    web_spec = engine.load_workflow("web_11_site_smart_patrol_dag")
    web_node_ids = [n["node_id"] for n in web_spec["nodes"]]
    assert web_node_ids == [
        "open_chrome_tab",
        "attach_cdp_socket",
        "detect_challenge_type",
        "solve_3tier_gpu",
        "verify_submission",
        "done",
    ]


def test_execute_builtin_dags_happy_path():
    engine = VisualFlowDAGEngine()

    res_tiktok = engine.execute_dag(
        "tiktok_smart_switch_and_engage_dag",
        serial="10CF5L0TYL00312",
        dry_run=True,
    )
    assert res_tiktok["status"] == "DAG_COMPLETED"
    assert res_tiktok["tokens_used"] == 0
    assert res_tiktok["nodes_visited"] == [
        "start_launch",
        "check_ime_or_popup",
        "switch_account_nht",
        "search_tra_dang",
        "open_video_and_like",
        "post_comment_and_verify",
        "exit_home_done",
    ]

    res_web = engine.execute_dag(
        "web_11_site_smart_patrol_dag",
        serial="10CF5L0TYL00312",
        dry_run=True,
    )
    assert res_web["status"] == "DAG_COMPLETED"
    assert res_web["tokens_used"] == 0
    assert res_web["nodes_visited"] == [
        "open_chrome_tab",
        "attach_cdp_socket",
        "detect_challenge_type",
        "solve_3tier_gpu",
        "verify_submission",
        "done",
    ]


def test_conditional_branching_and_failure_recovery():
    engine = VisualFlowDAGEngine()

    # Simulate failure at `open_video_and_like` -> must route to `on_failure` (`recover_back_and_retry`)
    # and then complete at `exit_home_done` with 0 tokens!
    res = engine.execute_dag(
        "tiktok_smart_switch_and_engage_dag",
        serial="10CF5L0TYL00312",
        context={"fail_nodes": ["open_video_and_like"]},
        dry_run=True,
    )
    assert res["status"] == "DAG_COMPLETED"
    assert res["tokens_used"] == 0
    assert "recover_back_and_retry" in res["nodes_visited"]
    assert res["nodes_visited"][-1] == "exit_home_done"

    failure_branches = [
        b for b in res["branch_decisions"] if b["from_node"] == "open_video_and_like"
    ]
    assert len(failure_branches) == 1
    assert failure_branches[0]["branch"] == "on_failure"
    assert failure_branches[0]["to_node"] == "recover_back_and_retry"

    # Also test custom `If Screen Contains X -> Branch A, Else -> Branch B` conditional DAG
    custom_dag = [
        DAGNode(
            node_id="check_captcha_banner",
            title="If Screen Contains Captcha -> Solve, Else -> Direct Submit",
            node_type="condition",
            params={"if_screen_contains": "Slide to verify"},
            on_success="branch_solve_slider",
            on_failure="branch_direct_submit",
        ),
        DAGNode(
            node_id="branch_solve_slider",
            title="Solve Slider Captcha",
            node_type="action",
            on_success="terminal_done",
            on_failure="terminal_done",
        ),
        DAGNode(
            node_id="branch_direct_submit",
            title="Direct Submit Form",
            node_type="action",
            on_success="terminal_done",
            on_failure="terminal_done",
        ),
        DAGNode(
            node_id="terminal_done",
            title="Workflow Complete",
            node_type="terminal",
        ),
    ]

    trace_a = engine.execute_dag(
        custom_dag,
        context={"screen_text": "Please Slide to verify your humanity"},
        dry_run=True,
    )
    assert trace_a["status"] == "DAG_COMPLETED"
    assert trace_a["nodes_visited"] == [
        "check_captcha_banner",
        "branch_solve_slider",
        "terminal_done",
    ]

    trace_b = engine.execute_dag(
        custom_dag,
        context={"screen_text": "Welcome Dashboard Ready"},
        dry_run=True,
    )
    assert trace_b["status"] == "DAG_COMPLETED"
    assert trace_b["nodes_visited"] == [
        "check_captcha_banner",
        "branch_direct_submit",
        "terminal_done",
    ]


def test_render_annotated_preview_frame_dimensions_and_drawings():
    engine = VisualFlowDAGEngine()
    base_img = Image.new("RGB", (1260, 2800), (15, 15, 20))

    blank_preview = engine.render_annotated_preview_frame(
        screen_image=base_img,
        touch_points=[],
        boxes=[],
        preview_size=(320, 700),
    )
    assert isinstance(blank_preview, Image.Image)
    assert blank_preview.mode == "RGB"
    assert blank_preview.size == (320, 700)

    annotated_preview = engine.render_annotated_preview_frame(
        screen_image=base_img,
        touch_points=[(630, 1400), (1140, 2680)],
        boxes=[
            {"bbox": [200, 400, 900, 800], "label": "target_video_card"},
            {"x": 100, "y": 100, "w": 300, "h": 120, "label": "search_bar"},
        ],
        preview_size=(320, 700),
    )
    assert isinstance(annotated_preview, Image.Image)
    assert annotated_preview.mode == "RGB"
    assert annotated_preview.size == (320, 700)

    # Verify that drawn crosshairs, trajectory lines, and bounding boxes altered pixel intensities
    diff = np.abs(
        np.asarray(annotated_preview, dtype=np.int32)
        - np.asarray(blank_preview, dtype=np.int32)
    )
    assert int(diff.sum()) > 10000


def test_visual_flow_subagent_45_wrapper():
    subagent = VisualFlowBuilderAndLiveMonitorSubagent()
    assert subagent.SUBAGENT_ID == 45
    assert subagent.SUBAGENT_NAME == "VisualFlowBuilderAndLiveMonitorSubagent"

    workflows = subagent.list_workflows()
    assert "tiktok_smart_switch_and_engage_dag" in workflows
    assert "web_11_site_smart_patrol_dag" in workflows

    res = subagent.execute_dag(
        "tiktok_smart_switch_and_engage_dag",
        serial="10CF5L0TYL00312",
        context={"fail_nodes": ["search_tra_dang"]},
        dry_run=True,
    )
    assert res["status"] == "DAG_COMPLETED"
    assert res["tokens_used"] == 0
    assert res["subagent_id"] == 45
    assert "recover_back_and_retry" in res["nodes_visited"]

    preview = subagent.render_annotated_preview_frame(
        screen_image=None,
        touch_points=[(500, 1200)],
        boxes=[{"bbox": [100, 200, 600, 500], "label": "button"}],
        preview_size=(320, 700),
    )
    assert preview.size == (320, 700)
    assert preview.mode == "RGB"
