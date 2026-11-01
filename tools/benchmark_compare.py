"""Offline, conservative comparison of manually observed Azeroth Survivors runs.

No game automation, save editing, network access, or fabricated metrics.
Never mix Windows client fingerprints, zones, difficulty, controlled settings,
races or interaction rules. Uses medians and requires 3 runs per candidate.
"""
import argparse
import json
import re
import statistics
import sys
from pathlib import Path

MAX_BYTES = 1024 * 1024
MAX_RUNS = 1000
SHA = re.compile(r"[0-9a-f]{64}\Z")
RUN_FIELDS = {
    "run_id", "build_id", "client_sha256", "zone", "difficulty", "race",
    "settings_id", "interaction_mode", "survival_seconds", "kills",
    "boss_defeated", "boss_kill_seconds", "manual_actions", "notes",
}
MODES = {"stand_still", "pickup_only", "unrestricted"}
MIN_COMPARABLE_RUNS = 3


class BenchmarkError(ValueError):
    pass


def text_field(value, name, maximum=100):
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise BenchmarkError("Invalid " + name)
    if any(ord(ch) < 32 for ch in value):
        raise BenchmarkError("Control character in " + name)
    return value


def validate_run(row):
    if not isinstance(row, dict) or set(row) != RUN_FIELDS:
        raise BenchmarkError("Run fields mismatch (check schema in docs/BENCHMARK_PROTOCOL.md)")
    for field in ("run_id","build_id","zone","difficulty","race","settings_id"):
        text_field(row[field], field)
    text_field(row["notes"], "notes", 500) if row["notes"] else None
    if not isinstance(row["client_sha256"], str) or not SHA.fullmatch(row["client_sha256"]):
        raise BenchmarkError("Invalid exact game EXE fingerprint")
    if row["interaction_mode"] not in MODES:
        raise BenchmarkError("Unknown interaction mode")
    seconds = row["survival_seconds"]
    if type(seconds) not in (float, int) or not 1 <= seconds <= 86400:
        raise BenchmarkError("Invalid survival seconds")
    if type(row["kills"]) is not int or not 0 <= row["kills"] <= 10_000_000:
        raise BenchmarkError("Invalid kill count")
    if type(row["manual_actions"]) is not int or not 0 <= row["manual_actions"] <= 10_000_000:
        raise BenchmarkError("Invalid manual action count")
    if row["interaction_mode"] == "stand_still" and row["manual_actions"] != 0:
        raise BenchmarkError("Stand-still trial cannot include manual actions")
    if type(row["boss_defeated"]) is not bool:
        raise BenchmarkError("boss_defeated must be a boolean")
    b = row["boss_kill_seconds"]
    if b is not None:
        if not row["boss_defeated"] or type(b) not in (float,int) or not 0 < b <= seconds:
            raise BenchmarkError("Boss kill time must be numeric <= survival duration and require a boss kill")
    return row


def load_runs(path):
    file = Path(path)
    if not file.is_file() or file.is_symlink() or not 1 <= file.stat().st_size <= MAX_BYTES:
        raise BenchmarkError("Input JSON is missing, symlinked or too large")
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise BenchmarkError("Invalid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "runs"} or payload["schema_version"] != 1:
        raise BenchmarkError("Unsupported benchmark schema")
    records = payload["runs"]
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_RUNS:
        raise BenchmarkError("Invalid number of runs")
    seen = set()
    for row in records:
        validate_run(row)
        if row["run_id"] in seen:
            raise BenchmarkError("Duplicate run_id")
        seen.add(row["run_id"])
    return records


def comparison_key(row):
    return tuple(row[k] for k in ("client_sha256", "zone", "difficulty",
                                  "race", "settings_id", "interaction_mode"))


def analyze(runs):
    if not runs:
        raise BenchmarkError("No runs available")
    for row in runs:
        validate_run(row)
    groups = {}
    for row in runs:
        groups.setdefault(comparison_key(row), {}).setdefault(row["build_id"], []).append(row)
    output = []
    for key, builds in sorted(groups.items()):
        candidates = []
        for build, data in sorted(builds.items()):
            n = len(data)
            candidates.append({
                "build_id": build,
                "run_count": n,
                "minimum_sample_met": n >= MIN_COMPARABLE_RUNS,
                "median_survival_seconds": round(statistics.median(r["survival_seconds"] for r in data), 2),
                "median_kills_per_minute": round(statistics.median(r["kills"] * 60 / r["survival_seconds"] for r in data), 2),
                "boss_kill_count": sum(r["boss_defeated"] for r in data),
                "median_boss_kill_seconds_when_observed":
                    round(statistics.median(r["boss_kill_seconds"] for r in data if r["boss_kill_seconds"] is not None), 2)
                    if any(r["boss_kill_seconds"] is not None for r in data) else None,
                "median_manual_actions": statistics.median(r["manual_actions"] for r in data),
            })
        enough = len(candidates) >= 2 and all(x["minimum_sample_met"] for x in candidates)
        output.append({
            "client_sha256": key[0], "zone": key[1], "difficulty": key[2],
            "race": key[3], "settings_id": key[4], "interaction_mode": key[5],
            "status": "DESCRIPTIVE_COMPARISON_ONLY" if enough else "INSUFFICIENT_COMPARABLE_TRIALS",
            "candidates": candidates,
            "winner_certified": False,
            "limitations": "Manual logs only; survival and kills are descriptive medians, not DPS or proof of build superiority. RNG, cards, drops and player behavior may confound results.",
        })
    return {"schema_version": 1, "comparisons": output, "game_executed_by_tool": False,
            "overall_winner_certified": False}


def main(argv=None):
    p = argparse.ArgumentParser(description="Compare manual runs without mixing versions or settings")
    p.add_argument("--runs", required=True, help="Private locally curated JSON records")
    p.add_argument("--out", help="New local JSON file only, no overwrite")
    args = p.parse_args(argv)
    try:
        result = analyze(load_runs(args.runs))
        if args.out:
            target = Path(args.out)
            if target.exists() or target.is_symlink() or not target.parent.is_dir():
                raise BenchmarkError("Output exists, is a symlink, or parent folder missing")
            with target.open("x", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
                f.write("\n")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (BenchmarkError, OSError) as exc:
        print("REFUSED:", str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
