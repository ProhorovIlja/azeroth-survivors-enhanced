"""Read-only 0.139 action-ID producer / native button-helper cross-reference.

Do not mistake an embedded action value, UI button creation or x64 call for an
ECS click-event consumer. Never patches/executes an original game file.
"""
from __future__ import annotations

from bisect import bisect_right
import hashlib
import mmap
from pathlib import Path
import re
import shutil
import struct
import subprocess

from tools.native_menu_probe import read_pe_sections
from tools.native_options_xrefs import unwind_functions
from tools.native_0139_footer_probe import EXPECTED_SHA, _call_disassembled

HELPER_RVA = 0x1E5530  # Original 0.139 action-widget constructor, independently reviewed.
EXPECTED_FOOTER_CALLS = (0x3F73CC, 0x3F7408)
EXPECTED_TAG_MOVES = ((16, 0x3F73A9), (17, 0x3F73E5))
MAX_OUTPUT = 192
MOVABS_PATTERN = re.compile(rb"[\x48-\x4f][\xb8-\xbf].{8}", re.DOTALL)


def owner_of(rva, starts, functions, instruction_bytes):
    idx = bisect_right(starts, rva) - 1
    if idx < 0 or rva + instruction_bytes > functions[idx][1]:
        return None
    return functions[idx][0]


def scan_action_tag_moves(code, code_rva, functions, limit=MAX_OUTPUT, allowed_owners=None):
    """Syntactic movabs + tagged small-ID candidates, not full disassembly."""
    starts = [a for a, _ in functions]
    matches = []
    total = 0
    ids = set()
    for m in MOVABS_PATTERN.finditer(code):
        tag = struct.unpack_from("<Q", code, m.start() + 2)[0]
        if not (1 << 63) <= tag <= ((1 << 63) | 63):
            continue
        site = code_rva + m.start()
        owner = owner_of(site, starts, functions, 10)
        if owner is None or (allowed_owners is not None and owner not in allowed_owners):
            continue
        total += 1
        ids.add(tag & 63)
        if len(matches) < limit:
            matches.append({"site_rva": hex(site), "owner_begin_rva": hex(owner),
                            "action_low_id_candidate": tag & 63,
                            "raw_shape_only": True})
    return {"total_candidate_count": total, "ids_seen": sorted(ids),
            "records": matches, "truncated": total > limit}


def scan_helper_calls(code, code_rva, functions, helper_rva=HELPER_RVA, limit=MAX_OUTPUT):
    """Bounded E8 rel32 byte-shapes; caller and target need disassembler corroboration."""
    starts = [a for a, _ in functions]
    matches, total = [], 0
    offset = 0
    while True:
        offset = code.find(b"\xe8", offset)
        if offset < 0 or offset + 5 > len(code):
            break
        site = code_rva + offset
        target = site + 5 + struct.unpack_from("<i", code, offset + 1)[0]
        if target == helper_rva:
            owner = owner_of(site, starts, functions, 5)
            if owner is not None:
                total += 1
                if len(matches) < limit:
                    matches.append({"site_rva": hex(site), "owner_begin_rva": hex(owner),
                                    "target_rva": hex(helper_rva),
                                    "disassembler_confirmed": False})
        offset += 1
    return {"total_candidate_count": total, "records": matches,
            "truncated": total > limit}


def correlate_tag_to_button_builder(tags, calls):
    """Strictly an adjacency hypothesis: never mark a click consumer found."""
    by_owner = {}
    for c in calls:
        by_owner.setdefault(c["owner_begin_rva"], []).append(int(c["site_rva"], 16))
    links = []
    for row in tags:
        tag_site = int(row["site_rva"], 16)
        upcoming = sorted(x for x in by_owner.get(row["owner_begin_rva"], [])
                          if 10 <= x - tag_site <= 128)
        if upcoming:
            links.append({"action_low_id_candidate": row["action_low_id_candidate"],
                          "tag_move_rva": row["site_rva"],
                          "nearest_helper_call_rva": hex(upcoming[0]),
                          "owner_begin_rva": row["owner_begin_rva"],
                          "relationship": "same_function_and_10_to_128_bytes_after_tag"})
    return links


def _tag_move_disassembled(exe, imagebase, row, game):
    """Confirm a tagged movabs instruction starts exactly at the candidate RVA."""
    site = int(row["site_rva"], 16)
    value = (1 << 63) | row["action_low_id_candidate"]
    va = imagebase + site
    proc = subprocess.run([exe, "-d", f"--start-address=0x{va:x}",
                           f"--stop-address=0x{va+10:x}", str(game)],
                          capture_output=True, text=True, check=False, timeout=25)
    pattern = rf"^\s*{va:x}:\s+[^\n]*\bmovabs(?:q)?\b[^\n]*0x{value:x}\b"
    return proc.returncode == 0 and re.search(pattern, proc.stdout, re.M | re.I) is not None


def analyze_action_flow(game, expected_sha):
    """Reads the SHA-pinned original EXE, exports only bounded address metadata."""
    if expected_sha != EXPECTED_SHA:
        return {"status": "unconfirmed", "reason": "wrong_client_identity"}
    path = Path(game)
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            return {"status": "unconfirmed", "reason": "original_sha_mismatch"}
        sec = {x["name"]: x for x in read_pe_sections(raw)}
        if not all(k in sec for k in (".text", ".pdata")):
            return {"status": "unconfirmed", "reason": "missing_pe_sections"}
        t, p = sec[".text"], sec[".pdata"]
        funcs = unwind_functions(raw[p["raw_offset"]:p["raw_offset"] + p["raw_bytes"]],
                                 t, p["virtual_bytes"])
        code = raw[t["raw_offset"]:t["raw_offset"] + t["raw_bytes"]]
        calls = scan_helper_calls(code, t["rva"], funcs)
        relevant_functions = {int(x["owner_begin_rva"], 16) for x in calls["records"]}
        # Only investigate functions actually calling the reviewed original UI helper.
        # A global search finds thousands of unrelated tagged values.
        tags = scan_action_tag_moves(code, t["rva"], funcs, allowed_owners=relevant_functions)
        header = raw[:8192]
        peoff = struct.unpack_from("<I", header, 0x3C)[0]
        imagebase = struct.unpack_from("<Q", header, peoff + 48)[0]
    footer_calls_found = {int(x["site_rva"], 16) for x in calls["records"]}
    footer_tags_found = {(x["action_low_id_candidate"], int(x["site_rva"], 16))
                         for x in tags["records"]}
    if not set(EXPECTED_FOOTER_CALLS) <= footer_calls_found or not set(EXPECTED_TAG_MOVES) <= footer_tags_found:
        return {"status": "unconfirmed", "reason": "baseline_footer_no_longer_found",
                "footer_call_matches": sorted(hex(x) for x in set(EXPECTED_FOOTER_CALLS) & footer_calls_found),
                "footer_tag_matches": sorted([{"action_low_id": idx, "site_rva": hex(addr)}
                                              for idx, addr in set(EXPECTED_TAG_MOVES) & footer_tags_found],
                                             key=lambda x: x["action_low_id"]),
                "helper_call_candidate_total": calls["total_candidate_count"],
                "tag_move_candidate_total": tags["total_candidate_count"],
                "tag_ids_observed": tags["ids_seen"]}
    disasm = shutil.which("llvm-objdump") or shutil.which("objdump")
    confirmed = 0
    if disasm and not calls["truncated"] and len(calls["records"]) <= 48:
        for row in calls["records"]:
            row["disassembler_confirmed"] = _call_disassembled(
                disasm, imagebase, int(row["site_rva"], 16), HELPER_RVA, path)
            if row["disassembler_confirmed"]:
                confirmed += 1
    confirmed_tags = 0
    if disasm and not tags["truncated"] and len(tags["records"]) <= 48:
        for row in tags["records"]:
            row["disassembler_confirmed"] = _tag_move_disassembled(disasm, imagebase, row, path)
            if row["disassembler_confirmed"]:
                confirmed_tags += 1
    links = correlate_tag_to_button_builder(tags["records"], calls["records"])
    return {
        "status": "candidate_inventory",
        "version": "0.139.0", "sha256": EXPECTED_SHA,
        "shared_ui_action_widget_helper_rva": hex(HELPER_RVA),
        "tagged_movabs_scoped_to_helper_calling_functions": tags, "direct_helper_calls": calls,
        "scoped_owner_function_count": len(relevant_functions),
        "tag_to_widget_creation_hypotheses": links[:MAX_OUTPUT],
        "disassembled_helper_call_count": confirmed,
        "disassembled_tag_move_count": confirmed_tags,
        "all_scoped_tag_movabs_disassembled": bool(disasm) and confirmed_tags == tags["total_candidate_count"] and not tags["truncated"],
        "all_helper_calls_disassembled": bool(disasm) and confirmed == calls["total_candidate_count"] and not calls["truncated"],
        "observed_footer_baseline_preserved": True,
        "native_tab_navigation_confirmed": False,
        "ecs_click_event_consumer_confirmed": False,
        "safe_hook_confirmed": False,
        "working_cheat_confirmed": False,
        "interpretation": "Static producers and widget construction candidates only; no direct evidence of event consumption.",
    }
