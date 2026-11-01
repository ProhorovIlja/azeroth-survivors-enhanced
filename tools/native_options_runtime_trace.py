"""Generate an opt-in WinDbg hardware-breakpoint recipe for original 0.138.

This is a *debugger command script*, not a mod. The generator checks the actual
private original EXE SHA before emitting commands. It never attaches, executes,
changes process memory, installs DLLs or modifies saves. If later run manually,
WinDbg's hardware breakpoint may interrupt game timing; offline tests only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PureWindowsPath
import sys

try:
    from .native_options_state_model import analyze_file, save_report, ModelError
except ImportError:
    from tools.native_options_state_model import analyze_file, save_report, ModelError


class TraceError(ValueError):
    pass


def validate_log_path(value):
    if not isinstance(value, str) or not 6 <= len(value) <= 190:
        raise TraceError("Windows log path missing or too long")
    if any(ord(c) < 32 or c in '";|&<>!`$' for c in value):
        raise TraceError("Unsafe characters in Windows debugger log path")
    p = PureWindowsPath(value)
    if not p.is_absolute() or not p.drive.endswith(":") or ".." in p.parts:
        raise TraceError("Expected ordinary absolute Windows drive path, e.g. C:\\AZSE\\trace.log")
    if p.suffix.lower() not in (".log", ".txt"):
        raise TraceError("Debugger output must be .log or .txt")
    return str(p)


def build_script(evidence, log_path):
    if (evidence.get("exe_sha256") !=
        "eb5fd1c1b96e6180fcf5f3d685d90a61471af28d22e5f060c02b7b7663fbf79e"):
        raise TraceError("Only exact reviewed original Windows 0.138.0 supported")
    if evidence.get("selection_read_rva") != "0x3f83b3" or evidence.get("page_selector_byte_offset") != "0x1da":
        raise TraceError("Unexpected selector evidence")
    path = validate_log_path(log_path)
    # WinDbg `ba e 1` uses a processor-supported hardware execution breakpoint,
    # rather than replacing target code bytes with INT3. It still attaches a
    # debugger and CAN pause gameplay. No gameplay fields are modified here.
    commands = [
        "$$ AZSE Windows 0.138.0 ORIGINAL OPTIONS PAGE TRACE (opt-in and untested in runtime)",
        "$$ Requires separate, fully backed-up offline SOLO Windows game copy.",
        "$$ Generated for exact SHA-256 " + evidence["exe_sha256"],
        "$$ NEVER run on another game build; debugger may pause/crash the game.",
        "$$ Do not attach while co-op / online / competing, and never share full logs blindly.",
        "$$ Hardware execution breakpoint at read-only page-state read. No DLL, no EXE patch.",
        '.logopen /t "' + path + '"',
        "r $t0 = 0xff",
        # The instruction at this RVA reads the byte from [r8+0x1da]; r8 is
        # populated by the preceding instruction in the verified code listing.
        'ba e 1 AzerothSurvivors+0x3f83b3 ".if (by(@r8+0x1da) != @$t0) { r $t0 = by(@r8+0x1da); .printf \\"AZSE_PAGE=0x%02x\\n\\", @$t0; }; gc"',
        "g",
        "",
    ]
    return "\n".join(commands)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Create SHA-gated WinDbg Commands; NEVER attaches by itself")
    parser.add_argument("--game-exe", required=True)
    parser.add_argument("--out", required=True, help="New local WinDbg script .txt; no overwrite")
    parser.add_argument("--log-path", default=r"C:\AZSE\options-page-trace.log")
    args = parser.parse_args(argv)
    try:
        evidence = analyze_file(args.game_exe)
        script = build_script(evidence, args.log_path)
        out = Path(args.out)
        if out.suffix.lower() not in (".txt", ".windbg"):
            raise TraceError("Script should use .txt or .windbg extension")
        if out.is_symlink() or out.exists() or not out.parent.is_dir() or out.parent.is_symlink():
            raise TraceError("Script file already exists, symlinked or parent directory missing")
        with out.open("x", encoding="utf-8") as stream:
            stream.write(script)
        print(json.dumps({
            "status": "script_generated_only", "output": str(out),
            "original_exe_modified": False, "debugger_attached": False,
            "gameplay_cheats_enabled": False, "tested_on_real_windows": False,
        }, indent=2))
        return 0
    except (OSError, ValueError) as err:
        print("REFUSED:", err, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
