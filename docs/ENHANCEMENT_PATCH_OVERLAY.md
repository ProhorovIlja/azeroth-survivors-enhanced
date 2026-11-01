# Critical fix: v0.137 Enhancement patch overlay is separate from legacy class-tree dictionary

Read-only, privately extracted English localization data from the user's own Windows executables reveals **two layers**:

1. An older ordered nine-class talent-name dictionary with 27 class-tree sections (345 short name candidates), still present in the 0.137 executable.
2. A separate appended **Shaman Enhancement update section** after `ability.stormstrike.name`, outside those 27 legacy sections.

The original Build Studio counted only layer 1 and could falsely imply that a legacy name such as `Feral Spirit` was appropriate for 0.137 just because it appeared in a retained English localization string. This is corrected.

| Source | Appended short-name candidates | Change |
| --- | ---: | --- |
| Windows backup 0.136.0, SHA `eb744751b4e17ec1397b0cdc85a22af63b6af63c1da1d9c2861762c3c4d8947c` | 12 | Includes `Earthen Bulwark`, `Unleashed Weapons` |
| Windows current 0.137.0, SHA `aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8` | 13 | Adds `Stormguard`, `Elemental Sunder`, `Heart of the Earthbreaker`; removes those two old labels |

These are **short text labels**, not a verified in-game node graph. The active branch has to be verified with screenshots or runtime observations. The old localization block is not reliable evidence of which talent is playable.

## New Build Studio behavior

`tools.extract_talent_names.extract` returns `patch_overlay` for these two exact SHA-256s, separately from legacy `classes` data. Unknown EXEs fail the usual exact-hash gate. `planner.build_studio.validate_against_inventory` now:

- Accepts a matching appended name such as `Stormguard` or `Elemental Sunder` for an experimental Shaman Enhancement draft under the exact 0.137 EXE.
- Reports `appended_patch_candidates_selected` and `patch_overlay_runtime_verified: false`.
- Warns `NAME_CHECK_WITH_PATCH_WARNINGS` if a draft uses Enhancement names seen only in the retained old tree block, e.g. `Feral Spirit`.
- Refuses `Unleashed Weapons` under the 0.137 Shaman overlay because it is neither in that overlay nor in the original ordered tree.
- Still does **not** assert rank caps, prerequisites, 51-point legality, gameplay availability or DPS.

Example: `python -m planner.build_studio validate --game-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe" --build artifacts\\my-shaman.json`.

## Independent upstream corroboration

Author [cadoky/ASBuilder v1.11.0](https://github.com/cadoky/ASBuilder/releases/tag/v1.11.0), published Nov 1, 2026, explicitly calls out **game 0.137.0 Shaman changes**, `Heart of the Earthbreaker` for Rockbiter, updated `Eye of the Tempest` for Stormstrike and the Stormbound Echoes starting-Stormstrike rule. This is useful independent addon-author evidence, not a substitute for user's live game verification. The separate [AZSMaxHit v1.3.3](https://github.com/ghoulcompiler/AZSMaxHit/releases/tag/v1.3.3) corrects overkill/proc attribution; its metrics should be checked before using for benchmark comparisons.

No third-party source, original EXE or proprietary game localization descriptions are copied into this repository.

## Next
Test extracted patch overlays against a clean Windows runtime; build official verified talent-rank/prerequisite graph; measure new Enhancement and stationary Warlock in repeatable runs. Never auto-allocate talents from locale strings.

## Comparing the user's next Windows update safely

With two *privately stored* user-owned EXE snapshots, the new `tools.compare_game_versions` detects localization changes without launching the game:

```powershell
py -m tools.compare_game_versions --old-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.old" --new-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe" --out artifacts\\update-diff.json
```

This tool requires both EXE hashes to be on the explicit reviewed allowlist. It reports dictionary-key counts, changed retained values, differences in retained ordered tree name candidates, and **separately** appended Shaman Enhancement name additions/removals, without exporting full proprietary descriptions. It refuses to overwrite an existing report, and does not execute or modify either binary.

The official GitHub watcher in `main` can discover remote updates before users download them, but the *private local version comparator* intentionally cannot run against the owner's Drive EXE on a public GitHub runner. Only compare local copies when the owner updates Drive/installation. Observed text differences are not damage or balance measurements.
