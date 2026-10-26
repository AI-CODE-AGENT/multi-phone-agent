"""
Unit Tests for Feature #44: Multi-Account Vault, Rate-Limit Scheduler & Network Proxy Isolation Engine
"""

import json
import sys
import time
from pathlib import Path
from typing import Iterator

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents.account_vault_proxy_subagent import MultiAccountVaultAndProxySubagent
from core.account_vault_proxy_engine import (
    DEFAULT_VAULT_PATH,
    AccountProfile,
    MultiAccountVaultAndProxyEngine,
)


@pytest.fixture
def isolated_vault_file() -> Iterator[Path]:
    """Provide a clean test vault file inside project config dir without touching OS %TEMP%."""
    test_vault = DEFAULT_VAULT_PATH.parent / f"test_account_vault_{int(time.time() * 1000)}.json"
    if test_vault.exists():
        test_vault.unlink()
    try:
        yield test_vault
    finally:
        if test_vault.exists():
            try:
                test_vault.unlink()
            except OSError:
                pass


def test_default_prepopulated_tiktok_profiles(isolated_vault_file: Path) -> None:
    """Verify default vault and isolated vault contain pre-populated `nht.tn472` and `wh0_am_i2342`."""
    default_engine = MultiAccountVaultAndProxyEngine()
    assert DEFAULT_VAULT_PATH.exists()
    assert "nht.tn472" in default_engine.accounts
    assert "wh0_am_i2342" in default_engine.accounts

    engine = MultiAccountVaultAndProxyEngine(vault_path=isolated_vault_file)
    assert isolated_vault_file.exists()

    p1 = engine.accounts["nht.tn472"]
    p2 = engine.accounts["wh0_am_i2342"]

    assert isinstance(p1, AccountProfile)
    assert p1.platform == "tiktok"
    assert p1.Assigned_serial == "10CF5L0TYL00312"
    assert p2.platform == "tiktok"
    assert p2.Assigned_serial == "10CF5L0TYL00312"
    assert 0.0 <= p1.trust_score <= 100.0
    assert 0.0 <= p2.trust_score <= 100.0

    saved_data = json.loads(isolated_vault_file.read_text(encoding="utf-8"))
    usernames = {item["username"] for item in saved_data["accounts"]}
    assert {"nht.tn472", "wh0_am_i2342"}.issubset(usernames)


def test_select_ready_account_and_cooldown_rotation(isolated_vault_file: Path) -> None:
    """Verify selecting highest-trust ready account, recording action with jitter cooldown, and rotating."""
    engine = MultiAccountVaultAndProxyEngine(vault_path=isolated_vault_file)

    # nht.tn472 starts with trust_score 98.0 > wh0_am_i2342 (96.0)
    sel1 = engine.select_next_ready_account(platform="tiktok", serial="10CF5L0TYL00312")
    assert sel1["status"] == "ACCOUNT_READY"
    assert sel1["ready"] is True
    assert sel1["account"]["username"] == "nht.tn472"
    assert sel1["tokens_used"] == 0

    # Record an action on nht.tn472 with 60s base cooldown
    act_res = engine.record_account_action_and_schedule_cooldown(
        username="nht.tn472",
        action_type="comment",
        base_cooldown_sec=60.0,
    )
    assert act_res["status"] == "ACTION_RECORDED"
    assert act_res["daily_actions_count"] == 1
    assert 60.0 * 0.85 <= act_res["applied_cooldown_sec"] <= 60.0 * 1.35
    assert act_res["cooldown_until_ts"] > time.time()
    assert act_res["tokens_used"] == 0

    # Now nht.tn472 is on cooldown, so select_next_ready_account should pick wh0_am_i2342
    sel2 = engine.select_next_ready_account(platform="tiktok", serial="10CF5L0TYL00312")
    assert sel2["status"] == "ACCOUNT_READY"
    assert sel2["ready"] is True
    assert sel2["account"]["username"] == "wh0_am_i2342"
    assert sel2["tokens_used"] == 0


def test_daily_rate_limit_enforcement(isolated_vault_file: Path) -> None:
    """Verify accounts that reach daily_limit are excluded from ready selection."""
    engine = MultiAccountVaultAndProxyEngine(vault_path=isolated_vault_file)

    engine.register_or_update_account(
        username="nht.tn472",
        platform="tiktok",
        assigned_serial="10CF5L0TYL00312",
        daily_actions_count=150,
        daily_limit=150,
        cooldown_until_ts=0.0,
    )
    engine.register_or_update_account(
        username="wh0_am_i2342",
        platform="tiktok",
        assigned_serial="10CF5L0TYL00312",
        daily_actions_count=150,
        daily_limit=150,
        cooldown_until_ts=0.0,
    )

    sel = engine.select_next_ready_account(platform="tiktok", serial="10CF5L0TYL00312")
    assert sel["status"] == "NO_READY_ACCOUNT"
    assert sel["ready"] is False
    assert sel["account"] is None
    assert sel["tokens_used"] == 0


def test_configure_and_clear_http_proxy_dry_run(isolated_vault_file: Path) -> None:
    """Verify setting and clearing Android global HTTP proxy in dry_run=True mode with 0 tokens."""
    engine = MultiAccountVaultAndProxyEngine(vault_path=isolated_vault_file)

    set_res = engine.configure_device_http_proxy(
        serial="10CF5L0TYL00312",
        proxy_host_port="127.0.0.1:8888",
        dry_run=True,
    )
    assert set_res["status"] == "PROXY_CONFIGURED"
    assert set_res["proxy"] == "127.0.0.1:8888"
    assert "settings put global http_proxy 127.0.0.1:8888" in set_res["command"]
    assert set_res["tokens_used"] == 0
    assert engine.accounts["nht.tn472"].proxy_endpoint == "127.0.0.1:8888"

    clear_res = engine.configure_device_http_proxy(
        serial="10CF5L0TYL00312",
        proxy_host_port=None,
        dry_run=True,
    )
    assert clear_res["status"] == "PROXY_CONFIGURED"
    assert clear_res["proxy"] == "DIRECT"
    assert "settings put global http_proxy :0" in clear_res["command"]
    assert clear_res["tokens_used"] == 0
    assert engine.accounts["nht.tn472"].proxy_endpoint == "DIRECT"


def test_subagent_44_vault_and_proxy_audit(isolated_vault_file: Path) -> None:
    """Verify MultiAccountVaultAndProxySubagent (#44) end-to-end audit in dry_run mode."""
    subagent = MultiAccountVaultAndProxySubagent(vault_path=isolated_vault_file)

    assert subagent.SUBAGENT_ID == 44
    assert subagent.SUBAGENT_NAME == "MultiAccountVaultAndProxySubagent"

    audit = subagent.run_vault_and_proxy_audit(
        serial="10CF5L0TYL00312",
        dry_run=True,
    )
    assert audit["status"] == "VAULT_AND_PROXY_AUDITED"
    assert audit["subagent_id"] == 44
    assert audit["tokens_used"] == 0
    assert audit["ready_selection"]["ready"] is True
    assert audit["network_audit"]["status"] == "NETWORK_ISOLATION_AUDITED"
    assert audit["network_audit"]["tokens_used"] == 0
    assert "nht.tn472" in audit["network_audit"]["bound_accounts"]
    assert "wh0_am_i2342" in audit["network_audit"]["bound_accounts"]
