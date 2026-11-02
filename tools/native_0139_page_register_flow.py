"""Exact-SHA 0.139 Options selected-page register comparison candidates.

A bounded, straight-line, alias-aware heuristic over objdump output. It is
NOT a proof of ECS handler identity or runtime object dataflow and does not
modify original game files. Source instruction bytes are never exported.
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

from tools.native_menu_probe import read_pe_sections
from tools.native_options_xrefs import unwind_functions
from tools.native_0139_footer_probe import EXPECTED_SHA
from tools.native_0139_page_branch_map import INSTRUCTION, FIELD, CONDITIONAL_BRANCHES

OWNERS = (0x3F5D40, 0x1FFDE0)
MAX_FORWARD = 32
MAX_FUNC_BYTES = 65536
REG_NAMES = {}
for full, others in {
    "rax": ("eax", "ax", "al", "ah"),
    "rbx": ("ebx", "bx", "bl", "bh"),
    "rcx": ("ecx", "cx", "cl", "ch"),
    "rdx": ("edx", "dx", "dl", "dh"),
    "rsi": ("esi", "si", "sil"),
    "rdi": ("edi", "di", "dil"),
    "rbp": ("ebp", "bp", "bpl"),
    "rsp": ("esp", "sp", "spl"),
    **{f"r{n}": (f"r{n}d", f"r{n}w", f"r{n}b") for n in range(8, 16)},
}.items():
    for name in (full, *others):
        REG_NAMES[name] = full

MEM_TO_REGISTER = re.compile(r"^0x1da\([^)]*\)\s*,\s*%([a-z0-9]+)\s*$", re.I)
IMM_TO_REGISTER = re.compile(r"^\$0x([0-9a-f]+)\s*,\s*%([a-z0-9]+)\s*$", re.I)
REGISTER_AT_END = re.compile(r"(?:^|,)\s*%([a-z0-9]+)\s*$", re.I)
BRANCH_TARGET = re.compile(r"^\s*(?:0x)?([0-9a-f]+)(?:\s|$)", re.I)
LOADS = frozenset(("movzbl", "movzbq", "movsbl", "movsbq"))


def normalize_gpr(name):
    return REG_NAMES.get(name.lower())


def parse_rows(disasm, base, begin, end):
    result = []
    for line in disasm.splitlines():
        m = INSTRUCTION.match(line)
        if m:
            rva = int(m.group(1), 16) - base
            if begin <= rva < end:
                result.append((rva, m.group(2).lower(), m.group(3).strip()))
    return result


def register_comparison_paths(disasm, base, begin, end, max_forward=MAX_FORWARD):
    """Only tag same-GPR straight-line comparisons after a real field load.

    A branch/call or any observable write to the register ends tracking.
    We intentionally do not infer propagation through copies, PHI nodes,
    jumps or Rust ECS query state.
    """
    if max_forward < 1 or max_forward > 64:
        raise ValueError("max_forward out of bounds")
    rows = parse_rows(disasm, base, begin, end)
    results = []
    for i, (site, opcode, operands) in enumerate(rows):
        if opcode not in LOADS or not FIELD.search(operands):
            continue
        m = MEM_TO_REGISTER.fullmatch(operands)
        if not m:
            continue
        register = normalize_gpr(m.group(1))
        if register is None:
            continue
        item = {"field_load_rva": hex(site), "destination_gpr": register,
                "candidate_comparisons": [], "tracking_boundary": "end_or_limit",
                "same_register_straight_line_only": True}
        for j in range(i + 1, min(len(rows), i + 1 + max_forward)):
            cmp_rva, op, arg = rows[j]
            if op in CONDITIONAL_BRANCHES or op.startswith(("jmp", "call", "ret", "loop")):
                item["tracking_boundary"] = "control_transfer"
                break
            if op.startswith(("cmp", "test")):
                c = IMM_TO_REGISTER.fullmatch(arg)
                if c and normalize_gpr(c.group(2)) == register:
                    value = int(c.group(1), 16)
                    if 0 <= value <= 255:
                        cond = None
                        if j + 1 < len(rows) and rows[j + 1][1] in CONDITIONAL_BRANCHES:
                            branch_rva, branch_op, branch_arg = rows[j + 1]
                            target = BRANCH_TARGET.match(branch_arg)
                            if target:
                                dest = int(target.group(1), 16) - base
                                cond = {"branch_site_rva": hex(branch_rva),
                                        "branch_condition": branch_op,
                                        "branch_target_rva": hex(dest),
                                        "target_inside_same_function": begin <= dest < end}
                        item["candidate_comparisons"].append({
                            "compare_site_rva": hex(cmp_rva),
                            "literal": value,
                            "immediate_to_same_register_without_observed_write": True,
                            **({"following_conditional": cond} if cond else {}),
                        })
                continue
            if op.startswith(("nop", "prefetch", "endbr", "push")):
                continue
            # Most x64 AT&T two-operand instructions write their final GPR.
            # Be conservative even if this over-stops a valid dataflow path.
            end_reg = REGISTER_AT_END.search(arg)
            if end_reg and normalize_gpr(end_reg.group(1)) == register:
                item["tracking_boundary"] = "register_overwrite_or_possible_mutation"
                break
        results.append(item)
    return results


def audit_page_register_flow(game, sha, branch_report):
    if sha != EXPECTED_SHA:
        return {"status": "unconfirmed", "reason": "unknown_client_sha"}
    if branch_report.get("status") != "confirmed_page_state_branch_inventory":
        return {"status": "unconfirmed", "reason": "page_branch_baseline_not_verified"}
    objdump = shutil.which("objdump")
    if not objdump:
        return {"status": "unconfirmed", "reason": "gnu_objdump_unavailable"}
    path = Path(game)
    with path.open("rb") as file, mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA:
            return {"status": "unconfirmed", "reason": "original_sha_mismatch"}
        sections = {s["name"]: s for s in read_pe_sections(raw)}
        if not {".text", ".pdata"} <= set(sections):
            return {"status": "unconfirmed", "reason": "missing_pe_sections"}
        t, p = sections[".text"], sections[".pdata"]
        funcs = unwind_functions(raw[p["raw_offset"]:p["raw_offset"] + p["raw_bytes"]],
                                 t, p["virtual_bytes"])
        peoff = struct.unpack_from("<I", raw, 0x3c)[0]
        imagebase = struct.unpack_from("<Q", raw, peoff + 48)[0]
    starts = [start for start, _ in funcs]
    profiles = []
    for owner in OWNERS:
        idx = bisect_right(starts, owner) - 1
        if idx < 0 or funcs[idx][0] != owner:
            return {"status": "unconfirmed", "reason": "owner_not_unwind_bounded"}
        start, end = funcs[idx]
        if not 0 < end - start <= MAX_FUNC_BYTES:
            return {"status": "unconfirmed", "reason": "owner_oversized"}
        p = subprocess.run([objdump, "-d", "--no-show-raw-insn",
                           f"--start-address=0x{imagebase+start:x}",
                           f"--stop-address=0x{imagebase+end:x}", str(path)],
                          capture_output=True, text=True, check=False, timeout=30)
        if p.returncode != 0:
            return {"status": "unconfirmed", "reason": "owner_disassembly_failed"}
        records = register_comparison_paths(p.stdout, imagebase, start, end)
        profiles.append({"owner_function_rva": hex(owner), "tracked_load_count": len(records),
                         "candidate_same_gpr_paths": records,
                         "candidate_comparison_count": sum(len(r["candidate_comparisons"]) for r in records)})
    return {"status": "bounded_register_comparison_candidates",
            "version": "0.139.0", "sha256": EXPECTED_SHA,
            "function_profiles": profiles,
            "whole_program_dataflow_verified": False,
            "bevy_interaction_consumer_verified": False,
            "selected_tab_write_verified": False,
            "native_cheats_implemented": False,
            "original_binary_modified": False,
            "caution": "Best-effort basic-block GPR alias tracking only; a candidate compare is not proof of enum value, live click handling or object ownership."}
