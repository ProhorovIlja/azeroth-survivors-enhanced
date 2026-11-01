"""Historical community build evidence; not a build legality or DPS validator."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "catalog" / "community_examples.json"
VALID_CLASSES = {"warrior", "paladin", "hunter", "rogue", "priest", "shaman", "mage", "warlock", "druid"}


def load_examples(path=DATA):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if obj.get("schema_version") != 1 or not isinstance(obj.get("examples"), list):
        raise ValueError("Unsupported community example schema")
    seen = set()
    for item in obj["examples"]:
        key = item.get("id")
        if not isinstance(key, str) or not key or key in seen:
            raise ValueError("Invalid or repeated community example ID")
        seen.add(key)
        if item.get("class") not in VALID_CLASSES:
            raise ValueError("Unknown class")
        split = item.get("talent_split")
        if not isinstance(split, dict) or len(split) != 3:
            raise ValueError("Expected three named talent trees")
        if any(not isinstance(k, str) or not k or not isinstance(v, int) or isinstance(v, bool) or v < 0 for k, v in split.items()):
            raise ValueError("Bad talent point allocation")
        total = sum(split.values())
        if item.get("points_recorded") != total or total > 51:
            raise ValueError("Talent split count mismatch or exceeds 51")
        if item.get("ranked_for_current_client") is not False:
            raise ValueError("Cannot promote historical builds without testing")
        if item.get("primary_source_verified") is not False:
            raise ValueError("Claimed direct evidence without audited primary source")
        if not isinstance(item.get("source_url"), str) or not item["source_url"].startswith("https://"):
            raise ValueError("Missing source link")
        if not isinstance(item.get("known_obsolescence"), str) or not item["known_obsolescence"]:
            raise ValueError("Missing patch caveat")
    return obj["examples"]


def main(argv=None):
    p = argparse.ArgumentParser(description="Version-aware historical community build examples")
    p.add_argument("action", choices=["validate", "list"], nargs="?", default="list")
    p.add_argument("--class", dest="class_key", choices=sorted(VALID_CLASSES))
    p.add_argument("--limit", type=int, default=15)
    args = p.parse_args(argv)
    builds = load_examples()
    if args.action == "validate":
        print(f"OK: {len(builds)} historical player examples; none certified for owner EXE")
        return 0
    matches = [x for x in builds if not args.class_key or x["class"] == args.class_key]
    for x in matches[:max(0, min(args.limit, 30))]:
        version = x["observed_client_version"] or "UNKNOWN"
        print(f"{x['id']} | {x['points_recorded']}/51 points | game {version} | NOT CURRENTLY VERIFIED")
        print(f"  PATCH WARNING: {x['known_obsolescence'][:180]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
