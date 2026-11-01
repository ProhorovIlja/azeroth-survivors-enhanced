# Read-only original Windows update comparison: 0.136.0 → 0.137.0

Compared **embedded English localization dictionary keys** from the owner-uploaded private backup `AzerothSurvivors.old` and current `AzerothSurvivors.exe`. No game execution and no redistribution of original localization texts.

| Finding | 0.136.0 backup | 0.137.0 current |
| --- | ---: | ---: |
| English dictionary keys | 3325 | 3334 |
| Added in new client | | 20 |
| Removed from old | | 11 |
| Changed values for retained keys | | 0 |
| Short talent-name candidates | 345 | 345 |
| Talent-tree sections | 27 | 27 |

**Enhancement Shaman / jewelry label changes**: new English dictionary adds talent-name candidates `Stormguard`, `Elemental Sunder` and separately adds the *amulet* `Heart of the Earthbreaker`. It removes `Earthen Bulwark`, `Unleashed Weapons`, and related old tooltip key forms. New text keys mention interactions among Rockbiter Weapon, Stormstrike, Fire Nova, Frost Shock, Lightning Shield, and various Shocks. This is **game-text evidence only**: it does not establish exact combat balance, legal talent rank order, updated DPS, or available talent tree routes.

The 345-name total remaining constant does **not** mean all names remained the same. Never carry cached 0.136 Shaman allocations over to 0.137 without validating individual name and tree against the exact new EXE. The Build Studio exact-hash inventory check deliberately refuses a build from another client.

The live author's EXE JSON manifest reports `0.137.0` (first verified GitHub Actions monitor run), matching the new EXE's version literal. Monitor `main` workflow checks latest.json and patches.json four times daily and will notify subscribers of issue #11 of subsequent manifest *byte changes*, not of future client/gameplay safety.

Original files and localization descriptions remain private; this document contains only short labels, counts and findings.

**Clarification:** the appended 0.137 short-name group contains 11 research-only Enhancement talent candidates and 2 amulets, not 13 talents. The current EXE also embeds both historical and newer Warlock Demonology name sets, so an older label's presence cannot establish current gameplay. See `docs/ENHANCEMENT_PATCH_OVERLAY.md`.
