"""Original Windows 0.139 metadata audit; game EXE is ephemeral, never uploaded.

The script does not execute or patch the original game and never approves hooks.
"""
import argparse
import hashlib
import json
import mmap
import re
import shutil
import struct
import subprocess
from pathlib import Path
import tempfile
import urllib.request
import zlib

LATEST = "https://wow.aethus.pl/exe/latest.json"
ORIGIN = "https://wow.aethus.pl/exe/"
VERSION = "0.139.0"
SHA = "0e8e314df4d78ab211b1bef5c48d78d713ed64260894af342f998d298d74d274"
SIZE = 150595584
PRIOR = {"options_page_controls": "0x3f74c0", "saves_page_content": "0x1021e0",
         "addons_page_content": "0x1038d0"}
CHUNK = 1024 * 1024

class AuditError(ValueError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise AuditError("Redirect refused")

def client():
    return urllib.request.build_opener(NoRedirect())

def validate(data):
    """Whole-release identity pinned to immutable issue #22 official metadata."""
    if not isinstance(data, dict) or data.get("version") != VERSION or data.get("sha256") != SHA or type(data.get("size")) is not int or data["size"] != SIZE:
        raise AuditError("Unreviewed original release: fail closed")
    parts = data.get("parts")
    if not isinstance(parts, list) or not 1 <= len(parts) <= 16:
        raise AuditError("Invalid original release part count")
    result = []
    for i, part in enumerate(parts):
        if not isinstance(part, dict) or part.get("url") != f"{VERSION}/part-{i:03d}.bin":
            raise AuditError("Unsafe/unsorted relative official part path")
        size = part.get("size")
        if type(size) is not int or not 1 <= size <= 64 * 1024 * 1024:
            raise AuditError("Invalid bounded GZIP size")
        result.append((ORIGIN + part["url"], size))
    return result

def read_manifest(opener):
    req = urllib.request.Request(LATEST, headers={"Accept":"application/json", "User-Agent":"AZSE-0139-audit/1", "Accept-Encoding":"identity"})
    with opener.open(req, timeout=25) as response:
        if response.status != 200: raise AuditError("Official manifest HTTP failure")
        raw = response.read(128 * 1024 + 1)
    if len(raw) > 128 * 1024: raise AuditError("Official manifest too large")
    try: return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError): raise AuditError("Invalid official manifest UTF-8 JSON") from None

def download_verified(parts, output, opener):
    """Stream GZIP over ordered HTTP parts.

    Important: large author updates split ONE gzip stream into 20MiB parts.
    When a gzip member ends exactly at a part boundary, a subsequent member
    can begin there. Neither format authorizes any output beyond pinned SHA.
    """
    target=Path(output)
    if target.exists() or target.is_symlink(): raise AuditError("Never overwrite game or other files")
    hashed=hashlib.sha256()
    total=0
    decoder=None
    try:
        with target.open("xb") as stream:
            for index,(url,length) in enumerate(parts):
                if not url.startswith(ORIGIN): raise AuditError("Unexpected download origin")
                if decoder is None or decoder.eof:
                    decoder=zlib.decompressobj(16+zlib.MAX_WBITS)
                request=urllib.request.Request(url,headers={"Accept-Encoding":"identity","User-Agent":"AZSE-0139-audit/1"})
                received=0
                with opener.open(request,timeout=50) as response:
                    if response.status!=200: raise AuditError("Official part HTTP failure")
                    while True:
                        chunk=response.read(min(CHUNK,length-received+1))
                        if not chunk: break
                        received+=len(chunk)
                        if received>length: raise AuditError("Compressed part oversize")
                        data=chunk
                        while data:
                            decoded=decoder.decompress(data,min(CHUNK,SIZE-total+1))
                            if total+len(decoded)>SIZE: raise AuditError("Decompressed output exceeded official size")
                            stream.write(decoded)
                            hashed.update(decoded)
                            total+=len(decoded)
                            data=decoder.unconsumed_tail
                            if decoder.eof:
                                if data or decoder.unused_data: raise AuditError("Trailing data after GZIP stream")
                                break
                if received!=length:
                    raise AuditError(f"Part {index} transfer length mismatch: received {received} expected {length}")
        if decoder is None or not decoder.eof:
            raise AuditError("GZIP stream not finished across supplied parts")
        tail=decoder.flush()
        if tail: raise AuditError("Unexpected decompressor tail after stream")
        if total!=SIZE or hashed.hexdigest()!=SHA:
            raise AuditError("Finished original EXE does not match official whole-file size/SHA256")
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return {"sha256":hashed.hexdigest(),"size":total}


def verify_direct_calls_with_disassembler(game, graph):
    """Only corroborate concrete direct E8 calls; never export original bytes."""
    exe=shutil.which("llvm-objdump") or shutil.which("objdump")
    if not exe:
        return {"tool_available":False,"checked":[]}
    with open(game,"rb") as src:
        header=src.read(8192)
    peoff=struct.unpack_from("<I",header,0x3c)[0]
    imagebase=struct.unpack_from("<Q",header,peoff+24+24)[0]
    central=graph["candidate_ui_entrypoints"].get("options_page_controls")
    targets={"saves_page_content","addons_page_content"}
    results=[]
    for candidate in graph.get("direct_call_candidates",[]):
        role=candidate["function"]
        if role not in targets or candidate["caller_begin_rva"]!=central:
            continue
        site=int(candidate["call_site_rva"],16)
        target=int(candidate["called_begin_rva"],16)
        va=imagebase+site
        proc=subprocess.run([exe,"-d",f"--start-address=0x{va:x}",
                             f"--stop-address=0x{va+5:x}",str(game)],
                            capture_output=True,text=True,timeout=25,check=False)
        pattern=rf"^\s*{va:x}:\s+[^\n]*\bcallq?\s+0x{imagebase+target:x}\b"
        confirmed=proc.returncode==0 and re.search(pattern,proc.stdout,re.M|re.I) is not None
        results.append({"role":role,"site_rva":candidate["call_site_rva"],
                        "target_rva":candidate["called_begin_rva"],
                        "call_instruction_confirmed":confirmed})
    return {"tool_available":True,"checked":results}

def static_report(game, identity):
    from tools.native_options_xrefs import map_binary
    from tools.native_menu_probe import collect_static_evidence
    with open(game, "rb") as src, mmap.mmap(src.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        graph = map_binary(mm, identity["sha256"], require_known=False)
        types = collect_static_evidence(mm, identity["sha256"], strict=False)
    verified_calls = verify_direct_calls_with_disassembler(game, graph)
    from tools.native_0139_footer_probe import probe_file
    observed = graph["candidate_ui_entrypoints"]
    footer = probe_file(game, identity["sha256"], observed.get("options_page_controls", ""))
    from tools.native_0139_action_xrefs import analyze_action_flow
    action_xrefs = analyze_action_flow(game, identity["sha256"])
    from tools.native_0139_saves_branch import probe_saves_branch
    saves_branch = probe_saves_branch(game, identity["sha256"], footer)
    from tools.native_0139_selector_xrefs import analyze_selector_xrefs
    selector_xrefs = analyze_selector_xrefs(game, identity["sha256"])
    from tools.native_0139_selector_callers import audit_byte_writer_callers
    selector_callers = audit_byte_writer_callers(game, identity["sha256"], selector_xrefs)
    from tools.native_0139_options_event_ancestry import analyze_options_event_ancestry
    event_ancestry = analyze_options_event_ancestry(game, identity["sha256"])
    from tools.native_0139_parent_event_profile import probe_parent_profiles
    parent_event_profiles = probe_parent_profiles(game, identity["sha256"], event_ancestry)
    from tools.native_0139_page_branch_map import audit_native_page_branches
    native_page_branches = audit_native_page_branches(game, identity["sha256"])
    return {
        "version": VERSION, "sha256": identity["sha256"], "bytes": identity["size"],
        "baseline": "0.138.0", "reviewed_static_ui_role_candidates": observed,
        "role_changes": {name: {"old_0138": prior, "candidate_0139": observed.get(name),
                                "safe_to_reuse_old_rva": False} for name,prior in PRIOR.items()},
        "menu_type_marker_count": types["string_evidence"]["wenilla_rogue_app::screens::options::OptionsCanvas"]["occurrences"],
        "ui_key_reference_candidates": graph["direct_key_xref_count"],
        "bounded_function_clusters": graph["unique_function_clusters"],
        "unwind_function_count": graph["unwind_function_count"],
        "direct_call_candidates": graph["direct_call_candidates"][:30],
        "direct_calls_disassembler_crosscheck": verified_calls,
        "footer_action_probe": footer,
        "native_action_id_xrefs": action_xrefs,
        "saves_footer_selector_probe": saves_branch,
        "selector_field_access_xrefs": selector_xrefs,
        "selector_byte_writer_callers": selector_callers,
        "native_options_event_ancestry": event_ancestry,
        "native_options_parent_event_profiles": parent_event_profiles,
        "original_page_state_branches": native_page_branches,
        "static_evidence_only": True, "disassembler_confirmed": bool(verified_calls["checked"]) and all(c["call_instruction_confirmed"] for c in verified_calls["checked"]),
        "native_cheats_menu_implemented": False, "live_game_verified": False,
        "original_binary_modified": False,
        "caution": "Byte-pattern candidate map, not verified instruction boundaries or safe hook/event ABI. No EXE/MPQ distributed."
    }

def main(argv=None):
    p=argparse.ArgumentParser(description="Ephemeral 0.139 source-only static PE Options audit")
    p.add_argument("--report",required=True)
    args=p.parse_args(argv)
    dest=Path(args.report)
    if dest.exists() or dest.is_symlink() or not dest.parent.is_dir() or dest.parent.is_symlink():
        raise AuditError("Report must be a new metadata file in an ordinary directory")
    opener=client()
    parts=validate(read_manifest(opener))
    with tempfile.TemporaryDirectory(prefix="original-exe-private-") as directory:
        original=Path(directory)/"original.exe"
        identity=download_verified(parts,original,opener)
        report=static_report(original,identity)
    with dest.open("x",encoding="utf-8") as output:
        json.dump(report,output,sort_keys=True,indent=2)
        output.write("\n")
    print(json.dumps({"version":VERSION,"official_sha256":identity["sha256"],
                     "native_options_candidates":report["reviewed_static_ui_role_candidates"],
                     "disassembler":report["direct_calls_disassembler_crosscheck"],
                     "original_exe_published":False},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
