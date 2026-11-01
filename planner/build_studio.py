"""Build Studio: exact-client, source-only draft planner with checked share codes.

A name appearing in the user's binary does NOT establish talent legality,
prerequisites, max ranks or a competitive build. Nothing here modifies a game.
No cloud/network calls; all outputs are opt-in local files.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import sys
import zlib

from tools.extract_talent_names import extract

MAX_JSON_BYTES = 24_000
MAX_CODE_CHARS = 12_000
SHARE_PREFIX = "AZSE3:"
VERSION = 1
SHA_PATTERN = re.compile(r"^[0-9a-f]{64}$")
TEXT_MAX = 200
MAX_ITEMS = 64
VALID_STYLES = {"experimental", "low_input_minions", "farming", "damage", "survival", "bosses"}


class BuildError(ValueError):
    pass


def canonical(payload):
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def bounded_json(path):
    p = Path(path)
    if not p.is_file() or p.stat().st_size > MAX_JSON_BYTES:
        raise BuildError("Build JSON missing or too large")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise BuildError("Malformed UTF-8 JSON build") from exc


def limited_text(s, label, maxlen=TEXT_MAX, empty_ok=False):
    if not isinstance(s, str) or (not s and not empty_ok) or len(s) > maxlen or any(ord(c) < 32 for c in s):
        raise BuildError("Invalid text field: " + label)
    return s


def validate_schema(build):
    if not isinstance(build, dict) or build.get("schema_version") != VERSION:
        raise BuildError("Unsupported build schema")
    # No executable code, files, URLs or inherited arbitrary maps.
    allowed = {"schema_version","client_sha256","name","class","race","style","talents",
               "spells","passives","gear","notes","evidence_level","legal_tree_verified"}
    if set(build) != allowed:
        raise BuildError("Missing or unknown build fields")
    if not isinstance(build["client_sha256"], str) or not SHA_PATTERN.fullmatch(build["client_sha256"]):
        raise BuildError("Invalid exact-client SHA-256")
    limited_text(build["name"], "name", 100)
    limited_text(build["class"], "class", 40)
    limited_text(build["race"], "race", 60, empty_ok=True)
    limited_text(build["notes"], "notes", 700, empty_ok=True)
    if build["style"] not in VALID_STYLES:
        raise BuildError("Unknown play style")
    if build["evidence_level"] != "name_only_unverified" or build["legal_tree_verified"] is not False:
        raise BuildError("This early Build Studio cannot certify gameplay or legality")
    for field in ("talents","spells","passives"):
        if not isinstance(build[field], list) or len(build[field]) > MAX_ITEMS:
            raise BuildError("Oversized list: " + field)
    for field in ("spells","passives"):
        if any(not isinstance(x, str) for x in build[field]):
            raise BuildError("Bad " + field + " entry")
        for item in build[field]:
            limited_text(item, field, 120)
    if not isinstance(build["gear"], dict) or set(build["gear"]) != {"rings", "trinkets", "amulet"}:
        raise BuildError("Gear must have rings/trinkets/amulet fields")
    for category, values in build["gear"].items():
        if not isinstance(values, list) or len(values) > 12:
            raise BuildError("Invalid gear list: " + category)
        for item in values:
            limited_text(item, category, 120)
    chosen = set()
    for item in build["talents"]:
        if not isinstance(item, dict) or set(item) != {"tree","name","points"}:
            raise BuildError("Invalid talent selection")
        tree = limited_text(item["tree"], "tree", 50)
        name = limited_text(item["name"], "talent", 100)
        points = item["points"]
        if type(points) is not int or not 1 <= points <= 51:
            raise BuildError("Talent points must be integers between 1 and 51")
        if (tree, name) in chosen:
            raise BuildError("Repeated talent selection")
        chosen.add((tree,name))
    if len(canonical(build)) > MAX_JSON_BYTES:
        raise BuildError("Build payload exceeds size budget")
    return build


def validate_against_inventory(build, inventory, budget=51):
    validate_schema(build)
    if build["client_sha256"] != inventory.get("client_sha256"):
        raise BuildError("CLIENT MISMATCH: build was authored for a different EXE")
    classes = inventory.get("classes")
    if not isinstance(classes, dict) or build["class"] not in classes:
        raise BuildError("Class not found in this exact client")
    trees = classes[build["class"]]
    for talent in build["talents"]:
        if talent["tree"] not in trees or talent["name"] not in trees[talent["tree"]]:
            raise BuildError("Talent not observed in selected class/tree: " + talent["name"])
    total = sum(item["points"] for item in build["talents"])
    if total > budget:
        raise BuildError("Points exceed assumed research budget; legality still unknown")
    return {
        "status": "NAME_CHECK_ONLY",
        "client_sha256": build["client_sha256"],
        "class": build["class"],
        "talents_observed": len(build["talents"]),
        "points_requested": total,
        "assumed_budget": budget,
        "points_and_prerequisites_verified": False,
        "legal_build_verified": False,
        "performance_measured": False,
        "ready_to_apply_automatically": False,
    }


def make_draft(inventory, cls, title="Experimental build", style="experimental"):
    classes = inventory.get("classes", {})
    if cls not in classes:
        raise BuildError("Unknown class in exact client: " + cls)
    if style not in VALID_STYLES:
        raise BuildError("Unknown style")
    build = {
        "schema_version": VERSION,
        "client_sha256": inventory["client_sha256"],
        "name": title,
        "class": cls,
        "race": "",
        "style": style,
        "talents": [],
        "spells": [],
        "passives": [],
        "gear": {"rings": [], "trinkets": [], "amulet": []},
        "notes": "Research-only draft. Verify talent ranks, dependencies, gear and combat in the exact original game.",
        "evidence_level": "name_only_unverified",
        "legal_tree_verified": False,
    }
    return validate_schema(build)


def encode(build):
    validate_schema(build)
    raw = canonical(build)
    packed = zlib.compress(raw, level=9)
    check = hashlib.sha256(raw).hexdigest()[:16]
    return SHARE_PREFIX + base64.urlsafe_b64encode(packed).decode("ascii").rstrip("=") + "." + check


def decode(code):
    if not isinstance(code, str) or not code.startswith(SHARE_PREFIX) or len(code) > MAX_CODE_CHARS:
        raise BuildError("Invalid AZSE3 share code")
    token = code[len(SHARE_PREFIX):]
    parts = token.split(".")
    if len(parts) != 2 or not re.fullmatch(r"[A-Za-z0-9_-]+", parts[0]) or not re.fullmatch(r"[a-f0-9]{16}", parts[1]):
        raise BuildError("Malformed share code")
    try:
        packed = base64.b64decode(parts[0] + "=" * (-len(parts[0]) % 4), altchars=b"-_", validate=True)
        decompress = zlib.decompressobj()
        raw = decompress.decompress(packed, MAX_JSON_BYTES + 1)
        if len(raw) > MAX_JSON_BYTES or decompress.unconsumed_tail or not decompress.eof or decompress.unused_data:
            raise BuildError("Share code payload exceeds bounds or has trailing data")
        raw += decompress.flush(MAX_JSON_BYTES + 1 - len(raw))
        if len(raw) > MAX_JSON_BYTES:
            raise BuildError("Oversized expanded share code")
        if hashlib.sha256(raw).hexdigest()[:16] != parts[1]:
            raise BuildError("Share code checksum mismatch")
        build = json.loads(raw.decode("utf-8"))
        validate_schema(build)
        if canonical(build) != raw:
            raise BuildError("Non-canonical share code rejected")
        return build
    except (ValueError, UnicodeError, zlib.error) as exc:
        if isinstance(exc, BuildError):
            raise
        raise BuildError("Cannot decode or verify share code") from exc


def save_new(path, build):
    data = json.dumps(validate_schema(build), ensure_ascii=False, indent=2) + "\n"
    output = Path(path)
    if output.is_symlink() or output.exists():
        raise BuildError("Output exists or is a symlink; refusing overwrite")
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise BuildError("Output folder must exist and not be a symlink")
    try:
        with output.open("x", encoding="utf-8") as stream:
            stream.write(data)
    except OSError as exc:
        raise BuildError("Cannot create output file") from exc
    return output


def main(argv=None):
    p = argparse.ArgumentParser(description="Exact-client Build Studio: draft/edit/import/share, no game modifications")
    sp = p.add_subparsers(dest="action", required=True)
    make = sp.add_parser("init", help="Create a blank class-verified draft for exact Windows EXE")
    make.add_argument("--game-exe", required=True)
    make.add_argument("--class", dest="class_name", required=True)
    make.add_argument("--name", default="Experimental build")
    make.add_argument("--style", choices=sorted(VALID_STYLES), default="experimental")
    make.add_argument("--out", required=True)
    check = sp.add_parser("validate", help="Verify name presence in correct tree for the exact EXE")
    check.add_argument("--game-exe", required=True)
    check.add_argument("--build", required=True)
    export = sp.add_parser("encode", help="Make a compact, checksummed share code, no network")
    export.add_argument("--build", required=True)
    export.add_argument("--game-exe", required=True)
    imp = sp.add_parser("decode", help="Decode share code into a new draft; revalidate before use")
    imp.add_argument("--code", required=True)
    imp.add_argument("--out", required=True)
    try:
        if args := p.parse_args(argv):
            if args.action == "init":
                inv = extract(args.game_exe)
                result = make_draft(inv, args.class_name, args.name, args.style)
                print("Created unverified draft at", save_new(args.out, result))
                return 0
            if args.action == "decode":
                result = decode(args.code)
                print("Decoded as unverified draft at", save_new(args.out, result))
                print("Re-run validate with the owner's EXE before using this build.")
                return 0
            build = bounded_json(args.build)
            inv = extract(args.game_exe)
            report = validate_against_inventory(build, inv)
            if args.action == "validate":
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 0
            print(encode(build))
            return 0
    except (BuildError, ValueError, OSError) as exc:
        print("REFUSED: " + str(exc), file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
