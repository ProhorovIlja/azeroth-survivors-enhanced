"""Original 0.139 Options-associated six-pointer cluster, read-only profiling.

Three new neighboring PE function entries were discovered adjacent to three
previously confirmed Options caller functions in the original .rdata.
Neither adjacency nor a function-pointer table establishes ECS event handling.
Original client is SHA-validated, and no code bytes/instructions are exported.
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

from tools.native_0139_footer_probe import EXPECTED_SHA, _call_disassembled
from tools.native_0139_options_event_ancestry import find_e8_edges
from tools.native_menu_probe import read_pe_sections
from tools.native_options_xrefs import unwind_functions
from tools.native_0139_parent_event_profile import profile_disassembly
from tools.native_0139_function_pointer_tables import find_function_slots

KNOWN_SIX_SLOT_CLUSTER = {
    0x652DBE8: 0x20E0C0,
    0x652DBF0: 0x2C1AD0,
    0x652DBF8: 0x2C1710,
    0x652DC00: 0x20E410,
    0x652DC08: 0x20E450,
    0x652DC10: 0x20E4A0,
}
NEW_NEIGHBOR_FUNCTIONS = (0x20E410, 0x20E450, 0x20E4A0)
MAX_NEW_FUNC_BYTES = 65536
MAX_CALL_XREFS = 96
CALL = re.compile(r"^\s*([0-9a-f]+):\s+callq?\s+0x([0-9a-f]+)\b", re.I)
JUMP = re.compile(r"^\s*([0-9a-f]+):\s+jmpq?\s+(.*?)\s*$", re.I)
SELECTOR = re.compile(r"0x1da\([^)]*\)", re.I)


def profile_neighbor(disassembly, base, begin, end):
    """Metadata-only real-address summaries for a bounded original function."""
    inherited = profile_disassembly(disassembly, base, begin, end)
    calls = []
    tail_indirect = []
    direct_jumps = []
    for line in disassembly.splitlines():
        m = CALL.match(line)
        if m:
            site = int(m.group(1), 16) - base
            target = int(m.group(2), 16) - base
            if begin <= site < end:
                calls.append({"site_rva": hex(site), "called_rva": hex(target)})
        j = JUMP.match(line)
        if j:
            site = int(j.group(1), 16) - base
            if not begin <= site < end:
                continue
            arg = j.group(2)
            if arg.startswith("*"):
                tail_indirect.append(hex(site))
            else:
                d = re.match(r"0x([0-9a-f]+)\b", arg, re.I)
                if d:
                    direct_jumps.append({"site_rva": hex(site),
                                         "target_rva": hex(int(d.group(1), 16) - base)})
    inherited["direct_call_targets"] = calls[:40]
    inherited["direct_call_target_records_truncated"] = len(calls) > 40
    inherited["indirect_unconditional_jumps"] = tail_indirect[:16]
    inherited["direct_unconditional_jumps"] = direct_jumps[:16]
    inherited["native_event_dispatcher_identity_verified"] = False
    return inherited


def exact_cluster_metadata(rdata, base_rva, imagebase, expected=KNOWN_SIX_SLOT_CLUSTER):
    """Fail closed on any missing, moved, unaligned or ambiguous pointer."""
    confirmed = []
    for slot, function in sorted(expected.items()):
        off = slot - base_rva
        if off < 0 or off + 8 > len(rdata) or off % 8:
            return {"confirmed": False, "reason": "cluster_slot_outside_aligned_rdata",
                    "found": confirmed}
        value = struct.unpack_from("<Q", rdata, off)[0]
        if value != imagebase + function:
            return {"confirmed": False, "reason": "pointer_value_does_not_match_official",
                    "found": confirmed}
        confirmed.append({"slot_rva": hex(slot),
                          "function_entry_rva": hex(function)})
    return {"confirmed": True, "slots": confirmed}


def audit_options_six_pointer_cluster(game, sha, function_table_report):
    if sha != EXPECTED_SHA:
        return {"status": "unconfirmed", "reason": "unknown_game_release"}
    if function_table_report.get("status") != "original_options_function_pointer_inventory":
        return {"status": "unconfirmed", "reason": "prior_pointer_inventory_missing"}
    objdump = shutil.which("objdump")
    if not objdump:
        return {"status": "unconfirmed", "reason": "gnu_objdump_unavailable"}
    path = Path(game)
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            return {"status": "unconfirmed", "reason": "full_file_original_sha_mismatch"}
        sections = {s["name"]: s for s in read_pe_sections(raw)}
        if not {".text", ".pdata", ".rdata"} <= set(sections):
            return {"status": "unconfirmed", "reason": "missing_pe_sections"}
        t, p, ro = (sections[n] for n in (".text", ".pdata", ".rdata"))
        funcs = unwind_functions(raw[p["raw_offset"]:p["raw_offset"] + p["raw_bytes"]],
                                 t, p["virtual_bytes"])
        starts = [start for start, _ in funcs]
        code = raw[t["raw_offset"]:t["raw_offset"] + t["raw_bytes"]]
        header_offset = struct.unpack_from("<I", raw, 0x3c)[0]
        imagebase = struct.unpack_from("<Q", raw, header_offset + 48)[0]
        exact_cluster = exact_cluster_metadata(
            raw[ro["raw_offset"]:ro["raw_offset"] + ro["raw_bytes"]], ro["rva"], imagebase)
    if not exact_cluster["confirmed"]:
        return {"status": "unconfirmed", "reason": exact_cluster["reason"]}
    if any(x not in starts for x in NEW_NEIGHBOR_FUNCTIONS):
        return {"status": "unconfirmed", "reason": "neighbor_not_function_entry"}

    functions = []
    for owner in NEW_NEIGHBOR_FUNCTIONS:
        i = bisect_right(starts, owner) - 1
        begin, end = funcs[i]
        if begin != owner or not 0 < end - begin <= MAX_NEW_FUNC_BYTES:
            return {"status": "unconfirmed", "reason": "neighbor_unwind_bound_invalid",
                    "owner": hex(owner)}
        proc = subprocess.run(
            [objdump, "-d", "--no-show-raw-insn",
             f"--start-address=0x{imagebase+begin:x}",
             f"--stop-address=0x{imagebase+end:x}", str(path)],
            capture_output=True, text=True, check=False, timeout=30)
        if proc.returncode:
            return {"status": "unconfirmed", "reason": "neighbor_objdump_failed",
                    "owner": hex(owner)}
        meta = profile_neighbor(proc.stdout, imagebase, begin, end)
        functions.append({"function_entry_rva": hex(owner),
                          "unwind_function_size": end - begin,
                          "function_profile": meta})
    direct = find_e8_edges(code, t["rva"], funcs,
                           set(NEW_NEIGHBOR_FUNCTIONS), limit=MAX_CALL_XREFS)
    if not direct["truncated"]:
        for row in direct["edges"]:
            row["instruction_confirmed"] = _call_disassembled(
                objdump, imagebase, int(row["site_rva"], 16),
                int(row["target_function_rva"], 16), path)
    return {
        "status": "six_pointer_cluster_original_client_verified",
        "original_client_sha256": EXPECTED_SHA,
        "exact_contiguous_rdata_pointer_cluster": exact_cluster,
        "previously_confirmed_options_ancestry_function_rvas": [
            "0x20e0c0", "0x2c1ad0", "0x2c1710"],
        "new_adjacent_function_profiles": functions,
        "direct_calls_into_new_adjacent_functions": direct,
        "Bevy_ECS_callback_registration_proven": False,
        "selected_options_page_mutator_proven": False,
        "button_interaction_handler_proven": False,
        "native_options_cheat_page_implemented": False,
        "original_binary_modified": False,
        "caution": "Vtable/function-pointer structural evidence only; neighboring callbacks do not imply ECS event semantics, live object ownership, or hook ABI.",
    }
