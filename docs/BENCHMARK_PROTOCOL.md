# Low-input build benchmark protocol (source-only, no game execution)

The purpose is to choose the true stationary / near-AFK class and Warlock variant on the **same exact game version** rather than producing a guessed tier list. The built-in official update monitor is already active in `main`.

`tools.benchmark_compare` reads user-curated **local** JSON records and groups experiments by exact client EXE SHA-256, zone, difficulty, race, control settings identifier, and player interaction rule. It never launches Azeroth Survivors, reads save files, downloads mods, or invents statistics. It intentionally does **not** calculate DPS from kills.

## Collecting a run

On an **isolated game copy**, manually record actual observations. Before each test:
- Record `client_sha256` (original Windows 0.137.0 `aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8`); compare only identical hashes.
- Record character race, zone, difficulty, unchanged account/heroic/perk rules in `settings_id`, and interaction mode.
- For `stand_still`, perform zero manual in-run movement/actions; other trials may use `pickup_only` or `unrestricted` but stay in separate groups.
- After the run, write actual survival duration (seconds), enemy kills, optional boss clear/time, and manual action count. Keep a private screen recording or timestamped notes if possible.
- Repeat each candidate at least **3** times under comparable settings, preferably more, and carefully note RNG, spell card options and boss phases.

JSON structure (all values are **illustrative placeholders**, not actual game performance):

```json
{
  "schema_version": 1,
  "runs": [
    {
      "run_id": "example-run-001",
      "build_id": "0137_warlock_permanent_greaters",
      "client_sha256": "aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8",
      "zone": "YOUR_ACTUAL_ZONE",
      "difficulty": "YOUR_ACTUAL_DIFFICULTY",
      "race": "YOUR_ACTUAL_RACE",
      "settings_id": "identical-gearing-perks-test-001",
      "interaction_mode": "stand_still",
      "survival_seconds": 300,
      "kills": 100,
      "boss_defeated": false,
      "boss_kill_seconds": null,
      "manual_actions": 0,
      "notes": ""
    }
  ]
}
```

Do **not** treat the placeholder 300 seconds / 100 kills as measured data. Replace every entry with real observations. The tool refuses duplicates, malformed statistics, boolean-as-integer coercion, contradictory stand-still actions, impossible boss times and oversized files.

From the repository root:
`py -m tools.benchmark_compare --runs artifacts\\my-private-runs.json --out artifacts\\comparison.json`

The output uses per-build medians for survival, kills per minute, observed boss time and manual actions. If there are fewer than three runs per candidate or fewer than two candidates with comparable settings, it reports `INSUFFICIENT_COMPARABLE_TRIALS`. Even with three or more, `DESCRIPTIVE_COMPARISON_ONLY` means the data are not sufficiently controlled to declare a certified winner. No measurements have been recorded from the owner's game in this project yet.

For Warlock 0.137 candidate definitions and capstone warnings, see `docs/WARLOCK_DEMONOLOGY_0137.md`.
