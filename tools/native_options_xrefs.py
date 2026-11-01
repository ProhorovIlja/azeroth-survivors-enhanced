"""Read-only Windows 0.136/0.137 original Options screen code-reference map.

Identifies direct x64 RIP-relative LEA candidates to short English menu keys,
then bounds their enclosing functions with PE .pdata unwind ranges. Not a
hook finder, not a disassembler, and not evidence that hooking is safe.
Never exports game code, runs the binary, downloads files or modifies EXEs.
"""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import defaultdict
import hashlib
import json
import mmap
from pathlib import Path
import re
import struct
import sys

try:
    from .native_menu_probe import read_pe_sections
except ImportError:
    from tools.native_menu_probe import read_pe_sections

KNOWN_EXES = {
    "eb744751b4e17ec1397b0cdc85a22af63b6af63c1da1d9c2861762c3c4d8947c": "0.136.0-backup",
    "aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8": "0.137.0-prior",
    "eb5fd1c1b96e6180fcf5f3d685d90a61471af28d22e5f060c02b7b7663fbf79e": "0.138.0-current",
}
MAX_SIZE = 300 * 1024 * 1024
# Only public-facing UI localization *keys*, not proprietary English prose.
# Exact public-facing UI localization *keys*, never copyrighted text values.
# Review this short allowlist for every new executable SHA.
KNOWN_MENU_KEYS = (
    'menu.back',
    'menu.character_select',
    'menu.confirm',
    'menu.end_run',
    'menu.escape_back',
    'menu.escape_resume',
    'menu.fullscreen',
    'menu.main_menu',
    'menu.paused',
    'menu.quit',
    'menu.resume',
    'menu.windowed',
    'options.addon_missing',
    'options.addon_on_demand',
    'options.addon_out_of_date',
    'options.addons_folder_note',
    'options.backup_from',
    'options.backups',
    'options.backups_about',
    'options.cancel',
    'options.cannot_read',
    'options.defaults',
    'options.done',
    'options.export_failed',
    'options.export_save',
    'options.exported',
    'options.exports_go_to',
    'options.hint',
    'options.hint.addons',
    'options.hint.gamepad',
    'options.hint.keybindings',
    'options.hint.saves',
    'options.import',
    'options.import_save',
    'options.imported',
    'options.install_addons',
    'options.install_note',
    'options.installing',
    'options.no_addons',
    'options.no_backups',
    'options.no_bindings',
    'options.no_export_folder',
    'options.no_save_files',
    'options.not_bound',
    'options.open_addons_folder',
    'options.open_saves_folder',
    'options.press_a_key',
    'options.remove',
    'options.replace',
    'options.replace_confirm',
    'options.restore',
    'options.save_downloaded',
    'options.save_files',
    'options.saves_about',
)
LEA_RE = re.compile(rb"[\x48\x49\x4c\x4d]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]")
MAX_NODES = 256



class XrefError(ValueError):
    pass


def section_by_name(sections, name):
    return next((section for section in sections if section["name"] == name), None)


def unwind_functions(raw, text, virtual_bytes=None):
    """Validate and parse table of x64 RuntimeFunction .pdata triples."""
    if virtual_bytes is not None:
        if virtual_bytes > len(raw) or virtual_bytes < 12:
            raise XrefError("Invalid .pdata virtual size")
        raw = raw[:virtual_bytes]
    if len(raw) % 12 != 0 or len(raw) > 8 * 1024 * 1024:
        raise XrefError("Unexpected x64 .pdata table size")
    funcs = []
    text_lo = text["rva"]
    text_hi = text_lo + text["virtual_bytes"]
    for off in range(0, len(raw), 12):
        start, end, uinfo = struct.unpack_from("<III", raw, off)
        if start == end == uinfo == 0:
            continue
        if not (text_lo <= start < end <= text_hi):
            raise XrefError(".pdata entry outside executable code region")
        if funcs and start < funcs[-1][0]:
            raise XrefError(".pdata entries are out of order")
        funcs.append((start, end))
    if not funcs:
        raise XrefError("No unwind functions")
    return funcs


def code_references(code, code_rva, address_to_key, funcs):
    """LEA instruction-shape candidates; no instruction-boundary verification."""
    starts = [f[0] for f in funcs]
    found = []
    for match in LEA_RE.finditer(code):
        off = match.start()
        if off + 7 > len(code):
            continue
        reference_rva = code_rva + off
        displacement = struct.unpack_from("<i", code, off + 3)[0]
        target_rva = reference_rva + 7 + displacement
        key = address_to_key.get(target_rva)
        if not key:
            continue
        ix = bisect_right(starts, reference_rva) - 1
        if ix < 0 or not (funcs[ix][0] <= reference_rva < funcs[ix][1]):
            # Can't establish a function range for this candidate.
            continue
        begin, end = funcs[ix]
        found.append({
            "key": key,
            "reference_rva": f"0x{reference_rva:x}",
            "target_rva": f"0x{target_rva:x}",
            "function_start_rva": f"0x{begin:x}",
            "function_end_rva": f"0x{end:x}",
            "function_bytes": end - begin,
            "evidence_level": "candidate_direct_rip_relative_lea_with_pdata_bound",
        })
    return sorted(found, key=lambda x: int(x["reference_rva"], 16))


def map_keys(rdata, base_rva):
    """Use exact, longest-first locale keys, not partial/re-concatenated names."""
    mapping = {}
    for name in sorted(KNOWN_MENU_KEYS, key=lambda n: (-len(n), n)):
        needle = name.encode("ascii")
        off = 0
        while True:
            pos = rdata.find(needle, off)
            if pos < 0:
                break
            rva = base_rva + pos
            mapping.setdefault(rva, name)
            off = pos + 1
    return mapping


def call_sites(code, code_rva, function_targets, funcs):
    """Find E8 rel32 shapes to selected function boundaries, with .pdata bounds.

    A raw byte scan is not a validated instruction decode. Run a separate
    disassembler before asserting any candidate is a real call instruction.
    """
    result = []
    starts = [start for start, _ in funcs]
    target_names = {rva: name for name, rva in function_targets.items()}
    off = 0
    while True:
        off = code.find(b"\xe8", off)
        if off < 0 or off + 5 > len(code):
            break
        site = code_rva + off
        target = site + 5 + struct.unpack_from("<i", code, off + 1)[0]
        if target in target_names:
            ix = bisect_right(starts, site) - 1
            if ix >= 0 and funcs[ix][0] <= site < funcs[ix][1]:
                result.append({"function": target_names[target],
                               "call_site_rva": f"0x{site:x}",
                               "caller_begin_rva": f"0x{funcs[ix][0]:x}",
                               "called_begin_rva": f"0x{target:x}",
                               "evidence_level": "candidate_e8_rel32_bounded_by_pdata"})
        off += 1
    return result


def map_binary(data, sha, *, require_known=True):
    if require_known and sha not in KNOWN_EXES:
        raise XrefError("Unreviewed original Windows EXE, no RVA assumptions permitted")
    sections = read_pe_sections(data)
    text = section_by_name(sections, ".text")
    rdata = section_by_name(sections, ".rdata")
    pdata = section_by_name(sections, ".pdata")
    if not text or not rdata or not pdata:
        raise XrefError("Missing code, strings or unwind section")
    t = data[text["raw_offset"]:text["raw_offset"] + text["raw_bytes"]]
    r = data[rdata["raw_offset"]:rdata["raw_offset"] + rdata["raw_bytes"]]
    u = data[pdata["raw_offset"]:pdata["raw_offset"] + pdata["raw_bytes"]]
    funcs = unwind_functions(u, text, pdata["virtual_bytes"])
    keys = map_keys(r, rdata["rva"])
    hits = code_references(t, text["rva"], keys, funcs)
    by_function = defaultdict(list)
    for h in hits:
        item = (h["function_start_rva"], h["function_end_rva"])
        by_function[item].append(h["key"])
    clusters = [{"start_rva": pair[0], "end_rva": pair[1],
                 "direct_ui_key_refs": sorted(set(values)),
                 "reference_count": len(values),
                 "menu_insertion_point_verified": False}
                for pair, values in by_function.items()]
    clusters.sort(key=lambda x: (-x["reference_count"], int(x["start_rva"], 16)))
    # Derived from distinct UI keys, never a hard-coded portable RVA.
    canonical = {}
    for cluster in clusters:
        labels = set(cluster["direct_ui_key_refs"])
        if {"options.defaults", "options.done"} <= labels:
            canonical["options_page_controls"] = int(cluster["start_rva"], 16)
        if {"options.save_files", "options.backups_about"} <= labels:
            canonical["saves_page_content"] = int(cluster["start_rva"], 16)
        if {"options.addon_missing", "options.addon_on_demand"} <= labels:
            canonical["addons_page_content"] = int(cluster["start_rva"], 16)
    direct_calls = call_sites(t, text["rva"], canonical, funcs)
    # Preserve a bounded structural graph only; it is NOT an active hook.
    return {
        "schema_version": 1,
        "exe_sha256": sha,
        "observed_binary_label": KNOWN_EXES.get(sha),
        "audit_type": "read_only_native_options_direct_code_references",
        "unwind_function_count": len(funcs),
        "direct_key_xref_count": len(hits),
        "unique_function_clusters": len(clusters),
        "function_clusters": clusters[:MAX_NODES],
        "direct_references": hits[:MAX_NODES],
        "candidate_ui_entrypoints": {name: f"0x{rva:x}" for name, rva in canonical.items()},
        "direct_call_candidates": direct_calls[:MAX_NODES],
        "disassembler_or_hook_verification": False,
        "original_options_page_modified": False,
        "native_cheat_menu_implemented": False,
        "cheats_verified": False,
        "caveat": "Candidates only: LEA pattern can match mid-instruction bytes; .pdata gives function bounds, not semantic event roles.",
    }


def inspect_file(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or not (1_000_000 <= p.stat().st_size <= MAX_SIZE):
        raise XrefError("Expected bounded ordinary game EXE")
    with p.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
        sha = hashlib.sha256(data).hexdigest()
        return map_binary(data, sha)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only original Options code xrefs, strict game EXE SHA")
    parser.add_argument("--game-exe", required=True)
    parser.add_argument("--out", help="Optional NEW JSON file: derived RVA metadata, not game code")
    args = parser.parse_args(argv)
    try:
        result = inspect_file(args.game_exe)
        if args.out:
            dest = Path(args.out)
            if dest.is_symlink() or dest.exists() or not dest.parent.is_dir() or dest.parent.is_symlink():
                raise XrefError("Refusing to overwrite destination or use invalid directory")
            with dest.open("x", encoding="utf-8") as file:
                json.dump(result, file, ensure_ascii=False, indent=2)
                file.write("\n")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (XrefError, OSError) as exc:
        print("REFUSED:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
