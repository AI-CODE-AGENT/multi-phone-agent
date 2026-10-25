"""
Mock OTP Service & Interceptor (Zero-Cost Testing)
Generates, stores, and intercepts OTP codes locally in memory and mock telephony provider.
Enables 100% automated end-to-end testing with 0 VND SMS carrier expenses.
"""

import time
import random
import re
import json
import threading
from typing import Dict, Optional, Any, Tuple
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.hardware_simulator import HardwareSimulator

STORE_FILE = Path(__file__).resolve().parent.parent / "config" / "mock_otp_store.json"


class MockOTPService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, hardware: Optional[HardwareSimulator] = None):
        if getattr(self, "_initialized", False):
            return
        if isinstance(hardware, HardwareSimulator):
            self.hardware = hardware
        elif hardware is not None and hasattr(hardware, "run_device_cmd"):
            # Caller passed an ADBWrapper instance directly
            self.hardware = HardwareSimulator(hardware)
        else:
            self.hardware = HardwareSimulator()
        self.store_file = STORE_FILE
        self._store_lock = threading.Lock()
        self._ensure_store_file()
        self._initialized = True

    def _ensure_store_file(self):
        with self._store_lock:
            if not self.store_file.exists():
                self.store_file.parent.mkdir(parents=True, exist_ok=True)
                self.store_file.write_text("{}", encoding="utf-8")

    def _load_store(self) -> Dict[str, Dict[str, Any]]:
        try:
            with open(self.store_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_store(self, data: Dict[str, Dict[str, Any]]):
        try:
            with open(self.store_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def generate_otp(self, phone: str, brand: str = "TestApp", length: int = 6, ttl_seconds: int = 300) -> str:
        """Generate, store, and return a fresh mock OTP code."""
        clean_phone = phone.strip().replace(" ", "").replace("+84", "0")
        code = "".join([str(random.randint(0, 9)) for _ in range(length)])
        now = time.time()

        with self._store_lock:
            store = self._load_store()
            store[clean_phone] = {
                "code": code,
                "brand": brand,
                "created_at": now,
                "expires_at": now + ttl_seconds,
                "verified": False
            }
            self._save_store(store)
        return code

    def get_latest_otp(self, phone: str) -> Optional[str]:
        """Fetch the active unexpired OTP code for a phone number."""
        clean_phone = phone.strip().replace(" ", "").replace("+84", "0")
        with self._store_lock:
            store = self._load_store()
            record = store.get(clean_phone)
            if record:
                if time.time() < record.get("expires_at", 0):
                    return record.get("code")
        return None

    def verify_otp(self, phone: str, code: str) -> bool:
        """Verify that the supplied OTP matches the active code."""
        clean_phone = phone.strip().replace(" ", "").replace("+84", "0")
        with self._store_lock:
            store = self._load_store()
            record = store.get(clean_phone)
            if record and not record.get("verified", False):
                if time.time() < record.get("expires_at", 0) and record.get("code") == code.strip():
                    record["verified"] = True
                    self._save_store(store)
                    return True
        return False

    def deliver_mock_sms_to_device(self, serial: str, phone: str, code: Optional[str] = None) -> Tuple[bool, str]:
        """
        Inject the OTP directly into the virtual phone's Android SMS inbox.
        Triggers Android Telephony SMS Receiver and Google SMS Retriever API with 0 VND cost.
        """
        otp_code = code or self.get_latest_otp(phone) or self.generate_otp(phone)
        msg = f"[MockOTP] Ma xac thuc cua ban la: {otp_code}. Co hieu luc trong 5 phut."
        ok, res = self.hardware.send_sms_otp(serial, phone, msg)
        return ok, f"Injected OTP {otp_code} to {serial} -> {res}"

    @staticmethod
    def extract_otp_from_text(text: str, length: int = 6) -> Optional[str]:
        """Extract a 4 to 8 digit OTP code from arbitrary notification or UI text."""
        if not text:
            return None
        # Match standalone digits
        patterns = [
            rf"\b(\d{{{length}}})\b",
            r"(?:code|otp|mã|xác thực|is|la)[:\s]*(\d{4,8})",
            r"\b(\d{4,8})\b"
        ]
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None


if __name__ == "__main__":
    service = MockOTPService()
    phone = "0941189263"
    code = service.generate_otp(phone)
    print(f"Generated OTP for {phone}: {code}")
    print("Fetched OTP:", service.get_latest_otp(phone))
    print("Verify with correct code:", service.verify_otp(phone, code))
    print("Verify with wrong code:", service.verify_otp(phone, "000000"))
