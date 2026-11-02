"""Temporary original Windows 0.139 EXE for *local* native SHA-gate CI.

The original executable is proprietary. Restore only to an explicit, fresh
GitHub Actions runner TEMP path, verify full official SHA/size, pass path to
the native verifier test, and delete it in the calling workflow finally block.
No executable, binary bytes, patches or MPQs are ever committed/uploaded.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.ephemeral_client_audit import (
    AuditError, client, download_verified, read_manifest, validate,
    SHA, SIZE, VERSION,
)


def restore_pinned_original(out: Path):
    if not out.is_absolute() or out.name.lower() not in (
        "azse-original-0139-positive-test.exe",
    ):
        raise AuditError("Only an explicit temporary original-test basename is accepted")
    if out.exists() or out.is_symlink():
        raise AuditError("Refuse existing or redirected destination")
    if not out.parent.is_dir() or out.parent.is_symlink():
        raise AuditError("Refuse missing or redirected temporary directory")
    opener = client()
    ordered_parts = validate(read_manifest(opener))
    result = download_verified(ordered_parts, out, opener)
    if result["sha256"] != SHA or result["size"] != SIZE:
        out.unlink(missing_ok=True)
        raise AuditError("Original client identity unexpectedly mismatched")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Temp exact-SHA original client for native Windows identity test")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    info = restore_pinned_original(args.out)
    # Path intentionally not printed to keep logs free of private paths.
    print(json.dumps({"official_version": VERSION, "sha256": info["sha256"],
                      "bytes": info["size"], "genuine_client_executed": False,
                      "game_files_published": False, "temporary_original_only": True},
                     sort_keys=True))


if __name__ == "__main__":
    main()
