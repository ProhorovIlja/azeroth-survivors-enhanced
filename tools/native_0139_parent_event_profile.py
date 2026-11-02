"""Read-only original Windows v0.139 parent-Options instruction profile.

Profiles verified menu caller functions for branch/call/selector-access shapes.
Neither instruction density nor local comparison IDs establish ECS click events.
No original instructions, bytes, executable, or assets leave the CI runner.
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
from tools.native_0139_selector_xrefs import classify_instruction

# These are confirmed _direct callers_ of the native Options renderer, not
# confirmed click handlers, and never version-agnostic addresses.
KNOWN_PARENT_FUNCTIONS = (0x1FFDE0, 0x20E0C0, 0x2C1710, 0x2C1AD0)
MAX_FUNCTION_BYTES = 65536
MAX_RECORDS = 40
ENTRY = re.compile(r"^\s*([0-9a-f]+):\s+([a-z][a-z0-9_.]*)\s*(.*)$", re.I)
IMM = re.compile(r"\$0x([a-f0-9]+)\b", re.I)
MEM_ID = re.compile(r"0x1da\([^)]*\)", re.I)


def profile_disassembly(disasm, imagebase, begin, end, cap=MAX_RECORDS):
    """Metadata-only local instruction shape summary, GNU objdump AT&T syntax."""
    if not (0 < cap <= MAX_RECORDS):
        raise ValueError("invalid profile record cap")
    op_counts = {"direct_calls": 0, "indirect_calls": 0,
                 "indirect_jumps": 0, "selector_displacement_accesses": 0}
    comparisons = []
    selector_sites = []
    for line in disasm.splitlines():
        m = ENTRY.match(line)
        if not m:
            continue
        rva = int(m.group(1), 16) - imagebase
        if not begin <= rva < end:
            continue
        op = m.group(2).lower()
        arg = m.group(3).strip()
        if op in ("call", "callq"):
            op_counts["indirect_calls" if arg.startswith("*") else "direct_calls"] += 1
        elif op.startswith("jmp") and arg.startswith("*"):
            op_counts["indirect_jumps"] += 1
        if op.startswith(("cmp", "test")):
            imm = IMM.search(arg)
            if imm:
                value = int(imm.group(1), 16)
                if 8 <= value <= 17:
                    if len(comparisons) < cap:
                        comparisons.append({"instruction_rva": hex(rva),
                                            "compared_small_integer": value,
                                            "opcode": op})
        if MEM_ID.search(arg):
            kind = classify_instruction(op, arg)
            if kind:
                op_counts["selector_displacement_accesses"] += 1
                if len(selector_sites) < cap:
                    selector_sites.append({"instruction_rva": hex(rva), "role": kind})
    return {"instruction_shape_counts": op_counts,
            "small_action_range_comparison_sites": comparisons,
            "selector_displacement_access_sites": selector_sites,
            "comparison_records_may_be_capped": len(comparisons) == cap,
            "selector_records_may_be_capped": len(selector_sites) == cap,
            "not_proof_of_handler": True}


def probe_parent_profiles(game, sha, ancestry):
    if sha != EXPECTED_SHA:
        return {"status": "unconfirmed", "reason": "wrong_client_identity"}
    if ancestry.get("status") != "verified_static_options_ancestry":
        return {"status": "unconfirmed", "reason": "options_ancestry_not_verified"}
    one = ancestry.get("direct_callers_of_parent_and_options", {})
    two = ancestry.get("second_layer_direct_call_candidates", {})
    if one.get("truncated") or two.get("truncated"):
        return {"status": "unconfirmed", "reason": "parent_ancestry_truncated"}
    proven_callees = {int(x["caller_function_rva"], 16)
                      for x in one.get("edges", []) + two.get("edges", [])
                      if x.get("instruction_confirmed")}
    if not set(KNOWN_PARENT_FUNCTIONS) <= proven_callees:
        return {"status": "unconfirmed", "reason": "known_parent_function_provenance_missing"}
    objdump = shutil.which("objdump")
    if not objdump:
        return {"status": "unconfirmed", "reason": "gnu_objdump_unavailable"}
    path = Path(game)
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            return {"status": "unconfirmed", "reason": "original_sha_mismatch"}
        sections = {s["name"]: s for s in read_pe_sections(raw)}
        if not {".text", ".pdata"} <= set(sections):
            return {"status": "unconfirmed", "reason": "missing_pe_sections"}
        t, p = sections[".text"], sections[".pdata"]
        functions = unwind_functions(raw[p["raw_offset"]:p["raw_offset"]+p["raw_bytes"]],
                                     t, p["virtual_bytes"])
        header_off = struct.unpack_from("<I", raw, 0x3c)[0]
        imagebase = struct.unpack_from("<Q", raw, header_off + 48)[0]
    starts = [start for start, _ in functions]
    summaries = []
    for owner in KNOWN_PARENT_FUNCTIONS:
        ix = bisect_right(starts, owner) - 1
        if ix < 0 or functions[ix][0] != owner:
            return {"status": "unconfirmed", "reason": "parent_not_unwind_bounded",
                    "owner_rva": hex(owner)}
        start, end = functions[ix]
        if not 0 < end - start <= MAX_FUNCTION_BYTES:
            return {"status": "unconfirmed", "reason": "parent_function_oversized",
                    "owner_rva": hex(owner)}
        result = subprocess.run(
            [objdump, "-d", "--no-show-raw-insn",
             f"--start-address=0x{imagebase+start:x}",
             f"--stop-address=0x{imagebase+end:x}", str(path)],
            capture_output=True, text=True, check=False, timeout=30)
        if result.returncode != 0:
            return {"status": "unconfirmed", "reason": "parent_disassembly_failed",
                    "owner_rva": hex(owner)}
        item = profile_disassembly(result.stdout, imagebase, start, end)
        item["function_begin_rva"] = hex(owner)
        item["function_size_bytes"] = end - start
        summaries.append(item)
    return {"status": "parent_options_instruction_profiles",
            "profiled_function_count": len(summaries),
            "original_client_sha256": EXPECTED_SHA,
            "original_function_profiles": summaries,
            "tab_click_event_consumer_identified": False,
            "options_canvas_state_mutation_proven": False,
            "native_cheats_menu_implemented": False,
            "original_binary_modified": False,
            "caution": "Function-local shape summaries are not a dynamic Bevy interaction or click-event trace."}
