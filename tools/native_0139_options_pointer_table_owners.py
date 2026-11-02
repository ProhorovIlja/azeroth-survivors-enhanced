"""Find code/data *owners* of the six-pointer original 0.139 Options cluster.

Targets the table itself, including short offsets nearby, unlike earlier scans
for named Rust types or exact pointer slots. On a 0.139 full-SHA original client,
only disassembler-validated RIP-relative LEA/MOV instruction starts count.
The original code, bytes and files are never exported by CI.
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
from tools.native_0139_options_pointer_cluster import KNOWN_SIX_SLOT_CLUSTER, exact_cluster_metadata
from tools.native_menu_probe import read_pe_sections
from tools.native_options_xrefs import unwind_functions
from tools.native_0139_function_pointer_tables import (
    RIP_LOAD, parse_disassembled_rip_loads,
)
from tools.native_0139_parent_event_profile import profile_disassembly

TABLE_BEGIN = min(KNOWN_SIX_SLOT_CLUSTER)
TABLE_END = max(KNOWN_SIX_SLOT_CLUSTER) + 8
MAX_DISTANCE = 96
MAX_XREFS = 128
MAX_PDATA_FUNCTIONS = 64
MAX_FN_BYTES = 65536
MAX_POINTERS = 96


def potential_rip_references(text, code_rva, begins, ends, functions, cap=MAX_XREFS):
    """Prefilter exact in-range RIP targets and .pdata-bounded instruction shapes."""
    if cap < 1 or begins >= ends:
        raise ValueError("invalid output cap or address range")
    starts = [s for s, _ in functions]
    events = []
    count = 0
    for m in RIP_LOAD.finditer(text):
        offset = m.start()
        if offset + 7 > len(text):
            continue
        site = code_rva + offset
        target = site + 7 + struct.unpack_from("<i", text, offset + 3)[0]
        if not begins <= target < ends:
            continue
        index = bisect_right(starts, site) - 1
        if index < 0 or site + 7 > functions[index][1]:
            continue
        count += 1
        if len(events) < cap:
            events.append({"site_rva": hex(site),
                           "target_rva": hex(target),
                           "target_offset_from_table_begin": target - TABLE_BEGIN,
                           "owner_function_rva": hex(functions[index][0]),
                           "instruction_confirmed": False})
    return {"raw_rip_target_count": count,
            "records": events, "truncated": count > len(events)}


def static_references_to_table(data, rva, imagebase, targets, cap=MAX_POINTERS):
    """Find aligned VA pointers to table vicinity, including exact start."""
    count, rows = 0, []
    for target in sorted(targets):
        word = struct.pack("<Q", imagebase + target)
        at = 0
        while True:
            pos = data.find(word, at)
            if pos < 0:
                break
            at = pos + 1
            if pos % 8:
                continue
            count += 1
            if len(rows) < cap:
                rows.append({"pointer_slot_rva": hex(rva + pos),
                             "target_table_rva": hex(target),
                             "target_offset_from_table_begin": target - TABLE_BEGIN})
    return {"pointer_count": count, "records": rows, "truncated": count > len(rows)}


def audit_pointer_table_owners(game, sha, cluster):
    if sha != EXPECTED_SHA:
        return {"status": "unconfirmed", "reason": "unknown_original_client"}
    if cluster.get("status") != "six_pointer_cluster_original_client_verified":
        return {"status": "unconfirmed", "reason": "six_pointer_baseline_missing"}
    objdump = shutil.which("objdump")
    if not objdump:
        return {"status": "unconfirmed", "reason": "objdump_missing"}
    path = Path(game)
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            return {"status": "unconfirmed", "reason": "original_client_hash_mismatch"}
        section = {s["name"]: s for s in read_pe_sections(raw)}
        if not {".rdata", ".text", ".pdata"} <= set(section):
            return {"status": "unconfirmed", "reason": "missing_PE_sections"}
        t, p, r = (section[k] for k in (".text", ".pdata", ".rdata"))
        code = raw[t["raw_offset"]:t["raw_offset"] + t["raw_bytes"]]
        funcs = unwind_functions(raw[p["raw_offset"]:p["raw_offset"] + p["raw_bytes"]],
                                 t, p["virtual_bytes"])
        off = struct.unpack_from("<I", raw, 0x3c)[0]
        base = struct.unpack_from("<Q", raw, off + 48)[0]
        original_table = raw[r["raw_offset"]:r["raw_offset"]+r["raw_bytes"]]
        exact = exact_cluster_metadata(original_table, r["rva"], base)
        if not exact["confirmed"]:
            return {"status": "unconfirmed", "reason": "source_cluster_changed"}
        search_begin = TABLE_BEGIN - MAX_DISTANCE
        search_end = TABLE_END + MAX_DISTANCE
        code_sites = potential_rip_references(
            code, t["rva"], search_begin, search_end, funcs)
        table_targets = {TABLE_BEGIN, TABLE_END} | set(KNOWN_SIX_SLOT_CLUSTER)
        ptr_tables = []
        for sname in (".rdata", ".data"):
            sec = section.get(sname)
            if not sec:
                continue
            data = raw[sec["raw_offset"]:sec["raw_offset"]+sec["raw_bytes"]]
            pointers = static_references_to_table(data, sec["rva"], base, table_targets)
            ptr_tables.append({"section": sname, **pointers})
    if code_sites["truncated"] or any(x["truncated"] for x in ptr_tables):
        return {"status": "incomplete", "reason": "raw_scan_truncated"}
    owner_profiles = []
    owners = sorted({int(row["owner_function_rva"], 16) for row in code_sites["records"]})
    if len(owners) > MAX_PDATA_FUNCTIONS:
        return {"status": "incomplete", "reason": "too_many_owner_functions",
                "owner_count": len(owners)}
    starts = [f[0] for f in funcs]
    failures = []
    for owner in owners:
        idx = bisect_right(starts, owner) - 1
        begin, end = funcs[idx]
        if end-begin > MAX_FN_BYTES:
            failures.append(hex(owner))
            continue
        proc = subprocess.run(
            [objdump, "-d", "--no-show-raw-insn",
             f"--start-address=0x{base+begin:x}",
             f"--stop-address=0x{base+end:x}", str(path)],
            capture_output=True, text=True, check=False, timeout=30)
        if proc.returncode:
            failures.append(hex(owner))
            continue
        real = parse_disassembled_rip_loads(proc.stdout, base, begin, end)
        for row in code_sites["records"]:
            if int(row["owner_function_rva"], 16) == owner:
                row["instruction_confirmed"] = int(row["site_rva"], 16) in real
        profile = profile_disassembly(proc.stdout, base, begin, end)
        owner_profiles.append({"function_entry_rva": hex(owner),
                               "function_length": end-begin,
                               "metadata_profile": profile})
    return {
        "status": "original_options_table_owner_inventory",
        "original_sha256": EXPECTED_SHA,
        "original_table_begin_rva": hex(TABLE_BEGIN),
        "original_table_end_rva": hex(TABLE_END),
        "near_table_code_rip_references": code_sites,
        "confirmed_rip_reference_count": sum(x["instruction_confirmed"] for x in code_sites["records"]),
        "near_table_static_data_pointers": ptr_tables,
        "owner_function_profiles": owner_profiles,
        "disassembly_failures": failures,
        "Bevy_ECS_system_table_owner_identified": False,
        "in_game_ui_event_consumer_identified": False,
        "safe_runtime_patch_verified": False,
        "original_exe_modified": False,
        "caution": "References to a pointer table or nearby data are not proof of dynamic Rust/Bevy event handling or safe menu insertion.",
    }
