"""Safe, read-only fingerprint of the original Aethus Windows client.

Never launches executables, modifies files, extracts game content or assumes
that finding a symbol proves an API works. Stdlib only.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

OWNER_EXE_SHA256 = "2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a"
TOKENS = (b"AZS_GetPhase", b"AZS_GetMeter", b"benilla-config", b"wenilla-rogue")
MAX_EXE_BYTES = 1024 * 1024 * 1024


def digest_file(path):
    """Compute SHA-256 with bounded memory."""
    sha = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def has_tokens(path, tokens=TOKENS):
    """Bounded binary string scan across chunk boundaries."""
    found = set()
    overlap = max(map(len, tokens)) - 1
    tail = b""
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            data = tail + block
            for token in tokens:
                if token in data:
                    found.add(token)
            tail = data[-overlap:] if overlap else b""
    return [t.decode("ascii") for t in tokens if t in found]


def inspect_exe(path):
    path = Path(path)
    size = path.stat().st_size
    if size > MAX_EXE_BYTES:
        raise ValueError("Refusing unusually large EXE for preliminary inspection")
    with path.open("rb") as stream:
        header = stream.read(4096)
        if len(header) < 0x40 or header[:2] != b"MZ":
            raise ValueError("Not a valid MZ executable header")
        pe_offset = struct.unpack_from("<I", header, 0x3C)[0]
        if pe_offset > 1024 * 1024 or pe_offset + 26 > size:
            raise ValueError("Invalid PE header offset")
        stream.seek(pe_offset)
        pe = stream.read(26)
        if len(pe) < 26 or pe[:4] != b"PE\x00\x00":
            raise ValueError("PE signature not found")
        machine = struct.unpack_from("<H", pe, 4)[0]
        magic = struct.unpack_from("<H", pe, 24)[0]
    digest = digest_file(path)
    return {
        "name": path.name,
        "size_bytes": size,
        "sha256": digest,
        "format": "PE32+" if magic == 0x20B else ("PE32" if magic == 0x10B else "unknown"),
        "machine": f"0x{machine:04x}",
        "matched_expected_owner_snapshot": digest == OWNER_EXE_SHA256,
        "exact_game_version": None,
        "api_strings_present": has_tokens(path),
        "runtime_api_verified": False,
        "safe_to_patch_automatically": False,
    }


def inspect_mpq(path, hash_contents=False):
    """Read only 32-byte header and optional SHA-256. No file extraction."""
    path = Path(path)
    size = path.stat().st_size
    with path.open("rb") as stream:
        data = stream.read(32)
    if len(data) < 32 or data[:4] != b"MPQ\x1a":
        raise ValueError("Invalid MPQ header: " + path.name)
    header_size, archive_size, fmt, block_shift, h_off, b_off, h_count, b_count = struct.unpack_from(
        "<IIHHIIII", data, 4
    )
    if (header_size < 32 or archive_size > size or archive_size < header_size
            or h_count > 2_000_000 or b_count > 2_000_000
            or h_off + 16 * h_count > archive_size
            or b_off + 16 * b_count > archive_size):
        raise ValueError("MPQ header structural bounds failed: " + path.name)
    result = {
        "name": path.name, "size_bytes": size, "format_version": fmt,
        "archive_bytes": archive_size, "hash_entries": h_count,
        "block_entries": b_count, "header_structurally_plausible": True,
        "files_extracted": 0,
    }
    if hash_contents:
        result["sha256"] = digest_file(path)
    return result


def inspect_game(root, all_mpq=False):
    root = Path(root).resolve()
    client = root / "AzerothSurvivors.exe"
    if not client.is_file():
        raise FileNotFoundError("AzerothSurvivors.exe not found at specified root")
    report = {
        "schema_version": 1, "operation": "read_only_preflight",
        "executed_client": False, "modified_client": False, "version_verified": False,
        "exe": inspect_exe(client), "mpq": [],
        "verdict": "REVIEW_REQUIRED: hash alone never certifies runtime compatibility",
    }
    data = root / "Data"
    if all_mpq and data.is_dir():
        for path in sorted(data.iterdir()):
            if path.is_file() and path.suffix.lower() == ".mpq":
                report["mpq"].append(inspect_mpq(path, hash_contents=True))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Safe local original game fingerprint (no execution)")
    parser.add_argument("--game-root", required=True)
    parser.add_argument("--all-mpq", action="store_true", help="Hash all MPQs; slower")
    parser.add_argument("--expected-sha", help="Require exact expected EXE SHA-256")
    parser.add_argument("--out", help="Write local JSON report (keep it private)")
    args = parser.parse_args(argv)
    data = inspect_game(args.game_root, args.all_mpq)
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    x = data["exe"]
    print("EXE SHA256:", x["sha256"])
    print("PE:", x["machine"], x["format"], "| owner snapshot match:", x["matched_expected_owner_snapshot"])
    print("MPQs indexed:", len(data["mpq"]), "| actual game version: unverified")
    print("VERDICT: human review required; no files modified")
    if args.expected_sha and x["sha256"].lower() != args.expected_sha.lower():
        print("HASH MISMATCH: refuse any automated patch step")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
