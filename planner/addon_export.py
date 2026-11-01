"""Offline export of an exact-client, unverified Build Studio draft to Lua 5.0.

Produces a new local file that can replace the advisor's Presets.lua in
a *separate test copy*. Never installs anything or changes the game.
All Lua strings are quoted; no Lua execution or eval is involved.
"""
import argparse
import json
from pathlib import Path
import sys

from planner.build_studio import BuildError, bounded_json, validate_against_inventory
from tools.extract_talent_names import extract


def lua_quote(value):
    if not isinstance(value, str):
        raise BuildError("Only plain string Lua fields are supported")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n") + '"'


def as_preset(build, inventory):
    validate_against_inventory(build, inventory)
    tallies = {}
    for x in build["talents"]:
        tallies[x["tree"]] = tallies.get(x["tree"], 0) + x["points"]
    dominant = sorted(tallies.items(), key=lambda x: (-x[1], x[0]))
    spec = dominant[0][0] if dominant else "Undecided"
    detail = ", ".join(x["name"] + " " + str(x["points"]) for x in build["talents"][:5])
    if len(build["talents"]) > 5:
        detail += ", ..."
    note = "NAME-ONLY, NOT LEGALITY-TESTED. "
    if detail:
        note += "Talents: " + detail + ". "
    note += build["notes"][:170]
    return {
        "id": "custom-name-only",
        "class": build["class"],
        "spec": spec,
        "name": build["name"],
        "playstyle": "idle" if build["style"] == "low_input_minions" else build["style"],
        "spells": ", ".join(build["spells"][:6]) or "(not specified)",
        "passives": ", ".join(build["passives"][:6]) or "(not specified)",
        "note": note[:420],
        "review_status": "name_only_unverified",
        "baseline": "EXE SHA-256 " + build["client_sha256"][:16] + "... | version UNKNOWN",
    }


def to_lua(build, inventory):
    preset = as_preset(build, inventory)
    keys = ("id","class","spec","name","playstyle","spells","passives","note","review_status","baseline")
    rows = [
        "-- AZSEnhancedAdvisor generated single research draft (Lua 5.0 compatible).",
        "-- WARNING: name presence checked; ranks/prerequisites/performance unverified.",
        "AZSE_PRESETS = {",
        "  { " + ", ".join(x + " = " + lua_quote(preset[x]) for x in keys) + " },",
        "}",
        "",
    ]
    return "\n".join(rows)


def save_lua(path, text):
    out = Path(path)
    if out.is_symlink() or out.exists():
        raise BuildError("Destination exists/symlink: refusal to overwrite existing Lua or other files")
    if not out.parent.is_dir() or out.parent.is_symlink():
        raise BuildError("Create an ordinary output folder first")
    try:
        with out.open("x", encoding="utf-8") as stream:
            stream.write(text)
    except OSError as exc:
        raise BuildError("Could not write local Lua output") from exc
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Export a checked, UNVERIFIED build to Lua advisor source")
    ap.add_argument("--game-exe", required=True)
    ap.add_argument("--build", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        build = bounded_json(a.build)
        inv = extract(a.game_exe)
        code = to_lua(build, inv)
        print("Draft-only Lua exported:", save_lua(a.out, code))
        print("Replace Presets.lua manually only in a TEST COPY; reinstall with explicit consent.")
        return 0
    except (BuildError, OSError, ValueError) as exc:
        print("REFUSED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
