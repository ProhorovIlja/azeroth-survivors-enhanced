"""Read-only talent-family evidence from the actual original Windows EXE.

Only searches exact ASCII English localization key/value patterns.
This is NOT a version detector or a talent gameplay validator.
Memory usage is bounded by a 1 MiB block and short overlap.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWN_PROFILE = ROOT / "catalog" / "client_profiles.json"
MAX_SIZE = 1024 * 1024 * 1024

LABEL_GROUPS = {
    "legacy_demonology": ("Demonic Pact", "Summon Imp", "Summon Felguard"),
    "modern_demonology": ("Legion Gate", "Pact of the Nathrezim", "Demonic Supremacy"),
    "legacy_enhancement": ("Windfury", "Feral Spirit"),
    "modern_enhancement": ("Rockbiter Weapon", "Stormstrike", "Stormbound Echoes"),
}


def _label_bytes(name):
    return ('"' + name + '": "' + name + '"').encode("utf-8")


def fingerprint(path):
    file = Path(path)
    size = file.stat().st_size
    if size <= 0 or size > MAX_SIZE:
        raise ValueError("EXE file size outside supported scan limit")
    patterns = {name: _label_bytes(name) for names in LABEL_GROUPS.values() for name in names}
    found = set()
    sha = hashlib.sha256()
    overlap = max(len(p) for p in patterns.values()) - 1
    tail = b""
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
            data = tail + chunk
            for name, value in patterns.items():
                if name not in found and value in data:
                    found.add(name)
            tail = data[-overlap:]
    groups = {name: [n for n in names if n in found] for name, names in LABEL_GROUPS.items()}
    # A group is a usable positive hint only if all its labels are observed.
    full = {name: len(groups[name]) == len(names) for name, names in LABEL_GROUPS.items()}
    warlock = classify(full["legacy_demonology"], full["modern_demonology"])
    shaman = classify(full["legacy_enhancement"], full["modern_enhancement"])
    known = json.loads(KNOWN_PROFILE.read_text(encoding="utf-8"))["profiles"]
    digest = sha.hexdigest()
    matched = next((p["id"] for p in known if p["sha256"] == digest and p["size_bytes"] == size), None)
    return {
        "schema_version": 1,
        "sha256": digest, "size_bytes": size,
        "known_snapshot_id": matched,
        "exact_version": None, "runtime_verified": False,
        "warlock_demonology_family": warlock,
        "shaman_enhancement_family": shaman,
        "labels_found": groups,
        "labels_absence_is_not_proof": True,
        "automatic_patching_allowed": False,
    }


def classify(legacy_present, modern_present):
    if legacy_present and modern_present:
        return "mixed"
    if legacy_present:
        return "legacy_label_family"
    if modern_present:
        return "modern_label_family"
    return "unknown"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit observed English talent labels without game execution")
    parser.add_argument("--game-exe", required=True)
    parser.add_argument("--out", default=None, help="Optional local JSON report, do not publish file paths")
    parser.add_argument("--require-modern", action="store_true", help="Fail closed unless both talent families are modern")
    args = parser.parse_args(argv)
    info = fingerprint(args.game_exe)
    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Original file SHA-256:", info["sha256"])
    print("Known client snapshot:", info["known_snapshot_id"] or "unrecognized")
    print("Warlock labels:", info["warlock_demonology_family"])
    print("Shaman labels:", info["shaman_enhancement_family"])
    print("Exact game version: UNKNOWN | live talent legality: UNTESTED")
    print("No binaries were run or modified; no auto-patching permitted.")
    modern = all(info[k] == "modern_label_family" for k in (
        "warlock_demonology_family", "shaman_enhancement_family"
    ))
    if args.require_modern and not modern:
        print("FAIL CLOSED: modern browser talent routes are not verified for this Windows EXE.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
