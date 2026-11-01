"""Read-only, strict-SHA comparison of two *owner-owned* Windows EXE snapshots.

No binary execution, network, raw localization text export, or automatic
changes. Report only aggregate key counts and short English talent-name
candidates from old ordered trees and newer appended Shaman patch blocks.
"""
import argparse
import json
from pathlib import Path
import sys

from tools.extract_talent_names import (
    decode_english_map, extract, find_anchor_and_hash, KNOWN_SHAS
)


def describe(path):
    sha, offset = find_anchor_and_hash(path)
    if sha not in KNOWN_SHAS:
        raise ValueError("Unknown original EXE SHA-256; refuse comparison")
    mapping = decode_english_map(path, offset)
    inventory = extract(path)
    return mapping, inventory


def compare_inventories(old_inventory, new_inventory, old_locale, new_locale):
    old_sha = old_inventory["client_sha256"]
    new_sha = new_inventory["client_sha256"]
    if old_sha == new_sha:
        # This is allowed for users who want to confirm a no-op update.
        no_version_change = True
    else:
        no_version_change = False
    old_labels, new_labels = set(old_locale), set(new_locale)
    changed_values = sum(old_locale[k] != new_locale[k] for k in old_labels & new_labels)
    # The ordered tree snapshot may be retained in binaries even after a
    # live game talent rework. Never call it "current active talent tree".
    old_trees = old_inventory.get("classes", {})
    new_trees = new_inventory.get("classes", {})
    identical_legacy_names = old_trees == new_trees
    old_patch = set(old_inventory.get("patch_overlay", {})
                    .get("shaman", {}).get("Enhancement", []))
    new_patch = set(new_inventory.get("patch_overlay", {})
                    .get("shaman", {}).get("Enhancement", []))
    new_total = sum(len(names) for trees in new_trees.values() for names in trees.values())
    old_total = sum(len(names) for trees in old_trees.values() for names in trees.values())
    return {
        "comparison_type": "read_only_embedded_English_dictionary",
        "old_exe_sha256": old_sha, "new_exe_sha256": new_sha,
        "same_executable": no_version_change,
        "old_dictionary_keys": len(old_labels),
        "new_dictionary_keys": len(new_labels),
        "added_dictionary_keys": len(new_labels - old_labels),
        "removed_dictionary_keys": len(old_labels - new_labels),
        "changed_retained_dictionary_values": changed_values,
        "old_ordered_tree_candidates": old_total,
        "new_ordered_tree_candidates": new_total,
        "older_ordered_tree_names_unchanged": identical_legacy_names,
        "old_shaman_appended_name_count": len(old_patch),
        "new_shaman_appended_name_count": len(new_patch),
        "shaman_appended_names_added": sorted(new_patch - old_patch),
        "shaman_appended_names_removed": sorted(old_patch - new_patch),
        "warning": "Text-layer delta only; old embedded names may be stale. This does NOT verify active talent trees, ranks, combat mechanics, client safety or FPS.",
        "gameplay_verified": False, "binary_modified": False,
    }


def compare_paths(old, new):
    old_map, old_inv = describe(old)
    new_map, new_inv = describe(new)
    return compare_inventories(old_inv, new_inv, old_map, new_map)


def main(argv=None):
    p = argparse.ArgumentParser(description="Compare private original Windows EXEs, without running them")
    p.add_argument("--old-exe", required=True)
    p.add_argument("--new-exe", required=True)
    p.add_argument("--out", help="Optional metadata-only JSON report; no original game text included")
    args = p.parse_args(argv)
    try:
        report = compare_paths(args.old_exe, args.new_exe)
        if args.out:
            path = Path(args.out)
            if path.exists() or path.is_symlink() or not path.parent.is_dir():
                raise ValueError("Refusing to overwrite report; parent folder must exist")
            with path.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print("REFUSED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
