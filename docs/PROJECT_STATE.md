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
- Metadata inventory only; executable version/hash and MPQ contents NOT verified yet.
- Starter catalogue: 11 **unverified editorial** build hypotheses covering nine classes.
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
