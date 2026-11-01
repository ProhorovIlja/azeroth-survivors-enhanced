"""Read-only GitHub source monitor. Public metadata only; no install or writes to GitHub.

Requires explicit --run for network access, and should be scheduled only after
human review and merge to the default branch. No game assets or private data.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

from tools.upstream_registry import load_registry

API = "https://api.github.com"
MAX_SOURCE_CHECKS = 30
QUERIES = ("azeroth survivors in:name,description", "azs addon in:name,description")


def api_get(path, token=None, timeout=12):
    if not path.startswith("/") or "://" in path:
        raise ValueError("Expected GitHub REST API path")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AZS-Enhanced-source-monitor/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(API + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise RuntimeError(f"GitHub API HTTP {exc.code}") from None


def snapshot_one(repo, get):
    path = "/repos/" + repo
    meta = get(path)
    if not isinstance(meta, dict):
        return {"repo": repo, "status": "not_found_or_unavailable"}
    info = {
        "repo": repo,
        "status": "found",
        "default_branch": meta.get("default_branch"),
        "archived": meta.get("archived"),
        "fork": meta.get("fork"),
        "parent": (meta.get("parent") or {}).get("full_name"),
        "pushed_at": meta.get("pushed_at"),
        "forks_count": meta.get("forks_count"),
        "license_spdx_reported": (meta.get("license") or {}).get("spdx_id"),
    }
    endpoints = [
        ("latest_release", path + "/releases/latest"),
        ("sample_open_prs", path + "/pulls?state=open&per_page=5"),
        ("sample_branches", path + "/branches?per_page=5"),
    ]
    for key, url in endpoints:
        try:
            result = get(url)
            if key == "latest_release":
                info[key] = {
                    "tag": result.get("tag_name"), "published_at": result.get("published_at")
                } if isinstance(result, dict) else None
            else:
                info[key] = [v.get("number") if key == "sample_open_prs" else v.get("name")
                             for v in result[:5]] if isinstance(result, list) else []
        except (RuntimeError, ValueError) as exc:
            info[key] = {"error": type(exc).__name__}
    return info


def collect(sources, get, search=True):
    output = {
        "schema_version": 1,
        "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "repository_count": len(sources),
        "source_snapshots": [],
        "potential_new_repositories": [],
        "limitations": "Samples only: first five open PRs/branches; no code audit or runtime compatibility tests.",
    }
    for source in sources:
        try:
            output["source_snapshots"].append(snapshot_one(source["repo"], get))
        except (RuntimeError, ValueError) as exc:
            output["source_snapshots"].append({
                "repo": source["repo"], "status": "request_failed",
                "error_type": type(exc).__name__,
            })
    if search:
        known = {x["repo"].lower() for x in load_registry()}
        candidates = {}
        for term in QUERIES:
            path = "/search/repositories?q=" + urllib.parse.quote(term) + "&per_page=100"
            try:
                data = get(path) or {}
                for obj in data.get("items", []):
                    name = obj.get("full_name")
                    if name and name.lower() not in known:
                        candidates[name.lower()] = {
                            "repo": name, "url": obj.get("html_url"),
                            "pushed_at": obj.get("pushed_at"),
                            "fork": obj.get("fork"),
                        }
            except (RuntimeError, ValueError) as exc:
                output.setdefault("search_errors", []).append(type(exc).__name__)
        output["potential_new_repositories"] = list(candidates.values())[:100]
    return output


def main(argv=None):
    p = argparse.ArgumentParser(description="Read-only GitHub repository/PR/fork monitor")
    p.add_argument("--run", action="store_true", help="Explicitly enable GitHub API reads")
    p.add_argument("--limit", type=int, default=MAX_SOURCE_CHECKS)
    p.add_argument("--out", default="artifacts/upstream-watch.json")
    p.add_argument("--skip-discovery", action="store_true")
    args = p.parse_args(argv)
    count = max(0, min(MAX_SOURCE_CHECKS, args.limit))
    sources = load_registry()[:count]
    if not args.run:
        print(f"DRY RUN: {len(sources)} curated GitHub repos, 2 discovery queries, no network requests")
        print("Use --run for read-only fetching. Scheduled jobs need merge into default branch.")
        return 0
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    report = collect(sources, lambda url: api_get(url, token), search=not args.skip_discovery)
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    found = sum(x.get("status") == "found" for x in report["source_snapshots"])
    print(f"Checked {len(sources)} public repos; found {found}; "
          f"new candidates {len(report['potential_new_repositories'])}; report saved to {dest}")
    return 0 if found else 2


if __name__ == "__main__":
    raise SystemExit(main())
