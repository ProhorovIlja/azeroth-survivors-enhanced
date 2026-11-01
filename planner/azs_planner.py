"""Versioned editorial build catalogue and Lua addon exporter, stdlib only."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "presets.json"
CLASSES = {"warrior", "paladin", "hunter", "rogue", "priest", "shaman", "mage", "warlock", "druid"}
STYLES = {"offense", "survival", "pets", "idle"}


def load_catalog(path=CATALOG):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("builds"), list):
        raise ValueError("Unsupported catalog schema")
    seen = set()
    for p in data["builds"]:
        if not isinstance(p, dict):
            raise ValueError("Build must be an object")
        if not isinstance(p.get("id"), str) or not re.fullmatch(r"[a-z0-9-]{3,80}", p["id"]):
            raise ValueError("Invalid build ID")
        if p["id"] in seen:
            raise ValueError("Duplicate ID: " + p["id"])
        seen.add(p["id"])
        if p.get("class") not in CLASSES:
            raise ValueError("Unknown class: " + p["id"])
        if p.get("playstyle") not in STYLES:
            raise ValueError("Unknown playstyle: " + p["id"])
        if not isinstance(p.get("spells"), list) or not isinstance(p.get("passives"), list):
            raise ValueError("Missing spell/passive list")
        if any(not isinstance(s, str) or len(s) > 120 for s in p["spells"] + p["passives"]):
            raise ValueError("Invalid spell/passive name")
        if p.get("review_status") != "unverified_editorial":
            raise ValueError("Unsupported review status")
        if not p.get("source_urls") or any(not isinstance(s, str) or not s.startswith("https://") for s in p["source_urls"]):
            raise ValueError("Missing source URLs")
        for key in ("name", "spec", "note", "last_reviewed", "baseline_game_version"):
            if not isinstance(p.get(key), str) or not p[key]:
                raise ValueError("Missing: " + key)
    return data["builds"]


def lua_q(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", " ").replace("\n", " ") + '"'


def export_addon(builds, path=ROOT / "addons" / "AZSEnhancedAdvisor" / "Presets.lua"):
    lines = ["-- Generated from catalog/presets.json. Read-only editorial hypotheses.", "AZSE_PRESETS = {"]
    for p in builds:
        fields = {
            "id": p["id"], "class": p["class"], "spec": p["spec"], "name": p["name"],
            "playstyle": p["playstyle"], "spells": ", ".join(p["spells"]),
            "passives": ", ".join(p["passives"]), "note": p["note"],
            "review_status": p["review_status"], "baseline": p["baseline_game_version"],
        }
        lines.append("  { " + ", ".join(k + " = " + lua_q(v) for k, v in fields.items()) + " },")
    lines.append("}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="AZS build catalogue (unverified)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    sub.add_parser("export-addon")
    lp = sub.add_parser("list")
    lp.add_argument("--class", dest="class_key", choices=sorted(CLASSES))
    lp.add_argument("--style", choices=sorted(STYLES))
    lp.add_argument("--limit", type=int, default=30)
    sp = sub.add_parser("show")
    sp.add_argument("id")
    args = parser.parse_args(argv)
    builds = load_catalog()
    if args.cmd == "validate":
        print(f"OK: {len(builds)} presets across {len({p['class'] for p in builds})} classes (unverified)")
        return 0
    if args.cmd == "export-addon":
        print("Wrote: " + str(export_addon(builds).relative_to(ROOT)))
        return 0
    if args.cmd == "show":
        result = next((p for p in builds if p["id"] == args.id), None)
        if not result:
            parser.error("Unknown preset")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "list":
        if args.limit < 1:
            parser.error("Limit must be >= 1")
        chosen = [p for p in builds if (not args.class_key or p["class"] == args.class_key) and (not args.style or p["playstyle"] == args.style)]
        for p in chosen[:min(args.limit, 100)]:
            print(f"{p['id']}: {p['class']} / {p['spec']} / {p['playstyle']}")
        print(f"{min(len(chosen), args.limit, 100)} shown of {len(chosen)} (all unverified)")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
