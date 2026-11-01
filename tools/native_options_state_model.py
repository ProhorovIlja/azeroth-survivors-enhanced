"""Strictly version-gated analysis of the original Windows 0.138 Options state.

This module never executes the game, edits its binaries/process, supplies hooks,
installs DLLs, or presents unsupported cheat buttons as functional.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
from pathlib import Path
import struct
import sys

try:
    from .native_menu_probe import read_pe_sections
    from .native_options_dispatch import analyze_selector, KNOWN_0138_SHA
except ImportError:
    from tools.native_menu_probe import read_pe_sections
    from tools.native_options_dispatch import analyze_selector, KNOWN_0138_SHA


class ModelError(ValueError):
    pass


MAX_BYTES = 300 * 1024 * 1024
IMAGE_RVA_TABLE = 0x635C970
CODE_RVA_DISPATCH = 0x3F877C
CODE_RVA_UI_RECORD_LOOP = 0x3F8420
CODE_RVA_RECORD_ID_COMPARE = 0x3F8443
CODE_RVA_HINT_TABLE_USE = 0x3F878B
CODE_RVA_ADDONS_ID_COMPARE = 0x3F8487
RECORD_STRIDE = 0x98
RECORD_LOOP_BOUND = 0x4020
RECORD_COUNT = RECORD_LOOP_BOUND // RECORD_STRIDE
HINT_VALUES = {
    1: "options.hint.gamepad",
    6: "options.hint.keybindings",
    10: "options.hint.addons",
    11: "options.hint.saves",
}
DEFAULT_HINT = "options.hint"


def _section(sections, name):
    found = [s for s in sections if s["name"] == name]
    if len(found) != 1:
        raise ModelError("Missing or repeated expected PE section: " + name)
    return found[0]


def read_rva(data, section, rva, size):
    rel = rva - section["rva"]
    if not isinstance(size, int) or size < 0 or rel < 0 or rel + size > min(section["raw_bytes"], section["virtual_bytes"]):
        raise ModelError("Read would exceed validated PE section")
    offset = section["raw_offset"] + rel
    if offset < 0 or offset + size > len(data):
        raise ModelError("Read outside file")
    return bytes(data[offset:offset + size])


def exact_instruction(data, text, rva, blob):
    if read_rva(data, text, rva, len(blob)) != blob:
        raise ModelError("Reviewed instruction changed at RVA 0x%x" % rva)


def _read_key(data, rdata, rva, length):
    raw = read_rva(data, rdata, rva, length)
    try:
        return raw.decode("ascii")
    except UnicodeError as exc:
        raise ModelError("UI key is not ASCII") from exc


def model_from_bytes(data, sha):
    if sha != KNOWN_0138_SHA:
        raise ModelError("Unknown or older original EXE, exact 0.138 review required")
    # Independent already-reviewed PE selector must pass before inspecting more.
    selector = analyze_selector(data, sha)
    sections = read_pe_sections(data)
    text, rdata = _section(sections, ".text"), _section(sections, ".rdata")
    exact_instruction(data, text, CODE_RVA_DISPATCH,
                      bytes.fromhex("41 0f b6 85 da 01 00 00 ff c8 83 f8 0a 77 48"))
    exact_instruction(data, text, CODE_RVA_HINT_TABLE_USE,
                      bytes.fromhex("48 8d 0d de 41 f6 05 48 63 04 81 48 01 c8 ff e0"))
    exact_instruction(data, text, CODE_RVA_UI_RECORD_LOOP,
                      bytes.fromhex("49 ff c7 49 81 c5 98 00 00 00 49 81 fd 20 40 00 00"))
    exact_instruction(data, text, CODE_RVA_RECORD_ID_COMPARE,
                      bytes.fromhex("3a 88 da 01 00 00"))
    exact_instruction(data, text, CODE_RVA_ADDONS_ID_COMPARE,
                      bytes.fromhex("41 80 bc 3d 91 00 00 00 0a"))
    if RECORD_LOOP_BOUND % RECORD_STRIDE:
        raise ModelError("Invalid UI record iteration geometry")

    # The original jump table is a signed 32-bit PC-relative array in .rdata.
    jump_raw = read_rva(data, rdata, IMAGE_RVA_TABLE, 11 * 4)
    jumps = []
    for idx in range(11):
        delta = struct.unpack_from("<i", jump_raw, 4 * idx)[0]
        target = IMAGE_RVA_TABLE + delta
        if not (0x3F877C <= target < 0x3F87E0):
            raise ModelError("Jump table points outside bounded local UI hint handler")
        jumps.append(target)
    expected = {
        1: 0x3F879B, 6: 0x3F87B7, 10: 0x3F87A9, 11: 0x3F87C5,
    }
    if {i:jumps[i-1] for i in expected} != expected:
        raise ModelError("Reviewed 0.138 hint targets moved")
    if any(jumps[i-1] != 0x3F87D3 for i in (2,3,4,5,7,8,9)):
        raise ModelError("Generic hint fallback targets moved")
    hints = {
        1: (0x631A9D8, 20), 6: (0x631A9EC, 24),
        10: (0x631AA04, 19), 11: (0x631AA17, 18),
    }
    for i, (rva, length) in hints.items():
        if _read_key(data, rdata, rva, length) != HINT_VALUES[i]:
            raise ModelError("Original UI hint key no longer matches expected case")
    if _read_key(data, rdata, 0x631AA29, 12) != DEFAULT_HINT:
        raise ModelError("Generic UI hint key changed")
    if selector.get("page_selector_field_offset") != "0x1da":
        raise ModelError("Conflicting selector offset from prior review")
    return {
        "schema": 1,
        "exe_sha256": sha,
        "embedded_version": "0.138.0",
        "evidence": "reviewed_instruction_bytes_jump_table_and_public_ui_locale_keys",
        "page_selector_byte_offset": "0x1da",
        "selection_read_rva": selector["selector_fetch_rva"],
        "hint_jump_table_rva": "0x%x" % IMAGE_RVA_TABLE,
        "observed_selector_hints": [
            {"selection_value": i, "hint_key": HINT_VALUES.get(i, DEFAULT_HINT),
             "local_handler_rva": "0x%x" % jumps[i-1]}
            for i in range(1, 12)
        ],
        "record_loop": {
            "record_stride_bytes": RECORD_STRIDE,
            "loop_byte_bound": RECORD_LOOP_BOUND,
            "maximum_iterated_records": RECORD_COUNT,
            "selection_id_field_offset_in_record": "0x91",
            "active_selection_comparison_rva": "0x%x" % CODE_RVA_RECORD_ID_COMPARE,
            "addons_selection_literal": "0x0a",
            "record_identity_and_mutability_verified": False,
        },
        "game_running_during_audit": False,
        "bevy_ecs_internal_type_verified": False,
        "runtime_page_handler_hook_verified": False,
        "new_native_cheats_page_installed": False,
        "gameplay_cheat_effects_verified": False,
        "warning": "Only 1/6/10/11 have independently mapped UI hint keys; others share generic fallback. This is NOT evidence of a safe page insertion ABI.",
    }


def analyze_file(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 1_000_000 <= path.stat().st_size <= MAX_BYTES:
        raise ModelError("Expected a bounded original Windows EXE file, not a symlink")
    with path.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
        return model_from_bytes(data, hashlib.sha256(data).hexdigest())


def save_report(path, value):
    dest = Path(path)
    if dest.exists() or dest.is_symlink() or not dest.parent.is_dir() or dest.parent.is_symlink():
        raise ModelError("Report exists, is symlinked, or directory is missing")
    with dest.open("x", encoding="utf-8") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)
        output.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Exact SHA-gated, read-only Bevy Options state audit")
    ap.add_argument("--game-exe", required=True)
    ap.add_argument("--out", help="Optional new JSON report, never overwrites")
    args = ap.parse_args(argv)
    try:
        result = analyze_file(args.game_exe)
        if args.out:
            save_report(args.out, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print("REFUSED:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
