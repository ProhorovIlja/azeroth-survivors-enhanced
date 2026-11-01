"""Unattended, metadata-only official Azeroth Survivors release intelligence.

Intended for GitHub Actions, not for running/patching proprietary game files.
Compiles versioned file hashes, compares them with the issue-backed baseline,
and creates actionable research tickets on substantive upstream changes.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

SOURCES = {"exe": "https://wow.aethus.pl/exe/latest.json",
           "mpq": "https://wow.aethus.pl/exe/data/patches.json"}
ISSUE_NO = 20
MARKER_RE = re.compile(r"<!-- AZSE_RELEASE_INTEL_V1:(\{[^\n]*\}) -->")
MAX_MANIFEST = 1024 * 1024
MAX_API = 250 * 1024
MAX_ISSUE = 120 * 1024
MAX_EXE = 600 * 1024 * 1024
MAX_MPQ = 3 * 1024 * 1024 * 1024
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
VERSION_RE = re.compile(r"[0-9A-Za-z][0-9A-Za-z._-]{0,48}\Z")
PATCH_RE = re.compile(r"patch-[A-Z0-9]{1,4}\.MPQ\Z")
AGENT = "AZSE-ReleaseIntel/1.0 (metadata-only)"


class ReleaseError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ReleaseError("Redirect refused")


def bounded_number(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ReleaseError("Invalid " + label)
    return value


def sha(value):
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise ReleaseError("Missing or invalid file SHA256")
    return value


def parts_summary(parts):
    if not isinstance(parts, list) or not 1 <= len(parts) <= 256:
        raise ReleaseError("Part count outside bounds")
    compressed = 0
    for part in parts:
        if not isinstance(part, dict):
            raise ReleaseError("Invalid part object")
        path = part.get("url")
        if not isinstance(path, str) or len(path) > 180:
            raise ReleaseError("Invalid relative download path")
        # Allow only author-controlled relative paths, never arbitrary hosts.
        if not re.fullmatch(r"[A-Za-z0-9._/-]{1,180}", path):
            raise ReleaseError("Unexpected part URL characters")
        segments = path.split("/")
        if len(segments) != 2 or any(x in ("", ".", "..") for x in segments):
            raise ReleaseError("Part URL must be relative to one release directory")
        if not re.fullmatch(r"part-[0-9]{3}\.bin", segments[-1]):
            raise ReleaseError("Unexpected part filename")
        compressed += bounded_number(part.get("size"), 1, 128 * 1024 * 1024, "part size")
    return {"count": len(parts), "compressed_bytes": compressed}


def clean_note(value):
    if not isinstance(value, str):
        return ""
    # Preserve readable release-note meaning, avoid HTML/Markdown injection.
    value = re.sub(r"[\x00-\x1f\x7f]", " ", value)
    return " ".join(value.split())[:500]


def parse_manifest(exe, mpq):
    if not isinstance(exe, dict) or not isinstance(mpq, dict):
        raise ReleaseError("Expected two object manifests")
    version = exe.get("version")
    if not isinstance(version, str) or not VERSION_RE.fullmatch(version):
        raise ReleaseError("Unknown version identifier")
    exe_record = {
        "version": version,
        "size": bounded_number(exe.get("size"), 1, MAX_EXE, "EXE size"),
        "sha256": sha(exe.get("sha256")),
        "parts": parts_summary(exe.get("parts")),
        "release_notes": clean_note(exe.get("notes")),
    }
    items = mpq.get("patches")
    if not isinstance(items, list) or len(items) > 64:
        raise ReleaseError("Unexpected patch list")
    records = {}
    for item in items:
        if not isinstance(item, dict):
            raise ReleaseError("Invalid patch entry")
        name = item.get("name")
        if not isinstance(name, str) or not PATCH_RE.fullmatch(name) or name in records:
            raise ReleaseError("Invalid or duplicate patch name")
        records[name] = {
            "size": bounded_number(item.get("size"), 1, MAX_MPQ, "MPQ size"),
            "sha256": sha(item.get("sha256")),
            "parts": parts_summary(item.get("parts")),
        }
    return {"schema": 1, "exe": exe_record, "mpq": dict(sorted(records.items()))}


def stable_hash(snapshot):
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def compare(old, new):
    if old is None:
        return {"first_baseline": True, "changed": False, "exe": None, "added": [], "removed": [], "modified": [], "notes_changed": False}
    if not isinstance(old, dict) or old.get("schema") != 1:
        raise ReleaseError("Stored previous snapshot has unsupported schema")
    exe_before, exe_after = old["exe"], new["exe"]
    exe_changed = (exe_before["sha256"] != exe_after["sha256"] or
                   exe_before["size"] != exe_after["size"] or
                   exe_before["version"] != exe_after["version"])
    a, b = old["mpq"], new["mpq"]
    added = sorted(set(b) - set(a))
    removed = sorted(set(a) - set(b))
    modified = sorted(name for name in set(a) & set(b)
                      if (a[name]["sha256"], a[name]["size"]) !=
                         (b[name]["sha256"], b[name]["size"]))
    notes_changed = exe_before.get("release_notes", "") != exe_after.get("release_notes", "")
    return {"first_baseline": False, "changed": exe_changed or bool(added or removed or modified or notes_changed),
            "exe": {"before": exe_before, "after": exe_after} if exe_changed else None,
            "added": added, "removed": removed, "modified": modified,
            "notes_changed": notes_changed}


def markdown(snapshot, change):
    e = snapshot["exe"]
    lines = ["# Official Azeroth Survivors release research: " + e["version"], "",
             "Source: original game's author-hosted HTTPS JSON manifests, fetched by GitHub Actions.",
             "This is a **metadata-only research report**, not proof of gameplay compatibility or a safe patch.", "",
             "**EXE:** `" + e["sha256"] + "` (" + str(e["size"]) + " bytes; " + str(e["parts"]["count"]) + " compressed parts).", "",
             "## Changed game files"]
    if change["first_baseline"]:
        lines.append("Initial recorded manifest baseline; no earlier comparison is available.")
    elif not change["changed"]:
        lines.append("No release-file or note changes compared to the previous successful snapshot.")
    else:
        if change["exe"]:
            b, a = change["exe"]["before"], change["exe"]["after"]
            lines.append("- EXE: " + b["version"] + " (`" + b["sha256"][:12] + "…`) → " + a["version"] + " (`" + a["sha256"][:12] + "…`)")
        for name in change["added"]: lines.append("- Added MPQ: `" + name + "`")
        for name in change["removed"]: lines.append("- Removed from update manifest: `" + name + "` (not a deletion instruction)")
        for name in change["modified"]:
            lines.append("- Modified MPQ: `" + name + "` SHA `" + snapshot["mpq"][name]["sha256"][:16] + "…`")
        if change["notes_changed"]:
            lines.append("- Author's release notes changed")
    lines.extend(["", "## Author release notes (untrusted source text)",
                  "\n" + ("> " + e["release_notes"].replace("\n", " ") if e["release_notes"] else "No notes supplied.") + "\n",
                  "## Compatibility work for Enhanced Edition", "",
                  "- [ ] Read-only audit of the exact new EXE, full SHA/version and embedded menus; no old RVA reuse",
                  "- [ ] Recheck Bevy Options selector/build functions and original native Cheats integration",
                  "- [ ] Reindex talents, races, spells, gear and active game-data assumptions against the new build",
                  "- [ ] Compare changed MPQ content safely, without uploading original assets",
                  "- [ ] Review upstream addons, PRs and forks for compatibility updates",
                  "- [ ] Run isolated Windows in-game QA before marking any preset or hook compatible", "",
                  "**Do not automatically patch the game, approve offsets, merge compatibility PRs or label builds verified.**"])
    return "\n".join(lines)


def get_official(name, opener=None):
    if name not in SOURCES:
        raise ReleaseError("Unknown source")
    opener = opener or urllib.request.build_opener(NoRedirect())
    req = urllib.request.Request(SOURCES[name], headers={"Accept": "application/json", "User-Agent": AGENT})
    try:
        with opener.open(req, timeout=20) as response:
            if response.status != 200:
                raise ReleaseError("HTTP status " + str(response.status))
            b = response.read(MAX_MANIFEST + 1)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        raise ReleaseError("Official source unavailable: " + type(exc).__name__) from None
    if len(b) > MAX_MANIFEST:
        raise ReleaseError("Manifest exceeds max bytes")
    try:
        return json.loads(b.decode("utf-8"))
    except (UnicodeError, ValueError):
        raise ReleaseError("Invalid official JSON") from None


def api(method, route, token, body=None):
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if not re.fullmatch(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+", repo):
        raise ReleaseError("Invalid repository")
    if not token:
        raise ReleaseError("GitHub token missing")
    if not route.startswith("/") or ".." in route:
        raise ReleaseError("Unsafe API route")
    url = "https://api.github.com/repos/" + repo + route
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, method=method, data=payload, headers={
        "Accept": "application/vnd.github+json", "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": AGENT,
        **({"Content-Type": "application/json"} if payload is not None else {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            b = response.read(MAX_API + 1)
    except (OSError, urllib.error.URLError) as exc:
        raise ReleaseError("GitHub issue API unavailable: " + type(exc).__name__) from None
    if len(b) > MAX_API:
        raise ReleaseError("GitHub API reply too large")
    try:
        return json.loads(b)
    except ValueError:
        raise ReleaseError("Invalid GitHub response") from None


def load_state(body):
    if not isinstance(body, str) or len(body) > MAX_ISSUE:
        raise ReleaseError("Invalid state issue body")
    matches = MARKER_RE.findall(body)
    if len(matches) != 1:
        raise ReleaseError("Expected one release state marker")
    try:
        state = json.loads(matches[0])
    except ValueError:
        raise ReleaseError("Malformed release state") from None
    if state != {} and (not isinstance(state, dict) or state.get("schema") != 1):
        raise ReleaseError("Unrecognized state schema")
    return state or None


def patch_state(body, snapshot):
    load_state(body)
    value = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    if len(value) > 30000:
        raise ReleaseError("Snapshot too large for issue state")
    return MARKER_RE.sub(lambda _: "<!-- AZSE_RELEASE_INTEL_V1:" + value + " -->", body, count=1)


def issue_title(snapshot):
    return "AZSE compatibility audit: " + snapshot["exe"]["version"] + " [" + stable_hash(snapshot)[:12] + "]"


def run(*, token, fetch=get_official, request=api, issue_no=ISSUE_NO):
    # When a source fails, preserve all prior data. Never advance partially.
    new = parse_manifest(fetch("exe"), fetch("mpq"))
    old_issue = request("GET", "/issues/" + str(issue_no), token)
    old_body = old_issue.get("body") or ""
    prior = load_state(old_body)
    delta = compare(prior, new)
    report = markdown(new, delta)
    if not delta["first_baseline"] and not delta["changed"]:
        return {"status": "unchanged", "version": new["exe"]["version"], "changes": delta, "snapshot": new}
    if delta["changed"]:
        # Duplicate guard: pre-existing issue title checked before creating.
        title = issue_title(new)
        existing = request("GET", "/issues?state=all&per_page=100", token)
        if not isinstance(existing, list):
            raise ReleaseError("Unexpected issue list")
        created = not any(i.get("title") == title for i in existing if isinstance(i, dict))
        if created:
            request("POST", "/issues", token, {"title": title, "body": report})
            request("POST", "/issues/" + str(issue_no) + "/comments", token,
                    {"body": "A new upstream release delta was detected. Research issue: **" + title + "**.\n\n" + report[:13000]})
    else:
        request("POST", "/issues/" + str(issue_no) + "/comments", token,
                {"body": "Initial release intelligence baseline established for **" + new["exe"]["version"] + "**. Future changes will create actionable compatibility issues."})
    request("PATCH", "/issues/" + str(issue_no), token, {"body": patch_state(old_body, new)})
    return {"status": "baseline" if delta["first_baseline"] else "changed",
            "version": new["exe"]["version"], "changes": delta, "report": report, "snapshot": new}


def main(argv=None):
    p = argparse.ArgumentParser(description="Track real Aethus file-level deltas in GitHub issues")
    p.add_argument("--check-only", action="store_true")
    p.add_argument("--output-dir", help="Write metadata-only JSON and Markdown report to a directory")
    args = p.parse_args(argv)
    try:
        if args.check_only:
            snapshot = parse_manifest(get_official("exe"), get_official("mpq"))
            delta = compare(None, snapshot)
            result = {"status": "read-only", "version": snapshot["exe"]["version"], "snapshot": snapshot}
        else:
            result = run(token=os.getenv("GITHUB_TOKEN", ""))
            snapshot = result["snapshot"]
            delta = result.get("changes")
        if args.output_dir:
            # Artifacts contain metadata only; source binary is never downloaded.
            from pathlib import Path
            folder = Path(args.output_dir)
            folder.mkdir(parents=True, exist_ok=True)
            if snapshot is not None:
                (folder / "release_snapshot.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
                (folder / "release_report.md").write_text(markdown(snapshot, delta), encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items() if k != "report"}, indent=2))
        return 0
    except ReleaseError as exc:
        print("RELEASE_INTELLIGENCE_ERROR: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
