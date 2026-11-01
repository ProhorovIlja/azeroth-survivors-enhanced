"""Validate and summarize a curated, version-dated upstream discovery registry.

No network access or package installation. A source being in this list does
not establish compatibility, security, permission to redistribute or support.
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "catalog" / "upstreams.json"
STATUSES = {"permissive", "copyleft", "restricted", "no_license_found", "unknown"}
RISKS = {"low", "medium", "high", "critical"}
INSTALLS = {
    "lua_addon", "native_companion", "mpq_native_mod", "native_overlay",
    "reference_only", "standalone_tool",
}


def load_registry(path=REGISTRY):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("sources"), list):
        raise ValueError("Unsupported registry schema")
    found = set()
    for item in data["sources"]:
        repo = item.get("repo")
        if not isinstance(repo, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise ValueError("Invalid repo")
        if repo.lower() in found:
            raise ValueError("Duplicate repository: " + repo)
        found.add(repo.lower())
        if item.get("url") != "https://github.com/" + repo:
            raise ValueError("Unverified repository URL shape")
        if item.get("license_status") not in STATUSES:
            raise ValueError("Unknown license status: " + repo)
        if item.get("risk") not in RISKS:
            raise ValueError("Unknown risk class: " + repo)
        if item.get("install_type") not in INSTALLS:
            raise ValueError("Unknown install type: " + repo)
        if item.get("compatible_with_user_exe") != "untested":
            raise ValueError("Runtime compatibility must be tested before promotion: " + repo)
        if not isinstance(item.get("notes"), str) or not item["notes"]:
            raise ValueError("Missing source notes: " + repo)
    return data["sources"]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Summarize curated community projects")
    parser.add_argument("action", nargs="?", choices=["validate", "list"], default="list")
    parser.add_argument("--risk", choices=sorted(RISKS))
    parser.add_argument("--category")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)
    sources = load_registry()
    if args.action == "validate":
        print(f"OK: {len(sources)} documented sources (none runtime-verified)")
        return 0
    selected = [
        x for x in sources if (not args.risk or x["risk"] == args.risk)
        and (not args.category or x["category"] == args.category)
    ]
    limit = max(0, min(args.limit, 40))
    for entry in selected[:limit]:
        print(f"{entry['repo']} | {entry['category']} | {entry['license_status']} | {entry['risk']}")
    print(f"Showing {min(limit, len(selected))} / {len(selected)}; no installations performed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
