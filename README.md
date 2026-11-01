# Azeroth Survivors: Enhanced Edition

Independent, non-invasive companion tools for [Aethus's Azeroth Survivors](https://wow.aethus.pl/). This repository is **not** an official source fork. It contains **no game assets, executables, MPQ files or redistributed third-party addons**.

## Status
- First versioned, offline **build catalogue** for all nine classes, with an experimental low-input/idle Warlock Demonology route.
- Python catalogue CLI for validation, filtering and exporting a **read-only WoW 1.12 Lua addon**.
- Original game source inventory from the owner's private Google Drive (file names and byte sizes only).
- Bounded log summaries to prevent giant diagnostics flooding ChatGPT.
- Automated Python unit tests in GitHub Actions.

**Important:** All starter builds are editorial hypotheses, not measured BiS builds. The Lua addon displays advice; it does not automatically change talents, equipment or game logic. Not yet runtime-tested against the exact user's EXE.

## Quick start

Requirements: Python 3.10+.

```powershell
py -m planner.azs_planner validate
py -m planner.azs_planner list --class warlock
py -m planner.azs_planner show warlock-demonology-idle
py -m planner.azs_planner export-addon
py -m unittest discover -s tests -v
```

Install addon by copying `addons/AZSEnhancedAdvisor/` to `benilla-config/AddOns/AZSEnhancedAdvisor/` alongside `AzerothSurvivors.exe`. Log back into the game and type `/azse`, `/azse class warlock`, `/azse list` or `/azse show warlock-demonology-idle`. The game version and compatibility still need live verification.

## Design principles
1. The owner's original Aethus Windows game is the target. Community Rust/Bevy reimplementations are references, **not** the original game's source.
2. Keep stock files and saves untouched. Backup before mod testing; offer rollback.
3. Integrate third-party code only after checking licenses and versions. Azerloot is all-rights-reserved.
4. Separate verified game data, community observations and unverified hypotheses.
5. Work through feature branches, reviews and reproducible CI. Keep long/raw logs outside chat.

## Project files

- `catalog/presets.json`: version-labeled preset catalogue.
- `planner/azs_planner.py`: validation and Lua catalogue export.
- `addons/AZSEnhancedAdvisor/`: read-only in-game advisory UI.
- `tools/inspect_archive.py`: archive inventory only, never executes files.
- `tools/log_summary.py`: bounded, redacted log digest.
- `docs/ORIGINAL_FILE_INVENTORY.md`: owner's private game inventory (metadata only).
- `docs/PROJECT_STATE.md`, `docs/HANDOFF.md`: continuation notes.

Game archives remain in the owner's private Google Drive and **never belong in public GitHub or a release**.

## New upstream and client preflight tools

The community-source registry (`catalog/upstreams.json`) records 30 checked GitHub projects, their categories, licensing warnings, collision risks and **untested** compatibility. It makes no claim to cover all forks or to certify third-party code.

```powershell
py -m tools.upstream_registry validate
py -m tools.upstream_registry list --risk critical
py -m tools.client_guard --game-root "C:\Games\AzerothSurvivors"
py -m tools.client_guard --game-root "C:\Games\AzerothSurvivors" --all-mpq --out artifacts/client-report.json
```

Client guard only reads PE/MPQ headers and hashes. A known binary fingerprint is **not** a verified game version and never authorizes automatic patching. Its detailed JSON reports must remain private. See `docs/DISCOVERY_2026-11-01.md` and `docs/COMPATIBILITY_POLICY.md`.

**Version warning:** public guides describe a Shaman Enhancement rework in browser v0.134.0 and a Demonology Warlock capstone rename in v0.129.0. These do not establish which features are in the owner's Windows EXE.
