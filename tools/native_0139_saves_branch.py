"""Exact-client, read-only confirmation of the original Saves/Defaults branch.

Confirms how one existing 0.139 Options page omits a footer button.
It is NOT a way to allocate a new page or to handle user clicks.
"""
from __future__ import annotations

import hashlib
import mmap
from pathlib import Path
import re
import shutil
import struct
import subprocess

from tools.native_menu_probe import read_pe_sections
from tools.native_0139_footer_probe import EXPECTED_SHA


def search_saves_footer_branch(region, region_rva, defaults_key_rva, done_key_rva):
    if not (region_rva <= defaults_key_rva <= region_rva + len(region)):
        return {"status": "unconfirmed", "reason": "defaults_key_outside_region"}
    candidates = []
    for p in range(max(0, defaults_key_rva - region_rva - 96),
                   min(len(region) - 9, defaults_key_rva - region_rva)):
        if region[p] != 0x80 or not 0xB8 <= region[p + 1] <= 0xBF:
            continue
        if region[p + 6] != 0x0B or region[p + 7] != 0x74:  # cmp byte,11 ; JE rel8
            continue
        # Correct x64 ModRM: mod=2 (disp32), /7 cmp, r/m any general register.
        disp = struct.unpack_from("<i", region, p + 2)[0]
        skip_target = region_rva + p + 9 + struct.unpack_from("<b", region, p + 8)[0]
        if skip_target == done_key_rva:
            candidates.append({"comparison_site_rva": hex(region_rva + p),
                               "page_selector_field_disp32": hex(disp),
                               "saves_page_literal": 11,
                               "conditional_branch_site_rva": hex(region_rva + p + 7),
                               "skip_defaults_to_done_rva": hex(skip_target),
                               "byte_pattern_only": True})
    if len(candidates) != 1:
        return {"status": "unconfirmed", "reason": "missing_or_ambiguous_saves_branch",
                "candidate_count": len(candidates)}
    return {"status": "candidate_saves_branch", **candidates[0]}


def _disassembler_confirms(exe, imagebase, game, evidence):
    site = int(evidence["comparison_site_rva"], 16)
    dest = int(evidence["skip_defaults_to_done_rva"], 16)
    va = imagebase + site
    proc = subprocess.run([exe, "-d", f"--start-address=0x{va:x}",
                           f"--stop-address=0x{va+9:x}", str(game)],
                          capture_output=True, text=True, check=False, timeout=25)
    cmp_pat = rf"^\\s*{va:x}:\\s+[^\\n]*\\bcmp(?:b)?\\b[^\\n]*0xb\\b"
    jump_pat = rf"^\\s*{va+7:x}:\\s+[^\\n]*\\bj(?:e|z)\\b[^\\n]*0x{imagebase+dest:x}\\b"
    return bool(proc.returncode == 0 and re.search(cmp_pat, proc.stdout, re.M | re.I)
                and re.search(jump_pat, proc.stdout, re.M | re.I))


def probe_saves_branch(game, sha, footer):
    if sha != EXPECTED_SHA or footer.get("status") != "candidate_same_helper" or not footer.get("disassembler_confirmed_calls"):
        return {"status": "unconfirmed", "reason": "footer_not_confirmed_for_this_client"}
    buttons = {x["public_key"]: x for x in footer["buttons"]}
    if not {"options.defaults", "options.done"} <= buttons.keys():
        return {"status": "unconfirmed", "reason": "missing_verified_footer_buttons"}
    defaults = int(buttons["options.defaults"]["key_load_rva"], 16)
    done = int(buttons["options.done"]["key_load_rva"], 16)
    path = Path(game)
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            return {"status": "unconfirmed", "reason": "original_sha_mismatch"}
        sec = {x["name"]: x for x in read_pe_sections(raw)}
        t = sec.get(".text")
        if not t:
            return {"status": "unconfirmed", "reason": "missing_text_section"}
        lower = max(t["rva"], defaults - 96)
        upper = min(t["rva"] + t["raw_bytes"], defaults + 16)
        code = raw[t["raw_offset"] + lower - t["rva"]:
                   t["raw_offset"] + upper - t["rva"]]
        evidence = search_saves_footer_branch(code, lower, defaults, done)
        header = raw[:8192]
        peoff = struct.unpack_from("<I", header, 0x3C)[0]
        imagebase = struct.unpack_from("<Q", header, peoff + 48)[0]
    if evidence["status"] != "candidate_saves_branch":
        return evidence
    disasm = shutil.which("llvm-objdump") or shutil.which("objdump")
    evidence["disassembler_confirmed_compare_and_jump"] = bool(
        disasm and _disassembler_confirms(disasm, imagebase, path, evidence))
    evidence["selected_page_field_owner_verified"] = False
    evidence["new_native_page_insertion_verified"] = False
    evidence["click_event_handler_verified"] = False
    evidence["original_game_modified"] = False
    return evidence
