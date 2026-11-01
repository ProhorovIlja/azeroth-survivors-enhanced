# Project state | 2026-11-01

## Identity
Repository: https://github.com/ProhorovIlja/azeroth-survivors-enhanced (public, user-created).
GitHub code changes on feature branch feat/bootstrap-and-original-inventory, with PR review prior to merge.
Original game: https://wow.aethus.pl/ (Aethus); no original official source repository verified.
Other repo ProhorovIlja/bloodborne_pc_windows_port is unrelated and MUST NOT be modified.

Private Drive: connected user account, folder named Azeroth Survivors Enhanced; access URL and IDs are kept only in the owner's private Drive project state, not this public repository.

## Verified
- GitHub repo exists; GitHub connector can push, branch, open pull requests.
- Drive contains AzerothSurvivors.exe plus seven patch*.MPQ archives in Data/.
- Original EXE SHA-256 is 2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a, PE32+ x86-64. Sample patch-6.MPQ structurally inspected; all other MPQs uninspected.\n- Binary English labels confirm older Demonology / Enhancement branches (Demonic Pact, Summon Felguard, Windfury, Feral Spirit). Modern browser labels Legion Gate / Nathrezim / Rockbiter / Stormbound Echoes were not found as literal names. Exact Windows game version remains unverified.
- Starter catalogue: 11 **unverified editorial** build hypotheses covering nine classes; misleading browser 0.135.1 baseline tag removed. Original Windows client and browser builds differ.
- Offline Python unit tests pass; in-game addon not yet tested against supplied Windows executable.

## Next work
1. Scan actual EXE in a controlled environment; calculate file hashes and exact client version. No execution of untrusted binary.
2. Verify Lua 1.12 API against shipped build; run smoke tests on isolated game copy.
3. Research actual races, specialization trees, spell scaling, gear and boss drops by patch; generate versioned accurate builds.
4. Analyze performance with before/after FPS, CPU, GC and crash evidence. Avoid speculative optimization claims.
5. Add preset editor/import/export, clear migration and rollback paths.
6. Keep future handoffs in GitHub docs and Drive. ChatGPT cannot automatically archive full chat history.

## Boundaries
Do not publish proprietary WoW assets, raw binary game files, saves, personal Drive credentials or huge logs. Never directly merge third-party addons without licensing review. No automatic game modification from the read-only API.


## Latest status | 2026-11-01

Draft PR stack **#1 → #7 → #8 → #9 → #10**, none merged to main. Last checked repository default branch still only has the original user-created README. Latest changes are in `feat/build-studio-share-codes` and must not be treated as shipped game modifications.

Original user EXE: SHA-256 `2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a`, 139691008 bytes. In-place read-only localization scan independently reproduced **2632 entries and 345 short name candidates in 27 talent tree sections / nine classes**; exact Windows version, individual rank caps, unlock rules and live gameplay compatibility remain unverified. Legacy Demonology / Enhancement labels differ from recent browser guide labels.

PR #9: `tools/addon_package.py`, an offline installer limited to the self-authored advisor with preview, backup, rollback and 14 synthetic tests. Real game installation not yet tested.

PR #10: `planner/build_studio.py` can initialize, validate and exchange client-hash-bound draft JSON through compressed `AZSE3:` share codes. `planner/addon_export.py` creates a separate, Lua-escaped advisor preset file for optional manual testing. 23 synthetic unit tests were added. Share codes are not encrypted, authenticated or proof of build strength. No talent prerequisite/rank cap validation or auto-apply exists. Latest PR #10 GitHub Actions green; check on each new commit.

Source audit still current at 2026-11-01: ASBuilder v1.10.0; AZSMaxHit v1.3.2. OutThisLife/azeroth-survivors-re has separate independent Rust/Bevy PRs #17–#20; never present these as official Aethus patch source. No third-party code was copied.

Next: inspect source and runtime risks of addon installer; run Build Studio against owner's EXE locally with saved results; verify talent edges/ranks and races from authoritative in-game evidence; implement visual editor when legality data is available; benchmark stationary Warlock; review/merge draft PRs sequentially only after compatibility QA.


## 2026-11-01 hotfix: 0.137 appended Shaman balance overlay

Private Windows EXE read-only binary comparison found old **ordered legacy tree names retained**, plus **appended Shaman Enhancement 0.137 labels** outside the prior 27-tree scanner. Backup 0.136 had 12 appended names, current 0.137 has 13. The delta includes new Stormguard / Elemental Sunder / Heart of the Earthbreaker, removed Earthen Bulwark / Unleashed Weapons. Therefore "same 345 short tree labels" does NOT prove same active talents. Updated exact SHA-gated extractor, Build Studio validator and safe private EXE comparator to warn on older-only names and show appended names as unverified. Source doc docs/ENHANCEMENT_PATCH_OVERLAY.md; 12 synthetic regression tests added. Upstream author ASBuilder v1.11.0 released 2026-11-01 directly confirms 0.137 Enhancement / Heart of Earthbreaker, and AZSMaxHit v1.3.3 addresses proc attribution. Still no in-game QA, no game binaries committed.
