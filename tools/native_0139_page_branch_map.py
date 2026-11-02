"""Read-only exact-SHA original Windows 0.139 Options page-state branch inventory.

Only evidence disassembled from .pdata function boundaries is reported. A
memory comparison is a read, NOT evidence of a tab writer or event consumer.
No original binary, instruction bytes, or decompiled code is published.
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

from tools.native_0139_footer_probe import EXPECTED_SHA
from tools.native_menu_probe import read_pe_sections
from tools.native_options_xrefs import unwind_functions

OPTIONS_CENTRAL = 0x3F5D40
OPTIONS_PARENT = 0x1FFDE0
SAVES_COMPARE = 0x3F738C
SAVES_BRANCH = 0x3F7393
DONE_TARGET = 0x3F73D1
MAX_FUNC_BYTES = 65536
MAX_RECORDS = 48
INSTRUCTION = re.compile(r"^\s*([0-9a-f]+):\s+([a-z][a-z0-9_.]*)\s*(.*?)\s*$", re.I)
FIELD = re.compile(r"(?<![0-9a-f])0x1da\([^)]*\)", re.I)
LITERAL_MEM_CMP = re.compile(r"^\s*\$0x([0-9a-f]+)\s*,\s*0x1da\([^)]*\)\s*$", re.I)
JUMP_DEST = re.compile(r"^\s*(?:0x)?([0-9a-f]+)(?:\s|$)", re.I)
CONDITIONAL_BRANCHES = frozenset({
    "je", "jz", "jne", "jnz", "ja", "jae", "jb", "jbe",
    "jg", "jge", "jl", "jle", "js", "jns", "jp", "jnp", "jo", "jno",
})


def parse_instruction_rows(output, imagebase, begin, end):
    rows = []
    for raw in output.splitlines():
        m = INSTRUCTION.match(raw)
        if not m:
            continue
        rva = int(m.group(1), 16) - imagebase
        if begin <= rva < end:
            rows.append((rva, m.group(2).lower(), m.group(3)))
    return rows


def page_comparison_map(output, imagebase, begin, end, cap=MAX_RECORDS):
    """Only immediate-to-memory comparisons followed by conditional branches.

    Any page-state value is a numeric candidate, not a semantic tab label.
    """
    if cap < 1:
        raise ValueError("nonpositive record cap")
    rows = parse_instruction_rows(output, imagebase, begin, end)
    reads, comparisons = [], []
    read_count = 0
    comparison_count = 0
    for i, (site, mnemonic, args) in enumerate(rows):
        if not FIELD.search(args):
            continue
        read_count += 1
        if len(reads) < cap:
            reads.append({"read_site_rva": hex(site),
                          "mnemonic": mnemonic,
                          "is_numeric_field_access_candidate": True})
        if mnemonic not in ("cmpb", "cmp"):
            continue
        match = LITERAL_MEM_CMP.fullmatch(args)
        if not match:
            continue
        value = int(match.group(1), 16)
        if not 0 <= value <= 255:
            continue
        comparison_count += 1
        next_row = rows[i + 1] if i + 1 < len(rows) else None
        branch = None
        if next_row and next_row[1] in CONDITIONAL_BRANCHES:
            dest_match = JUMP_DEST.match(next_row[2])
            if dest_match:
                target = int(dest_match.group(1), 16) - imagebase
                branch = {
                    "branch_site_rva": hex(next_row[0]),
                    "branch_condition": next_row[1],
                    "branch_target_rva": hex(target),
                    "target_inside_same_function": begin <= target < end,
                }
        if len(comparisons) < cap:
            item = {
                "comparison_site_rva": hex(site),
                "page_state_value_candidate": value,
                "accessed_memory_disp": "+0x1da",
                "source_instruction_confirmed_from_function_start": True,
                "label_and_runtime_object_unverified": True,
            }
            if branch:
                item["immediately_following_conditional"] = branch
            comparisons.append(item)
    return {
        "numeric_field_access_count": read_count,
        "numeric_field_comparison_count": comparison_count,
        "candidate_page_comparisons": comparisons,
        "field_access_sites": reads,
        "comparison_records_truncated": comparison_count > len(comparisons),
        "field_access_records_truncated": read_count > len(reads),
    }


def audit_native_page_branches(game, sha):
    if sha != EXPECTED_SHA:
        return {"status": "unconfirmed", "reason": "unknown_client_sha"}
    objdump = shutil.which("objdump")
    if not objdump:
        return {"status": "unconfirmed", "reason": "gnu_objdump_unavailable"}
    path = Path(game)
    with path.open("rb") as src, mmap.mmap(src.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            return {"status": "unconfirmed", "reason": "original_sha_mismatch"}
        sections = {s["name"]: s for s in read_pe_sections(raw)}
        if not {".text", ".pdata"} <= set(sections):
            return {"status": "unconfirmed", "reason": "missing_pe_sections"}
        text, pdata = sections[".text"], sections[".pdata"]
        functions = unwind_functions(raw[pdata["raw_offset"]:pdata["raw_offset"] + pdata["raw_bytes"]],
                                     text, pdata["virtual_bytes"])
        peoff = struct.unpack_from("<I", raw, 0x3c)[0]
        imagebase = struct.unpack_from("<Q", raw, peoff + 48)[0]
    starts = [begin for begin, _ in functions]
    results = []
    for owner in (OPTIONS_CENTRAL, OPTIONS_PARENT):
        idx = bisect_right(starts, owner) - 1
        if idx < 0 or functions[idx][0] != owner:
            return {"status": "unconfirmed", "reason": "expected_function_not_unwind_bounded"}
        begin, end = functions[idx]
        if not 0 < end - begin <= MAX_FUNC_BYTES:
            return {"status": "unconfirmed", "reason": "expected_function_oversized"}
        p = subprocess.run(
            [objdump, "-d", "--no-show-raw-insn",
             f"--start-address=0x{imagebase+begin:x}",
             f"--stop-address=0x{imagebase+end:x}", str(path)],
            capture_output=True, text=True, check=False, timeout=30)
        if p.returncode != 0:
            return {"status": "unconfirmed", "reason": "objdump_function_failed"}
        report = page_comparison_map(p.stdout, imagebase, begin, end)
        report["owner_function_rva"] = hex(owner)
        results.append(report)
    known = [x for x in results[0]["candidate_page_comparisons"]
             if int(x["comparison_site_rva"], 16) == SAVES_COMPARE
             and x["page_state_value_candidate"] == 11
             and x.get("immediately_following_conditional", {}).get("branch_site_rva") == hex(SAVES_BRANCH)
             and x["immediately_following_conditional"]["branch_condition"] in ("je", "jz")
             and x["immediately_following_conditional"]["branch_target_rva"] == hex(DONE_TARGET)]
    return {
        "status": "confirmed_page_state_branch_inventory" if len(known) == 1 else "unconfirmed",
        "reason": None if len(known) == 1 else "saves_branch_baseline_not_confirmed",
        "version": "0.139.0",
        "sha256": EXPECTED_SHA,
        "original_known_saves_11_done_skip_reconfirmed": len(known) == 1,
        "function_profiles": results,
        "bevy_interaction_consumer_confirmed": False,
        "tab_change_writer_confirmed": False,
        "new_cheats_tab_implemented": False,
        "game_exe_modified": False,
        "caution": "Read-only comparisons and branches in renderer/parent; no menu tab registration, UI event subscription or state mutation inferred.",
    }
