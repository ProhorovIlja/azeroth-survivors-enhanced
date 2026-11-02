"""Read-only exact-SHA 0.139 Rust Options type descriptor and pointer graph.

Investigates static indirect .rdata/.data pointers to original Options
type-name strings. An address or type descriptor is NOT a Bevy ECS system
registration, event handler or safe hook. Original bytes never leave CI.
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
from tools.native_0139_options_type_xrefs import find_type_names, TYPE_PREFIX

TARGET_TYPES = ("OptionsCanvas", "OptionsRoot", "PageList", "Footer", "TipText")
DATA_SECTIONS = (".rdata", ".data")
MAX_POINTER_SITES = 128
MAX_CODE_XREFS = 128
MAX_FUNCTIONS_DISASSEMBLED = 64
MAX_FUNCTION_BYTES = 65536
RIP_REL = re.compile(rb"[\x48-\x4f][\x8b\x8d][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]")
OBJDUMP_RIP = re.compile(r"^\s*([0-9a-f]+):\s+(lea|leaq|mov|movq)\s+", re.I)


def locate_type_pointer_slots(region, section_rva, type_address_to_name,
                              imagebase, cap=MAX_POINTER_SITES):
    """Find exact 64-bit virtual-address slots for known full type names."""
    if cap < 1:
        raise ValueError("cap must be positive")
    events = []
    total = 0
    for target_rva, name in sorted(type_address_to_name.items()):
        pattern = struct.pack("<Q", imagebase + target_rva)
        at = 0
        while True:
            at = region.find(pattern, at)
            if at < 0:
                break
            at += 1
            if (at - 1) % 8:
                continue
            pos = at - 1
            total += 1
            if len(events) < cap:
                full_len = len(TYPE_PREFIX) + len(name.encode("ascii"))
                exact_str_pair = (
                    pos + 16 <= len(region)
                    and struct.unpack_from("<Q", region, pos + 8)[0] == full_len)
                events.append({
                    "type_name": name,
                    "type_string_rva": hex(target_rva),
                    "data_pointer_slot_rva": hex(section_rva + pos),
                    "adjacent_exact_string_length": exact_str_pair,
                    "pointer_slot_aligned_8": True,
                })
    return {"pointer_slot_count": total,
            "pointer_slots": events,
            "pointer_slots_truncated": total > len(events)}


def direct_rip_slot_reads(code, code_rva, pointer_slot_rvas, functions,
                          cap=MAX_CODE_XREFS):
    """Discover RIP-relative MOV/LEA reads of exact native pointer slots."""
    starts = [begin for begin, _ in functions]
    result = []
    total = 0
    for m in RIP_REL.finditer(code):
        at = m.start()
        if at + 7 > len(code):
            continue
        site = code_rva + at
        disp = struct.unpack_from("<i", code, at + 3)[0]
        target = site + 7 + disp
        if target not in pointer_slot_rvas:
            continue
        i = bisect_right(starts, site) - 1
        if i < 0 or site + 7 > functions[i][1]:
            continue
        total += 1
        if len(result) < cap:
            result.append({
                "instruction_site_rva": hex(site),
                "owner_function_rva": hex(functions[i][0]),
                "referenced_type_name": pointer_slot_rvas[target],
                "pointer_slot_rva": hex(target),
                "disassembled_instruction_start": False,
            })
    return {"direct_rip_slot_xref_count": total,
            "records": result, "truncated": total > len(result)}


def confirmed_rip_instructions(output, imagebase, begin, end):
    found = set()
    for line in output.splitlines():
        m = OBJDUMP_RIP.match(line)
        if m:
            site = int(m.group(1), 16) - imagebase
            if begin <= site < end:
                found.add(site)
    return found


def function_pointers_near_slots(data, section_rva, imagebase, functions,
                                 records, proximity=48, cap=6):
    """Nearby pointer candidates only; not inferred callbacks or vtables."""
    function_starts = {s for s, _ in functions}
    unique = []
    for entry in records:
        ptr_off = int(entry["data_pointer_slot_rva"], 16) - section_rva
        adjacent = []
        lo = max(0, (ptr_off - proximity + 7) & ~7)
        hi = min(len(data) - 7, ptr_off + proximity + 1)
        for pos in range(lo, hi, 8):
            if pos == ptr_off:
                continue
            va = struct.unpack_from("<Q", data, pos)[0]
            possible_rva = va - imagebase
            if possible_rva in function_starts:
                if len(adjacent) < cap:
                    adjacent.append({"code_function_entry_rva": hex(possible_rva),
                                     "pointer_slot_rva": hex(section_rva + pos)})
        if adjacent:
            unique.append({"type_name": entry["type_name"],
                           "type_pointer_slot_rva": entry["data_pointer_slot_rva"],
                           "nearby_pdata_function_entry_pointer_candidates": adjacent})
    return unique


def audit_options_reflection_pointer_graph(game, sha, type_report):
    if sha != EXPECTED_SHA:
        return {"status": "unconfirmed", "reason": "wrong_original_client_sha"}
    if type_report.get("status") != "read_only_options_type_marker_map":
        return {"status": "unconfirmed", "reason": "original_type_markers_unverified"}
    exe = shutil.which("objdump")
    if not exe:
        return {"status": "unconfirmed", "reason": "gnu_objdump_unavailable"}
    path = Path(game)
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            return {"status": "unconfirmed", "reason": "original_sha_mismatch"}
        sections = {s["name"]: s for s in read_pe_sections(raw)}
        if not {".text", ".rdata", ".pdata"} <= set(sections):
            return {"status": "unconfirmed", "reason": "missing_pe_sections"}
        t, r, p = sections[".text"], sections[".rdata"], sections[".pdata"]
        funcs = unwind_functions(raw[p["raw_offset"]:p["raw_offset"] + p["raw_bytes"]],
                                 t, p["virtual_bytes"])
        ro = raw[r["raw_offset"]:r["raw_offset"] + r["raw_bytes"]]
        names = find_type_names(ro, r["rva"])
        if any(not names.get(n) for n in TARGET_TYPES):
            return {"status": "unconfirmed", "reason": "expected_options_types_missing"}
        target_rvas = {rva: name for name in TARGET_TYPES for rva in names[name]}
        peoff = struct.unpack_from("<I", raw, 0x3c)[0]
        imagebase = struct.unpack_from("<Q", raw, peoff + 48)[0]
        observed = []
        candidate_nearby = []
        for section_name in DATA_SECTIONS:
            s = sections.get(section_name)
            if not s:
                continue
            region = raw[s["raw_offset"]:s["raw_offset"] + s["raw_bytes"]]
            refs = locate_type_pointer_slots(region, s["rva"], target_rvas, imagebase)
            observed.append({"section": section_name, **refs})
            candidate_nearby.extend(function_pointers_near_slots(
                region, s["rva"], imagebase, funcs, refs["pointer_slots"]))
        slots = {int(x["data_pointer_slot_rva"], 16): x["type_name"]
                 for section in observed for x in section["pointer_slots"]}
        if any(x["pointer_slots_truncated"] for x in observed):
            return {"status": "incomplete", "reason": "type_pointer_slot_inventory_truncated",
                    "pointer_slots": observed}
        code = raw[t["raw_offset"]:t["raw_offset"] + t["raw_bytes"]]
        direct = direct_rip_slot_reads(code, t["rva"], slots, funcs)
    confirmed = 0
    failures = []
    if not direct["truncated"]:
        grouped = {}
        for row in direct["records"]:
            grouped.setdefault(int(row["owner_function_rva"], 16), []).append(row)
        if len(grouped) <= MAX_FUNCTIONS_DISASSEMBLED:
            starts = [a for a, _ in funcs]
            for owner, rows in sorted(grouped.items()):
                idx = bisect_right(starts, owner) - 1
                begin, end = funcs[idx]
                if end - begin > MAX_FUNCTION_BYTES:
                    failures.append(hex(owner))
                    continue
                p = subprocess.run(
                    [exe, "-d", "--no-show-raw-insn",
                     f"--start-address=0x{imagebase+begin:x}",
                     f"--stop-address=0x{imagebase+end:x}", str(path)],
                    capture_output=True, text=True, check=False, timeout=30)
                if p.returncode != 0:
                    failures.append(hex(owner))
                    continue
                true_sites = confirmed_rip_instructions(p.stdout, imagebase, begin, end)
                for row in rows:
                    row["disassembled_instruction_start"] = (
                        int(row["instruction_site_rva"], 16) in true_sites)
                    confirmed += int(row["disassembled_instruction_start"])
        else:
            failures.append("too_many_xref_owner_functions")
    return {
        "status": "read_only_options_type_pointer_graph",
        "original_client_sha256": EXPECTED_SHA,
        "pointer_slot_sections": observed,
        "total_type_name_pointer_slots": sum(x["pointer_slot_count"] for x in observed),
        "exact_Rust_str_descriptor_count": sum(
            int(x["adjacent_exact_string_length"])
            for section in observed for x in section["pointer_slots"]),
        "original_options_canvas_data_pointer_slots": sum(
            int(x["type_name"] == "OptionsCanvas")
            for section in observed for x in section["pointer_slots"]),
        "possible_nearby_code_pointer_candidates": candidate_nearby[:32],
        "nearby_code_pointer_candidate_rows_truncated": len(candidate_nearby) > 32,
        "direct_code_references_to_pointer_slots": direct,
        "confirmed_code_ref_instruction_starts": confirmed,
        "disassembly_failed_function_owners": failures,
        "Bevy_ECS_system_registration_proven": False,
        "native_Options_click_consumer_proven": False,
        "safe_game_hook_proven": False,
        "original_game_modified": False,
        "caution": "Rust string descriptors are static pointers, not proven ECS system callbacks. Nearby executable pointers are candidate data only; source bytes never exported.",
    }
