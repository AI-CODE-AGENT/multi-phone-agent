"""
Universal 2FA Engine (RFC 4226 HOTP & RFC 6238 TOTP + otpauth:// Vault + Backup Codes)
Inspired by pyauth/pyotp, Google Authenticator otpauth:// URI Format, and Android Credential Manager.
Pure Python standard library implementation (hmac, hashlib, base64, struct, urllib.parse, time, json).
"""

import base64
import hashlib
import hmac
import json
import os
import struct
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional


class Universal2FAEngine:
    """
    Production-grade RFC 4226 HOTP and RFC 6238 TOTP generator, verifier,
    otpauth:// URI parser, and atomic 2FA account & backup recovery code vault.
    """

    HASH_ALGORITHMS = {
        "SHA1": hashlib.sha1,
        "SHA256": hashlib.sha256,
        "SHA512": hashlib.sha512,
    }

    def __init__(self, vault_file: Optional[Path] = None):
        self.vault_file = (
            Path(vault_file)
            if vault_file
            else (Path(__file__).resolve().parent.parent / "config" / "2fa_vault.json")
        )
        self._lock = threading.Lock()
        self._ensure_vault_file()

    def _ensure_vault_file(self) -> None:
        """Initialize the 2FA vault JSON file if it does not exist."""
        self.vault_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.vault_file.exists():
            default_vault = {
                "version": "1.0",
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "accounts": {},
                "backup_codes": {},
            }
            self._save_vault(default_vault)

    def _load_vault(self) -> Dict[str, Any]:
        """Load the 2FA vault safely with thread lock."""
        with self._lock:
            try:
                if self.vault_file.exists():
                    with open(self.vault_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            data.setdefault("accounts", {})
                            data.setdefault("backup_codes", {})
                            return data
            except Exception:
                pass
            return {
                "version": "1.0",
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "accounts": {},
                "backup_codes": {},
            }

    def _save_vault(self, data: Dict[str, Any]) -> None:
        """Atomically write the 2FA vault JSON to disk."""
        with self._lock:
            self.vault_file.parent.mkdir(parents=True, exist_ok=True)
            data["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            tmp_file = self.vault_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_file, self.vault_file)

    # ------------------------------------------------------------------
    # 1. RFC 4226 HOTP & RFC 6238 TOTP Pure-Python Implementation
    # ------------------------------------------------------------------
    @staticmethod
    def _decode_base32_secret(secret: str) -> bytes:
        """
        Normalize a Base32 secret string (removes spaces/hyphens, uppercases,
        pads with '=' to a multiple of 8) and return decoded bytes via base64.b32decode.
        """
        if not secret:
            raise ValueError("2FA secret cannot be empty")
        cleaned = secret.strip().replace(" ", "").replace("-", "").upper()
        cleaned = cleaned.rstrip("=")
        pad_len = (8 - (len(cleaned) % 8)) % 8
        padded = cleaned + ("=" * pad_len)
        return base64.b32decode(padded, casefold=True)

    def generate_hotp(
        self,
        secret: str,
        counter: int,
        digits: int = 6,
        algorithm: str = "SHA1",
    ) -> str:
        """
        Generate an RFC 4226 HMAC-Based One-Time Password (HOTP).
        Uses dynamic truncation:
          offset = hmac_digest[-1] & 0x0F
          code_int = ((hmac_digest[offset] & 0x7F) << 24 | ...) % (10 ** digits)
        """
        algo_name = (algorithm or "SHA1").upper().replace("-", "")
        if algo_name not in self.HASH_ALGORITHMS:
            raise ValueError(f"Unsupported HMAC algorithm: {algorithm}")

        key = self._decode_base32_secret(secret)
        counter_bytes = struct.pack(">Q", int(counter))
        hmac_digest = hmac.new(key, counter_bytes, self.HASH_ALGORITHMS[algo_name]).digest()

        offset = hmac_digest[-1] & 0x0F
        code_int = (
            ((hmac_digest[offset] & 0x7F) << 24)
            | ((hmac_digest[offset + 1] & 0xFF) << 16)
            | ((hmac_digest[offset + 2] & 0xFF) << 8)
            | (hmac_digest[offset + 3] & 0xFF)
        ) % (10 ** int(digits))

        return str(code_int).zfill(int(digits))

    def generate_totp(
        self,
        secret: str,
        timestamp: Optional[float] = None,
        period: int = 30,
        digits: int = 6,
        algorithm: str = "SHA1",
    ) -> Dict[str, Any]:
        """
        Generate an RFC 6238 Time-Based One-Time Password (TOTP) along with
        countdown metadata (counter, remaining_seconds, period, algorithm).
        """
        ts = float(timestamp) if timestamp is not None else time.time()
        period_int = max(1, int(period))
        digits_int = int(digits)
        algo_name = (algorithm or "SHA1").upper().replace("-", "")

        counter = int(ts // period_int)
        remaining_seconds = period_int - (int(ts) % period_int)
        code_str = self.generate_hotp(
            secret=secret,
            counter=counter,
            digits=digits_int,
            algorithm=algo_name,
        )

        return {
            "code": code_str,
            "digits": digits_int,
            "period": period_int,
            "algorithm": algo_name,
            "counter": counter,
            "remaining_seconds": remaining_seconds,
        }

    def verify_totp(
        self,
        secret: str,
        code: str,
        timestamp: Optional[float] = None,
        period: int = 30,
        digits: int = 6,
        algorithm: str = "SHA1",
        valid_window: int = 1,
    ) -> bool:
        """
        Verify a TOTP code against `counter + d` for `d in range(-valid_window, valid_window + 1)`
        to gracefully handle device/server clock drift.
        """
        if not code:
            return False
        candidate_clean = str(code).strip().replace(" ", "")
        ts = float(timestamp) if timestamp is not None else time.time()
        period_int = max(1, int(period))
        base_counter = int(ts // period_int)
        window = max(0, int(valid_window))

        for delta in range(-window, window + 1):
            expected = self.generate_hotp(
                secret=secret,
                counter=base_counter + delta,
                digits=digits,
                algorithm=algorithm,
            )
            if hmac.compare_digest(expected, candidate_clean):
                return True
        return False

    # ------------------------------------------------------------------
    # 2. otpauth:// URI Parser & Vault Manager
    # ------------------------------------------------------------------
    def register_otpauth_uri(self, uri: str) -> Dict[str, Any]:
        """
        Parse a Google Authenticator `otpauth://` URI:
          otpauth://totp/Issuer:account?secret=JBSWY3DPEHPK3PXP&issuer=Issuer&digits=6&period=30&algorithm=SHA1
        or `otpauth://hotp/...&counter=0`.
        Saves the account in `self.vault_file` under `account_id` and returns
        the parsed account metadata + current generated code.
        """
        if not uri or not uri.strip().lower().startswith("otpauth://"):
            raise ValueError(f"Invalid otpauth:// URI: {uri}")

        parsed = urllib.parse.urlparse(uri.strip())
        otp_type = parsed.netloc.lower()
        if otp_type not in ("totp", "hotp"):
            raise ValueError(f"Unsupported otpauth type '{otp_type}' in URI: {uri}")

        raw_label = urllib.parse.unquote(parsed.path.lstrip("/"))
        params = urllib.parse.parse_qs(parsed.query)

        secret = (params.get("secret", [""])[0]).strip()
        if not secret:
            raise ValueError("Missing 'secret' parameter in otpauth:// URI")
        # Validate base32 secret early
        self._decode_base32_secret(secret)

        issuer_param = (params.get("issuer", [""])[0]).strip()
        if ":" in raw_label:
            label_issuer, account_name = raw_label.split(":", 1)
            label_issuer = label_issuer.strip()
            account_name = account_name.strip()
        else:
            label_issuer = ""
            account_name = raw_label.strip()

        issuer = issuer_param or label_issuer
        account_id = raw_label if raw_label else (f"{issuer}:{account_name}" if issuer else account_name or "default")

        digits = int(params.get("digits", ["6"])[0])
        period = int(params.get("period", ["30"])[0])
        counter = int(params.get("counter", ["0"])[0])
        algorithm = (params.get("algorithm", ["SHA1"])[0]).strip().upper()

        account_record = {
            "account_id": account_id,
            "type": otp_type,
            "issuer": issuer,
            "account_name": account_name,
            "secret": secret.replace(" ", "").upper(),
            "digits": digits,
            "period": period,
            "counter": counter,
            "algorithm": algorithm,
            "uri": uri.strip(),
            "registered_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        vault = self._load_vault()
        vault["accounts"][account_id] = account_record
        self._save_vault(vault)

        if otp_type == "totp":
            gen = self.generate_totp(
                secret=secret,
                period=period,
                digits=digits,
                algorithm=algorithm,
            )
            current_code = gen["code"]
            remaining_seconds = gen["remaining_seconds"]
        else:
            current_code = self.generate_hotp(
                secret=secret,
                counter=counter,
                digits=digits,
                algorithm=algorithm,
            )
            remaining_seconds = None

        return {
            **account_record,
            "current_code": current_code,
            "remaining_seconds": remaining_seconds,
        }

    def get_account_code(
        self,
        account_id: str,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve an account from the vault by `account_id` (or partial match)
        and compute its current TOTP/HOTP code.
        """
        vault = self._load_vault()
        accounts = vault.get("accounts", {})
        record = accounts.get(account_id)

        if not record:
            for key, val in accounts.items():
                if account_id.lower() in key.lower() or account_id.lower() == val.get("account_name", "").lower():
                    record = val
                    account_id = key
                    break

        if not record:
            raise KeyError(f"Account '{account_id}' not found in 2FA vault")

        otp_type = record.get("type", "totp").lower()
        secret = record["secret"]
        digits = int(record.get("digits", 6))
        period = int(record.get("period", 30))
        algorithm = record.get("algorithm", "SHA1")

        if otp_type == "hotp":
            counter = int(record.get("counter", 0))
            code = self.generate_hotp(
                secret=secret,
                counter=counter,
                digits=digits,
                algorithm=algorithm,
            )
            record["counter"] = counter + 1
            vault["accounts"][account_id] = record
            self._save_vault(vault)
            return {
                "account_id": account_id,
                "type": "hotp",
                "code": code,
                "digits": digits,
                "counter": counter,
                "algorithm": algorithm,
            }

        totp_res = self.generate_totp(
            secret=secret,
            timestamp=timestamp,
            period=period,
            digits=digits,
            algorithm=algorithm,
        )
        return {
            "account_id": account_id,
            "type": "totp",
            **totp_res,
        }

    def register_backup_codes(self, account_id: str, codes: List[str]) -> Dict[str, Any]:
        """
        Store recovery backup codes (e.g., ["8492-1029", "7381-9920"]) for `account_id`
        so they can be consumed one by one when `consume_backup_code(account_id)` is called.
        """
        cleaned_codes = [str(c).strip() for c in codes if str(c).strip()]
        vault = self._load_vault()
        vault.setdefault("backup_codes", {})
        vault["backup_codes"][account_id] = {
            "unused": cleaned_codes,
            "consumed": [],
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._save_vault(vault)
        return {
            "account_id": account_id,
            "unused_count": len(cleaned_codes),
            "consumed_count": 0,
            "unused": list(cleaned_codes),
        }

    def consume_backup_code(self, account_id: Optional[str] = None) -> Optional[str]:
        """
        Pop and return the next unused backup recovery code for `account_id`.
        If `account_id` is None, checks any account with available backup codes.
        """
        vault = self._load_vault()
        backup_map = vault.get("backup_codes", {})

        target_id = account_id
        if not target_id or target_id not in backup_map:
            for k, v in backup_map.items():
                if v.get("unused"):
                    target_id = k
                    break

        if not target_id or target_id not in backup_map:
            return None

        entry = backup_map[target_id]
        unused = entry.get("unused", [])
        if not unused:
            return None

        next_code = unused.pop(0)
        entry.setdefault("consumed", []).append(
            {"code": next_code, "consumed_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        )
        entry["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        vault["backup_codes"][target_id] = entry
        self._save_vault(vault)
        return next_code


if __name__ == "__main__":
    import tempfile

    print("Running Universal2FAEngine RFC 4226 / RFC 6238 self-test...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        vault_path = Path(tmp_dir) / "test_2fa_vault.json"
        engine = Universal2FAEngine(vault_file=vault_path)

        # RFC 4226 Official Test Vector (Secret = "12345678901234567890" -> Base32 "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ")
        rfc_secret_b32 = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        expected_hotp = [
            "755224",
            "287082",
            "359152",
            "969429",
            "338314",
            "254676",
            "287922",
            "162583",
            "399871",
            "520489",
        ]
        for cnt, exp in enumerate(expected_hotp):
            got = engine.generate_hotp(rfc_secret_b32, counter=cnt, digits=6, algorithm="SHA1")
            assert got == exp, f"RFC 4226 mismatch at counter={cnt}: got {got}, expected {exp}"

        # RFC 6238 Test Vector at timestamp=59 (counter=1 -> 94287082 for 8 digits)
        totp_59 = engine.generate_totp(rfc_secret_b32, timestamp=59, period=30, digits=8, algorithm="SHA1")
        assert totp_59["code"] == "94287082", f"RFC 6238 mismatch: {totp_59}"
        assert engine.verify_totp(rfc_secret_b32, "94287082", timestamp=60, period=30, digits=8, valid_window=1)

        # otpauth:// URI registration & lookup
        uri = "otpauth://totp/GitHub:octocat?secret=JBSWY3DPEHPK3PXP&issuer=GitHub&digits=6&period=30&algorithm=SHA1"
        reg = engine.register_otpauth_uri(uri)
        assert reg["account_id"] == "GitHub:octocat"
        assert len(reg["current_code"]) == 6
        acct_code = engine.get_account_code("GitHub:octocat")
        assert len(acct_code["code"]) == 6

        # Backup codes registration & consumption
        engine.register_backup_codes("GitHub:octocat", ["8492-1029", "7381-9920"])
        c1 = engine.consume_backup_code("GitHub:octocat")
        c2 = engine.consume_backup_code("GitHub:octocat")
        c3 = engine.consume_backup_code("GitHub:octocat")
        assert c1 == "8492-1029"
        assert c2 == "7381-9920"
        assert c3 is None

        print("ALL Universal2FAEngine checks PASSED:", {
            "rfc4226_counter_0": expected_hotp[0],
            "rfc6238_ts_59_8digits": totp_59["code"],
            "otpauth_account": reg["account_id"],
            "sample_totp": acct_code["code"],
        })
