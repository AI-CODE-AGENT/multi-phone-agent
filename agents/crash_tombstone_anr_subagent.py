"""
Crash Tombstone & ANR Stack-Trace Demangler Subagent (Subagent #29)
Inspired by Google `bugreportz`, Android Tombstone / `logcat -b crash` stack-trace demanglers,
and ANR (`Application Not Responding`) trace analyzers.

Parses 3 categories of severe runtime faults:
1. Java / Kotlin Fatal Exceptions (`JAVA_FATAL_EXCEPTION`)
2. Native C/C++ Signals & Tombstones (`NATIVE_TOMBSTONE_CRASH`)
3. Application Not Responding (`ANR_DEADLOCK_OR_MAIN_THREAD_BLOCK`)

Computes deterministic `crash_signature_sha256` per fault so duplicate crashes are grouped
and counted, and generates structured root-cause diagnoses & fix suggestions for `CodeImproverSubagent` (#8).
"""

import hashlib
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.adb_wrapper import ADBWrapper
from core.memory_manager import MemoryManager


class CrashTombstoneAndANRSubagent:
    """
    Subagent #29: Crash, Native Tombstone, and ANR Root-Cause Analyzer.
    """

    def __init__(
        self,
        adb: Optional[ADBWrapper] = None,
        memory: Optional[MemoryManager] = None,
    ):
        self.adb = adb or ADBWrapper()
        self.memory = memory or MemoryManager()
        self.crash_history: List[Dict[str, Any]] = []

    @staticmethod
    def _compute_signature(category: str, primary_type: str, location_key: str) -> str:
        """
        Compute a deterministic SHA-256 signature for grouping identical crashes.
        """
        payload = f"{category}|{primary_type.strip()}|{location_key.strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _parse_java_fatal_exceptions(
        self,
        text: str,
        package_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract Java / Kotlin Fatal Exceptions (`JAVA_FATAL_EXCEPTION`):
        - Exception class (e.g., `java.lang.NullPointerException`, `java.lang.IndexOutOfBoundsException`,
          `kotlin.UninitializedPropertyAccessException`)
        - Exception message
        - Top offending stack frame `at com.example.app.MainActivity.onClick(MainActivity.kt:42)`
          (`file_name`, `class_name`, `method_name`, `line_number`)
        """
        faults: List[Dict[str, Any]] = []
        lines = text.splitlines()
        n = len(lines)
        i = 0

        exc_line_re = re.compile(
            r"(?:AndroidRuntime\s*:\s*|Caused by:\s*)?([a-zA-Z0-9_$.]+(?:Exception|Error))(?::\s*(.*))?$"
        )
        frame_re = re.compile(
            r"at\s+([a-zA-Z0-9_$.]+)\.([a-zA-Z0-9_$<>]+)\(([^():]+)(?::(\d+))?\)"
        )
        proc_re = re.compile(r"Process:\s*([a-zA-Z0-9_.]+)")

        while i < n:
            line = lines[i]
            is_fatal_header = "FATAL EXCEPTION" in line
            exc_match = exc_line_re.search(line.strip())

            if is_fatal_header or (exc_match and "at " not in line):
                block_lines = [line]
                proc_pkg = None
                pm = proc_re.search(line)
                if pm:
                    proc_pkg = pm.group(1)

                j = i + 1
                while j < n:
                    nxt = lines[j]
                    if j > i + 1 and (
                        "FATAL EXCEPTION" in nxt
                        or "Fatal signal " in nxt
                        or "ANR in " in nxt
                    ):
                        break
                    block_lines.append(nxt)
                    if not proc_pkg:
                        pm2 = proc_re.search(nxt)
                        if pm2:
                            proc_pkg = pm2.group(1)
                    j += 1

                # Find exception class & message within block
                exception_class = None
                exception_message = ""
                frames: List[Dict[str, Any]] = []

                for bl in block_lines:
                    stripped = bl.strip()
                    # Strip logcat prefix if present (e.g., "10-25 12:00:00.000  1234  1234 E AndroidRuntime: ")
                    cleaned = re.sub(
                        r"^.*?(?:AndroidRuntime|System\.err)\s*:\s*", "", stripped
                    )
                    fm = frame_re.search(cleaned)
                    if fm:
                        frames.append(
                            {
                                "class_name": fm.group(1),
                                "method_name": fm.group(2),
                                "file_name": fm.group(3),
                                "line_number": int(fm.group(4)) if fm.group(4) else 0,
                                "raw_frame": fm.group(0),
                            }
                        )
                        continue

                    em = exc_line_re.search(cleaned)
                    if em and "FATAL EXCEPTION" not in cleaned:
                        cand_cls = em.group(1)
                        cand_msg = (em.group(2) or "").strip()
                        # Prefer Caused by or first exception class
                        if exception_class is None or cleaned.startswith("Caused by:"):
                            exception_class = cand_cls
                            exception_message = cand_msg

                if exception_class:
                    if package_filter and proc_pkg and package_filter not in proc_pkg:
                        # Also check if package_filter appears in frames
                        if not any(package_filter in f["class_name"] for f in frames):
                            i = j
                            continue

                    # Choose top offending app frame (prefer matching package_filter or non-framework frame)
                    top_frame = None
                    if package_filter:
                        for f in frames:
                            if package_filter in f["class_name"]:
                                top_frame = f
                                break
                    if top_frame is None and frames:
                        for f in frames:
                            if not f["class_name"].startswith(("android.", "java.", "dalvik.", "com.android.internal.")):
                                top_frame = f
                                break
                        if top_frame is None:
                            top_frame = frames[0]

                    if top_frame is None:
                        top_frame = {
                            "class_name": proc_pkg or "UnknownClass",
                            "method_name": "unknownMethod",
                            "file_name": "UnknownFile.kt",
                            "line_number": 0,
                            "raw_frame": "unknown",
                        }

                    loc_key = f"{top_frame['class_name']}.{top_frame['method_name']}({top_frame['file_name']}:{top_frame['line_number']})"
                    sig = self._compute_signature(
                        "JAVA_FATAL_EXCEPTION", exception_class, loc_key
                    )
                    faults.append(
                        {
                            "category": "JAVA_FATAL_EXCEPTION",
                            "severity": "CRITICAL",
                            "package": proc_pkg or package_filter or "unknown",
                            "exception_class": exception_class,
                            "message": exception_message,
                            "top_frame": top_frame,
                            "file_name": top_frame["file_name"],
                            "class_name": top_frame["class_name"],
                            "method_name": top_frame["method_name"],
                            "line_number": top_frame["line_number"],
                            "all_frames": frames,
                            "crash_signature_sha256": sig,
                        }
                    )
                    i = j
                    continue

            i += 1

        return faults

    def _parse_native_tombstones(
        self,
        text: str,
        package_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect Native C/C++ Signals & Tombstones (`NATIVE_TOMBSTONE_CRASH`):
        - `Fatal signal 11 (SIGSEGV)`, `Fatal signal 6 (SIGABRT)`, etc.
        - Backtrace frames `#00 pc 0001a2b4 /data/app/.../libnative.so (func+24)`
        """
        faults: List[Dict[str, Any]] = []
        lines = text.splitlines()
        n = len(lines)
        i = 0

        sig_re = re.compile(
            r"Fatal signal\s+(\d+)\s*\(([A-Z0-9_]+)\)(?:,\s*code\s+(-?\d+)\s*\(([^)]+)\))?(?:.*?>>>\s*([a-zA-Z0-9_.:]+)\s*<<<)?"
        )
        bt_re = re.compile(
            r"#(\d{2})\s+pc\s+([0-9a-fA-F]+)\s+([^\s(]+)(?:\s*\(([^)]+)\))?"
        )
        pkg_marker_re = re.compile(r">>>\s*([a-zA-Z0-9_.:]+)\s*<<<")

        while i < n:
            line = lines[i]
            sm = sig_re.search(line)
            if sm:
                signal_num = int(sm.group(1))
                signal_name = sm.group(2)
                signal_code = sm.group(4) or "UNKNOWN_CODE"
                proc_pkg = sm.group(5)

                backtrace: List[Dict[str, Any]] = []
                j = i + 1
                while j < n:
                    nxt = lines[j]
                    if j > i + 1 and (
                        "Fatal signal " in nxt
                        or "FATAL EXCEPTION" in nxt
                        or "ANR in " in nxt
                    ):
                        break
                    if not proc_pkg:
                        pm = pkg_marker_re.search(nxt)
                        if pm:
                            proc_pkg = pm.group(1)
                    bm = bt_re.search(nxt)
                    if bm:
                        so_path = bm.group(3)
                        so_name = Path(so_path).name
                        symbol = bm.group(4) or "unknown_symbol"
                        backtrace.append(
                            {
                                "frame_index": int(bm.group(1)),
                                "pc_offset": bm.group(2),
                                "library_path": so_path,
                                "library_name": so_name,
                                "symbol": symbol,
                                "raw_frame": bm.group(0),
                            }
                        )
                    j += 1

                if package_filter and proc_pkg and package_filter not in proc_pkg:
                    if not any(package_filter in b["library_path"] for b in backtrace):
                        i = j
                        continue

                top_bt = (
                    backtrace[0]
                    if backtrace
                    else {
                        "frame_index": 0,
                        "pc_offset": "00000000",
                        "library_path": "unknown.so",
                        "library_name": "unknown.so",
                        "symbol": "unknown_symbol",
                        "raw_frame": "unknown",
                    }
                )
                loc_key = f"{top_bt['library_name']}@{top_bt['pc_offset']}:{top_bt['symbol']}"
                sig = self._compute_signature(
                    "NATIVE_TOMBSTONE_CRASH",
                    f"SIG{signal_num}_{signal_name}",
                    loc_key,
                )

                faults.append(
                    {
                        "category": "NATIVE_TOMBSTONE_CRASH",
                        "severity": "CRITICAL",
                        "package": proc_pkg or package_filter or "unknown",
                        "signal_number": signal_num,
                        "signal_name": signal_name,
                        "signal_code": signal_code,
                        "top_backtrace_frame": top_bt,
                        "library_path": top_bt["library_path"],
                        "library_name": top_bt["library_name"],
                        "pc_offset": top_bt["pc_offset"],
                        "symbol": top_bt["symbol"],
                        "backtrace": backtrace,
                        "crash_signature_sha256": sig,
                    }
                )
                i = j
                continue

            i += 1

        return faults

    def _parse_anr_traces(
        self,
        text: str,
        package_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Detect Application Not Responding (`ANR_DEADLOCK_OR_MAIN_THREAD_BLOCK`):
        - `ANR in <pkg>`
        - `Reason:` (e.g., `Input dispatching timed out`)
        - `CPU usage` (e.g., `85% TOTAL: 60% user + 25% kernel`)
        """
        faults: List[Dict[str, Any]] = []
        lines = text.splitlines()
        n = len(lines)
        i = 0

        anr_re = re.compile(r"ANR in\s+([a-zA-Z0-9_./:]+)(?:\s*\(([^)]+)\))?")
        reason_re = re.compile(r"Reason:\s*(.+)")
        cpu_re = re.compile(r"CPU usage[^:]*:\s*(.+)", re.IGNORECASE)
        total_cpu_re = re.compile(r"([\d.]+)%\s*TOTAL:\s*(.+)", re.IGNORECASE)

        while i < n:
            line = lines[i]
            am = anr_re.search(line)
            if am:
                raw_proc = am.group(1)
                component = am.group(2) or raw_proc
                pkg_name = raw_proc.split("/")[0]

                reason = "Input dispatching timed out"
                cpu_usage = "unknown"

                j = i + 1
                while j < n:
                    nxt = lines[j]
                    if j > i + 1 and (
                        "ANR in " in nxt
                        or "FATAL EXCEPTION" in nxt
                        or "Fatal signal " in nxt
                    ):
                        break
                    rm = reason_re.search(nxt)
                    if rm:
                        reason = rm.group(1).strip()
                    cm = cpu_re.search(nxt)
                    if cm:
                        cpu_usage = cm.group(1).strip()
                    else:
                        tm = total_cpu_re.search(nxt)
                        if tm:
                            cpu_usage = f"{tm.group(1)}% TOTAL: {tm.group(2).strip()}"
                    j += 1

                if package_filter and package_filter not in pkg_name and package_filter not in component:
                    i = j
                    continue

                sig = self._compute_signature(
                    "ANR_DEADLOCK_OR_MAIN_THREAD_BLOCK",
                    pkg_name,
                    f"{component}|{reason}",
                )
                faults.append(
                    {
                        "category": "ANR_DEADLOCK_OR_MAIN_THREAD_BLOCK",
                        "severity": "CRITICAL",
                        "package": pkg_name,
                        "component": component,
                        "reason": reason,
                        "cpu_usage": cpu_usage,
                        "crash_signature_sha256": sig,
                    }
                )
                i = j
                continue

            i += 1

        return faults

    def _build_root_cause_recommendation(self, fault: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a structured root-cause diagnosis & fix suggestion for `CodeImproverSubagent` (#8).
        """
        cat = fault["category"]
        sig = fault["crash_signature_sha256"]

        if cat == "JAVA_FATAL_EXCEPTION":
            exc_cls = fault.get("exception_class", "java.lang.RuntimeException")
            file_name = fault.get("file_name", "UnknownFile.kt")
            class_name = fault.get("class_name", "UnknownClass")
            method_name = fault.get("method_name", "unknownMethod")
            line_num = fault.get("line_number", 0)
            msg = fault.get("message", "")

            if "NullPointerException" in exc_cls or "UninitializedPropertyAccessException" in exc_cls:
                diagnosis = (
                    f"Null reference or uninitialized Kotlin property dereferenced in "
                    f"`{class_name}.{method_name}` ({file_name}:{line_num}): {msg}"
                )
                fix_suggestion = (
                    f"Add null-safe call (`?.`), `lateinit var` initialization check (`::prop.isInitialized`), "
                    f"or defensive guard clause before line {line_num} in `{file_name}`."
                )
            elif "IndexOutOfBoundsException" in exc_cls:
                diagnosis = (
                    f"Collection or array index out of bounds in `{class_name}.{method_name}` "
                    f"({file_name}:{line_num}): {msg}"
                )
                fix_suggestion = (
                    f"Use `getOrNull(index)` or validate `index in 0 until list.size` before accessing elements "
                    f"at `{file_name}:{line_num}`."
                )
            else:
                diagnosis = (
                    f"Unhandled `{exc_cls}` thrown in `{class_name}.{method_name}` "
                    f"({file_name}:{line_num}): {msg}"
                )
                fix_suggestion = (
                    f"Validate input state and wrap risky operation in `{class_name}.{method_name}` "
                    f"with structured error handling."
                )

            return {
                "target_subagent": "CodeImproverSubagent (#8)",
                "category": cat,
                "crash_signature_sha256": sig,
                "occurrence_count": fault.get("occurrence_count", 1),
                "target_file": file_name,
                "target_symbol": f"{class_name}.{method_name}:{line_num}",
                "root_cause_diagnosis": diagnosis,
                "fix_suggestion": fix_suggestion,
            }

        if cat == "NATIVE_TOMBSTONE_CRASH":
            sig_name = fault.get("signal_name", "SIGSEGV")
            sig_num = fault.get("signal_number", 11)
            lib_name = fault.get("library_name", "libnative.so")
            pc = fault.get("pc_offset", "00000000")
            symbol = fault.get("symbol", "unknown_symbol")

            if sig_name == "SIGSEGV":
                diagnosis = (
                    f"Native segmentation fault (`Fatal signal {sig_num} ({sig_name})`) in `{lib_name}` "
                    f"at PC `0x{pc}` ({symbol}) caused by invalid memory pointer dereference or use-after-free."
                )
                fix_suggestion = (
                    f"Symbolicate `{lib_name}` at offset `0x{pc}` with `llvm-addr2line`, validate JNI/native pointers "
                    f"for `nullptr`, and enable AddressSanitizer (HWASan/ASan) in CMake."
                )
            else:
                diagnosis = (
                    f"Native abort/fault (`Fatal signal {sig_num} ({sig_name})`) in `{lib_name}` at PC `0x{pc}` ({symbol})."
                )
                fix_suggestion = (
                    f"Inspect native assertion or JNI exception check (`env->ExceptionCheck()`) around `{symbol}` in `{lib_name}`."
                )

            return {
                "target_subagent": "CodeImproverSubagent (#8)",
                "category": cat,
                "crash_signature_sha256": sig,
                "occurrence_count": fault.get("occurrence_count", 1),
                "target_file": fault.get("library_path", lib_name),
                "target_symbol": f"{lib_name}@0x{pc} ({symbol})",
                "root_cause_diagnosis": diagnosis,
                "fix_suggestion": fix_suggestion,
            }

        # ANR_DEADLOCK_OR_MAIN_THREAD_BLOCK
        pkg = fault.get("package", "unknown")
        comp = fault.get("component", pkg)
        reason = fault.get("reason", "Input dispatching timed out")
        cpu = fault.get("cpu_usage", "unknown")
        diagnosis = (
            f"Main UI thread blocked (>5s ANR) in `{comp}` — Reason: `{reason}` (CPU usage: `{cpu}`)."
        )
        fix_suggestion = (
            f"Offload synchronous I/O, database queries, or heavy lock contention in `{comp}` from Main thread "
            f"to `Dispatchers.IO` / background worker."
        )
        return {
            "target_subagent": "CodeImproverSubagent (#8)",
            "category": cat,
            "crash_signature_sha256": sig,
            "occurrence_count": fault.get("occurrence_count", 1),
            "target_file": comp,
            "target_symbol": comp,
            "root_cause_diagnosis": diagnosis,
            "fix_suggestion": fix_suggestion,
        }

    def analyze_logcat_and_tombstones(
        self,
        serial: str,
        package_name: Optional[str] = None,
        raw_logcat_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch crash logcat via `raw_logcat_override` or `self.adb.get_logcat_crashes(serial, lines=300)`,
        parse Java/Kotlin Fatal Exceptions, Native Tombstone crashes, and ANR traces,
        deduplicate/group by `crash_signature_sha256`, and generate recommendations for `CodeImproverSubagent` (#8).
        """
        raw_log = (
            raw_logcat_override
            if raw_logcat_override is not None
            else self.adb.get_logcat_crashes(serial, lines=300)
        )
        text = raw_log or ""

        java_faults = self._parse_java_fatal_exceptions(text, package_filter=package_name)
        native_faults = self._parse_native_tombstones(text, package_filter=package_name)
        anr_faults = self._parse_anr_traces(text, package_filter=package_name)

        all_raw_faults = java_faults + native_faults + anr_faults

        # Group and count duplicate crashes by deterministic crash_signature_sha256
        sig_counts: Dict[str, int] = {}
        grouped_by_sig: Dict[str, Dict[str, Any]] = {}
        for f in all_raw_faults:
            sig = f["crash_signature_sha256"]
            sig_counts[sig] = sig_counts.get(sig, 0) + 1
            if sig not in grouped_by_sig:
                grouped_by_sig[sig] = f

        faults: List[Dict[str, Any]] = []
        for f in all_raw_faults:
            sig = f["crash_signature_sha256"]
            f_copy = dict(f)
            f_copy["occurrence_count"] = sig_counts[sig]
            faults.append(f_copy)

        unique_sigs = list(grouped_by_sig.keys())
        recommendations: List[Dict[str, Any]] = []
        for sig in unique_sigs:
            rep_fault = dict(grouped_by_sig[sig])
            rep_fault["occurrence_count"] = sig_counts[sig]
            recommendations.append(self._build_root_cause_recommendation(rep_fault))

        result = {
            "serial": serial,
            "package": package_name,
            "status": "CRASH_ANALYSIS_COMPLETED",
            "total_faults": len(faults),
            "unique_signatures": len(unique_sigs),
            "has_critical_fault": len(faults) > 0,
            "faults": faults,
            "root_cause_recommendations": recommendations,
        }

        self.crash_history.append(result)
        if faults:
            self.memory.remember(
                key=f"crash_analysis_{serial}_{package_name or 'all'}",
                value={
                    "total_faults": len(faults),
                    "unique_signatures": len(unique_sigs),
                    "categories": list({f["category"] for f in faults}),
                },
                tags=["crash", "tombstone", "anr", serial, package_name or "all"],
            )

        return result


if __name__ == "__main__":
    analyzer = CrashTombstoneAndANRSubagent()
    sample_crash_log = """
10-25 19:45:01.112  4512  4512 E AndroidRuntime: FATAL EXCEPTION: main
10-25 19:45:01.112  4512  4512 E AndroidRuntime: Process: com.example.app, PID: 4512
10-25 19:45:01.112  4512  4512 E AndroidRuntime: java.lang.NullPointerException: Attempt to invoke virtual method 'int java.lang.String.length()' on a null object reference
10-25 19:45:01.112  4512  4512 E AndroidRuntime:     at com.example.app.MainActivity.onClick(MainActivity.kt:42)
10-25 19:45:01.112  4512  4512 E AndroidRuntime:     at android.view.View.performClick(View.java:7448)

10-25 19:45:05.300  4890  4890 F libc    : Fatal signal 11 (SIGSEGV), code 1 (SEGV_MAPERR), fault addr 0x0 in tid 4890 (com.example.app), pid 4890 (>>> com.example.app <<<)
10-25 19:45:05.350  4900  4900 F DEBUG   : backtrace:
10-25 19:45:05.350  4900  4900 F DEBUG   :       #00 pc 0001a2b4  /data/app/~~xyz==/com.example.app-123/lib/arm64/libnative.so (Java_com_example_app_NativeBridge_processFrame+24)
10-25 19:45:05.350  4900  4900 F DEBUG   :       #01 pc 0000f110  /data/app/~~xyz==/com.example.app-123/lib/arm64/libnative.so

10-25 19:45:12.900  1024  1088 E ActivityManager: ANR in com.example.app (com.example.app/.MainActivity)
10-25 19:45:12.900  1024  1088 E ActivityManager: PID: 5012
10-25 19:45:12.900  1024  1088 E ActivityManager: Reason: Input dispatching timed out (Waiting to send non-key event because the touched window has not finished processing certain input events that were delivered to it over 5000.0ms ago.)
10-25 19:45:12.900  1024  1088 E ActivityManager: CPU usage from 0ms to 5210ms later: 88% TOTAL: 64% user + 24% kernel
"""

    report = analyzer.analyze_logcat_and_tombstones(
        serial="emulator-5554",
        package_name="com.example.app",
        raw_logcat_override=sample_crash_log,
    )

    assert report["status"] == "CRASH_ANALYSIS_COMPLETED"
    assert report["total_faults"] == 3, f"Expected 3 faults, got {report['total_faults']}"
    assert report["unique_signatures"] == 3
    assert report["has_critical_fault"] is True

    categories = {f["category"] for f in report["faults"]}
    assert categories == {
        "JAVA_FATAL_EXCEPTION",
        "NATIVE_TOMBSTONE_CRASH",
        "ANR_DEADLOCK_OR_MAIN_THREAD_BLOCK",
    }

    java_f = next(f for f in report["faults"] if f["category"] == "JAVA_FATAL_EXCEPTION")
    assert java_f["exception_class"] == "java.lang.NullPointerException"
    assert java_f["file_name"] == "MainActivity.kt"
    assert java_f["class_name"] == "com.example.app.MainActivity"
    assert java_f["method_name"] == "onClick"
    assert java_f["line_number"] == 42

    native_f = next(f for f in report["faults"] if f["category"] == "NATIVE_TOMBSTONE_CRASH")
    assert native_f["signal_number"] == 11
    assert native_f["signal_name"] == "SIGSEGV"
    assert native_f["pc_offset"] == "0001a2b4"
    assert native_f["library_name"] == "libnative.so"

    anr_f = next(f for f in report["faults"] if f["category"] == "ANR_DEADLOCK_OR_MAIN_THREAD_BLOCK")
    assert "Input dispatching timed out" in anr_f["reason"]
    assert "88% TOTAL" in anr_f["cpu_usage"]

    print("[Self-Test PASSED] CrashTombstoneAndANRSubagent (#29) parsed all 3 fault categories with 100% accuracy!")
    print("Summary:", {k: report[k] for k in ["status", "total_faults", "unique_signatures", "has_critical_fault"]})
