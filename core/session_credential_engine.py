"""
Session & Credential Engine for Cross-App Authentication Workflows (AMAF v8.0)
Inspired by Mobile-Agent-E and AndroidWorld cross-app authentication, account inspection,
autofill service auditing, and OTP replay-deduplication workflows.
"""

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


class SessionAndCredentialEngine:
    """
    Deterministic engine for classifying authentication screen gates, inspecting
    registered Android accounts + Autofill/Credential Manager services, and
    extracting fresh OTP tokens with replay deduplication.
    """

    AUTH_STATES = (
        "CAPTCHA_WALL",
        "TWO_FACTOR_PROMPT",
        "BIOMETRIC_PROMPT",
        "OEM_SECURITY_DIALOG",
        "LOGIN_CREDENTIALS_FORM",
        "AUTHENTICATED_OR_GENERAL",
    )

    CAPTCHA_INDICATORS = (
        "captcha",
        "recaptcha",
        "hcaptcha",
        "turnstile",
        "geetest",
        "arkose",
        "funcaptcha",
        "verify you are human",
        "verify human",
        "i'm not a robot",
        "i am not a robot",
        "slide to verify",
        "drag the slider",
        "kéo thanh trượt",
        "xác minh bạn là con người",
        "select all images",
        "select all squares",
        "rotate the image",
        "xoay hình",
    )

    TWO_FACTOR_INDICATORS = (
        "2fa",
        "two-factor",
        "two factor",
        "2-step verification",
        "verification code",
        "enter 6-digit",
        "enter the 6-digit",
        "6-digit code",
        "one-time password",
        "otp",
        "totp",
        "hotp",
        "authenticator",
        "google authenticator",
        "microsoft authenticator",
        "mã xác thực",
        "mã xác minh",
        "mã otp",
        "nhập mã gồm 6 chữ số",
        "security code",
        "backup code",
        "passkey",
    )

    BIOMETRIC_INDICATORS = (
        "biometric",
        "biometric_prompt",
        "fingerprint",
        "face unlock",
        "face id",
        "touch sensor",
        "verify your identity",
        "vân tay",
        "xác nhận vân tay",
        "khuôn mặt",
        "sinh trắc học",
        "com.android.systemui:id/biometric",
    )

    OEM_SECURITY_INDICATORS = (
        "com.vivo.secime",
        "com.bbk.account",
        "com.vivo.permissionmanager",
        "com.android.packageinstaller",
        "com.google.android.packageinstaller",
        "originos",
        "vivo security",
        "install unknown apps",
        "high risk",
        "cài đặt ứng dụng",
        "tiếp tục cài đặt",
        "install anyway",
        "allow from this source",
        "security warning",
        "clear-text",
        "cleartext",
        "allow this time",
        "while using the app",
    )

    USERNAME_INDICATORS = (
        "username",
        "email",
        "phone number",
        "account",
        "user id",
        "tên đăng nhập",
        "số điện thoại",
        "tài khoản",
    )

    PASSWORD_INDICATORS = (
        "password",
        "passcode",
        "mật khẩu",
    )

    LOGIN_ACTION_INDICATORS = (
        "log in",
        "login",
        "sign in",
        "signin",
        "đăng nhập",
        "continue",
        "tiếp tục",
    )

    # Common years / non-OTP numbers to ignore when extracting OTPs without explicit context
    IGNORED_NUMERIC_TOKENS = {
        "1970",
        "2020",
        "2021",
        "2022",
        "2023",
        "2024",
        "2025",
        "2026",
        "2027",
        "2028",
        "2029",
        "2030",
        "0000",
    }

    OTP_CONTEXT_KEYWORDS = (
        "otp",
        "code",
        "verification",
        "verify",
        "auth",
        "security",
        "pin",
        "mã",
        "xác thực",
        "xác minh",
        "passcode",
        "token",
    )

    def _extract_xml_corpus(self, ui_xml: str, current_focus: str = "") -> Dict[str, Any]:
        """Parse UI XML into lowercase searchable corpus and structured node list."""
        nodes: List[Dict[str, Any]] = []
        raw_text_parts: List[str] = []
        has_password_field = False
        edit_text_count = 0

        if current_focus:
            raw_text_parts.append(current_focus)

        if ui_xml and ui_xml.strip():
            try:
                root = ET.fromstring(ui_xml.strip())
                for elem in root.iter("node"):
                    attrib = elem.attrib
                    text = (attrib.get("text") or "").strip()
                    desc = (attrib.get("content-desc") or "").strip()
                    res_id = (attrib.get("resource-id") or "").strip()
                    cls_name = (attrib.get("class") or "").strip()
                    pkg = (attrib.get("package") or "").strip()
                    is_password = attrib.get("password", "false").lower() == "true"
                    hint = (attrib.get("hint") or "").strip()

                    if is_password:
                        has_password_field = True
                    if "edittext" in cls_name.lower():
                        edit_text_count += 1

                    node_info = {
                        "text": text,
                        "content_desc": desc,
                        "resource_id": res_id,
                        "class": cls_name,
                        "package": pkg,
                        "password": is_password,
                        "hint": hint,
                    }
                    nodes.append(node_info)
                    combined = " ".join(filter(None, [text, desc, res_id, pkg, hint]))
                    if combined:
                        raw_text_parts.append(combined)
            except Exception:
                raw_text_parts.append(ui_xml)

        full_corpus = " | ".join(raw_text_parts).lower()
        return {
            "corpus": full_corpus,
            "nodes": nodes,
            "has_password_field": has_password_field,
            "edit_text_count": edit_text_count,
        }

    def classify_auth_screen_state(
        self,
        ui_xml: str,
        current_focus: str = "",
    ) -> Dict[str, Any]:
        """
        Classifies the current screen into one of 6 deterministic authentication states:
          1. "CAPTCHA_WALL"
          2. "TWO_FACTOR_PROMPT"
          3. "BIOMETRIC_PROMPT"
          4. "OEM_SECURITY_DIALOG"
          5. "LOGIN_CREDENTIALS_FORM"
          6. "AUTHENTICATED_OR_GENERAL"
        Returns:
          {
            "auth_state": state,
            "recommended_subagent": subagent_name,
            "confidence": float,
            "indicators_matched": list
          }
        """
        parsed = self._extract_xml_corpus(ui_xml or "", current_focus or "")
        corpus = parsed["corpus"]

        # 1. CAPTCHA_WALL
        captcha_matches = [kw for kw in self.CAPTCHA_INDICATORS if kw in corpus]
        if captcha_matches:
            return {
                "auth_state": "CAPTCHA_WALL",
                "recommended_subagent": "WebAndAdvancedCaptchaSubagent",
                "confidence": min(0.99, 0.85 + 0.04 * len(captcha_matches)),
                "indicators_matched": captcha_matches,
            }

        # 2. BIOMETRIC_PROMPT (check before 2FA when explicit fingerprint/biometric prompt is active)
        biometric_matches = [kw for kw in self.BIOMETRIC_INDICATORS if kw in corpus]
        if biometric_matches:
            return {
                "auth_state": "BIOMETRIC_PROMPT",
                "recommended_subagent": "ClipboardAndBiometricHookSubagent",
                "confidence": min(0.98, 0.86 + 0.04 * len(biometric_matches)),
                "indicators_matched": biometric_matches,
            }

        # 3. TWO_FACTOR_PROMPT
        two_factor_matches = [kw for kw in self.TWO_FACTOR_INDICATORS if kw in corpus]
        if two_factor_matches:
            return {
                "auth_state": "TWO_FACTOR_PROMPT",
                "recommended_subagent": "Universal2FASubagent",
                "confidence": min(0.98, 0.86 + 0.04 * len(two_factor_matches)),
                "indicators_matched": two_factor_matches,
            }

        # 4. OEM_SECURITY_DIALOG
        oem_matches = [kw for kw in self.OEM_SECURITY_INDICATORS if kw in corpus]
        if oem_matches:
            return {
                "auth_state": "OEM_SECURITY_DIALOG",
                "recommended_subagent": "OEMPopupGuardSubagent",
                "confidence": min(0.97, 0.84 + 0.04 * len(oem_matches)),
                "indicators_matched": oem_matches,
            }

        # 5. LOGIN_CREDENTIALS_FORM
        user_matches = [kw for kw in self.USERNAME_INDICATORS if kw in corpus]
        pass_matches = [kw for kw in self.PASSWORD_INDICATORS if kw in corpus]
        login_btn_matches = [kw for kw in self.LOGIN_ACTION_INDICATORS if kw in corpus]
        has_password = parsed["has_password_field"] or bool(pass_matches)

        if has_password and (user_matches or login_btn_matches or parsed["edit_text_count"] >= 2):
            indicators = list(dict.fromkeys(user_matches + pass_matches + login_btn_matches))
            if parsed["has_password_field"] and "password_attribute=true" not in indicators:
                indicators.append("password_attribute=true")
            return {
                "auth_state": "LOGIN_CREDENTIALS_FORM",
                "recommended_subagent": "CrossAppSessionAndCredentialGuardSubagent",
                "confidence": min(0.96, 0.82 + 0.03 * len(indicators)),
                "indicators_matched": indicators,
            }

        # 6. AUTHENTICATED_OR_GENERAL
        return {
            "auth_state": "AUTHENTICATED_OR_GENERAL",
            "recommended_subagent": "OperatorSubagent",
            "confidence": 0.90,
            "indicators_matched": [],
        }

    @staticmethod
    def _mask_account_name(name: str) -> str:
        """
        Safely mask sensitive email prefixes or account identifiers while preserving
        domain / structure (e.g., 'alice.wonder@gmail.com' -> 'al***@gmail.com').
        """
        clean = (name or "").strip()
        if not clean:
            return "***"
        if "@" in clean:
            local, domain = clean.split("@", 1)
            if len(local) <= 2:
                masked_local = local[:1] + "***"
            else:
                masked_local = local[:2] + "***"
            return f"{masked_local}@{domain}"
        if len(clean) <= 3:
            return clean[:1] + "***"
        return clean[:2] + "***" + clean[-1:]

    def parse_dumpsys_accounts_and_autofill(
        self,
        account_raw: str,
        autofill_raw: str = "",
    ) -> Dict[str, Any]:
        """
        Extracts registered Android `Account {name=..., type=...}` entries from
        `dumpsys account` output (masking sensitive email prefixes safely while keeping
        domain/type) and detects the active Android Autofill / Credential Manager service
        from `dumpsys autofill`.
        """
        accounts: List[Dict[str, str]] = []
        seen_pairs = set()

        if account_raw:
            pattern = re.compile(
                r"Account\s*\{\s*name\s*=\s*([^,}]+?)\s*,\s*type\s*=\s*([^}]+?)\s*\}",
                re.IGNORECASE,
            )
            for match in pattern.finditer(account_raw):
                raw_name = match.group(1).strip()
                acct_type = match.group(2).strip()
                dedup_key = (raw_name.lower(), acct_type.lower())
                if dedup_key in seen_pairs:
                    continue
                seen_pairs.add(dedup_key)
                domain = raw_name.split("@", 1)[1] if "@" in raw_name else ""
                accounts.append(
                    {
                        "masked_name": self._mask_account_name(raw_name),
                        "type": acct_type,
                        "domain": domain,
                    }
                )

        autofill_service: Optional[str] = None
        credential_manager_enabled = False

        if autofill_raw:
            # Look for common `dumpsys autofill` service declarations
            svc_patterns = [
                re.compile(r"mService\s*=\s*([^\s\r\n]+)", re.IGNORECASE),
                re.compile(r"Service[s]?\s*:\s*([a-zA-Z0-9_.]+/[a-zA-Z0-9_.$]+)", re.IGNORECASE),
                re.compile(r"autofill_service\s*=\s*([a-zA-Z0-9_.]+/[a-zA-Z0-9_.$]+)", re.IGNORECASE),
                re.compile(r"([a-zA-Z0-9_.]+/[a-zA-Z0-9_.$]*Autofill[a-zA-Z0-9_.$]*)", re.IGNORECASE),
            ]
            for pat in svc_patterns:
                m = pat.search(autofill_raw)
                if m:
                    candidate = m.group(1).strip().rstrip(",}")
                    if candidate.lower() not in ("null", "none"):
                        autofill_service = candidate
                        break

            lower_af = autofill_raw.lower()
            if (
                "credential" in lower_af
                or "com.google.android.gms" in lower_af
                or bool(autofill_service)
            ):
                credential_manager_enabled = True

        account_types = sorted({a["type"] for a in accounts})
        return {
            "account_count": len(accounts),
            "accounts": accounts,
            "account_types": account_types,
            "autofill_service": autofill_service,
            "autofill_enabled": bool(autofill_service),
            "credential_manager_enabled": credential_manager_enabled,
        }

    def extract_fresh_otp_from_notifications(
        self,
        notif_raw: str,
        sms_raw: str = "",
        consumed_codes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Uses regex to extract 4-to-8 digit OTP codes from notification dumps
        (`dumpsys notification --noredact`) or SMS dumps while filtering out any codes
        already in `consumed_codes` and filtering out timestamps/years like `2026`.
        """
        consumed_set = {str(c).strip() for c in (consumed_codes or []) if c is not None}
        candidate_lines: List[Dict[str, str]] = []

        if notif_raw:
            for line in notif_raw.splitlines():
                stripped = line.strip()
                if stripped:
                    candidate_lines.append({"source": "notification", "text": stripped})

        if sms_raw:
            for line in sms_raw.splitlines():
                stripped = line.strip()
                if stripped:
                    candidate_lines.append({"source": "sms", "text": stripped})

        fresh_candidates: List[Dict[str, Any]] = []
        skipped_consumed: List[str] = []
        skipped_timestamps: List[str] = []
        seen_fresh = set()

        for entry in candidate_lines:
            line_text = entry["text"]
            line_lower = line_text.lower()

            # Ignore pure metadata lines like hex IDs, timestamps, or uid/pid lines
            if re.search(r"\b(?:when|posttime|creationtime|uid|pid)\s*=", line_lower):
                continue

            has_otp_context = any(kw in line_lower for kw in self.OTP_CONTEXT_KEYWORDS) or (
                "android.text" in line_lower
                or "android.bigtext" in line_lower
                or "body=" in line_lower
                or entry["source"] == "sms"
            )

            for match in re.finditer(r"\b(\d{4,8})\b", line_text):
                code = match.group(1)

                # Filter out years/timestamps (e.g. 2024, 2025, 2026) or date/time patterns (2026-10-25, 12:3000)
                start, end = match.span(1)
                prefix_char = line_text[start - 1] if start > 0 else ""
                suffix_char = line_text[end] if end < len(line_text) else ""
                if prefix_char in ("-", "/", ":") or suffix_char in ("-", "/", ":"):
                    skipped_timestamps.append(code)
                    continue

                if code in self.IGNORED_NUMERIC_TOKENS:
                    skipped_timestamps.append(code)
                    continue

                if not has_otp_context:
                    continue

                if code in consumed_set:
                    if code not in skipped_consumed:
                        skipped_consumed.append(code)
                    continue

                if code not in seen_fresh:
                    seen_fresh.add(code)
                    priority = 2 if any(kw in line_lower for kw in self.OTP_CONTEXT_KEYWORDS) else 1
                    fresh_candidates.append(
                        {
                            "code": code,
                            "source": entry["source"],
                            "priority": priority,
                            "line": line_text[:160],
                        }
                    )

        # Sort so lines with explicit OTP keywords take precedence while preserving arrival order
        fresh_candidates.sort(key=lambda item: -item["priority"])
        fresh_codes = [c["code"] for c in fresh_candidates]
        best_code = fresh_codes[0] if fresh_codes else None
        best_source = fresh_candidates[0]["source"] if fresh_candidates else None

        return {
            "found": best_code is not None,
            "fresh_otp": best_code,
            "source": best_source,
            "all_fresh_otps": fresh_codes,
            "skipped_consumed": skipped_consumed,
            "skipped_timestamps": skipped_timestamps,
        }
