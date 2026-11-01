"""Private, read-only talent NAME index from the owner's exact Windows EXE.

This tool does not export game prose/descriptions or assets to GitHub.
It is version-gated to the observed owner SHA-256, and cannot infer ranks,
leveling order, prerequisites or whether talents function in-game.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWN_SHA = "2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a"
ENGLISH_ANCHOR = b'{\n  "game.title": "Azeroth Survivors"'
CHUNK = 1024 * 1024
MAX_JSON = 512 * 1024
MAX_FILE = 1024 * 1024 * 1024

# Ordered name boundaries observed in this exact EXE only. Some tree
# headers (Holy, Protection, Restoration) share English strings and
# appear just once in the source dictionary, so a later tree's first
# talent is an explicit boundary. Revalidate for every new binary.
TREE_SECTIONS = [
    ("warrior", "Arms", "Arms", "Fury", False),
    ("warrior", "Fury", "Fury", "Protection", False),
    ("warrior", "Protection", "Protection", "Holy", False),
    ("paladin", "Holy", "Holy", "Improved Devotion Aura", False),
    ("paladin", "Protection", "Improved Devotion Aura", "Retribution", True),
    ("paladin", "Retribution", "Retribution", "Beast Mastery", False),
    ("hunter", "Beast Mastery", "Beast Mastery", "Marksmanship", False),
    ("hunter", "Marksmanship", "Marksmanship", "Survival", False),
    ("hunter", "Survival", "Survival", "Assassination", False),
    ("rogue", "Assassination", "Assassination", "Combat", False),
    ("rogue", "Combat", "Combat", "Subtlety", False),
    ("rogue", "Subtlety", "Subtlety", "Discipline", False),
    ("priest", "Discipline", "Discipline", "Holy Specialization", False),
    ("priest", "Holy", "Holy Specialization", "Shadow", True),
    ("priest", "Shadow", "Shadow", "Elemental", False),
    ("shaman", "Elemental", "Elemental", "Enhancement", False),
    ("shaman", "Enhancement", "Enhancement", "Restoration", False),
    ("shaman", "Restoration", "Restoration", "Arcane", False),
    ("mage", "Arcane", "Arcane", "Fire", False),
    ("mage", "Fire", "Fire", "Frost", False),
    ("mage", "Frost", "Frost", "Affliction", False),
    ("warlock", "Affliction", "Affliction", "Demonology", False),
    ("warlock", "Demonology", "Demonology", "Destruction", False),
    ("warlock", "Destruction", "Destruction", "Balance", False),
    ("druid", "Balance", "Balance", "Feral Combat", False),
    ("druid", "Feral Combat", "Feral Combat", "Improved Mark of the Wild", False),
    ("druid", "Restoration", "Improved Mark of the Wild", "Wolf", True),
]


def find_anchor_and_hash(path):
    file = Path(path)
    if not file.is_file() or not (0 < file.stat().st_size <= MAX_FILE):
        raise ValueError("Expected bounded original Windows game EXE file")
    sha = hashlib.sha256()
    start = None
    offset = 0
    tail = b""
    with file.open("rb") as source:
        for block in iter(lambda: source.read(CHUNK), b""):
            sha.update(block)
            sample = tail + block
            if start is None:
                pos = sample.find(ENGLISH_ANCHOR)
                if pos >= 0:
                    start = offset - len(tail) + pos
            offset += len(block)
            tail = sample[-(len(ENGLISH_ANCHOR) - 1):]
    return sha.hexdigest(), start


def decode_english_map(path, anchor_offset):
    if anchor_offset is None:
        raise ValueError("English game localization anchor not found")
    with Path(path).open("rb") as source:
        source.seek(anchor_offset)
        raw = source.read(MAX_JSON)
    # JSON ends well before the end of the bounded buffer.
    # bytes after the JSON may be arbitrary binary, so only decode
    # valid UTF-8 up to the first invalid byte.
    text = raw.decode("utf-8", errors="ignore")
    try:
        mapping, end = json.JSONDecoder().raw_decode(text)
    except ValueError as exc:
        raise ValueError("Unable to parse embedded game localization as JSON") from exc
    if (not isinstance(mapping, dict) or mapping.get("game.title") != "Azeroth Survivors"
            or len(mapping) < 500 or end < 10000):
        raise ValueError("Unrecognized or incomplete localization dictionary")
    return mapping


def is_short_talent_label(key, value):
    if not isinstance(key, str) or value != key:
        return False
    if not (2 <= len(key) <= 48) or len(key.split()) > 6:
        return False
    if any(ch in key for ch in (".", "!", "?", "{", "}", "%", "\n")):
        return False
    return True


def build_index(mapping):
    keys = list(mapping.keys())
    trees = {}
    for cls, tree, first, next_name, include_first in TREE_SECTIONS:
        try:
            a = keys.index(first)
            b = keys.index(next_name, a + 1)
        except ValueError as exc:
            raise ValueError(f"Tree section changed: {cls}/{tree}") from exc
        if a >= b:
            raise ValueError("Invalid ordered tree boundaries")
        candidates = keys[a if include_first else a + 1:b]
        names = [k for k in candidates if is_short_talent_label(k, mapping[k])]
        if not 7 <= len(names) <= 20 or len(names) != len(set(names)):
            raise ValueError(f"Unexpected candidate count for {cls}/{tree}: {len(names)}")
        trees.setdefault(cls, {})[tree] = names
    if len(trees) != 9 or sum(map(len, trees.values())) != 27:
        raise ValueError("Expected 9 classes / 27 tree sections")
    return trees


def extract(path):
    digest, start = find_anchor_and_hash(path)
    if digest != KNOWN_SHA:
        raise ValueError("Unknown executable SHA-256; refuse to reuse original-client tree boundary assumptions")
    mapping = decode_english_map(path, start)
    trees = build_index(mapping)
    return {
        "schema_version": 1,
        "client_sha256": digest,
        "client_version": None,
        "source": "owner Windows EXE, embedded English localization names",
        "runtime_verified": False, "points_and_prerequisites_known": False,
        "classes": trees,
        "counts_are_heuristic": True,
        "caution": "Name candidates only, not a verified ability graph, max-rank map or build",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract only talent names locally; do not publish game text")
    parser.add_argument("--game-exe", required=True)
    parser.add_argument("--class", dest="class_name")
    parser.add_argument("--out", help="Local-only JSON output; never commit original game data")
    args = parser.parse_args(argv)
    data = extract(args.game_exe)
    if args.class_name:
        if args.class_name not in data["classes"]:
            parser.error("Unknown class")
        data["classes"] = {args.class_name: data["classes"][args.class_name]}
    n = sum(len(v) for d in data["classes"].values() for v in d.values())
    tree_count = sum(len(d) for d in data["classes"].values())
    print(f"Detected {len(data['classes'])} classes, {tree_count} tree sections, {n} short talent-name candidates")
    print("Exact point costs, prerequisites and runtime behavior NOT VERIFIED")
    for cls, trees in data["classes"].items():
        print(cls + ": " + ", ".join(t + " (" + str(len(names)) + ")" for t, names in trees.items()))
    if args.out:
        dest = Path(args.out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Private name-only index written:", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
