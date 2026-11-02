"""Read-only SHA-pinned direct-call provenance for native 0.139 selector byte stores.

Direct E8 call edges do not establish Bevy ECS event-handler, object lifetime
or semantic association. Never patches a game binary or emits original bytes.
"""
from __future__ import annotations

from bisect import bisect_right
import hashlib
import mmap
from pathlib import Path
import shutil
import struct

from tools.native_menu_probe import read_pe_sections
from tools.native_options_xrefs import unwind_functions
from tools.native_0139_footer_probe import EXPECTED_SHA, _call_disassembled

# Five previously reviewed menu action constructor caller functions plus
# the original AddOns page content. Page widget rendering is NOT click dispatch.
KNOWN_UI_FUNCTIONS = frozenset((0x3F5D40, 0x1DF770, 0x1E0E60,
                                 0x3F05F0, 0x3F0A20, 0x3F0EB0))
MAX_EDGES = 256
MAX_DISASSEMBLY_CHECKS = 128
MAX_TARGETS = 64


def byte_writer_owners(selector_report):
    """Only use fully scanned and disassembled byte stores as candidates."""
    if selector_report.get("status") != "confirmed_full_displacement_inventory":
        return set()
    if not selector_report.get("raw_prefilter_fully_examined"):
        return set()
    if selector_report.get("access_records_truncated"):
        return set()
    return {int(x["function_begin_rva"], 16)
            for x in selector_report["access_records"]
            if x.get("access_candidate") == "write_candidate"
            and x.get("instruction_mnemonic") == "movb"
            and x.get("disassembled_from_function_start") is True}


def scan_direct_calls(code, base_rva, functions, targets, limit=MAX_EDGES):
    """Prefilter E8 rel32 xrefs by exact function entry RVA, not verified yet."""
    starts = [x[0] for x in functions]
    edges, total = [], 0
    per_target = {x: 0 for x in targets}
    idx = 0
    while True:
        idx = code.find(b"\xe8", idx)
        if idx < 0 or idx + 5 > len(code):
            break
        call_site = base_rva + idx
        target = call_site + 5 + struct.unpack_from("<i", code, idx + 1)[0]
        if target in targets:
            fi = bisect_right(starts, call_site) - 1
            if fi >= 0 and call_site + 5 <= functions[fi][1]:
                caller = functions[fi][0]
                total += 1
                per_target[target] += 1
                if len(edges) < limit:
                    edges.append({"call_site_rva": hex(call_site),
                                  "caller_function_rva": hex(caller),
                                  "target_byte_writer_function_rva": hex(target),
                                  "known_ui_caller": caller in KNOWN_UI_FUNCTIONS,
                                  "disassembler_confirmed": False})
        idx += 1
    return {"direct_e8_candidate_count": total,
            "per_target_candidate_counts": {hex(k): v for k, v in sorted(per_target.items())},
            "edges": edges, "edges_truncated": total > limit}


def audit_byte_writer_callers(game, expected_sha, selector_report):
    if expected_sha != EXPECTED_SHA:
        return {"status": "unconfirmed", "reason": "wrong_client_identity"}
    owners = byte_writer_owners(selector_report)
    if not owners or len(owners) > MAX_TARGETS:
        return {"status": "unconfirmed", "reason": "missing_complete_strict_byte_writer_inventory"}
    exe = shutil.which("objdump")
    if not exe:
        return {"status": "unconfirmed", "reason": "gnu_objdump_unavailable"}
    path = Path(game)
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            return {"status": "unconfirmed", "reason": "original_sha_mismatch"}
        s = {x["name"]: x for x in read_pe_sections(raw)}
        if not {".text", ".pdata"} <= set(s):
            return {"status": "unconfirmed", "reason": "missing_pe_sections"}
        t, p = s[".text"], s[".pdata"]
        functions = unwind_functions(
            raw[p["raw_offset"]:p["raw_offset"] + p["raw_bytes"]],
            t, p["virtual_bytes"])
        candidate = scan_direct_calls(
            raw[t["raw_offset"]:t["raw_offset"] + t["raw_bytes"]],
            t["rva"], functions, owners)
        header_offset = struct.unpack_from("<I", raw, 0x3C)[0]
        imagebase = struct.unpack_from("<Q", raw, header_offset + 48)[0]
    records = candidate["edges"]
    checked = 0
    confirmed = 0
    if not candidate["edges_truncated"] and len(records) <= MAX_DISASSEMBLY_CHECKS:
        for edge in records:
            edge["disassembler_confirmed"] = _call_disassembled(
                exe, imagebase, int(edge["call_site_rva"], 16),
                int(edge["target_byte_writer_function_rva"], 16), path)
            checked += 1
            if edge["disassembler_confirmed"]:
                confirmed += 1
    ui_edges = [x for x in records if x["known_ui_caller"] and x["disassembler_confirmed"]]
    return {
        "status": "verified_direct_call_inventory" if checked == candidate["direct_e8_candidate_count"] else "candidate_direct_call_inventory",
        "candidate_direct_calls_total": candidate["direct_e8_candidate_count"],
        "disassembler_checked_count": checked,
        "disassembler_confirmed_count": confirmed,
        "byte_writer_function_count": len(owners),
        "byte_writer_function_rvas": [hex(x) for x in sorted(owners)],
        "per_target_candidate_counts": candidate["per_target_candidate_counts"],
        "edges": records,
        "edges_truncated": candidate["edges_truncated"],
        "direct_calls_from_known_ui_functions_confirmed": len(ui_edges),
        "direct_known_ui_to_writer_edges": ui_edges,
        "object_identity_verified": False,
        "tab_click_handler_verified": False,
        "indirect_calls_examined": False,
        "new_native_menu_implemented": False,
        "safe_hook_verified": False,
        "original_game_modified": False,
        "caution": "A disassembler-confirmed E8 call to a function containing a store at numeric +0x1DA is not proof of click-event handling or OptionsCanvas object identity.",
    }
