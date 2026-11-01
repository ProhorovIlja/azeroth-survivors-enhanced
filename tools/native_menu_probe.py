"""Static, read-only map of the actual Windows 0.137 native Options UI.

Purpose: establish the Bevy/ECS menu seam before attempting any native hook.
NEVER executes game code, patches an EXE, loads a DLL, or changes a save.
"""
import argparse
import hashlib
import json
import mmap
from pathlib import Path
import re
import struct
import sys

OWNER_EXE_SHA256 = "aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8"
MAX_EXE_BYTES = 300 * 1024 * 1024
LABELS = (
    b"menu.main_menu",
    b"options.saves",
    b"options.import_save",
    b"options.export_save",
    b"options.open_saves_folder",
    b"wenilla_rogue_app::screens::options::OptionsCanvas",
    b"bevy_ui::ui_node::Node",
    b"AvSetMmThreadCharacteristicsW",
)
OPTION_TYPE = re.compile(rb"wenilla_rogue_app::screens::options::([A-Za-z][A-Za-z0-9_]*)")


class ProbeError(ValueError):
    pass


def read_pe_sections(data):
    """Minimal PE32+ reader: validates mapped sections, never touches imports/code."""
    if len(data) < 1024 or data[:2] != b"MZ":
        raise ProbeError("Expected Windows PE executable")
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_off > len(data) - 256 or pe_off > 8 * 1024 * 1024 or data[pe_off:pe_off + 4] != b"PE\x00\x00":
        raise ProbeError("Invalid PE header")
    machine, n_sections, _, _, _, opt_len, _ = struct.unpack_from("<HHIIIHH", data, pe_off + 4)
    if machine != 0x8664 or not (1 <= n_sections <= 24) or opt_len < 112 or opt_len > 4096:
        raise ProbeError("Not a supported Windows PE32+ x64 image")
    opt = pe_off + 24
    if struct.unpack_from("<H", data, opt)[0] != 0x20B:
        raise ProbeError("Not a PE32+ image")
    table = opt + opt_len
    if table + 40 * n_sections > len(data):
        raise ProbeError("Truncated PE section table")
    sections = []
    for i in range(n_sections):
        off = table + 40 * i
        name = bytes(data[off:off + 8]).split(b"\x00", 1)[0].decode("ascii", "replace")
        virtual_size, rva, raw_size, raw_off = struct.unpack_from("<IIII", data, off + 8)
        if raw_off > len(data) or raw_size > len(data) - raw_off:
            raise ProbeError("PE section points outside file")
        sections.append({"name": name, "rva": rva, "raw_offset": raw_off,
                         "raw_bytes": raw_size, "virtual_bytes": virtual_size})
    return sections


def _locate(offset, sections):
    for s in sections:
        if s["raw_offset"] <= offset < s["raw_offset"] + s["raw_bytes"]:
            return s["name"]
    return "unmapped"


def collect_static_evidence(data, sha, strict=True):
    if strict and sha != OWNER_EXE_SHA256:
        raise ProbeError("Unreviewed game EXE SHA-256; refusing to infer menu layout")
    sections = read_pe_sections(data)
    rdata = next((s for s in sections if s["name"] == ".rdata"), None)
    text = next((s for s in sections if s["name"] == ".text"), None)
    if not rdata or not text:
        raise ProbeError("Missing .rdata/.text, unexpected client structure")
    region = data[rdata["raw_offset"]: rdata["raw_offset"] + rdata["raw_bytes"]]
    labels = {}
    for raw in LABELS:
        name = raw.decode("ascii")
        first = region.find(raw)
        count = region.count(raw)
        labels[name] = {"occurrences": count,
                        "first_file_offset": (rdata["raw_offset"] + first) if first >= 0 else None}
    types = sorted({m.group(1).decode("ascii").split("wenilla_rogue_app", 1)[0]
                    for m in OPTION_TYPE.finditer(region)})
    verified = bool(sha == OWNER_EXE_SHA256 and
                    labels["wenilla_rogue_app::screens::options::OptionsCanvas"]["occurrences"] == 1 and
                    labels["options.saves"]["occurrences"] >= 1)
    return {
        "audit_kind": "native_options_static_inventory",
        "exe_sha256": sha,
        "known_owner_0137_client": sha == OWNER_EXE_SHA256,
        "native_menu_framework": "Rust / Bevy ECS with bevy_ui (symbol strings, not public source)",
        "menu_framework_anchor_verified": verified,
        "section_names": [s["name"] for s in sections],
        "options_component_type_candidates": types,
        "string_evidence": labels,
        "native_cheat_menu_present": any(x in types for x in ("CheatCanvas", "CheatsCanvas")),
        "native_cheat_actions_verified": [],
        "hook_addresses_verified": False,
        "gameplay_cheats_verified": False,
        "can_install_native_menu": False,
        "game_files_modified": False,
        "next_research": ["Identify Bevy OptionsCanvas system registration and construction path",
                          "Locate verified 0.137 UI event insertion point with full original-byte verification",
                          "Implement explicit sandbox/rollback and Windows runtime smoke test"],
    }


def analyze(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or not 1_000_000 <= p.stat().st_size <= MAX_EXE_BYTES:
        raise ProbeError("Expected bounded ordinary original EXE")
    with p.open("rb") as stream:
        with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
            sha = hashlib.sha256(data).hexdigest()
            return collect_static_evidence(data, sha, strict=True)


def main(argv=None):
    p = argparse.ArgumentParser(description="Read-only native Options menu probe; no DLL/EXE patching")
    p.add_argument("--exe", required=True)
    p.add_argument("--out", help="Optional new JSON report file (metadata only)")
    args = p.parse_args(argv)
    try:
        report = analyze(args.exe)
        if args.out:
            path = Path(args.out)
            if path.exists() or path.is_symlink() or not path.parent.is_dir() or path.parent.is_symlink():
                raise ProbeError("Output must be a NEW file in an existing ordinary directory")
            with path.open("x", encoding="utf-8") as output:
                json.dump(report, output, ensure_ascii=False, indent=2)
                output.write("\n")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ProbeError) as exc:
        print("REFUSED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
