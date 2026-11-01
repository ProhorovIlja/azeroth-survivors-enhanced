"""Read-only watcher for Aethus's *embedded* Windows update manifest URLs.

GitHub Actions uses this on the default branch. It monitors JSON only:
never executes game binaries, downloads a patch, or uploads a private file.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

OFFICIAL = {
    "exe": "https://wow.aethus.pl/exe/latest.json",
    "mpq": "https://wow.aethus.pl/exe/data/patches.json",
}
STATE_PREFIX = "<!-- azse-official-manifests-state:"
STATE_RE = re.compile(r"<!-- azse-official-manifests-state:(\{[^\n]*\}) -->")
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
MAX_ISSUE_BYTES = 100 * 1024
USER_AGENT = "AZS-Enhanced-readonly-manifest-watch/1.0"
ISSUE_NO = 11


class WatchError(Exception):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise WatchError("Official manifest redirected; address must be reviewed before following")


def fetch_manifest(name, opener=None):
    if name not in OFFICIAL:
        raise WatchError("Unknown manifest name")
    request = urllib.request.Request(
        OFFICIAL[name],
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    opener = opener or urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=15) as response:
            status = response.status
            if status != 200:
                raise WatchError("Manifest returned HTTP " + str(status))
            payload = response.read(MAX_MANIFEST_BYTES + 1)
            if len(payload) > MAX_MANIFEST_BYTES:
                raise WatchError("Manifest too large, refusing")
            if len(payload) < 2:
                raise WatchError("Empty manifest")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise WatchError("Cannot fetch official " + name + " manifest: " + type(exc).__name__) from None
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeError):
        raise WatchError("Official " + name + " manifest was not valid UTF-8 JSON") from None
    if not isinstance(parsed, (dict, list)):
        raise WatchError("Unexpected official manifest top-level JSON type")
    version = parsed.get("version") if isinstance(parsed, dict) else None
    if not isinstance(version, (str, int, float)) or isinstance(version, bool):
        version = None
    if version is not None:
        version = str(version)[:70]
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "version": version,
        "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }


def load_state(body):
    if len(body) > MAX_ISSUE_BYTES:
        raise WatchError("GitHub issue body exceeds safety limit")
    markers = STATE_RE.findall(body)
    if len(markers) != 1:
        raise WatchError("Expected exactly one state marker in issue body")
    try:
        state = json.loads(markers[0])
    except ValueError:
        raise WatchError("Malformed issue state marker") from None
    if not isinstance(state, dict) or set(state) - set(OFFICIAL):
        raise WatchError("Unexpected state contents")
    for name, record in state.items():
        if not isinstance(record, dict) or not re.fullmatch("[a-f0-9]{64}", str(record.get("sha256", ""))):
            raise WatchError("Invalid recorded SHA-256")
    return state


def update_body(body, new_state):
    load_state(body)
    # Only known source keys with narrowly bounded metadata.
    safe = {name: {
        "sha256": rec["sha256"], "bytes": rec["bytes"],
        "version": rec["version"],
    } for name, rec in new_state.items() if name in OFFICIAL}
    marker = STATE_PREFIX + json.dumps(safe, sort_keys=True, separators=(",", ":")) + " -->"
    return STATE_RE.sub(lambda _: marker, body, count=1)


def changes(previous, fresh):
    changed = {}
    for name in OFFICIAL:
        if name not in fresh:
            continue
        old = previous.get(name)
        if old is not None and old.get("sha256") != fresh[name]["sha256"]:
            changed[name] = {"before": old, "after": fresh[name]}
    return changed


def issue_api(method, route, token, payload=None):
    if not token:
        raise WatchError("GitHub token missing; no persistent alert can be posted")
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise WatchError("Unexpected GITHUB_REPOSITORY")
    if not route.startswith("/") or ".." in route:
        raise WatchError("Invalid GitHub endpoint")
    url = "https://api.github.com/repos/" + repo + route
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Accept": "application/vnd.github+json", "User-Agent": USER_AGENT,
        "Authorization": "Bearer " + token, "X-GitHub-Api-Version": "2022-11-28",
        **({"Content-Type": "application/json"} if body is not None else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as reply:
            limited = reply.read(MAX_ISSUE_BYTES + 1)
        if len(limited) > MAX_ISSUE_BYTES:
            raise WatchError("GitHub response too large")
        return json.loads(limited)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise WatchError("GitHub API unavailable: " + type(exc).__name__) from None


def run(*, token, issue_no=ISSUE_NO, fetch=fetch_manifest, api=issue_api):
    old_issue = api("GET", "/issues/" + str(issue_no), token)
    body = old_issue.get("body") or ""
    previous = load_state(body)
    fresh = {}
    failures = {}
    for name in OFFICIAL:
        try:
            fresh[name] = fetch(name)
        except WatchError as exc:
            failures[name] = str(exc)[:200]
    if not fresh:
        raise WatchError("No official manifest could be checked: " + "; ".join(failures.values()))
    merged = dict(previous)
    merged.update(fresh)
    changed = changes(previous, fresh)
    if any(k not in previous or previous[k]["sha256"] != fresh[k]["sha256"] for k in fresh):
        api("PATCH", "/issues/" + str(issue_no), token, {"body": update_body(body, merged)})
    if changed:
        lines = ["## Official manifest change observed (UTC)",
                 "Content SHA-256 changed. This does NOT certify a new playable game version.",
                 "The watcher did not download, execute or install anything."]
        for name, pair in changed.items():
            before, after = pair["before"], pair["after"]
            lines.append("- **" + name.upper() + "** " + OFFICIAL[name] +
                         " | former SHA256 " + before["sha256"][:16] + "… → " +
                         after["sha256"][:16] + "… | embedded version " +
                         str(after.get("version") or "unknown"))
        if failures:
            lines.append("Other checks unavailable: " + ", ".join(sorted(failures)))
        lines.append("Human review required before updating the original EXE/MPQ files.")
        api("POST", "/issues/" + str(issue_no) + "/comments", token, {"body": "\n".join(lines)})
    return {"checked": sorted(fresh), "changed": sorted(changed), "unavailable": failures,
            "baseline_created": [x for x in fresh if x not in previous]}


def main(argv=None):
    p = argparse.ArgumentParser(description="Watch official updater JSON; no game files downloaded")
    p.add_argument("--check-only", action="store_true", help="Fetch public JSON without issue writes")
    args = p.parse_args(argv)
    try:
        if args.check_only:
            state = {}
            for name in OFFICIAL:
                try:
                    state[name] = fetch_manifest(name)
                except WatchError as exc:
                    print(name + ": " + str(exc), file=sys.stderr)
            print(json.dumps(state, indent=2))
            return 0 if state else 2
        result = run(token=os.getenv("GITHUB_TOKEN", ""))
        print(json.dumps(result, indent=2))
        return 0
    except WatchError as exc:
        print("Official update watch: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
