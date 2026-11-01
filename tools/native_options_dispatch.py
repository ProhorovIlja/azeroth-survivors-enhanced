"""Conservative, read-only dissection of the reviewed Windows 0.138 Options selector.

The offsets and branch roles are evidence for static analysis only, NOT an ABI,
public menu API, injectable handler or a cheat enabler. No game execution/writes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import mmap
from pathlib import Path
import struct
import sys

from tools.native_menu_probe import read_pe_sections
from tools.native_options_xrefs import map_binary, XrefError

KNOWN_0138_SHA = 'eb5fd1c1b96e6180fcf5f3d685d90a61471af28d22e5f060c02b7b7663fbf79e'
MAX_SIZE = 300 * 1024 * 1024
# Reviewed isolated first instruction shape, not an installable patch signature.
LOAD_PAGE_SELECTOR = bytes.fromhex('41 0f b6 80 da 01 00 00')


def checked_bytes(data, section, rva, count):
    offset = rva - section['rva']
    if offset < 0 or count < 0 or offset + count > section['virtual_bytes']:
        raise XrefError('Selector instruction outside reviewed code section')
    begin = section['raw_offset'] + offset
    return bytes(data[begin:begin + count])


def decode_jcc(data, text, site):
    """Read x86 short Jcc or near Jcc target; no arbitrary code execution."""
    instr = checked_bytes(data, text, site, 6)
    if instr[:2] == b'\x0f\x84' or instr[:2] == b'\x0f\x85':
        return site + 6 + struct.unpack_from('<i', instr, 2)[0]
    if instr[0] in (0x74, 0x75):
        return site + 2 + struct.unpack_from('<b', instr, 1)[0]
    raise XrefError('Unrecognized conditional jump at recorded site')


def analyze_selector(data, sha):
    if sha != KNOWN_0138_SHA:
        raise XrefError('Only the reviewed original 0.138 EXE is supported')
    graph = map_binary(data, sha)
    text = next(s for s in read_pe_sections(data) if s['name'] == '.text')
    controls = int(graph['candidate_ui_entrypoints']['options_page_controls'], 16)
    # Locate the state-index fetch inside the single bounded Options function.
    candidate = bytes(data[text['raw_offset'] + controls - text['rva']:
                           text['raw_offset'] + controls - text['rva'] + 0x2000])
    offsets = []
    p = 0
    while True:
        found = candidate.find(LOAD_PAGE_SELECTOR, p)
        if found < 0:
            break
        offsets.append(controls + found)
        p = found + 1
    if len(offsets) != 1:
        raise XrefError('Unexpected number of page-state loads, refusing semantic inference')
    fetch = offsets[0]
    # Verify the local conditional dispatch without hard-coding portable call addresses.
    if checked_bytes(data, text, fetch + 8, 3) != b'\x83\xf8\x06':
        raise XrefError('Unexpected initial selector comparison')
    if checked_bytes(data, text, fetch + 17, 3) != b'\x83\xf8\x0b':
        raise XrefError('Unexpected Saves selector comparison')
    case_06 = decode_jcc(data, text, fetch + 11)
    case_0b = decode_jcc(data, text, fetch + 20)
    # Additional 0x0a branch is 93 bytes after the initial load in this build.
    ten = fetch + 93
    if checked_bytes(data, text, ten, 3) != b'\x83\xf8\x0a':
        raise XrefError('Expected AddOns selector comparison is missing')
    not_case_0a = decode_jcc(data, text, ten + 3)
    # These are static branch targets, not runtime Bevy state enum identities.
    if case_06 != 0x3f84ca or case_0b != 0x3f84b2 or not_case_0a != 0x3f842a:
        raise XrefError('Dispatch branch target changed: reject 0.138 candidate map')
    return {
        'schema_version': 1,
        'exe_sha256': sha,
        'version_literal': '0.138.0',
        'evidence': 'read_only_disassembled_selector_branch_structure',
        'options_function_rva': f'0x{controls:x}',
        'page_selector_field_offset': '0x1da',
        'selector_fetch_rva': f'0x{fetch:x}',
        'compared_0x06_branch_rva': f'0x{case_06:x}',
        'compared_0x0b_saves_branch_rva': f'0x{case_0b:x}',
        'compared_0x0a_nonmatching_branch_rva': f'0x{not_case_0a:x}',
        'observed_saves_value': '0x0b',
        'observed_addons_value': '0x0a',
        'bevy_selector_type_verified': False,
        'safe_write_or_hook_verified': False,
        'cheat_menu_installed': False,
        'gameplay_cheats_implemented': False,
        'note': 'Branch observations require live Windows UI state verification; do NOT modify selector memory.'
    }


def inspect_file(path):
    file = Path(path)
    if file.is_symlink() or not file.is_file() or not 1_000_000 <= file.stat().st_size <= MAX_SIZE:
        raise XrefError('Expected ordinary bounded original EXE file')
    with file.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as buf:
        return analyze_selector(buf, hashlib.sha256(buf).hexdigest())


def main(argv=None):
    p = argparse.ArgumentParser(description='Read-only 0.138 original Options selector branch audit')
    p.add_argument('--game-exe', required=True)
    p.add_argument('--out', help='New local JSON report file; no game code or content')
    args = p.parse_args(argv)
    try:
        result = inspect_file(args.game_exe)
        if args.out:
            dest = Path(args.out)
            if dest.exists() or dest.is_symlink() or not dest.parent.is_dir() or dest.parent.is_symlink():
                raise XrefError('Output must be a new file in an existing directory')
            with dest.open('x', encoding='utf-8') as writer:
                json.dump(result, writer, ensure_ascii=False, indent=2)
                writer.write('\n')
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (XrefError, OSError) as error:
        print('REFUSED:', error, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
