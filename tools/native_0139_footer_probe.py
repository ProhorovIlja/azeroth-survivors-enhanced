"""Read-only 0.139 Options footer-action discovery on the exact official EXE.

This is NOT an injection point, runtime click handler, cheat, or supported ABI.
Only small public locale keys and derived RVA metadata leave the CI runner.
"""
from __future__ import annotations

from bisect import bisect_right
import mmap
from pathlib import Path
import re
import shutil
import struct
import subprocess

from tools.native_menu_probe import read_pe_sections
from tools.native_options_xrefs import unwind_functions

EXPECTED_SHA = "0e8e314df4d78ab211b1bef5c48d78d713ed64260894af342f998d298d74d274"
TAGS = {"options.defaults": 16, "options.done": 17}
MAX_FUNCTION_BYTES = 65536


def infer_action_pairs(code, base, rdata, rdata_rva, function_starts):
    """Return evidence only if both localized buttons uniquely call one helper.

    The search is deliberately bounded to one .pdata Options function.
    Byte shapes alone do not verify instruction boundaries.
    """
    if not isinstance(base, int) or len(code) > MAX_FUNCTION_BYTES:
        return {"status": "unconfirmed", "reason": "invalid_function_bound"}
    indexed = {}
    for key, action_id in TAGS.items():
        matches = []
        offset = 0
        while True:
            i = code.find(b"\x48\x8d\x0d", offset)
            if i < 0 or i + 7 > len(code):
                break
            offset = i + 1
            target = base + i + 7 + struct.unpack_from("<i", code, i + 3)[0]
            rel = target - rdata_rva
            if rel < 0 or rdata[rel:rel + len(key)] != key.encode("ascii"):
                continue
            tag = b"\x48\xb9" + struct.pack("<Q", (1 << 63) | action_id)
            stop = min(len(code), i + 88)
            at = code.find(tag, i + 7, stop)
            if at < 0:
                continue
            for j in range(at + 10, min(len(code) - 4, at + 92)):
                if code[j] != 0xE8:
                    continue
                destination = base + j + 5 + struct.unpack_from("<i", code, j + 1)[0]
                if destination in function_starts:
                    matches.append({"key_load_rva": base + i,
                                    "tag_rva": base + at, "call_site_rva": base + j,
                                    "helper_rva": destination, "action_id": action_id})
        indexed[key] = matches

    defaults = indexed["options.defaults"]
    done = indexed["options.done"]
    joint = [(a, b) for a in defaults for b in done
             if a["helper_rva"] == b["helper_rva"] and
             a["call_site_rva"] != b["call_site_rva"]]
    # Require exactly one pairing. Do not infer a helper from a broad
    # collection of accidental E8 byte matches.
    if len(joint) != 1:
        return {"status": "unconfirmed", "reason": "missing_or_ambiguous_footer_pair",
                "defaults_candidates": len(defaults), "done_candidates": len(done),
                "joint_candidates": len(joint)}
    a, b = joint[0]
    return {"status": "candidate_same_helper", "function_rva": hex(base),
            "shared_helper_rva": hex(a["helper_rva"]),
            "buttons": [{"public_key": key,
                         "tag_low_id": item["action_id"],
                         "key_load_rva": hex(item["key_load_rva"]),
                         "tag_rva": hex(item["tag_rva"]),
                         "call_site_rva": hex(item["call_site_rva"])}
                        for key, item in (( "options.defaults", a), ("options.done", b))],
            "byte_pattern_only": True, "runtime_event_dispatcher_verified": False}


def _call_disassembled(exe, imagebase, site, target, game):
    va = imagebase + site
    p = subprocess.run([exe, "-d", f"--start-address=0x{va:x}",
                        f"--stop-address=0x{va+5:x}", str(game)],
                       capture_output=True, text=True, check=False, timeout=25)
    pattern = rf"^\s*{va:x}:\s+[^\n]*\bcallq?\s+0x{imagebase+target:x}\b"
    return p.returncode == 0 and re.search(pattern, p.stdout, re.M | re.I) is not None


def probe_file(game, expected_sha, central_rva):
    """Full-file identity is checked by the calling ephemeral downloader."""
    if expected_sha != EXPECTED_SHA:
        return {"status": "unconfirmed", "reason": "unknown_client_sha"}
    game = Path(game)
    with game.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        sections = read_pe_sections(raw)
        section = {s["name"]: s for s in sections}
        if any(k not in section for k in (".text", ".rdata", ".pdata")):
            return {"status": "unconfirmed", "reason": "missing_pe_sections"}
        text, rdata, pdata = (section[k] for k in (".text", ".rdata", ".pdata"))
        funcs = unwind_functions(raw[pdata["raw_offset"]:pdata["raw_offset"] + pdata["raw_bytes"]],
                                 text, pdata["virtual_bytes"])
        matches = [f for f in funcs if f[0] == int(central_rva, 16)]
        if len(matches) != 1 or matches[0][1] - matches[0][0] > MAX_FUNCTION_BYTES:
            return {"status": "unconfirmed", "reason": "central_not_unwind_bounded"}
        start, end = matches[0]
        offset = text["raw_offset"] + start - text["rva"]
        r = raw[rdata["raw_offset"]:rdata["raw_offset"] + rdata["raw_bytes"]]
        evidence = infer_action_pairs(raw[offset:offset + end - start], start, r,
                                      rdata["rva"], {begin for begin, _ in funcs})
        if evidence["status"] != "candidate_same_helper":
            return evidence
        header = raw[:8192]
        peoff = struct.unpack_from("<I", header, 0x3c)[0]
        imagebase = struct.unpack_from("<Q", header, peoff + 48)[0]
    exe = shutil.which("llvm-objdump") or shutil.which("objdump")
    if exe:
        target = int(evidence["shared_helper_rva"], 16)
        evidence["disassembler_confirmed_calls"] = all(
            _call_disassembled(exe, imagebase, int(button["call_site_rva"], 16),
                               target, game) for button in evidence["buttons"])
    else:
        evidence["disassembler_confirmed_calls"] = False
    evidence["safe_hook_verified"] = False
    evidence["native_cheats_implemented"] = False
    return evidence
