"""Read-only ZIP/RAR inventory; never extracts or executes game content."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def inventory(path, limit=30):
    path = Path(path)
    sha = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha.update(chunk)
    meta = {
        "name": path.name, "bytes": path.stat().st_size, "sha256": sha.hexdigest(),
        "format": path.suffix.lower(), "entries_total": None,
        "entries_sample": [], "safe_no_extract": True,
    }
    limit = min(max(int(limit), 0), 100)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            items = archive.infolist()
            meta["entries_total"] = len(items)
            meta["entries_sample"] = [{"name": f.filename[:180], "bytes": f.file_size} for f in items[:limit]]
    elif path.suffix.lower() == ".rar":
        try:
            import rarfile
        except ImportError:
            meta["note"] = "Install optional rarfile to inspect RAR metadata."
        else:
            try:
                with rarfile.RarFile(path) as archive:
                    items = archive.infolist()
                    meta["entries_total"] = len(items)
                    meta["entries_sample"] = [{"name": f.filename[:180], "bytes": f.file_size} for f in items[:limit]]
            except Exception as exc:
                meta["note"] = "RAR metadata unavailable: " + type(exc).__name__
    else:
        meta["note"] = "Not a recognized ZIP/RAR archive"
    return meta


def main():
    p = argparse.ArgumentParser(description="Inventory an archive without extraction")
    p.add_argument("archive")
    p.add_argument("--out", default="artifacts/archive-manifest.json")
    p.add_argument("--limit", type=int, default=30)
    args = p.parse_args()
    manifest = inventory(args.archive, args.limit)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Inventory: {manifest['bytes']} bytes; sha256 {manifest['sha256'][:16]}...; saved {target}")


if __name__ == "__main__":
    main()
