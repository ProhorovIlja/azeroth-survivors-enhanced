"""Original Windows 0.139 metadata audit; game EXE is ephemeral, never uploaded.

The script does not execute or patch the original game and never approves hooks.
"""
import argparse
import hashlib
import json
import mmap
from pathlib import Path
import re
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
    """GZIP members are individually decompressed, with strict size bounds."""
    target = Path(output)
    if target.exists() or target.is_symlink(): raise AuditError("Never overwrite game or other files")
    hashed = hashlib.sha256()
    total = 0
    try:
        with target.open("xb") as stream:
            for url, length in parts:
                if not url.startswith(ORIGIN): raise AuditError("Unexpected download origin")
                request = urllib.request.Request(url, headers={"Accept-Encoding":"identity", "User-Agent":"AZSE-0139-audit/1"})
                decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
                received = 0
                with opener.open(request, timeout=50) as response:
                    if response.status != 200: raise AuditError("Official part HTTP failure")
                    while True:
                        chunk = response.read(min(CHUNK, length - received + 1))
                        if not chunk: break
                        received += len(chunk)
                        if received > length: raise AuditError("Compressed part exceeds manifest")
                        data = chunk
                        while data:
                            decoded = decoder.decompress(data, min(CHUNK, SIZE - total + 1))
                            if total + len(decoded) > SIZE: raise AuditError("Decompressed beyond expected target size")
                            stream.write(decoded)
                            hashed.update(decoded)
                            total += len(decoded)
                            data = decoder.unconsumed_tail
                            if decoder.eof:
                                if data or decoder.unused_data: raise AuditError("Extra data after GZIP member")
                                break
                trailer = decoder.flush()
                if total + len(trailer) > SIZE: raise AuditError("Excess final GZIP output")
                stream.write(trailer)
                hashed.update(trailer)
                total += len(trailer)
                if received != length or not decoder.eof or decoder.unused_data:
                    raise AuditError("Incomplete/corrupt GZIP member")
        if total != SIZE or hashed.hexdigest() != SHA:
            raise AuditError("Whole original EXE SHA256 or size does not match official manifest")
        return {"sha256": hashed.hexdigest(), "size": total}
    except Exception:
        target.unlink(missing_ok=True)
        raise

def static_report(game, identity):
    from tools.native_options_xrefs import map_binary
    from tools.native_menu_probe import collect_static_evidence
    with open(game, "rb") as src, mmap.mmap(src.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        graph = map_binary(mm, identity["sha256"], require_known=False)
        types = collect_static_evidence(mm, identity["sha256"], strict=False)
    observed = graph["candidate_ui_entrypoints"]
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
        "static_evidence_only": True, "disassembler_confirmed": False,
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
                     "original_exe_published":False},sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
