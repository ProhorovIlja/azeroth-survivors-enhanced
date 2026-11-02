"""Inspect real 0.139 UI *function-pointer tables*, rather than type-name pointers.

Read-only, exact-official-SHA static Windows PE analysis. A function-pointer slot
is neither a proven ECS system registration nor an event handler. We do not
publish raw instructions, pointer table bytes or original-client files.
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

# Known independent 0.139 original native builders & their direct callers.
# Selector candidates are OTHER functions and are not conflated with these.
FUNCTIONS = {
    "options_renderer": 0x3F5D40,
    "options_parent": 0x1FFDE0,
    "saves_content": 0x1DF770,
    "addons_content": 0x1E0E60,
    "ui_action_constructor": 0x1E5530,
    "parent_of_options": 0x20E0C0,
    "parent_layer_2": 0x2C1710,
    "parent_layer_3": 0x2C1AD0,
}
SECTIONS = (".rdata", ".data")
MAX_SLOTS_PER_SECTION = 128
MAX_CONTEXT = 24
MAX_CODE_CANDIDATES = 128
MAX_FUNCTION_OWNERS = 64
MAX_FUNCTION_BYTES = 65536

# x64 RIP-relative MOV or LEA (with REX prefix), including r8-r15 destinations.
RIP_LOAD = re.compile(rb"[\x48-\x4f][\x8b\x8d][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]")
ENTRY = re.compile(r"^\s*([0-9a-f]+):\s+([a-z][a-z0-9_.]*)\s+(.*?)\s*$", re.I)
RIP_OPERAND = re.compile(r"0x[0-9a-f]+\(%rip\)", re.I)


def find_function_slots(data, section_rva, imagebase, targets, cap=MAX_SLOTS_PER_SECTION):
    """Find 8-byte aligned exact image-base+function-start values."""
    if cap < 1:
        raise ValueError("cap must be positive")
    rows = []
    found = 0
    for name, rva in sorted(targets.items()):
        needle = struct.pack("<Q", imagebase + rva)
        pos = 0
        while True:
            pos = data.find(needle, pos)
            if pos < 0:
                break
            if not pos % 8:
                found += 1
                if len(rows) < cap:
                    rows.append({
                        "target_role": name, "target_function_rva": hex(rva),
                        "slot_rva": hex(section_rva + pos),
                        "aligned_pointer_shape": True,
                    })
            pos += 1
    return {"pointer_slot_count": found, "pointer_slots": rows,
            "truncated": found > len(rows)}


def nearest_function_pointer_neighbors(data, section_rva, imagebase, function_starts,
                                       slots, window=MAX_CONTEXT, limit=6):
    """Collect only adjacent .pdata-start pointer metadata, never code bytes."""
    rows = []
    for item in slots:
        pos = int(item["slot_rva"], 16) - section_rva
        around = []
        lo = max(0, pos - window)
        hi = min(len(data) - 8, pos + window)
        for j in range(lo, hi + 1):
            if j == pos or j % 8:
                continue
            ptr_rva = struct.unpack_from("<Q", data, j)[0] - imagebase
            if ptr_rva in function_starts and len(around) < limit:
                around.append({"neighbor_function_rva": hex(ptr_rva),
                               "neighbor_pointer_slot_rva": hex(section_rva + j)})
        rows.append({"reference_role": item["target_role"],
                     "reference_pointer_slot_rva": item["slot_rva"],
                     "nearby_function_entry_pointer_shapes": around,
                     "incomplete_neighborhood": False})
    return rows


def raw_rip_load_candidates(text, text_rva, exact_slots, functions, cap=MAX_CODE_CANDIDATES):
    """Only prefilter address matches, verify opcode and RIP target later."""
    starts = [start for start, _ in functions]
    records = []
    total = 0
    for match in RIP_LOAD.finditer(text):
        pos = match.start()
        if pos + 7 > len(text):
            continue
        site = text_rva + pos
        disp = struct.unpack_from("<i", text, pos + 3)[0]
        target = site + 7 + disp
        if target not in exact_slots:
            continue
        idx = bisect_right(starts, site) - 1
        if idx < 0 or site + 7 > functions[idx][1]:
            continue
        total += 1
        if len(records) < cap:
            records.append({"code_site_rva": hex(site),
                            "code_owner_rva": hex(functions[idx][0]),
                            "referenced_slot_rva": hex(target),
                            "referenced_builder_role": exact_slots[target],
                            "instruction_confirmed": False})
    return {"raw_candidate_count": total, "records": records,
            "truncated": total > len(records)}


def parse_disassembled_rip_loads(disassembly, imagebase, begin, end):
    """Capture real instruction-start RVA only, without exporting instructions."""
    out = set()
    for line in disassembly.splitlines():
        m = ENTRY.match(line)
        if not m:
            continue
        site = int(m.group(1), 16) - imagebase
        if not begin <= site < end:
            continue
        if m.group(2).lower() not in ("lea", "leaq", "mov", "movq"):
            continue
        if RIP_OPERAND.search(m.group(3)):
            out.add(site)
    return out


def audit_function_pointer_tables(game, sha):
    if sha != EXPECTED_SHA:
        return {"status": "unconfirmed", "reason": "unknown_original_client_identity"}
    disassembler = shutil.which("objdump")
    if not disassembler:
        return {"status": "unconfirmed", "reason": "objdump_unavailable"}
    path = Path(game)
    with path.open("rb") as file, mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            return {"status": "unconfirmed", "reason": "full_original_sha_mismatch"}
        sec = {s["name"]: s for s in read_pe_sections(raw)}
        if not {".text", ".pdata", ".rdata"} <= set(sec):
            return {"status": "unconfirmed", "reason": "missing_original_pe_sections"}
        text, pdata = sec[".text"], sec[".pdata"]
        functions = unwind_functions(
            raw[pdata["raw_offset"]:pdata["raw_offset"] + pdata["raw_bytes"]],
            text, pdata["virtual_bytes"])
        function_starts = {start for start, _ in functions}
        if not all(x in function_starts for x in FUNCTIONS.values()):
            return {"status": "unconfirmed", "reason": "original_ui_entries_not_unwind_bounded"}
        peoff = struct.unpack_from("<I", raw, 0x3c)[0]
        imagebase = struct.unpack_from("<Q", raw, peoff + 48)[0]
        sections = []
        neighbors = []
        for secname in SECTIONS:
            part = sec.get(secname)
            if part is None:
                continue
            data = raw[part["raw_offset"]:part["raw_offset"] + part["raw_bytes"]]
            ptrs = find_function_slots(data, part["rva"], imagebase, FUNCTIONS)
            sections.append({"name": secname, **ptrs})
            neighbors.extend(nearest_function_pointer_neighbors(
                data, part["rva"], imagebase, function_starts, ptrs["pointer_slots"]))
        if any(s["truncated"] for s in sections):
            return {"status": "incomplete", "reason": "pointer_inventory_over_limit",
                    "section_pointer_counts": {s["name"]: s["pointer_slot_count"] for s in sections}}
        slot_roles = {int(row["slot_rva"], 16): row["target_role"]
                      for s in sections for row in s["pointer_slots"]}
        code = raw[text["raw_offset"]:text["raw_offset"] + text["raw_bytes"]]
        xrefs = raw_rip_load_candidates(code, text["rva"], slot_roles, functions)
    confirmed = 0
    failures = []
    if not xrefs["truncated"]:
        by_owner = {}
        for row in xrefs["records"]:
            by_owner.setdefault(int(row["code_owner_rva"], 16), []).append(row)
        if len(by_owner) > MAX_FUNCTION_OWNERS:
            failures.append("too_many_function_owners")
        else:
            starts = [start for start, _ in functions]
            for owner, rows in sorted(by_owner.items()):
                ix = bisect_right(starts, owner) - 1
                begin, end = functions[ix]
                if end - begin > MAX_FUNCTION_BYTES:
                    failures.append(hex(owner))
                    continue
                p = subprocess.run(
                    [disassembler, "-d", "--no-show-raw-insn",
                     f"--start-address=0x{imagebase+begin:x}",
                     f"--stop-address=0x{imagebase+end:x}", str(path)],
                    capture_output=True, text=True, check=False, timeout=30)
                if p.returncode != 0:
                    failures.append(hex(owner))
                    continue
                proven = parse_disassembled_rip_loads(p.stdout, imagebase, begin, end)
                for row in rows:
                    row["instruction_confirmed"] = int(row["code_site_rva"], 16) in proven
                    confirmed += int(row["instruction_confirmed"])
    return {
        "status": "original_options_function_pointer_inventory",
        "original_sha256": EXPECTED_SHA,
        "function_roles_scanned": {role: hex(rva) for role, rva in FUNCTIONS.items()},
        "original_pointer_slots_per_section": sections,
        "total_matching_function_pointer_slots": sum(s["pointer_slot_count"] for s in sections),
        "neighbor_function_entry_pointer_shapes": neighbors[:64],
        "neighbor_records_truncated": len(neighbors) > 64,
        "code_references_to_exact_pointer_slots": xrefs,
        "confirmed_code_reference_instruction_count": confirmed,
        "disassembly_failures": failures,
        "indirect_bevy_system_callback_verified": False,
        "original_options_click_consumer_verified": False,
        "selected_tab_writer_verified": False,
        "safe_native_runtime_hook_verified": False,
        "working_native_menu_implemented": False,
        "original_game_modified": False,
        "caution": "Function pointer shapes in static data do not prove ECS registration, event-handler semantics, ABI or safe native hooks."
    }
