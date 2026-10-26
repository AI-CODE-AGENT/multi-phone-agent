"""
Unit & Integration Tests for AMAF v20.0:
- Feature #1: OpenTelemetry GenAI Agent Flight Recorder (`logs/agent_flight_recorder.jsonl`) + Unbuffered Heartbeat Stream
- Feature #2: Universal Cross-Project Error Ledger & Auto-Reflexion Guard (`ERR-001`..`ERR-012`)
- Feature #3: MCP Stdio Oneshot Probe Runner (Eliminates 'Status: RUNNING / No log output recorded yet' hangs)
- Feature #4: Live Flight Log Multi-Criteria Filter & Agent Context Export
- Feature #5: Time-Travel Step Replay & Smart Locator Self-Healing Engine (`Dynamic-First, Coordinate-Fallback`)
- Subagents #126-#135 (Total 135 Subagents) & MCP Tools #71-#76 (Total 76 On-Demand MCP Tools)
"""

import io
import os
from pathlib import Path

from core.agent_flight_recorder import AgentFlightRecorder, redact_and_truncate_payload
from core.universal_error_ledger_engine import UniversalErrorLedgerEngine
from agents.agent_observability_and_error_ledger_subagent import (
    AutoReflexionExceptionDiagnoserSubagent,
    Causal10xV20ObservabilityAndReflexionEvolverSubagent,
    LiveFlightLogFilterAndExportSubagent,
    MCPStdioOneshotProbeSubagent,
    OTelGenAIFlightRecorderSubagent,
    PIIAndTokenBloatRedactorSubagent,
    SmartLocatorSelfHealingEngineSubagent,
    TimeTravelStepReplayInspectorSubagent,
    UnbufferedHeartbeatStreamGuardSubagent,
    UniversalCrossProjectErrorLedgerSubagent,
)
from mcp_bridge.android_farm_mcp_server import AndroidFarmMCPServer


def test_v20_otel_flight_recorder_and_unbuffered_heartbeat():
    assert os.environ.get("PYTHONUNBUFFERED") == "1"
    recorder = AgentFlightRecorder()

    buf = io.StringIO()
    hb = recorder.emit_heartbeat(
        phase="START",
        agent_name="DrawSIMCPBridge",
        tool_name="probe_stdio",
        trace_id="trc_test_001",
        detail="step=1",
        stream=buf,
    )
    assert "[HEARTBEAT:START]" in hb
    assert "trace=trc_test_001" in buf.getvalue()

    with recorder.span(
        agent_name="VivoInstaller(#46)",
        tool_name="install_apk_guarded",
        device_serial="10CF5L0TYL00312",
        input_args={"apk": "app.apk", "api_key": "sk-1234567890abcdefghijklmnop"},
        emit_heartbeat_line=True,
    ) as sp:
        sp["output"] = {"installed": True}
        sp["snapshot"] = {
            "screen_signature": "vivo_install_modal",
            "resource_id": "com.android.packageinstaller:id/confirm_btn",
            "text_label": "Tiếp tục",
            "fallback_coordinates": [630, 2580],
        }

    rec = sp["record"]
    assert rec["attributes"]["gen_ai.agent.name"] == "VivoInstaller(#46)"
    assert rec["attributes"]["gen_ai.tool.status"] == "success"
    assert "[REDACTED" in str(rec["payload"]["input"])
    assert Path(recorder.log_path).exists()


def test_v20_pii_redaction_and_token_bloat_truncation():
    s133 = PIIAndTokenBloatRedactorSubagent()
    huge_payload = {
        "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secretpayload",
        "xml_dump": "<node index='0'>" * 120,
    }
    res = s133.execute(huge_payload, max_chars=200)
    sanitized = res["sanitized_payload"]
    assert sanitized["_truncated"] is True
    assert "[REDACTED_TOKEN]" in sanitized["preview"]
    assert len(sanitized["sha256_16"]) == 16


def test_v20_universal_cross_project_error_ledger_and_diagnosis():
    ledger = UniversalErrorLedgerEngine()
    entries = ledger.list_errors()
    assert len(entries) >= 12
    assert Path(r"D:\Project\UNIVERSAL_ENGINEERING_ERROR_PLAYBOOK.md").exists()
    assert Path(r"D:\Project\universal_error_ledger.jsonl").exists()

    # Diagnose exact user screenshot symptom (ERR-001)
    s129 = AutoReflexionExceptionDiagnoserSubagent(ledger)
    d1 = s129.execute("Checked task Test DrawSI MCP with npx tsx: Status: RUNNING - No log output recorded yet.")
    assert d1["matched"] is True
    assert d1["entry"]["error_id"] == "ERR-001"
    assert d1["confidence"] >= 0.99

    # Diagnose PowerShell UTF-8 corruption (ERR-002)
    d2 = s129.execute("Piping script via PowerShell turned Tiếng Việt into ? Light Mode")
    assert d2["matched"] is True
    assert d2["entry"]["error_id"] == "ERR-002"

    # Diagnose ImageGrab failure (ERR-004)
    d4 = s129.execute("OSError: screen grab failed in ImageGrab.grab")
    assert d4["matched"] is True
    assert d4["entry"]["error_id"] == "ERR-004"

    # Register in-memory test error without polluting disk
    reg = ledger.register_error(
        category="TEST_CATEGORY",
        tech_stack=["Pytest"],
        symptom="Unique synthetic test symptom v20",
        root_cause="Synthetic root cause",
        golden_rule="Always isolate test state",
        persist_to_disk=False,
    )
    assert reg["status"] in ("registered", "already_exists")


def test_v20_mcp_stdio_oneshot_probe_zero_hang():
    s130 = MCPStdioOneshotProbeSubagent()
    res = s130.execute(timeout_sec=5.0)
    assert res["subagent_id"] == 130
    assert res["stdin_eof_closed"] is True
    assert res["hang_prevented"] is True
    assert res["healthy"] is True
    assert res["status"] == "ONESHOT_PROBE_OK"
    assert res["jsonrpc_response"]["result"]["serverInfo"]["name"] == "android-multi-agent-farm"


def test_v20_time_travel_replay_and_smart_locator_self_healing():
    s131 = TimeTravelStepReplayInspectorSubagent()
    s132 = SmartLocatorSelfHealingEngineSubagent()
    s134 = LiveFlightLogFilterAndExportSubagent()
    s135 = Causal10xV20ObservabilityAndReflexionEvolverSubagent()

    r135 = s135.execute(serial="10CF5L0TYL00312", loops=10)
    assert r135["subagent_id"] == 135
    assert r135["loops_completed"] == 10
    assert r135["all_10_loops_passed"] is True
    assert r135["self_healing_verified"] is True

    r131 = s131.execute()
    assert r131["subagent_id"] == 131
    assert r131["inspected_span"] is not None

    r132 = s132.execute(broken_locator="//android.widget.Button[@text='Cài đặt']")
    assert r132["subagent_id"] == 132
    assert r132["healing_status"] == "SELF_HEALED_VERIFIED"
    assert len(r132["primary_dynamic_locators"]) >= 3
    assert "absolute_xy" in r132["coordinate_fallback"]

    r134 = s134.execute(status="healed", limit=10)
    assert r134["subagent_id"] == 134
    assert r134["matched_count"] >= 1


def test_v20_mcp_server_76_tools_end_to_end():
    server = AndroidFarmMCPServer()
    tools = server.list_tools()
    assert len(tools) == 76
    tool_names = {t["name"] for t in tools}
    expected_v20_tools = {
        "android_record_agent_flight_span",
        "android_query_agent_flight_logs",
        "android_diagnose_with_error_ledger",
        "android_register_cross_project_error",
        "android_probe_mcp_stdio_health",
        "android_time_travel_replay_and_heal_locator",
    }
    assert expected_v20_tools.issubset(tool_names)

    r71 = server.handle_tool_call(
        "android_record_agent_flight_span",
        {"agent_name": "TestAgent", "tool_name": "tap_confirm", "duration_ms": 8.5},
    )
    assert r71["success"] is True
    assert r71["otel_compliant"] is True

    r72 = server.handle_tool_call("android_query_agent_flight_logs", {"limit": 5})
    assert r72["success"] is True
    assert r72["matched_count"] >= 1

    r73 = server.handle_tool_call(
        "android_diagnose_with_error_ledger",
        {"error_text": "Status: RUNNING - No log output recorded yet"},
    )
    assert r73["success"] is True
    assert r73["entry"]["error_id"] == "ERR-001"

    r75 = server.handle_tool_call("android_probe_mcp_stdio_health", {"timeout_sec": 4.0})
    assert r75["success"] is True
    assert r75["healthy"] is True

    r76 = server.handle_tool_call(
        "android_time_travel_replay_and_heal_locator",
        {"broken_locator": "//android.widget.Button[@text='Tiếp tục']", "run_10x_loop": True},
    )
    assert r76["success"] is True
    assert r76["healing_status"] == "SELF_HEALED_VERIFIED"
    assert r76["causal_10x_v20"]["all_10_loops_passed"] is True
