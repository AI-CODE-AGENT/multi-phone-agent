"""
Multi-User Profile Normalizer & Pure-Python Binary AXML APK Parser (Iteration #6)
=================================================================================
Solves two critical Android multi-user & package inspection challenges with 0 AI tokens:
  1. Vivo OriginOS `user 666` (App Clone profile) `SecurityException` protection:
     - `normalize_pm_command(cmd, user_id=0)` injects `--user 0` into `pm list packages`,
       `pm grant`, `pm revoke`, `pm path`, `cmd package`, and `appops` commands.
     - `filter_user_666_errors(output)` strips benign `Shell does not have permission to access user 666`
       exception lines while preserving valid `package:...` output lines.
  2. Pure-Python Binary `AndroidManifest.xml` (`AXML`) APK Parser:
     - `extract_apk_metadata_pure_python(apk_path)` opens `.apk` archives via `zipfile.ZipFile`,
       parses the compiled Android Binary XML (`RES_XML_TYPE` string pool + XML element attributes)
       and fallback UTF-8 / UTF-16LE regex streams without requiring `aapt` or `androguard`.
"""

from __future__ import annotations

import hashlib
import os
import re
import struct
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class MultiUserPackageEngine:
    """
    Normalizes Android `pm` / `cmd package` / `appops` commands with `--user 0`,
    filters Vivo OriginOS `user 666` `SecurityException` noise, and parses binary
    `AndroidManifest.xml` (`AXML`) inside `.apk` archives in pure Python.
    """

    RES_XML_TYPE = 0x0003
    RES_STRING_POOL_TYPE = 0x0001
    RES_XML_START_ELEMENT_TYPE = 0x0102
    UTF8_FLAG = 0x00000100

    USER_666_ERROR_PATTERNS: Tuple[re.Pattern[str], ...] = (
        re.compile(r".*Shell does not have permission to access user 666.*", re.IGNORECASE),
        re.compile(r"^\s*java\.lang\.SecurityException:.*user 666.*", re.IGNORECASE),
        re.compile(r"^\s*Exception occurred while executing.*user 666.*", re.IGNORECASE),
        re.compile(r"^\s*at com\.android\.server\.pm\..*"),
        re.compile(r"^\s*at com\.android\.server\.am\..*"),
        re.compile(r"^\s*at android\.os\.ShellCommand\..*"),
    )

    @classmethod
    def normalize_pm_command(cls, cmd: str, user_id: int = 0) -> str:
        """
        Ensures `pm list packages`, `pm grant`, `pm revoke`, `pm path`, `cmd package`,
        and `appops` commands include `--user <user_id>` (default `0`) so Vivo OriginOS
        App Clone profile (`user 666`) never triggers a `SecurityException`.
        """
        if not cmd or not cmd.strip():
            return cmd

        raw = cmd.strip()
        # If --user is already specified, replace any --user 666 with target user_id or keep existing
        if re.search(r"--user\s+\S+", raw):
            return re.sub(r"--user\s+666\b", f"--user {int(user_id)}", raw)

        user_flag = f"--user {int(user_id)}"

        # 1. pm list packages [flags/filter]
        m_pm_list = re.match(r"^((?:adb\s+(?:-s\s+\S+\s+)?shell\s+)?pm\s+list\s+packages)\b(.*)$", raw)
        if m_pm_list:
            prefix, rest = m_pm_list.group(1), m_pm_list.group(2).strip()
            return f"{prefix} {user_flag}" + (f" {rest}" if rest else "")

        # 2. pm grant / revoke / path
        m_pm_sub = re.match(r"^((?:adb\s+(?:-s\s+\S+\s+)?shell\s+)?pm\s+(?:grant|revoke|path))\b(.*)$", raw)
        if m_pm_sub:
            prefix, rest = m_pm_sub.group(1), m_pm_sub.group(2).strip()
            return f"{prefix} {user_flag}" + (f" {rest}" if rest else "")

        # 3. cmd package <subcmd> ...
        m_cmd_pkg = re.match(
            r"^((?:adb\s+(?:-s\s+\S+\s+)?shell\s+)?cmd\s+package\s+(?:list\s+packages|path|grant|revoke|resolve-activity|query-activities))\b(.*)$",
            raw,
        )
        if m_cmd_pkg:
            prefix, rest = m_cmd_pkg.group(1), m_cmd_pkg.group(2).strip()
            return f"{prefix} {user_flag}" + (f" {rest}" if rest else "")

        # 4. appops / cmd appops <get|set|reset> ...
        m_appops = re.match(
            r"^((?:adb\s+(?:-s\s+\S+\s+)?shell\s+)?(?:cmd\s+)?appops\s+(?:get|set|reset))\b(.*)$",
            raw,
        )
        if m_appops:
            prefix, rest = m_appops.group(1), m_appops.group(2).strip()
            return f"{prefix} {user_flag}" + (f" {rest}" if rest else "")

        return raw

    @classmethod
    def filter_user_666_errors(cls, output: str) -> str:
        """
        Strips benign Vivo OriginOS `Error: Shell does not have permission to access user 666`
        and associated `SecurityException` stack trace lines from ADB stdout/stderr while
        preserving valid `package:...` and command output lines.
        """
        if not output:
            return ""

        kept_lines: List[str] = []
        skipping_stack = False

        for line in output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            if "user 666" in stripped.lower() and (
                "permission" in stripped.lower()
                or "securityexception" in stripped.lower()
                or "error" in stripped.lower()
            ):
                skipping_stack = True
                continue

            if skipping_stack and (
                stripped.startswith("at ")
                or stripped.startswith("Caused by:")
                or stripped.startswith("...")
            ):
                continue

            if any(pat.match(line) for pat in cls.USER_666_ERROR_PATTERNS):
                continue

            skipping_stack = False
            kept_lines.append(line)

        return "\n".join(kept_lines)

    @classmethod
    def extract_apk_metadata_pure_python(cls, apk_path: str | Path) -> Dict[str, Any]:
        """
        Opens an `.apk` file as a `zipfile.ZipFile`, reads `AndroidManifest.xml`,
        and parses the Android Binary XML (`AXML`) string pool and XML start-element
        attributes in pure Python (plus fallback regex scanning) to extract:
          - `package_name`
          - `permissions`
          - `activities`
          - `apk_size_bytes`
          - `sha256_prefix`
        """
        path_obj = Path(apk_path)
        if not path_obj.is_file():
            raise FileNotFoundError(f"APK file not found: {path_obj}")

        apk_size_bytes = os.path.getsize(path_obj)
        sha256_hasher = hashlib.sha256()
        with open(path_obj, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                sha256_hasher.update(chunk)
        sha256_prefix = sha256_hasher.hexdigest()[:16]

        with zipfile.ZipFile(path_obj, "r") as zf:
            if "AndroidManifest.xml" not in zf.namelist():
                raise ValueError(f"AndroidManifest.xml not found inside APK: {path_obj}")
            manifest_bytes = zf.read("AndroidManifest.xml")

        parsed = cls.parse_axml_manifest_bytes(manifest_bytes)

        return {
            "apk_path": str(path_obj),
            "package_name": parsed["package_name"],
            "permissions": parsed["permissions"],
            "activities": parsed["activities"],
            "apk_size_bytes": apk_size_bytes,
            "sha256_prefix": sha256_prefix,
            "string_pool_count": len(parsed["strings"]),
            "tokens_used": 0,
        }

    @classmethod
    def parse_axml_manifest_bytes(cls, data: bytes) -> Dict[str, Any]:
        """
        Parses raw `AndroidManifest.xml` bytes (supporting both compiled Android Binary XML
        `AXML` and plain-text XML / raw string pools) into structured metadata.
        """
        strings: List[str] = []
        package_name: str = ""
        permissions: List[str] = []
        activities: List[str] = []

        # Check if plain-text XML (e.g. starts with '<?xml' or '<manifest')
        stripped_data = data.lstrip()
        if stripped_data.startswith(b"<?xml") or stripped_data.startswith(b"<manifest"):
            text_xml = data.decode("utf-8", errors="ignore")
            m_pkg = re.search(r'package\s*=\s*["\']([a-zA-Z0-9_.]+)["\']', text_xml)
            if m_pkg:
                package_name = m_pkg.group(1)
            for m_perm in re.finditer(r'android\.permission\.[A-Z0-9_]+', text_xml):
                if m_perm.group(0) not in permissions:
                    permissions.append(m_perm.group(0))
            for m_act in re.finditer(r'<activity[^>]+android:name\s*=\s*["\']([^"\']+)["\']', text_xml):
                if m_act.group(1) not in activities:
                    activities.append(m_act.group(1))
            return {
                "package_name": package_name,
                "permissions": permissions,
                "activities": activities,
                "strings": [package_name] + permissions + activities,
            }

        # Parse binary AXML chunks
        if len(data) >= 8:
            xml_type, xml_header_size, _ = struct.unpack_from("<HHI", data, 0)
            if xml_type == cls.RES_XML_TYPE:
                offset = xml_header_size if xml_header_size >= 8 else 8
                while offset + 8 <= len(data):
                    chunk_type, header_size, chunk_size = struct.unpack_from("<HHI", data, offset)
                    if chunk_size < 8 or offset + chunk_size > len(data):
                        break

                    if chunk_type == cls.RES_STRING_POOL_TYPE and header_size >= 28:
                        strings = cls._parse_string_pool(data, offset, header_size, chunk_size)
                    elif chunk_type == cls.RES_XML_START_ELEMENT_TYPE and strings:
                        elem_info = cls._parse_start_element(data, offset, strings)
                        elem_name = elem_info.get("name", "")
                        attrs = elem_info.get("attributes", {})
                        if elem_name == "manifest" and not package_name:
                            pkg_cand = attrs.get("package", "")
                            if pkg_cand:
                                package_name = pkg_cand
                        elif elem_name in ("uses-permission", "uses-permission-sdk-23", "permission"):
                            perm_cand = attrs.get("name", "")
                            if perm_cand and perm_cand not in permissions:
                                permissions.append(perm_cand)
                        elif elem_name in ("activity", "activity-alias"):
                            act_cand = attrs.get("name", "")
                            if act_cand and act_cand not in activities:
                                activities.append(act_cand)

                    offset += chunk_size

        # Fallback scan over decoded string pool + raw UTF-8 / UTF-16LE decoded buffers
        fallback_corpus = list(strings)
        utf8_Sweep = data.decode("utf-8", errors="ignore")
        utf16_Sweep = data.decode("utf-16le", errors="ignore")
        for token in re.findall(r"[A-Za-z0-9_.$]{3,120}", utf8_Sweep + "\n" + utf16_Sweep):
            fallback_corpus.append(token)

        for s in fallback_corpus:
            s_clean = s.strip("\x00").strip()
            if not s_clean:
                continue
            if s_clean.startswith("android.permission.") or ".permission." in s_clean:
                if re.match(r"^[a-zA-Z0-9_.]+\.permission\.[A-Z0-9_]+$", s_clean):
                    if s_clean not in permissions:
                        permissions.append(s_clean)
            if (
                s_clean.endswith("Activity")
                or s_clean == ".MainActivity"
                or ".MainActivity" in s_clean
            ) and re.match(r"^\.?[a-zA-Z0-9_.$]+Activity$", s_clean):
                if s_clean not in activities:
                    activities.append(s_clean)

        if not package_name:
            package_name = cls._infer_package_name_from_strings(fallback_corpus)

        return {
            "package_name": package_name,
            "permissions": permissions,
            "activities": activities,
            "strings": strings,
        }

    @classmethod
    def _parse_string_pool(
        cls,
        data: bytes,
        chunk_offset: int,
        header_size: int,
        chunk_size: int,
    ) -> List[str]:
        string_count, _style_count, flags, strings_start, _styles_start = struct.unpack_from(
            "<IIIII", data, chunk_offset + 8
        )
        is_utf8 = bool(flags & cls.UTF8_FLAG)
        offsets_base = chunk_offset + header_size
        pool_base = chunk_offset + strings_start
        chunk_end = chunk_offset + chunk_size

        result: List[str] = []
        for idx in range(string_count):
            if offsets_base + (idx + 1) * 4 > chunk_end:
                break
            str_rel_offset = struct.unpack_from("<I", data, offsets_base + idx * 4)[0]
            pos = pool_base + str_rel_offset
            if pos >= chunk_end:
                result.append("")
                continue

            try:
                if is_utf8:
                    # Skip UTF-16 char length (1 or 2 bytes)
                    if data[pos] & 0x80:
                        pos += 2
                    else:
                        pos += 1
                    # Read UTF-8 byte length (1 or 2 bytes)
                    if data[pos] & 0x80:
                        utf8_len = ((data[pos] & 0x7F) << 8) | data[pos + 1]
                        pos += 2
                    else:
                        utf8_len = data[pos]
                        pos += 1
                    raw_bytes = data[pos : min(chunk_end, pos + utf8_len)]
                    result.append(raw_bytes.decode("utf-8", errors="replace"))
                else:
                    u16_len = struct.unpack_from("<H", data, pos)[0]
                    if u16_len & 0x8000:
                        high = u16_len & 0x7FFF
                        low = struct.unpack_from("<H", data, pos + 2)[0]
                        u16_len = (high << 16) | low
                        pos += 4
                    else:
                        pos += 2
                    byte_len = u16_len * 2
                    raw_bytes = data[pos : min(chunk_end, pos + byte_len)]
                    result.append(raw_bytes.decode("utf-16le", errors="replace"))
            except Exception:
                result.append("")

        return result

    @classmethod
    def _parse_start_element(
        cls,
        data: bytes,
        chunk_offset: int,
        strings: List[str],
    ) -> Dict[str, Any]:
        if chunk_offset + 36 > len(data):
            return {"name": "", "attributes": {}}

        _ns_idx, name_idx, attr_start, attr_size, attr_count = struct.unpack_from(
            "<iiHHH", data, chunk_offset + 16
        )
        elem_name = strings[name_idx] if 0 <= name_idx < len(strings) else ""
        attrs: Dict[str, str] = {}

        attr_base = chunk_offset + 16 + attr_start
        step = attr_size if attr_size >= 20 else 20

        for i in range(attr_count):
            pos = attr_base + i * step
            if pos + 20 > len(data):
                break
            _a_ns, a_name_idx, a_raw_val, _a_size, _a_res0, a_type, a_data = struct.unpack_from(
                "<iiiHBBI", data, pos
            )
            attr_name = strings[a_name_idx] if 0 <= a_name_idx < len(strings) else ""
            attr_val = ""
            if 0 <= a_raw_val < len(strings):
                attr_val = strings[a_raw_val]
            elif a_type == 0x03 and 0 <= a_data < len(strings):
                attr_val = strings[a_data]
            if attr_name:
                attrs[attr_name] = attr_val

        return {"name": elem_name, "attributes": attrs}

    @classmethod
    def _infer_package_name_from_strings(cls, candidates: List[str]) -> str:
        ignored_prefixes = (
            "android.",
            "androidx.",
            "com.google.android.",
            "dalvik.",
            "java.",
            "kotlin.",
            "kotlinx.",
            "org.apache.",
        )
        pkg_regex = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,5}$")
        for item in candidates:
            s = item.strip("\x00").strip()
            if not pkg_regex.match(s):
                continue
            if any(s.startswith(prefix) for prefix in ignored_prefixes):
                continue
            return s
        return ""
