"""
Unit Tests for Iteration #5 & Iteration #6:
  - Subagent #48 (`OEMVaultAndSecIMEHandlerSubagent` + `OEMSecIMEVaultEngine`)
  - Subagent #49 (`MultiUserProfileAndPackageSubagent` + `MultiUserPackageEngine`)
"""

from __future__ import annotations

import struct
import sys
import zipfile
from pathlib import Path
from typing import List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.multi_user_package_subagent import MultiUserProfileAndPackageSubagent
from agents.oem_secime_vault_subagent import OEMVaultAndSecIMEHandlerSubagent
from core.multi_user_package_engine import MultiUserPackageEngine
from core.oem_secime_vault_engine import OEMSecIMEVaultEngine


REAL_GEMINICALL_APK = Path(
    r"D:\Project\Du-an-ghi-am\.worktrees\pro-upgrade\coordinator\apps\mobile\android\app\build\outputs\apk\debug\app-debug.apk"
)


def _build_synthetic_axml_manifest(
    package_name: str = "com.geminicall.ai",
    permissions: List[str] | None = None,
    activities: List[str] | None = None,
) -> bytes:
    """
    Builds a valid compiled Android Binary XML (`RES_XML_TYPE` = 0x0003) buffer
    with a UTF-16LE `RES_STRING_POOL_TYPE` (0x0001) and `RES_XML_START_ELEMENT_TYPE` (0x0102)
    chunks for `<manifest package="...">`, `<uses-permission name="..."/>`, and `<activity name="..."/>`.
    """
    perms = permissions or [
        "android.permission.RECORD_AUDIO",
        "android.permission.INTERNET",
    ]
    acts = activities or [
        "com.geminicall.ai.MainActivity",
    ]

    pool_strings = [
        "manifest",
        "package",
        package_name,
        "uses-permission",
        "name",
        "activity",
        *perms,
        *acts,
    ]

    encoded_items: List[bytes] = []
    offsets: List[int] = []
    current_offset = 0
    for s in pool_strings:
        offsets.append(current_offset)
        u16_bytes = s.encode("utf-16le")
        item = struct.pack("<H", len(s)) + u16_bytes + b"\x00\x00"
        encoded_items.append(item)
        current_offset += len(item)

    strings_blob = b"".join(encoded_items)
    if len(strings_blob) % 4 != 0:
        strings_blob += b"\x00" * (4 - (len(strings_blob) % 4))

    header_size = 28
    strings_start = header_size + 4 * len(pool_strings)
    pool_chunk_size = strings_start + len(strings_blob)

    pool_header = struct.pack(
        "<HHIIIIII",
        0x0001,  # RES_STRING_POOL_TYPE
        header_size,
        pool_chunk_size,
        len(pool_strings),
        0,  # styleCount
        0,  # flags (UTF-16LE)
        strings_start,
        0,  # stylesStart
    )
    offsets_blob = b"".join(struct.pack("<I", off) for off in offsets)
    pool_chunk = pool_header + offsets_blob + strings_blob

    def _make_start_element(elem_str: str, attr_name_str: str, attr_val_str: str) -> bytes:
        elem_idx = pool_strings.index(elem_str)
        attr_name_idx = pool_strings.index(attr_name_str)
        attr_val_idx = pool_strings.index(attr_val_str)

        # 36-byte start element header + 20-byte attribute = 56 bytes
        chunk_sz = 56
        elem_hdr = struct.pack(
            "<HHIIIiiHHHHHH",
            0x0102,  # RES_XML_START_ELEMENT_TYPE
            16,      # headerSize
            chunk_sz,
            1,       # lineNumber
            0xFFFFFFFF,  # comment
            -1,      # ns
            elem_idx,
            20,      # attributeStart
            20,      # attributeSize
            1,       # attributeCount
            0,       # idIndex
            0,       # classIndex
            0,       # styleIndex
        )
        attr_bytes = struct.pack(
            "<iiiHBBI",
            -1,            # ns
            attr_name_idx,
            attr_val_idx,  # rawValue
            8,             # size
            0,             # res0
            0x03,          # dataType = TYPE_STRING
            attr_val_idx,  # data
        )
        return elem_hdr + attr_bytes

    elem_chunks = [_make_start_element("manifest", "package", package_name)]
    for p in perms:
        elem_chunks.append(_make_start_element("uses-permission", "name", p))
    for a in acts:
        elem_chunks.append(_make_start_element("activity", "name", a))

    body = pool_chunk + b"".join(elem_chunks)
    xml_header = struct.pack("<HHI", 0x0003, 8, 8 + len(body))
    return xml_header + body


class DummyADBWrapper:
    def __init__(self, dumpsys_out: str = "") -> None:
        self.dumpsys_out = dumpsys_out
        self.commands: List[str] = []
        self.taps: List[tuple[int, int]] = []
        self.texts: List[str] = []

    def shell(self, cmd: str) -> str:
        self.commands.append(cmd)
        if "dumpsys window" in cmd:
            return self.dumpsys_out
        return ""

    def tap(self, x: int, y: int) -> None:
        self.taps.append((x, y))

    def input_text(self, text: str) -> None:
        self.texts.append(text)


# ============================================================================
# 1. Tests for Iteration #5: OEMSecIMEVaultEngine & Subagent #48
# ============================================================================


def test_detect_vivo_secime_and_bbk_account_from_dumpsys_and_xml() -> None:
    engine = OEMSecIMEVaultEngine()
    dumpsys_sample = """
    Window #1 Window{a12345 u0 com.vivo.secime/.SecIME}:
      mInputMethodWindow=Window{a12345 u0 com.vivo.secime/.SecIME}
      mCurrentFocus=Window{b67890 u0 com.bbk.account/com.bbk.account.activity.VerifyPasswordActivity}
    """
    xml_sample = """<?xml version="1.0" encoding="UTF-8"?>
    <hierarchy rotation="0">
      <node index="0" text="Nhập mật khẩu tài khoản Vivo" resource-id="com.bbk.account:id/title"
            class="android.widget.TextView" clickable="false" bounds="[100,400][1160,500]" />
      <node index="1" text="" resource-id="com.bbk.account:id/pwd_edit"
            class="android.widget.EditText" clickable="true" focusable="true" bounds="[120,600][1140,720]" />
      <node index="2" text="Xác nhận" resource-id="android:id/button1"
            class="android.widget.Button" clickable="true" bounds="[700,800][1140,920]" />
    </hierarchy>
    """
    det = engine.detect_secime_and_auth_prompt(dumpsys_sample, xml_sample)
    assert det["secime_active"] is True
    assert det["auth_prompt_detected"] is True
    assert det["flag_secure_lockout"] is True
    assert "com.bbk.account" in det["matched_prompts"]
    assert "Nhập mật khẩu tài khoản Vivo" in det["matched_prompts"]
    assert det["input_center"] == (630, 660)
    assert det["confirm_button_center"] == (920, 860)


def test_detect_flag_secure_black_screen_zero_nodes() -> None:
    engine = OEMSecIMEVaultEngine()
    dumpsys_sample = "mCurrentFocus=Window{999 u0 com.android.systemui/com.android.systemui.biometrics.BiometricPrompt}"
    empty_xml = '<hierarchy rotation="0"></hierarchy>'
    det = engine.detect_secime_and_auth_prompt(dumpsys_sample, empty_xml)
    assert det["flag_secure_lockout"] is True
    assert det["actionable_xml_nodes"] == 0
    assert det["auth_prompt_detected"] is True


def test_compute_secime_key_coordinates_calibration() -> None:
    grid = OEMSecIMEVaultEngine.compute_secime_key_coordinates(1260, 2800)
    assert grid["screen_width"] == 1260
    assert grid["screen_height"] == 2800
    for digit in "0123456789":
        x, y = grid["numeric_pad"][digit]
        assert 0 < x < 1260
        assert 1800 < y < 2800
    cx, cy = grid["confirm_button"]
    assert 900 < cx < 1260
    assert 2400 < cy < 2800


def test_handle_oem_auth_prompt_missing_credential_returns_diagnostic() -> None:
    adb = DummyADBWrapper(
        dumpsys_out="mCurrentFocus=Window{111 u0 com.bbk.account/.LoginActivity}\nmInputMethodWindow=Window{222 u0 com.vivo.secime/.SecIME}"
    )
    subagent = OEMVaultAndSecIMEHandlerSubagent(adb=adb)
    report = subagent.inspect_and_handle_secime(password_or_pin=None)
    assert report["subagent_id"] == 48
    assert report["status"] == "VAULT_CREDENTIAL_REQUIRED"
    assert report["handled"] is False
    assert report["detection"]["secime_active"] is True
    assert len(adb.taps) == 0


def test_handle_oem_auth_prompt_with_pin_executes_calibrated_taps() -> None:
    adb = DummyADBWrapper(
        dumpsys_out="mCurrentFocus=Window{111 u0 com.bbk.account/.VerifyActivity}\nmInputMethodWindow=Window{222 u0 com.vivo.secime/.SecIME}"
    )
    subagent = OEMVaultAndSecIMEHandlerSubagent(adb=adb)
    report = subagent.inspect_and_handle_secime(password_or_pin="1234")
    assert report["status"] == "OEM_AUTH_PROMPT_HANDLED"
    assert report["handled"] is True
    # 4 PIN digit taps + 1 confirm button tap = 5 taps
    assert len(adb.taps) == 5


# ============================================================================
# 2. Tests for Iteration #6: MultiUserPackageEngine & Subagent #49
# ============================================================================


def test_normalize_pm_command_injects_user_0() -> None:
    engine = MultiUserPackageEngine()
    assert engine.normalize_pm_command("pm list packages") == "pm list packages --user 0"
    assert engine.normalize_pm_command("pm list packages -3") == "pm list packages --user 0 -3"
    assert (
        engine.normalize_pm_command("pm grant com.geminicall.ai android.permission.RECORD_AUDIO")
        == "pm grant --user 0 com.geminicall.ai android.permission.RECORD_AUDIO"
    )
    assert (
        engine.normalize_pm_command("pm path com.geminicall.ai")
        == "pm path --user 0 com.geminicall.ai"
    )
    assert (
        engine.normalize_pm_command("cmd package list packages --user 666")
        == "cmd package list packages --user 0"
    )
    assert (
        engine.normalize_pm_command("appops set com.geminicall.ai PROJECT_MEDIA allow")
        == "appops set --user 0 com.geminicall.ai PROJECT_MEDIA allow"
    )


def test_filter_user_666_errors_strips_vivo_clone_profile_exceptions() -> None:
    raw_adb_output = """package:com.android.settings
Error: Shell does not have permission to access user 666
java.lang.SecurityException: Shell does not have permission to access user 666
    at com.android.server.pm.UserManagerService.checkManageUsersPermission(UserManagerService.java:2104)
    at com.android.server.pm.PackageManagerShellCommand.runListPackages(PackageManagerShellCommand.java:912)
package:com.geminicall.ai
package:com.zhiliaoapp.musically
"""
    subagent = MultiUserProfileAndPackageSubagent()
    res = subagent.normalize_and_filter_pm_execution("pm list packages", raw_output=raw_adb_output)
    assert res["subagent_id"] == 49
    assert res["normalized_cmd"] == "pm list packages --user 0"
    assert "user 666" not in res["cleaned_output"]
    assert "SecurityException" not in res["cleaned_output"]
    assert res["packages"] == [
        "com.android.settings",
        "com.geminicall.ai",
        "com.zhiliaoapp.musically",
    ]


def test_extract_apk_metadata_pure_python_synthetic_apk() -> None:
    tmp_dir = Path(__file__).resolve().parent.parent / "logs" / "tmp_apk_test"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    apk_file = tmp_dir / "synthetic_test.apk"
    try:
        axml_bytes = _build_synthetic_axml_manifest(
            package_name="com.geminicall.ai",
            permissions=[
                "android.permission.RECORD_AUDIO",
                "android.permission.FOREGROUND_SERVICE",
                "android.permission.INTERNET",
            ],
            activities=[
                "com.geminicall.ai.MainActivity",
            ],
        )
        with zipfile.ZipFile(apk_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("AndroidManifest.xml", axml_bytes)
            zf.writestr("classes.dex", b"dex\n035\x00" + b"\x00" * 64)

        subagent = MultiUserProfileAndPackageSubagent()
        meta = subagent.inspect_apk(apk_file)
        assert meta["status"] == "APK_METADATA_EXTRACTED"
        assert meta["package_name"] == "com.geminicall.ai"
        assert "android.permission.RECORD_AUDIO" in meta["permissions"]
        assert "android.permission.FOREGROUND_SERVICE" in meta["permissions"]
        assert "com.geminicall.ai.MainActivity" in meta["activities"]
        assert meta["apk_size_bytes"] > 0
        assert len(meta["sha256_prefix"]) == 16
    finally:
        if apk_file.exists():
            apk_file.unlink()


@pytest.mark.skipif(not REAL_GEMINICALL_APK.is_file(), reason="Real GeminiCall APK not present on disk")
def test_extract_apk_metadata_pure_python_real_geminicall_apk() -> None:
    meta = MultiUserPackageEngine.extract_apk_metadata_pure_python(REAL_GEMINICALL_APK)
    assert meta["package_name"] == "com.geminicall.ai"
    assert len(meta["permissions"]) >= 1
    assert any(p.startswith("android.permission.") for p in meta["permissions"])
    assert len(meta["activities"]) >= 1
    assert meta["apk_size_bytes"] > 100_000
    assert len(meta["sha256_prefix"]) == 16
