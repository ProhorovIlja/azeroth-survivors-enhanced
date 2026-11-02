"""Exact-original-client 0.139 OptionsCanvas Bevy type-name cross-references.

Answers whether reflected Options UI type-name markers have direct RIP-relative
references in x64 code. String symbols are NOT a proof of active ECS event
system registration. Read-only, exact SHA, only derived metadata published.
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

TYPE_PREFIX = b"wenilla_rogue_app::screens::options::"
KNOWN_TYPE_NAMES = (b"OptionsCanvas", b"OptionsRoot", b"PageList", b"Footer",
                    b"Act", b"Fill", b"Readout", b"Track", b"TipText")
TYPE_PATTERN = re.compile(re.escape(TYPE_PREFIX) + b"(" + b"|".join(KNOWN_TYPE_NAMES) + b")")
TYPE_CANVAS = "OptionsCanvas"
MAX_TYPES = 60
MAX_XREFS = 120
MAX_FUNC_BYTES = 65536
LEA_PATTERN = re.compile(rb"[\x48\x49\x4c\x4d]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]")
OBJDUMP_ENTRY = re.compile(r"^\s*([0-9a-f]+):\s+(lea|leaq)\s+", re.I)


def find_type_names(rdata, base_rva):
    """Only actual ASCII namespace-qualified type names, not raw game prose."""
    result = {}
    for m in TYPE_PATTERN.finditer(rdata):
        following = rdata[m.end():m.end() + 1]
        # Rust type-name byte strings may be tightly packed, with the next
        # fully-qualified name beginning immediately. Reject a genuine suffix
        # within one longer type identifier such as OptionsCanvasExtra.
        is_other_identifier_char = bool(following and (
            65 <= following[0] <= 90 or 97 <= following[0] <= 122 or
            48 <= following[0] <= 57 or following[0] == 95))
        if is_other_identifier_char and not rdata[m.end():].startswith(b"wenilla_rogue_app::"):
            continue
        name = m.group(1).decode("ascii")
        result.setdefault(name, []).append(base_rva + m.start())
    return result


def find_exact_lea_xrefs(text, text_rva, target_rvas, functions, limit=MAX_XREFS):
    """Raw RIP-relative LEA prefilter bounded by .pdata, pending disassembly."""
    starts = [x[0] for x in functions]
    result = []
    total = 0
    for m in LEA_PATTERN.finditer(text):
        i = m.start()
        if i + 7 > len(text):
            continue
        site = text_rva + i
        target = site + 7 + struct.unpack_from("<i", text, i + 3)[0]
        if target not in target_rvas:
            continue
        fi = bisect_right(starts, site) - 1
        if fi < 0 or site + 7 > functions[fi][1]:
            continue
        total += 1
        if len(result) < limit:
            result.append({"lea_rva": hex(site),
                           "target_type_marker": target_rvas[target],
                           "function_begin_rva": hex(functions[fi][0]),
                           "instruction_confirmed": False})
    return {"raw_lea_xref_count": total, "records": result,
            "truncated": total > limit}


def confirmed_lea_sites(disasm, imagebase, begin, end):
    out = set()
    for line in disasm.splitlines():
        m = OBJDUMP_ENTRY.match(line)
        if not m:
            continue
        site = int(m.group(1), 16) - imagebase
        if begin <= site < end:
            out.add(site)
    return out


def audit_options_type_xrefs(game, sha):
    if sha != EXPECTED_SHA:
        return {"status": "unconfirmed", "reason": "unknown_client_identity"}
    objdump = shutil.which("objdump")
    if not objdump:
        return {"status": "unconfirmed", "reason": "gnu_objdump_unavailable"}
    path = Path(game)
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            return {"status": "unconfirmed", "reason": "original_sha_mismatch"}
        secs = {s["name"]: s for s in read_pe_sections(raw)}
        if not {".text", ".rdata", ".pdata"} <= set(secs):
            return {"status": "unconfirmed", "reason": "missing_pe_sections"}
        text, ro, pd = secs[".text"], secs[".rdata"], secs[".pdata"]
        funcs = unwind_functions(raw[pd["raw_offset"]:pd["raw_offset"] + pd["raw_bytes"]],
                                 text, pd["virtual_bytes"])
        region = raw[ro["raw_offset"]:ro["raw_offset"] + ro["raw_bytes"]]
        types = find_type_names(region, ro["rva"])
        if TYPE_CANVAS not in types:
            return {"status": "unconfirmed", "reason": "original_options_canvas_type_not_found"}
        if len(types) > MAX_TYPES:
            return {"status": "unconfirmed", "reason": "too_many_type_names"}
        target_names = {rva: name for name, sites in types.items() for rva in sites}
        code = raw[text["raw_offset"]:text["raw_offset"] + text["raw_bytes"]]
        xrefs = find_exact_lea_xrefs(code, text["rva"], target_names, funcs)
        peoff = struct.unpack_from("<I", raw, 0x3c)[0]
        imagebase = struct.unpack_from("<Q", raw, peoff + 48)[0]
    starts = [a for a, _ in funcs]
    confirmed = 0
    failures = []
    if not xrefs["truncated"]:
        owner_sites = {}
        for row in xrefs["records"]:
            owner_sites.setdefault(int(row["function_begin_rva"], 16), []).append(row)
        for owner, rows in owner_sites.items():
            ix = bisect_right(starts, owner) - 1
            begin, end = funcs[ix]
            if end - begin > MAX_FUNC_BYTES:
                failures.append(hex(owner))
                continue
            p = subprocess.run(
                [objdump, "-d", "--no-show-raw-insn",
                 f"--start-address=0x{imagebase+begin:x}",
                 f"--stop-address=0x{imagebase+end:x}", str(path)],
                capture_output=True, text=True, check=False, timeout=30)
            if p.returncode != 0:
                failures.append(hex(owner))
                continue
            verified_sites = confirmed_lea_sites(p.stdout, imagebase, begin, end)
            for row in rows:
                row["instruction_confirmed"] = int(row["lea_rva"], 16) in verified_sites
                confirmed += int(row["instruction_confirmed"])
    return {
        "status": "read_only_options_type_marker_map",
        "official_version": "0.139.0", "sha256": EXPECTED_SHA,
        "options_canvas_marker_occurrences": len(types[TYPE_CANVAS]),
        "type_marker_names_and_counts": {k: len(v) for k, v in sorted(types.items())},
        "raw_rip_relative_type_marker_lea_xrefs": xrefs["raw_lea_xref_count"],
        "confirmed_lea_instruction_sites": confirmed,
        "direct_options_canvas_lea_instruction_count": sum(int(x["instruction_confirmed"]) for x in xrefs["records"] if x["target_type_marker"] == TYPE_CANVAS),
        "only_known_native_type_names_scanned": True,
        "lea_xrefs": xrefs["records"],
        "xrefs_truncated": xrefs["truncated"],
        "disassembly_failed_function_rvas": failures,
        "ecs_system_registry_verified": False,
        "actual_interaction_dispatcher_verified": False,
        "safe_native_menu_integration_verified": False,
        "original_exe_modified": False,
        "caution": "The existence of a Rust/Bevy reflected type-name string, or even a code LEA to that string, does not establish which ECS system handles clicks.",
    }
