"""Research a native Options footer action-renderer path in original Windows 0.138.

Strictly read-only and exact-SHA gated. A *localized action-widget call* is not
an exposed mod API, an installed native tab or an established event callback.
Only metadata and public UI localization identifiers are exported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
from pathlib import Path
import struct
import sys

try:
    from .native_menu_probe import read_pe_sections
    from .native_options_descriptors import read_rva, section, save_new
    from .native_options_dispatch import KNOWN_0138_SHA
except ImportError:
    from tools.native_menu_probe import read_pe_sections
    from tools.native_options_descriptors import read_rva, section, save_new
    from tools.native_options_dispatch import KNOWN_0138_SHA

IMAGE_BASE = 0x140000000
SHARED_WIDGET_HELPER = 0x107FA0
# Eight observed E8 rel32 direct call sites in *exact* owner EXE 0.138.
# Sites are confirmed to be instruction boundaries by llvm-objdump.
OBSERVED_CALL_SITES = (
    0x102670, 0x1026A5, 0x3F213B, 0x3F258F,
    0x3F25C7, 0x3F2871, 0x3F8B4C, 0x3F8B88,
)
FOOTER = (
    {"key":"options.defaults", "key_load_rva":0x3F8B15,
     "action_imm_rva":0x3F8B29, "call_rva":0x3F8B4C, "action_id":16,
     "branch":"not_selected_saves_page"},
    {"key":"options.done", "key_load_rva":0x3F8B51,
     "action_imm_rva":0x3F8B65, "call_rva":0x3F8B88, "action_id":17,
     "branch":"always_on_this_path"},
)
SELECTOR_CHECK_RVA = 0x3F8B0C
OTHER_DONE_TEXT_SITE_RVA = 0x3C30EB
MAX_EXE_BYTES = 300 * 1024 * 1024

class ActionAuditError(ValueError):
    pass


def direct_target(data, text, site):
    instruction = read_rva(data,text,site,5)
    if instruction[0] != 0xE8:
        raise ActionAuditError("Expected original rel32 call at reviewed site")
    return site+5+struct.unpack_from("<i",instruction,1)[0]


def verify_all_calls(data,text):
    for site in OBSERVED_CALL_SITES:
        if direct_target(data,text,site)!=SHARED_WIDGET_HELPER:
            raise ActionAuditError("Original localized action helper call changed")
    return [hex(x) for x in OBSERVED_CALL_SITES]


def verify_footer_item(data,text,rdata,row):
    # x64 lea rcx,[rip+disp32] ; mov edx, <length> ; later call string helper
    site=row["key_load_rva"]
    ins=read_rva(data,text,site,7)
    if ins[:3]!=b"\x48\x8d\x0d":
        raise ActionAuditError("Original footer key load changed")
    target=site+7+struct.unpack_from("<i",ins,3)[0]
    raw=read_rva(data,rdata,target,len(row["key"]))
    if raw != row["key"].encode("ascii"):
        raise ActionAuditError("Original localized footer key changed")
    # Low-level action tag: movabs rcx, 0x8000000000000000 + small action ID.
    a=row["action_imm_rva"]
    imm=read_rva(data,text,a,10)
    if imm[:2]!=b"\x48\xb9" or struct.unpack_from("<Q",imm,2)[0] != ((1<<63)|row["action_id"]):
        raise ActionAuditError("Original footer action tag changed")
    if direct_target(data,text,row["call_rva"]) != SHARED_WIDGET_HELPER:
        raise ActionAuditError("Original footer action-widget call changed")
    return {"public_localization_key":row["key"],"action_tag_low_id":row["action_id"],
            "key_load_rva":hex(site),"action_imm_rva":hex(a),
            "widget_helper_call_rva":hex(row["call_rva"]),"branch_note":row["branch"]}


def analyze_bytes(data,sha):
    if sha!=KNOWN_0138_SHA:
        raise ActionAuditError("Unreviewed EXE; exact 0.138 SHA required")
    sections=read_pe_sections(data)
    text=section(sections,'.text');rdata=section(sections,'.rdata')
    calls=verify_all_calls(data,text)
    # Distinct Saves-selected conditional skip over the Defaults footer control.
    check=read_rva(data,text,SELECTOR_CHECK_RVA,7)
    if check!=bytes.fromhex("80 b8 da 01 00 00 0b"):
        raise ActionAuditError("Native Saves-only footer condition changed")
    jump=read_rva(data,text,SELECTOR_CHECK_RVA+7,2)
    if jump[0]!=0x74 or SELECTOR_CHECK_RVA+9+struct.unpack("<b",jump[1:])[0]!=FOOTER[1]["key_load_rva"]:
        raise ActionAuditError("Saves branch no longer skips Defaults and enters Done")
    # The other 'options.done' label is in a separate native function, not
    # another call to the 0x107fa0 helper. Avoid conflating these render paths.
    if read_rva(data,text,OTHER_DONE_TEXT_SITE_RVA,3)!=b"\x48\x8d\x0d":
        raise ActionAuditError("Alternate options.done label load changed")
    items=[verify_footer_item(data,text,rdata,r) for r in FOOTER]
    return {"schema":1,"exe_sha256":sha,"version":"0.138.0",
            "audit_kind":"read_only_native_options_localized_footer_actions",
            "shared_widget_helper_rva":hex(SHARED_WIDGET_HELPER),
            "observed_call_site_count":len(calls),"observed_helper_call_sites":calls,
            "options_footer_action_items":items,
            "saves_section_selector":11,
            "defaults_hidden_for_saves_page":True,
            "alternate_done_label_path_rva":hex(OTHER_DONE_TEXT_SITE_RVA),
            "interpretation":"Shared localized action widget builder candidate; actual handler, Bevy entity ownership and new-tab insertion remain unknown",
            "native_cheats_page_installed":False,
            "runtime_event_abi_verified":False,
            "native_cheats_verified":False,
            "game_modified":False}


def analyze_file(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or not 1_000_000<=p.stat().st_size<=MAX_EXE_BYTES:
        raise ActionAuditError("Expected an original bounded regular EXE")
    with p.open('rb') as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
        sha=hashlib.sha256(mm).hexdigest()
        return analyze_bytes(mm,sha)


def main(argv=None):
    p=argparse.ArgumentParser(description="Read-only original 0.138 footer action-path research")
    p.add_argument('--game-exe',required=True)
    p.add_argument('--out',help="new JSON output path; will not overwrite")
    a=p.parse_args(argv)
    try:
        report=analyze_file(a.game_exe)
        if a.out:save_new(a.out,report)
        print(json.dumps(report,indent=2,sort_keys=True))
        return 0
    except (ValueError,OSError) as exc:
        print("Refused: "+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
