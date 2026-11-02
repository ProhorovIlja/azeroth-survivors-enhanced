"""Read-only original Windows 0.139 native Options caller and action-tag provenance.

Not a click-event consumer identifier, injection helper, gameplay modification
or Bevy ECS object-layout proof. Only address/role metadata may be published.
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

OPTIONS_RENDER_RVA = 0x3F5D40
OPTIONS_RENDER_PARENT_RVA = 0x1FFDE0
KNOWN_PARENT_CALLSITE_RVA = 0x2005A5
ORIGINAL_ACTION_TAGS = {16: 0x3F73A9, 17: 0x3F73E5}
MAX_TAG_CANDIDATES = 96
MAX_CALL_CANDIDATES = 96
MAX_DISASSEMBLY_FUNCTION_BYTES = 65536


def unwind_owner(rva, starts, functions, length=1):
    i = bisect_right(starts, rva) - 1
    if i < 0 or not (functions[i][0] <= rva and rva + length <= functions[i][1]):
        return None
    return functions[i][0]


def find_tagged_actions(code, base_rva, functions, ids=(16, 17)):
    """Raw exact movabs shapes, pending full-function disassembly confirmation."""
    starts = [f[0] for f in functions]
    hits = []
    for action_id in ids:
        tag = struct.pack("<Q", (1 << 63) | action_id)
        pattern = re.compile(rb"[\x48-\x4f][\xb8-\xbf]" + re.escape(tag))
        for m in pattern.finditer(code):
            site = base_rva + m.start()
            owner = unwind_owner(site, starts, functions, 10)
            if owner is not None:
                hits.append({"action_low_id": action_id, "site_rva": hex(site),
                             "function_begin_rva": hex(owner),
                             "instruction_confirmed": False})
    hits.sort(key=lambda x: int(x["site_rva"], 16))
    return hits


def find_e8_edges(code, code_rva, functions, targets, limit=MAX_CALL_CANDIDATES):
    """Find direct x64 E8 sites to exact target function entrypoints."""
    starts = [f[0] for f in functions]
    hits, count = [], 0
    pos = 0
    while True:
        pos = code.find(b"\xe8", pos)
        if pos < 0 or pos + 5 > len(code):
            break
        site = code_rva + pos
        target = site + 5 + struct.unpack_from("<i", code, pos + 1)[0]
        if target in targets:
            owner = unwind_owner(site, starts, functions, 5)
            if owner is not None:
                count += 1
                if len(hits) < limit:
                    hits.append({"site_rva": hex(site), "caller_function_rva": hex(owner),
                                 "target_function_rva": hex(target),
                                 "instruction_confirmed": False})
        pos += 1
    return {"total_e8_shapes": count, "edges": hits, "truncated": count > limit}


def parse_tag_instructions(output, imagebase, function_start, function_end, target_ids):
    """Return real function-aligned movabs starts with exact high-bit tag literals."""
    matches = []
    line = re.compile(r"^\s*([0-9a-f]+):\s+movabs(?:q)?\s+([^\n]+)$", re.I)
    literals = {(1 << 63) | action: action for action in target_ids}
    for raw in output.splitlines():
        m = line.match(raw)
        if not m:
            continue
        rva = int(m.group(1), 16) - imagebase
        if not function_start <= rva < function_end:
            continue
        # GNU objdump AT&T syntax emits '$0x...', never infer operands.
        lit = re.search(r"\$0x([0-9a-f]+)\b", m.group(2), re.I)
        if lit and int(lit.group(1), 16) in literals:
            matches.append((rva, literals[int(lit.group(1), 16)]))
    return matches


def verify_tag_instruction_owners(game, exe, imagebase, funcs, candidates):
    """Disassemble each involved function once from its real .pdata entrypoint."""
    starts = [a for a, _ in funcs]
    owners = sorted({int(x["function_begin_rva"], 16) for x in candidates})
    if len(owners) > MAX_TAG_CANDIDATES:
        return {"status": "truncated", "function_count": len(owners),
                "tag_count_confirmed": 0, "records": []}
    real = set()
    failures = []
    for owner in owners:
        idx = bisect_right(starts, owner) - 1
        start, end = funcs[idx]
        if end - start > MAX_DISASSEMBLY_FUNCTION_BYTES:
            failures.append({"owner": hex(owner), "reason": "oversized_function"})
            continue
        p = subprocess.run(
            [exe, "-d", "--no-show-raw-insn",
             f"--start-address=0x{imagebase+start:x}",
             f"--stop-address=0x{imagebase+end:x}", str(game)],
            capture_output=True, text=True, check=False, timeout=30)
        if p.returncode != 0:
            failures.append({"owner": hex(owner), "reason": "disassembly_failure"})
            continue
        real.update(parse_tag_instructions(p.stdout, imagebase, start, end, (16, 17)))
    for row in candidates:
        row["instruction_confirmed"] = (
            (int(row["site_rva"], 16), row["action_low_id"]) in real)
    return {"status": "complete" if not failures else "partial",
            "function_count": len(owners),
            "function_failures": failures[:12],
            "tag_count_confirmed": sum(x["instruction_confirmed"] for x in candidates),
            "records": candidates}


def analyze_options_event_ancestry(game, sha):
    if sha != EXPECTED_SHA:
        return {"status": "unconfirmed", "reason": "wrong_client_identity"}
    exe = shutil.which("objdump")
    if not exe:
        return {"status": "unconfirmed", "reason": "gnu_objdump_unavailable"}
    path = Path(game)
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            return {"status": "unconfirmed", "reason": "original_sha_mismatch"}
        sections = {s["name"]: s for s in read_pe_sections(raw)}
        if not {".text", ".pdata"} <= set(sections):
            return {"status": "unconfirmed", "reason": "missing_pe_sections"}
        t, p = sections[".text"], sections[".pdata"]
        funcs = unwind_functions(
            raw[p["raw_offset"]:p["raw_offset"] + p["raw_bytes"]],
            t, p["virtual_bytes"])
        code = raw[t["raw_offset"]:t["raw_offset"] + t["raw_bytes"]]
        header_offset = struct.unpack_from("<I", raw, 0x3C)[0]
        imagebase = struct.unpack_from("<Q", raw, header_offset + 48)[0]

    starts = [x[0] for x in funcs]
    if (unwind_owner(KNOWN_PARENT_CALLSITE_RVA, starts, funcs, 5)
            != OPTIONS_RENDER_PARENT_RVA or
            OPTIONS_RENDER_RVA not in starts or OPTIONS_RENDER_PARENT_RVA not in starts):
        return {"status": "unconfirmed", "reason": "options_parent_baseline_not_bounded"}
    first = find_e8_edges(code, t["rva"], funcs,
                          {OPTIONS_RENDER_RVA, OPTIONS_RENDER_PARENT_RVA})
    if first["truncated"]:
        return {"status": "unconfirmed", "reason": "ancestry_first_layer_truncated",
                "e8_count": first["total_e8_shapes"]}
    all_calls_confirmed = True
    for row in first["edges"]:
        ok = _call_disassembled(exe, imagebase, int(row["site_rva"], 16),
                               int(row["target_function_rva"], 16), path)
        row["instruction_confirmed"] = ok
        all_calls_confirmed = all_calls_confirmed and ok
    parent_verified = any(
        int(x["site_rva"], 16) == KNOWN_PARENT_CALLSITE_RVA
        and int(x["target_function_rva"], 16) == OPTIONS_RENDER_RVA
        and int(x["caller_function_rva"], 16) == OPTIONS_RENDER_PARENT_RVA
        and x["instruction_confirmed"] for x in first["edges"])
    if not parent_verified:
        return {"status": "unconfirmed", "reason": "original_options_parent_call_unconfirmed"}
    parent_callers = {int(x["caller_function_rva"], 16)
                      for x in first["edges"] if x["instruction_confirmed"]}
    second = find_e8_edges(code, t["rva"], funcs, parent_callers)
    if not second["truncated"]:
        for row in second["edges"]:
            row["instruction_confirmed"] = _call_disassembled(
                exe, imagebase, int(row["site_rva"], 16),
                int(row["target_function_rva"], 16), path)
    tags = find_tagged_actions(code, t["rva"], funcs)
    tag_confirmation = verify_tag_instruction_owners(path, exe, imagebase, funcs, tags)
    baseline_tags = all(
        any(x["action_low_id"] == action and int(x["site_rva"], 16) == rva
            and x["instruction_confirmed"] for x in tag_confirmation.get("records", []))
        for action, rva in ORIGINAL_ACTION_TAGS.items())
    return {
        "status": "verified_static_options_ancestry"
                  if baseline_tags and all_calls_confirmed
                  else "unconfirmed",
        "official_sha256": EXPECTED_SHA,
        "parent_function_rva": hex(OPTIONS_RENDER_PARENT_RVA),
        "central_options_function_rva": hex(OPTIONS_RENDER_RVA),
        "parent_to_options_site_rva": hex(KNOWN_PARENT_CALLSITE_RVA),
        "parent_to_options_direct_call_confirmed": parent_verified,
        "direct_callers_of_parent_and_options": first,
        "second_layer_direct_call_candidates": second,
        "known_footer_ids": [16, 17],
        "footer_id_movabs_global_provenance": tag_confirmation,
        "footer_id_baseline_both_confirmed": baseline_tags,
        "bevy_click_event_consumer_confirmed": False,
        "options_canvas_state_writer_confirmed": False,
        "new_native_page_safe_hook_confirmed": False,
        "working_cheat_implemented": False,
        "original_binary_modified": False,
        "caution": "Producers and direct caller ancestry are real x64 instructions; no evidence of button click handling, ECS registration, or runtime object identity."}
