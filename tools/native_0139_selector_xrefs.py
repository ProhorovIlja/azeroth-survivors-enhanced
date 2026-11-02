"""Exact-SHA Windows 0.139 native Options selector (+0x1DA) access xrefs.

Read-only analysis. A selector byte displacement shared by two instructions
does NOT prove the two instructions refer to the same runtime object.

Unlike raw E8 or displacement scans, each candidate is checked by disassembling
from its containing .pdata function start. No binaries or instructions emitted.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
import hashlib
import mmap
from pathlib import Path
import re
import shutil
import struct
import subprocess

from tools.native_menu_probe import read_pe_sections
from tools.native_options_xrefs import unwind_functions
from tools.native_0139_footer_probe import EXPECTED_SHA

FIELD_DISPLACEMENT = 0x1DA
BASELINE_READER_RVA = 0x3F738C
MAX_FUNCTIONS = 192
MAX_FUNCTION_BYTES = 65536
MAX_RECORDS = 160
DISP_BYTES = struct.pack("<I", FIELD_DISPLACEMENT)
INST = re.compile(r"^\s*([0-9a-f]+):\s*([A-Za-z][A-Za-z0-9_.]*)\s*(.*)$", re.I)
MEM = re.compile(r"(?<![0-9a-f])0x1da\([^)]*\)", re.I)
DEST = re.compile(r"(?:^|,)\s*0x1da\([^)]*\)\s*$", re.I)


def find_displacement_functions(code, text_rva, functions, max_functions=MAX_FUNCTIONS):
    """Raw displacement prefilter only, not a verified x64 instruction scan."""
    if max_functions < 1:
        raise ValueError("max_functions must be >= 1")
    starts = [s for s, _ in functions]
    candidates = defaultdict(list)
    pos = 0
    raw_hits = 0
    outside_functions = 0
    while True:
        pos = code.find(DISP_BYTES, pos)
        if pos < 0:
            break
        raw_hits += 1
        site = text_rva + pos
        idx = bisect_right(starts, site) - 1
        if idx >= 0 and site + len(DISP_BYTES) <= functions[idx][1]:
            owner = functions[idx][0]
            candidates[owner].append(site)
        else:
            outside_functions += 1
        pos += 1
    sorted_owners = sorted(candidates)
    sampled = sorted_owners[:max_functions]
    return {"candidate_function_count": len(sorted_owners),
            "raw_displacement_hit_count": raw_hits,
            "outside_unwind_functions": outside_functions,
            "truncated": len(sorted_owners) > max_functions,
            "sampled_owner_rvas": sampled}


def classify_instruction(mnemonic, operands):
    """AT&T disassembly semantics only; no object ownership inferred."""
    opcode = mnemonic.lower()
    if not MEM.search(operands):
        return None
    has_target_memory = bool(DEST.search(operands))
    if opcode.startswith(("mov", "vmov", "set", "stos")) and has_target_memory:
        return "write_candidate"
    if opcode.startswith(("mov", "vmov", "cmp", "test", "lea")):
        return "read_or_address_candidate"
    if has_target_memory and opcode.startswith((
        "add", "sub", "and", "or", "xor", "inc", "dec", "neg", "not", "adc",
        "sbb", "btc", "btr", "bts", "xchg", "xadd", "cmpxchg", "shl",
        "shr", "sar", "rol", "ror")):
        return "read_modify_write_candidate"
    return "unknown_access_candidate"


def parse_accesses(stdout, imagebase, owner, end, cap=MAX_RECORDS):
    """Parse disassembled *instruction starts*, returning address-only evidence."""
    out = []
    count = 0
    for line in stdout.splitlines():
        m = INST.match(line)
        if not m:
            continue
        address = int(m.group(1), 16)
        rva = address - imagebase
        if not owner <= rva < end:
            continue
        role = classify_instruction(m.group(2), m.group(3))
        if role is None:
            continue
        count += 1
        if len(out) < cap:
            out.append({"instruction_rva": hex(rva), "function_begin_rva": hex(owner),
                        "instruction_mnemonic": m.group(2).lower(),
                        "access_candidate": role,
                        "disassembled_from_function_start": True})
    return out, count


def analyze_selector_xrefs(game, expected_sha):
    if expected_sha != EXPECTED_SHA:
        return {"status": "unconfirmed", "reason": "wrong_client_identity"}
    exe = shutil.which("objdump")
    if not exe:
        return {"status": "unconfirmed", "reason": "gnu_objdump_unavailable"}
    path = Path(game)
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            return {"status": "unconfirmed", "reason": "original_sha_mismatch"}
        sections = {s["name"]: s for s in read_pe_sections(raw)}
        if ".text" not in sections or ".pdata" not in sections:
            return {"status": "unconfirmed", "reason": "missing_pe_sections"}
        t, p = sections[".text"], sections[".pdata"]
        funcs = unwind_functions(raw[p["raw_offset"]:p["raw_offset"] + p["raw_bytes"]],
                                 t, p["virtual_bytes"])
        code = raw[t["raw_offset"]:t["raw_offset"] + t["raw_bytes"]]
        inventory = find_displacement_functions(code, t["rva"], funcs)
        starts = [a for a, _ in funcs]
        pe_offset = struct.unpack_from("<I", raw, 0x3C)[0]
        imagebase = struct.unpack_from("<Q", raw, pe_offset + 48)[0]

    # A read-only inventory over all bounded candidate functions. Do not infer
    # writes from fixed byte signatures; require disassembly from entrypoint.
    sampled = set(inventory["sampled_owner_rvas"])
    idx = bisect_right(starts, BASELINE_READER_RVA) - 1
    if idx < 0 or BASELINE_READER_RVA >= funcs[idx][1]:
        return {"status": "unconfirmed", "reason": "baseline_not_unwind_bounded"}
    baseline_owner = funcs[idx][0]
    # If the inventory truncates, include the known baseline reader to keep
    # validity testing meaningful; clearly label all output incomplete.
    sampled.add(baseline_owner)
    events = []
    total = 0
    failures = []
    oversized = []
    scanned = 0
    for owner in sorted(sampled):
        idx = bisect_right(starts, owner) - 1
        begin, end = funcs[idx]
        if begin != owner or end - owner > MAX_FUNCTION_BYTES:
            oversized.append(hex(owner))
            continue
        va = imagebase + owner
        proc = subprocess.run(
            [exe, "-d", "--no-show-raw-insn",
             f"--start-address=0x{va:x}", f"--stop-address=0x{imagebase+end:x}",
             str(path)],
            capture_output=True, text=True, check=False, timeout=30)
        if proc.returncode != 0:
            failures.append(hex(owner))
            continue
        scanned += 1
        matches, count = parse_accesses(proc.stdout, imagebase, owner, end)
        total += count
        for item in matches:
            if len(events) < MAX_RECORDS:
                events.append(item)
    baseline_read = any(int(x["instruction_rva"], 16) == BASELINE_READER_RVA
                        and x["instruction_mnemonic"].startswith("cmp")
                        and x["access_candidate"] == "read_or_address_candidate"
                        for x in events)
    complete = (not inventory["truncated"] and not oversized and not failures
                and scanned == inventory["candidate_function_count"])
    status = "confirmed_partial_inventory" if baseline_read else "unconfirmed"
    return {"status": status,
            "reason": None if baseline_read else "baseline_read_instruction_not_found",
            "official_sha256": EXPECTED_SHA,
            "field_disp": hex(FIELD_DISPLACEMENT),
            "baseline_saves_read_rva": hex(BASELINE_READER_RVA),
            "baseline_saves_cmp_disassembled_from_function_start": baseline_read,
            "raw_prefilter": {
                "candidate_function_count": inventory["candidate_function_count"],
                "raw_displacement_hit_count": inventory["raw_displacement_hit_count"],
                "outside_unwind_functions": inventory["outside_unwind_functions"],
                "sampling_truncated": inventory["truncated"]},
            "function_count_disassembled": scanned,
            "function_count_oversized": len(oversized),
            "oversized_owner_rvas": oversized[:12],
            "function_count_disassembly_failed": len(failures),
            "failed_owner_rvas": failures[:12],
            "parsed_instruction_access_count": total,
            "access_records": events,
            "access_records_truncated": total > len(events),
            "raw_prefilter_fully_examined": complete,
            "state_object_owner_confirmed": False,
            "state_writer_semantics_confirmed": False,
            "click_event_consumer_found": False,
            "new_tab_registration_verified": False,
            "safe_hook_verified": False,
            "original_binary_modified": False,
            "caution": "Only disassembled instructions referring to a numeric +0x1DA displacement. Shared runtime object identity and live event flow remain unverified."}
