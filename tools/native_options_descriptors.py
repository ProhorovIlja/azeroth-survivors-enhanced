"""Read-only, original 0.138 Options descriptor inventory (metadata only).

Do not publish the underlying proprietary UI prose, game EXE or offsets as a
verified native patch. The 108 descriptor records are not a Bevy page registry.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import mmap
from pathlib import Path
import struct
import sys

try:
    from .native_menu_probe import read_pe_sections
    from .native_options_dispatch import KNOWN_0138_SHA
except ImportError:
    from tools.native_menu_probe import read_pe_sections
    from tools.native_options_dispatch import KNOWN_0138_SHA

IMAGE_BASE = 0x140000000
TABLE_RVA = 0x6316970
STRIDE = 0x98
ENTRY_COUNT = 108
FIELD_KIND = 0x00
FIELD_POINTER = 0x08
FIELD_LENGTH = 0x10
FIELD_DEPENDENT = 0x90
FIELD_PAGE = 0x91
ALLOWED_KINDS = {0, 1, 2}  # short tooltip identifier, inline help, separator
MAX_TEXT_BYTES = 512
EMITTER_RVA = 0x105810
EMITTER_CALLS = (0x3F8464, 0x3F84A4)
MAX_EXE_BYTES = 300 * 1024 * 1024
# Reviewed, exact local counts for original 0.138 build. They are descriptive,
# not the number of distinct tabs or an in-game edit authorization.
EXPECTED_BY_PAGE = {0:18,1:5,2:21,3:2,4:19,5:6,7:7,8:17,9:12,10:1}
EXPECTED_BY_KIND = {0:69,1:36,2:3}


class DescriptorError(ValueError):
    pass


def section(sections, name):
    found = [x for x in sections if x["name"] == name]
    if len(found) != 1:
        raise DescriptorError("Missing or duplicate PE section " + name)
    return found[0]


def read_rva(data, part, rva, size):
    rel = rva - part["rva"]
    if rel < 0 or size < 0 or rel + size > min(part["virtual_bytes"], part["raw_bytes"]):
        raise DescriptorError("RVA outside validated PE section")
    start = part["raw_offset"] + rel
    if start < 0 or start + size > len(data):
        raise DescriptorError("Read exceeds binary file")
    return bytes(data[start:start + size])


def scan_records(data, rdata):
    """Inspect descriptors without returning strings from proprietary client."""
    table = read_rva(data, rdata, TABLE_RVA, ENTRY_COUNT * STRIDE)
    found = []
    for i in range(ENTRY_COUNT):
        row = table[i*STRIDE:(i+1)*STRIDE]
        kind = row[FIELD_KIND]
        page = row[FIELD_PAGE]
        dependent = row[FIELD_DEPENDENT]
        if kind not in ALLOWED_KINDS or page > 11 or dependent not in (0, 1):
            raise DescriptorError("Unexpected kind, section or dependency flag")
        ptr, length = struct.unpack_from("<QQ", row, FIELD_POINTER)
        if kind == 2:
            if ptr != 0 or length != 0:
                raise DescriptorError("Separator unexpectedly carries a text pointer")
        else:
            if not ptr or not 1 <= length <= MAX_TEXT_BYTES:
                raise DescriptorError("Descriptor lacks bounded text")
            pointer_rva = ptr - IMAGE_BASE
            raw = read_rva(data, rdata, pointer_rva, length)
            try:
                s = raw.decode("utf-8", errors="strict")
            except UnicodeError as exc:
                raise DescriptorError("Descriptor text encoding invalid") from exc
            if len(s.strip()) == 0 or "\x00" in s:
                raise DescriptorError("Descriptor text empty or contains NUL")
            if kind == 0 and not s.startswith("OPTION_TOOLTIP_"):
                raise DescriptorError("Descriptor localization identifier unexpectedly changed")
        found.append({"page_id":page,"kind":kind,"dependent":dependent})
    return found


def summarize(records, *, strict=True):
    by_page = Counter(x["page_id"] for x in records)
    by_kind = Counter(x["kind"] for x in records)
    by_dependent = Counter(x["dependent"] for x in records)
    if strict and (len(records) != ENTRY_COUNT or dict(by_page) != EXPECTED_BY_PAGE
                   or dict(by_kind) != EXPECTED_BY_KIND):
        raise DescriptorError("Original reviewed descriptor population has changed")
    return {
        "schema":1,
        "exe_sha256":KNOWN_0138_SHA,
        "version":"0.138.0",
        "table_rva":hex(TABLE_RVA),
        "record_stride_bytes":STRIDE,
        "record_count":len(records),
        "page_id_counts":{str(k):v for k,v in sorted(by_page.items())},
        "record_kinds":{"localization_key":by_kind[0],"inline_help_prose":by_kind[1],"separator":by_kind[2]},
        "dependency_flag_counts":{str(k):v for k,v in sorted(by_dependent.items())},
        "observed_page_ids":sorted(by_page),
        "special_handled_ids_without_descriptor_rows":[6,11],
        "description":"Tooltip/help configuration records used by Options; NOT a native tab/page constructor registry",
        "content_strings_exported":False,
        "runtime_abi_confirmed":False,
        "native_cheat_page_installed":False,
    }


def verify_emitter_calls(data, text):
    """Verify the two actual Options calls consuming static descriptor rows.

    These call addresses are evidence of a shared help/control renderer, not a
    confirmed Bevy entity-spawn ABI, nor a safe patch/injection location.
    """
    result = []
    for site in EMITTER_CALLS:
        b = read_rva(data, text, site, 5)
        if b[0] != 0xE8 or site + 5 + struct.unpack_from("<i",b,1)[0] != EMITTER_RVA:
            raise DescriptorError("Original Options descriptor consumer call changed")
        result.append(hex(site))
    return result


def analyze_bytes(data, sha):
    if sha != KNOWN_0138_SHA:
        raise DescriptorError("Refusing an unreviewed or older Windows executable")
    sections = read_pe_sections(data)
    rdata = section(sections, ".rdata")
    text_section = section(sections, ".text")
    calls = verify_emitter_calls(data, text_section)
    report = summarize(scan_records(data,rdata))
    report["shared_descriptor_consumer_rva"] = hex(EMITTER_RVA)
    report["verified_descriptor_consumer_calls"] = calls
    return report


def analyze_file(path):
    f = Path(path)
    if not f.is_file() or f.is_symlink() or not 1_000_000 <= f.stat().st_size <= MAX_EXE_BYTES:
        raise DescriptorError("Expected original bounded regular EXE, never a symlink")
    with f.open("rb") as fp, mmap.mmap(fp.fileno(),0,access=mmap.ACCESS_READ) as data:
        return analyze_bytes(data, hashlib.sha256(data).hexdigest())


def save_new(path, report):
    f=Path(path)
    if f.exists() or f.is_symlink() or not f.parent.is_dir() or f.parent.is_symlink():
        raise DescriptorError("Refusing to overwrite or follow a symlink")
    with f.open("x",encoding="utf8") as out:
        json.dump(report,out,indent=2,sort_keys=True)
        out.write("\n")


def main(argv=None):
    p=argparse.ArgumentParser(description="Original 0.138 Options descriptors; read-only metadata, not a patch")
    p.add_argument("--game-exe",required=True)
    p.add_argument("--out",help="New metadata JSON file; never overwrites")
    a=p.parse_args(argv)
    try:
        result=analyze_file(a.game_exe)
        if a.out: save_new(a.out,result)
        print(json.dumps(result,indent=2,sort_keys=True))
        return 0
    except (ValueError,OSError) as exc:
        print("Refused: "+str(exc),file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
