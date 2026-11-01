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

## Historical player examples (not patch-certified)

See `catalog/community_examples.json` for seven **attributed historical** talent splits with observed patch when available, source URL, and explicit warnings for outdated capstones. They are **not** ranked or validated on the owner's EXE:

```powershell
py -m planner.community_examples validate
py -m planner.community_examples list --class warlock
```

## GitHub upstream monitoring (pending merge)

The read-only `tools.upstream_watch` can check curated repository releases, a sample of branches and open PRs, fork/parent metadata, plus new repository candidates. No automatic installation, copying, merging or source trust implied.

```powershell
py -m tools.upstream_watch --limit 10
# Requires network and optionally GITHUB_TOKEN:
py -m tools.upstream_watch --run --limit 30
```

The daily `upstream-watch.yml` workflow is configured but **does not run on a schedule until merged to main**. Its public metadata report is an expiring GitHub Actions artifact; web/Reddit/video research still requires independent review. See `docs/UPSTREAM_MONITORING.md`.

## Original Windows executable is **not** browser v0.135.1

Static inspection of the user's exact original Windows executable (SHA-256 in `catalog/client_profiles.json`) confirmed English labels for **older Demonology (`Demonic Pact`, `Summon Felguard`)** and **older Enhancement (`Windfury`, `Feral Spirit`)**. Newer browser 0.135.1 talent names such as `Legion Gate`, `Pact of the Nathrezim`, `Rockbiter Weapon` and `Stormbound Echoes` were not observed in that EXE. This does **not** establish the exact game version or verify talent gameplay.

```powershell
py -m tools.talent_probe --game-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe"
py -m tools.talent_probe --game-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe" --require-modern
```

The second command is supposed to return code 2 on an unrecognized/legacy client. No automated game patching is authorized by either command. See `docs/ORIGINAL_CLIENT_TALENTS_2026-11-01.md` and `catalog/original_client_archetypes.json`. All 11 early builds remain **unverified editorial sketches**, not tested optimal strategies.

## Offline addon installation (safe preview / rollback)

The developer-preview installer manages **only** the self-authored AZSEnhancedAdvisor folder under the original game's benilla-config/AddOns directory. No MPQ, EXE, save or third-party addon is changed. Inspect the game's Options > AddOns > Open AddOns Folder location before using it. **Game runtime compatibility is not yet certified.**

```powershell
py -m tools.addon_package plan --game-root "C:\\Games\\AzerothSurvivors"
py -m tools.addon_package install --game-root "C:\\Games\\AzerothSurvivors" --yes
py -m tools.addon_package rollback --game-root "C:\\Games\\AzerothSurvivors" --yes
```

Install refuses a different EXE SHA unless an explicit --allow-unknown-client override is provided. Pre-existing addon directories require --replace-existing and are backed up. Rollback refuses to overwrite modified user files. See docs/SAFE_ADDON_INSTALLER.md for the full safety and interrupted-transaction procedure.

## Build Studio alpha: exact-client drafts and share codes

The first usable offline Build Studio is a Python CLI. It can create a blank build for the **exact uploaded original Windows EXE**, verify selected talent names against its 27 extracted talent-tree sections, and exchange portable checksummed `AZSE3:` draft codes.

```powershell
mkdir artifacts
py -m planner.build_studio init --game-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe" --class warlock --style low_input_minions --out artifacts\\warlock.json
py -m planner.build_studio validate --game-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe" --build artifacts\\warlock.json
py -m planner.build_studio encode --game-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe" --build artifacts\\warlock.json
```

For import use `py -m planner.build_studio decode --code "AZSE3:..." --out artifacts\\imported.json` and revalidate the result. It does **not** auto-allocate talents, prove level/rank prerequisites, or certify build strength. Share codes are compressed plain data, **not encrypted**. Complete guide: `docs/BUILD_STUDIO.md`.

Optional custom advisor data: `py -m planner.addon_export --game-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe" --build artifacts\\warlock.json --out artifacts\\CustomPresets.lua`. This produces Lua-escaped **read-only**, unverified build data, never an installed or auto-applied build. Manual tests with backups are required. See `docs/BUILD_STUDIO.md`.

## Owner's new original Windows 0.137 update (Nov 1, 2026)

Verified owner EXE SHA-256: `aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8` (147844608 bytes; version literal 0.137.0). Backup `AzerothSurvivors.old` has version literal 0.136.0 and a different SHA. The new English localization is CRLF-encoded and was privately indexed with 3334 entries and the same 27 talent tree sections / 345 short name candidates.

**Built-in updater endpoints recovered directly from the EXE:**
- `https://wow.aethus.pl/exe/latest.json`
- `https://wow.aethus.pl/exe/data/patches.json`

The independent [official update watcher](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/issues/11) was merged into `main` in PR #12 and **successfully contacted both real endpoints**, confirming the EXE manifest reported `0.137.0`. It checks four times a day, comments on changes, and never installs anything. The local Build Studio CLI now accepts the new EXE hash while preserving unknown-client refusal. Full metadata: `docs/WINDOWS_CLIENT_0137.md`.

The old Windows game has not been launched for actual QA; static talent names do not prove legality. The entire original game and its MPQs remain private.
