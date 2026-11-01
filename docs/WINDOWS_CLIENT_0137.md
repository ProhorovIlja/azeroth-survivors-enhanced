# Windows original-client v0.137.0 update | November 1, 2026

The user replaced the original game files in their PRIVATE Google Drive. All inspections below were read-only; no executable or MPQ payload was run, decompressed into public source, or uploaded to GitHub.

| Private owner file | Bytes | SHA-256 | Evidence |
| --- | ---: | --- | --- |
| `AzerothSurvivors.exe` | 147844608 | `aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8` | embedded 0.137.0 literal |
| `AzerothSurvivors.old` | 147811840 | `eb744751b4e17ec1397b0cdc85a22af63b6af63c1da1d9c2861762c3c4d8947c` | embedded 0.136.0 literal |
| `Data/patch-8.MPQ` | 4155417 | `ae3aaa29cadb7aeba8255f5b4a8305c7cbecfe8f0d3ed9646522113d16c3e12e` | MPQ header only |
| `Data/patch-9.MPQ` | 5739608 | `ffff8ea890bdaf91a1680543ac60106db92132bc2210105279610fa73661a524` | MPQ header only |
| `Data/patch-A.MPQ` | 1453122 | `350cde8cd0f76e5246a663eb3811f5a7b1a9c75e4e699190208c9299177b8d90` | MPQ header only |
| `Data/patch-B.MPQ` | 2935 | `e9d074b012078efc1c1c8c729bf94d28b1d213d5fcb721dc4370a142f98834bd` | MPQ header only |

Prior client SHA256: `2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a`, 139691008 bytes.

The new EXE includes **author-hosted updater endpoints**:
- https://wow.aethus.pl/exe/latest.json
- https://wow.aethus.pl/exe/data/patches.json

GitHub Actions in a separately merged, independent PR #12 fetched both JSON files successfully, verified current official manifest's `version=0.137.0`, and established hashes in [issue #11](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/issues/11). Scheduled checks monitor JSON, not executable binary files. Nothing downloads/installs automatically.

## Build Studio support

The new EXE's English localization uses `English{\r\n` (CRLF) where the prior original used LF. Privately checked English dictionary has **3334 entries** and still maps **nine classes, 27 tree sections, 345 short talent-name candidates**, with identical per-tree counts to the prior snapshot. This is a heuristic static name index, **not proof of rank caps, prerequisites, talent legality, old-vs-new combat behavior or best DPS**.

The name-only extractor now allowlists the exact new and backup SHA-256s alongside the previous owner EXE; other files still fail closed. The safe addon installer and read-only client inspector recognize the same exact fingerprints. Recognizing a checksum does not prove in-game API support. Run only on an isolated game copy and keep an EXE, MPQ, saves and AddOns backup.

This PR stacks on the existing Build Studio PR #10. The independent official update monitor is already on `main`. Don't merge the game tooling stack without reviewing its PR dependencies and testing actual in-game addon compatibility.


## Corrected extraction model: 0.137 appends a second Shaman name block

The original 27 talent-tree sections (345 candidate labels) are **retained older text**, not a certified active tree. A separate appended 0.137 Enhancement block has **13** short names and includes Stormguard, Elemental Sunder, Heart of the Earthbreaker, Rockbiter Initiation and Stormbound Echoes. The 0.136 backup appended block had **12**, including the since-removed Earthen Bulwark and Unleashed Weapons.

The app now reports this second layer separately as `patch_overlay`; Build Studio flags legacy-only names as possible stale content and never marks any build as legal or runtime verified. To compare the two downloaded owner EXEs privately, see `tools.compare_game_versions` and `docs/ENHANCEMENT_PATCH_OVERLAY.md`. ASBuilder v1.11.0 release notes corroborate 0.137 Shaman changes; not a direct in-game test.
