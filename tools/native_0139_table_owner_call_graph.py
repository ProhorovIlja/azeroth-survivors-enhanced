"""Read-only disassembly call graph for original v0.139 Options table owner.

The original PE exact-SHA-pinned function 0x1E3BC0 contains two verified
RIP-relative references to the vicinity of the six-pointer Options function
table. This tool follows *actual E8 call instructions* and nearby public
localization key names, never exports original instructions, pointer data,
game assets or binary code, and never implies a safe hook.
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
from tools.native_0139_options_pointer_table_owners import TABLE_BEGIN
from tools.native_menu_probe import read_pe_sections
from tools.native_options_xrefs import unwind_functions

OWNER_RVA = 0x1E3BC0
KNOWN_TABLE_REFS = {0x1E4135: 0x652DBA0, 0x1E4385: 0x652DC48}
LOCAL_CMP_15 = 0x1E3DE0
KNOWN_NATIVE = {
    "options_renderer":0x3F5D40,
    "native_saves_content":0x1DF770,
    "native_addons_content":0x1E0E60,
    "action_widget_constructor":0x1E5530,
    "options_parent":0x1FFDE0,
    "six_pointer_parent":0x20E0C0,
    "six_pointer_near_1":0x20E410,
    "six_pointer_near_2":0x20E450,
    "six_pointer_near_3":0x20E4A0,
}
MAX_FUNC_SIZE = 65536
MAX_CALLERS = 64
MAX_CALLS = 160
INST = re.compile(r"^\s*([0-9a-f]+):\s+([a-z][a-z0-9_.]*)\s*(.*?)\s*$", re.I)
DIRECT_CALL = re.compile(r"^\s*0x([0-9a-f]+)(?:\s|$)", re.I)
RIP = re.compile(r"0x([0-9a-f]+)\(%rip\)", re.I)
TAG = re.compile(r"\$0x80000000000000([0-3][0-9a-f])\b", re.I)
IMM = re.compile(r"\$0x([0-9a-f]+)\b", re.I)


def profile_owner(disasm, imagebase, begin, end, rdata, rdata_rva, cap=MAX_CALLS):
    """Instruction-start validated call list + narrow known public keys."""
    if cap < 1:
        raise ValueError("invalid cap")
    calls = []
    event_tags = []
    public_keys = []
    pointer_ref_sites = {}
    cmp15 = None
    for line in disasm.splitlines():
        m = INST.match(line)
        if not m:
            continue
        rva = int(m.group(1), 16) - imagebase
        if not begin <= rva < end:
            continue
        op, arg = m.group(2).lower(), m.group(3)
        if op in ("call", "callq") and not arg.startswith("*"):
            target = DIRECT_CALL.match(arg)
            if target:
                target_rva = int(target.group(1),16) - imagebase
                if len(calls) < cap:
                    calls.append({"call_site_rva": hex(rva),
                                  "target_rva": hex(target_rva),
                                  **({"known_role": role}
                                     if (role := next((k for k,v in KNOWN_NATIVE.items()
                                                       if v == target_rva),None)) else {})})
        if op in ("movabs", "movabsq"):
            tag = TAG.search(arg)
            if tag:
                low = int(tag.group(1),16)
                if low <= 63 and len(event_tags) < 60:
                    event_tags.append({"tag_site_rva":hex(rva),"generic_low_id":low})
        if rva == LOCAL_CMP_15 and op.startswith("cmp"):
            imm = IMM.search(arg)
            cmp15 = {"site_rva":hex(rva),"is_real_compare":True,
                     "is_small_15": bool(imm and int(imm.group(1),16)==15),
                     "tab_label_unconfirmed":True}
        if op in ("lea","leaq","mov","movq"):
            # For the two externally verified table-vicinity refs, only
            # report presence of a real RIP operand on the instruction.
            if rva in KNOWN_TABLE_REFS and RIP.search(arg):
                pointer_ref_sites[hex(rva)] = {
                    "original_target_rva":hex(KNOWN_TABLE_REFS[rva]),
                    "disassembled_rip_relative_instruction":True}
            rip = RIP.search(arg)
            if rip:
                # GNU objdump emits signed displacement as hex for x64 RIP
                # but code xrefs are metadata only; known source pub keys
                # are validated separately against section bounds.
                displacement=int(rip.group(1),16)
                if displacement < 0x80000000:
                    target = rva + 7 + displacement
                    rel = target - rdata_rva
                    if 0 <= rel < len(rdata) and rdata[rel:rel+8]==b"options.":
                        name = re.match(rb"options\.[a-z0-9._-]{1,48}",
                                        rdata[rel:rel+64])
                        if name and len(public_keys) < 40:
                            public_keys.append({"site_rva":hex(rva),
                                                "public_key":name.group().decode("ascii")})
    callsites = [int(c["call_site_rva"],16) for c in calls]
    nearby = []
    for site,target in KNOWN_TABLE_REFS.items():
        preceding = [x for x in callsites if site-96 <= x < site]
        following = [x for x in callsites if site < x <= site+96]
        nearby.append({"known_table_reference_site_rva":hex(site),
                       "known_table_vicinity_target_rva":hex(target),
                       "nearest_previous_call_site_rva":hex(max(preceding)) if preceding else None,
                       "nearest_following_call_site_rva":hex(min(following)) if following else None,
                       "validated_rip_instruction":hex(site) in pointer_ref_sites})
    return {
        "source_original_function_rva":hex(begin),
        "original_function_length":end-begin,
        "direct_call_count_bounded":len(calls),
        "direct_call_records_truncated":len(calls) >= cap,
        "direct_call_sites":calls,
        "generic_highbit_tag_candidates":event_tags,
        "direct_public_options_key_load_candidates":public_keys,
        "known_table_reference_near_call_context":nearby,
        "small_integer_15_comparison":cmp15,
        "original_click_event_consumer_verified":False,
        "options_selector_write_verified":False,
    }


def audit_table_owner_call_graph(game, sha, owner_report):
    if sha != EXPECTED_SHA:
        return {"status":"unconfirmed","reason":"unexpected_original_client"}
    if owner_report.get("status")!="original_options_table_owner_inventory":
        return {"status":"unconfirmed","reason":"missing_confirmed_table_ownership"}
    confirmed = owner_report.get("near_table_code_rip_references",{}).get("records",[])
    if not all(any(int(x["site_rva"],16)==site and x.get("instruction_confirmed")
                   for x in confirmed) for site in KNOWN_TABLE_REFS):
        return {"status":"unconfirmed","reason":"table_ownership_instruction_pair_not_verified"}
    disassembler=shutil.which("objdump")
    if not disassembler:
        return {"status":"unconfirmed","reason":"objdump_missing"}
    path=Path(game)
    with path.open("rb") as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as raw:
        if hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA:
            return {"status":"unconfirmed","reason":"client_sha_mismatch"}
        sections={s["name"]:s for s in read_pe_sections(raw)}
        if not {".text",".rdata",".pdata"}<=set(sections):
            return {"status":"unconfirmed","reason":"missing_sections"}
        t,p,ro=(sections[n] for n in (".text",".pdata",".rdata"))
        funcs=unwind_functions(raw[p["raw_offset"]:p["raw_offset"]+p["raw_bytes"]],
                               t,p["virtual_bytes"])
        starts=[s for s,_ in funcs]
        i=bisect_right(starts,OWNER_RVA)-1
        if i<0 or funcs[i][0]!=OWNER_RVA or not 0<funcs[i][1]-OWNER_RVA<=MAX_FUNC_SIZE:
            return {"status":"unconfirmed","reason":"owner_unwind_boundary_changed"}
        begin,end=funcs[i]
        peoff=struct.unpack_from("<I",raw,0x3c)[0]
        imagebase=struct.unpack_from("<Q",raw,peoff+48)[0]
        rdata=raw[ro["raw_offset"]:ro["raw_offset"]+ro["raw_bytes"]]
        code=raw[t["raw_offset"]:t["raw_offset"]+t["raw_bytes"]]
    dis=subprocess.run([disassembler,"-d","--no-show-raw-insn",
                        f"--start-address=0x{imagebase+begin:x}",
                        f"--stop-address=0x{imagebase+end:x}",str(path)],
                       capture_output=True,text=True,check=False,timeout=30)
    if dis.returncode:
        return {"status":"unconfirmed","reason":"owner_disassembly_failed"}
    profile=profile_owner(dis.stdout,imagebase,begin,end,rdata,ro["rva"])
    if not all(x["validated_rip_instruction"] for x in profile["known_table_reference_near_call_context"]):
        return {"status":"unconfirmed","reason":"original_table_ref_instructions_missing"}
    calls_to_owner=find_e8_edges(code,t["rva"],funcs,{OWNER_RVA},limit=MAX_CALLERS)
    if not calls_to_owner["truncated"]:
        for record in calls_to_owner["edges"]:
            record["instruction_confirmed"]=_call_disassembled(
                disassembler,imagebase,int(record["site_rva"],16),OWNER_RVA,path)
    return {
        "status":"original_native_table_owner_callgraph",
        "original_client_sha256":EXPECTED_SHA,
        "table_owner_rva":hex(OWNER_RVA),
        "table_owner_metadata":profile,
        "direct_E8_callers_of_table_owner":calls_to_owner,
        "Bevy_event_dispatcher_identified":False,
        "selected_options_page_writer_identified":False,
        "safe_original_client_hook_identified":False,
        "working_cheat_menu":False,
        "original_exe_modified":False,
        "caution":"Read-only function call site metadata, context around table references and generic IDs do not establish ECS button click semantics."
    }
