"""
Multi-Account Vault, Rate-Limit Scheduler & Network Proxy Isolation Engine (Feature #44)
========================================================================================
Zero-AI-token engine for managing multi-platform accounts (TikTok `wh0_am_i2342`,
`nht.tn472`, Google, Facebook, etc.), TOTP secrets, device serial binding, human-like
anti-shadowban rate-limiting with jittered cooldowns, and per-device Android HTTP proxy
& network IP isolation auditing.
"""

from __future__ import annotations

import json
import random
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_VAULT_PATH = Path(__file__).resolve().parent.parent / "config" / "account_vault.json"


@dataclass
class AccountProfile:
    """
    Represents a managed social/platform account bound to an Android hardware serial.
    Supports both `Assigned_serial` and `assigned_serial` attribute access for compatibility.
    """

    account_id: str
    platform: str = "tiktok"
    username: str = ""
    Assigned_serial: str = "10CF5L0TYL00312"
    totp_secret: str = ""
    proxy_endpoint: str = "DIRECT"
    daily_actions_count: int = 0
    daily_limit: int = 120
    cooldown_until_ts: float = 0.0
    trust_score: float = 95.0
    last_action: str = "none"

    def __init__(
        self,
        account_id: str = "",
        platform: str = "tiktok",
        username: str = "",
        Assigned_serial: Optional[str] = None,
        totp_secret: str = "",
        proxy_endpoint: str = "DIRECT",
        daily_actions_count: int = 0,
        daily_limit: int = 120,
        cooldown_until_ts: float = 0.0,
        trust_score: float = 95.0,
        last_action: str = "none",
        assigned_serial: Optional[str] = None,
    ) -> None:
        resolved_serial = Assigned_serial or assigned_serial or "10CF5L0TYL00312"
        self.account_id = account_id or f"{platform.lower()}:{username}"
        self.platform = platform.lower()
        self.username = username
        self.Assigned_serial = resolved_serial
        self.totp_secret = totp_secret
        self.proxy_endpoint = proxy_endpoint or "DIRECT"
        self.daily_actions_count = int(daily_actions_count)
        self.daily_limit = int(daily_limit)
        self.cooldown_until_ts = float(cooldown_until_ts)
        self.trust_score = max(0.0, min(100.0, float(trust_score)))
        self.last_action = last_action

    @property
    def assigned_serial(self) -> str:
        return self.Assigned_serial

    @assigned_serial.setter
    def assigned_serial(self, value: str) -> None:
        self.Assigned_serial = value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "account_id": self.account_id,
            "platform": self.platform,
            "username": self.username,
            "Assigned_serial": self.Assigned_serial,
            "assigned_serial": self.Assigned_serial,
            "totp_secret": self.totp_secret,
            "proxy_endpoint": self.proxy_endpoint,
            "daily_actions_count": self.daily_actions_count,
            "daily_limit": self.daily_limit,
            "cooldown_until_ts": self.cooldown_until_ts,
            "trust_score": self.trust_score,
            "last_action": self.last_action,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccountProfile":
        return cls(
            account_id=data.get("account_id", ""),
            platform=data.get("platform", "tiktok"),
            username=data.get("username", ""),
            Assigned_serial=data.get("Assigned_serial") or data.get("assigned_serial") or "10CF5L0TYL00312",
            totp_secret=data.get("totp_secret", ""),
            proxy_endpoint=data.get("proxy_endpoint", "DIRECT"),
            daily_actions_count=int(data.get("daily_actions_count", 0)),
            daily_limit=int(data.get("daily_limit", 120)),
            cooldown_until_ts=float(data.get("cooldown_until_ts", 0.0)),
            trust_score=float(data.get("trust_score", 95.0)),
            last_action=data.get("last_action", "none"),
        )


class MultiAccountVaultAndProxyEngine:
    """
    Persists multi-app account profiles in `config/account_vault.json`, schedules
    human-jitter rate-limited actions, and configures/audits per-device Android
    HTTP proxies and network IP isolation with 0 AI tokens.
    """

    def __init__(
        self,
        vault_path: Optional[Path | str] = None,
        adb_binary: str = "adb",
    ) -> None:
        self.vault_path = Path(vault_path) if vault_path else DEFAULT_VAULT_PATH
        self.adb_binary = adb_binary
        self.accounts: Dict[str, AccountProfile] = {}
        self._load_or_initialize_vault()

    def _default_seed_accounts(self) -> List[AccountProfile]:
        return [
            AccountProfile(
                account_id="tiktok:nht.tn472",
                platform="tiktok",
                username="nht.tn472",
                Assigned_serial="10CF5L0TYL00312",
                totp_secret="",
                proxy_endpoint="DIRECT",
                daily_actions_count=0,
                daily_limit=150,
                cooldown_until_ts=0.0,
                trust_score=98.0,
                last_action="seed_init",
            ),
            AccountProfile(
                account_id="tiktok:wh0_am_i2342",
                platform="tiktok",
                username="wh0_am_i2342",
                Assigned_serial="10CF5L0TYL00312",
                totp_secret="",
                proxy_endpoint="DIRECT",
                daily_actions_count=0,
                daily_limit=150,
                cooldown_until_ts=0.0,
                trust_score=96.0,
                last_action="seed_init",
            ),
        ]

    def _load_or_initialize_vault(self) -> None:
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        if self.vault_path.exists():
            try:
                raw = json.loads(self.vault_path.read_text(encoding="utf-8"))
                records = raw.get("accounts", []) if isinstance(raw, dict) else []
                for item in records:
                    if isinstance(item, dict) and item.get("username"):
                        profile = AccountProfile.from_dict(item)
                        self.accounts[profile.username] = profile
            except Exception:
                self.accounts = {}

        # Ensure pre-populated accounts (`nht.tn472` and `wh0_am_i2342`) always exist
        seeded = False
        for seed_profile in self._default_seed_accounts():
            if seed_profile.username not in self.accounts:
                self.accounts[seed_profile.username] = seed_profile
                seeded = True

        if seeded or not self.vault_path.exists():
            self._save_vault()

    def _save_vault(self) -> None:
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": "1.0",
            "updated_at": time.time(),
            "tokens_used": 0,
            "accounts": [prof.to_dict() for prof in self.accounts.values()],
        }
        self.vault_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def register_or_update_account(
        self,
        username: str,
        platform: str = "tiktok",
        assigned_serial: str = "10CF5L0TYL00312",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Registers a new account or updates an existing account profile in the vault.
        """
        serial_val = kwargs.pop("Assigned_serial", None) or assigned_serial or "10CF5L0TYL00312"
        existing = self.accounts.get(username)

        if existing is None:
            profile = AccountProfile(
                account_id=kwargs.get("account_id", f"{platform.lower()}:{username}"),
                platform=platform.lower(),
                username=username,
                Assigned_serial=serial_val,
                totp_secret=kwargs.get("totp_secret", ""),
                proxy_endpoint=kwargs.get("proxy_endpoint", "DIRECT"),
                daily_actions_count=int(kwargs.get("daily_actions_count", 0)),
                daily_limit=int(kwargs.get("daily_limit", 120)),
                cooldown_until_ts=float(kwargs.get("cooldown_until_ts", 0.0)),
                trust_score=float(kwargs.get("trust_score", 95.0)),
                last_action=kwargs.get("last_action", "registered"),
            )
            self.accounts[username] = profile
        else:
            existing.platform = platform.lower() if platform else existing.platform
            existing.Assigned_serial = serial_val
            for key, val in kwargs.items():
                if hasattr(existing, key) and val is not None:
                    setattr(existing, key, val)
            existing.trust_score = max(0.0, min(100.0, float(existing.trust_score)))
            profile = existing

        self._save_vault()
        return {
            "status": "ACCOUNT_SAVED",
            "account": profile.to_dict(),
            "vault_path": str(self.vault_path),
            "tokens_used": 0,
        }

    def select_next_ready_account(
        self,
        platform: str = "tiktok",
        serial: str = "10CF5L0TYL00312",
        now_ts: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Selects an account matching `platform` and `serial` whose `cooldown_until_ts <= now`
        and `daily_actions_count < daily_limit` with the highest `trust_score`.
        """
        now = float(now_ts) if now_ts is not None else time.time()
        target_platform = platform.lower()

        candidates: List[AccountProfile] = []
        matching_total = 0

        for prof in self.accounts.values():
            if prof.platform == target_platform and prof.Assigned_serial == serial:
                matching_total += 1
                if prof.cooldown_until_ts <= now and prof.daily_actions_count < prof.daily_limit:
                    candidates.append(prof)

        if not candidates:
            return {
                "status": "NO_READY_ACCOUNT",
                "ready": False,
                "platform": target_platform,
                "serial": serial,
                "matching_accounts": matching_total,
                "account": None,
                "tokens_used": 0,
            }

        # Sort by highest trust_score, then lowest daily_actions_count, then username
        candidates.sort(
            key=lambda p: (-p.trust_score, p.daily_actions_count, p.username)
        )
        chosen = candidates[0]
        return {
            "status": "ACCOUNT_READY",
            "ready": True,
            "platform": target_platform,
            "serial": serial,
            "account": chosen.to_dict(),
            "candidates_count": len(candidates),
            "tokens_used": 0,
        }

    def record_account_action_and_schedule_cooldown(
        self,
        username: str,
        action_type: str = "comment",
        base_cooldown_sec: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Increments `daily_actions_count`, computes human jitter cooldown
        (`base_cooldown_sec * uniform(0.85, 1.35)`), updates `trust_score`,
        and persists to `account_vault.json` with `tokens_used: 0`.
        """
        if username not in self.accounts:
            self.register_or_update_account(username=username)

        profile = self.accounts[username]
        now = time.time()
        jitter_factor = random.uniform(0.85, 1.35)
        applied_cooldown_sec = round(max(0.0, float(base_cooldown_sec)) * jitter_factor, 3)

        profile.daily_actions_count += 1
        profile.cooldown_until_ts = now + applied_cooldown_sec
        profile.last_action = action_type

        # Slight organic trust adjustment based on utilization ratio
        utilization = profile.daily_actions_count / max(1, profile.daily_limit)
        if utilization > 0.9:
            profile.trust_score = max(0.0, round(profile.trust_score - 1.5, 2))
        else:
            profile.trust_score = min(100.0, round(profile.trust_score + 0.1, 2))

        self._save_vault()

        return {
            "status": "ACTION_RECORDED",
            "username": profile.username,
            "action_type": action_type,
            "daily_actions_count": profile.daily_actions_count,
            "daily_limit": profile.daily_limit,
            "applied_cooldown_sec": applied_cooldown_sec,
            "jitter_factor": round(jitter_factor, 4),
            "cooldown_until_ts": profile.cooldown_until_ts,
            "trust_score": profile.trust_score,
            "tokens_used": 0,
        }

    def _run_adb_shell(self, serial: str, shell_cmd: str, timeout: float = 8.0) -> str:
        cmd = [self.adb_binary, "-s", serial, "shell", shell_cmd]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return (proc.stdout or "").strip()
        except Exception:
            return ""

    def configure_device_http_proxy(
        self,
        serial: str,
        proxy_host_port: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Sets or clears the Android global HTTP proxy (`settings put global http_proxy <host:port>`
        or `:0` to clear) and returns:
        `{"status": "PROXY_CONFIGURED", "proxy": proxy_host_port or "DIRECT", "tokens_used": 0}`
        """
        cleaned_proxy = (proxy_host_port or "").strip()
        is_clear = not cleaned_proxy or cleaned_proxy.upper() == "DIRECT" or cleaned_proxy == ":0"
        target_arg = ":0" if is_clear else cleaned_proxy
        effective_proxy = "DIRECT" if is_clear else cleaned_proxy
        shell_cmd = f"settings put global http_proxy {target_arg}"

        output = ""
        if not dry_run:
            output = self._run_adb_shell(serial, shell_cmd)

        # Also update bound accounts for this serial
        for prof in self.accounts.values():
            if prof.Assigned_serial == serial:
                prof.proxy_endpoint = effective_proxy
        self._save_vault()

        return {
            "status": "PROXY_CONFIGURED",
            "serial": serial,
            "proxy": effective_proxy,
            "command": shell_cmd,
            "dry_run": dry_run,
            "adb_output": output,
            "tokens_used": 0,
        }

    def audit_device_network_isolation(
        self,
        serial: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Inspects current Wi-Fi / cellular IP and global HTTP proxy settings on `serial`
        with `tokens_used: 0`.
        """
        if dry_run:
            proxy_raw = ":0"
            ip_raw = "inet 192.168.1.100/24 brd 192.168.1.255 scope global wlan0"
        else:
            proxy_raw = self._run_adb_shell(serial, "settings get global http_proxy")
            ip_raw = self._run_adb_shell(serial, "ip -4 addr show wlan0")
            if not ip_raw:
                ip_raw = self._run_adb_shell(serial, "ip route")

        proxy_clean = (proxy_raw or "").strip()
        if not proxy_clean or proxy_clean in (":0", "null", "None"):
            active_proxy = "DIRECT"
        else:
            active_proxy = proxy_clean

        ipv4_match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})", ip_raw or "")
        local_ip = ipv4_match.group(1) if ipv4_match else "0.0.0.0"

        bound_accounts = [
            prof.username
            for prof in self.accounts.values()
            if prof.Assigned_serial == serial
        ]

        return {
            "status": "NETWORK_ISOLATION_AUDITED",
            "serial": serial,
            "active_proxy": active_proxy,
            "local_ipv4": local_ip,
            "bound_accounts": bound_accounts,
            "dry_run": dry_run,
            "tokens_used": 0,
        }
