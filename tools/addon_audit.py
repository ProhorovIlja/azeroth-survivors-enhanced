"""Read-only addon catalog and HUD conflict check for the *local* game folder.

Only inspects names and bounded plain text .toc metadata. Never executes Lua,
installs content, downloads files or changes addon settings.
"""
import argparse
import json
from pathlib import Path
import re
import sys

HUD = frozenset({"survivorsdragonui", "nfui", "bordoui", "keijinui", "survivorui", "survivor-ui", "blackwellui"})
CURSOR = frozenset({"azcursor", "azerothcursor", "bigcursor", "cursorreticle"})
METER = frozenset({"azsspellmeter", "azsmaxhit", "shagudps", "statoverlayas"})
MAX_TOC_BYTES = 128 * 1024
MAX_ADDONS = 256


class AuditError(ValueError):
    pass


def scan(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise AuditError("Expected a non-symlink game directory")
    location = root / "benilla-config" / "AddOns"
    if location.is_symlink():
        raise AuditError("Refusing a symlinked AddOns directory")
    if not location.is_dir():
        return {"installed_addon_folders": 0, "entries": [],
                "warnings": ["No benilla-config/AddOns directory found"],
                "game_files_modified": False}
    entries = []
    for folder in sorted(location.iterdir(), key=lambda x: x.name.lower()):
        if folder.is_symlink():
            raise AuditError("Symlinked addon directory: " + folder.name)
        if not folder.is_dir():
            continue
        if len(entries) >= MAX_ADDONS:
            raise AuditError("Too many addon directories")
        toc = folder / (folder.name + ".toc")
        if toc.is_symlink():
            raise AuditError("Symlinked .toc file")
        if not toc.is_file():
            entries.append({"folder": folder.name, "recognized_toc": False,
                            "warning": "Matching .toc not found; addon might not load"})
            continue
        if toc.stat().st_size > MAX_TOC_BYTES:
            raise AuditError("Oversized TOC file")
        metadata = {}
        for line in toc.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            match = re.fullmatch(r"##\s*([A-Za-z][A-Za-z ]{0,40})\s*:\s*(.*)", line)
            if match:
                metadata[match.group(1).strip().lower()] = match.group(2).strip()[:200]
        entries.append({"folder": folder.name, "recognized_toc": True,
                        "interface": metadata.get("interface"),
                        "title": metadata.get("title"),
                        "version": metadata.get("version"),
                        "interface_11200": metadata.get("interface") == "11200"})
    warnings = []
    installed = {item["folder"].lower() for item in entries if item.get("recognized_toc")}
    for group, members in (("HUD replacements", HUD), ("cursor modifiers", CURSOR), ("damage meters", METER)):
        found = sorted(installed & members)
        if len(found) > 1:
            warnings.append("Potential " + group + " overlap: " + ", ".join(found))
    for entry in entries:
        if entry.get("recognized_toc") and not entry["interface_11200"]:
            warnings.append("Verify Interface 11200 compatibility: " + entry["folder"])
        if not entry.get("recognized_toc"):
            warnings.append("Missing matching TOC: " + entry["folder"])
    return {"installed_addon_folders": len(entries), "entries": entries,
            "warnings": warnings, "active_addons_verified": False,
            "game_files_modified": False}


def main(argv=None):
    p = argparse.ArgumentParser(description="Read-only Azeroth Survivors addon inventory")
    p.add_argument("--game-root", required=True)
    args = p.parse_args(argv)
    try:
        print(json.dumps(scan(args.game_root), indent=2, ensure_ascii=False))
        return 0
    except (AuditError, OSError) as exc:
        print("REFUSED:", str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
