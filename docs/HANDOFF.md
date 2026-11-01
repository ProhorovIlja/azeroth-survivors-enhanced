# Continuation handoff

Start by checking the state of GitHub PRs, CI runs, and docs/PROJECT_STATE.md. Then inspect new files in the owner's Drive folder and read docs/ORIGINAL_FILE_INVENTORY.md. Never mistake community reimplementations for official Aethus source.

User priorities: top build planner and class/race/spec/gear presets; idle/minion Warlock in particular; integration of licensed addons, UI QoL, performance, crash/stability fixes. Prefer evidence-backed recommendations to marketing claims.

Work in feature branches/PRs and maintain small commits, a patch matrix and clear rollback. All raw logs/large computation go into files. Chat messages should contain concise summaries, not unlimited error streams.

Security: preserve private original assets, saves, tokens, personal chats, archives. Avoid running executable from untrusted source and distributing game IP. The read-only WoW 1.12 AZS_* addon surface cannot be assumed to change talents/combat.

Helpful repositories: HejAsh/azeroth-survivors-addon-skill, kex0/AZSSpellMeter, migwynkriid13/SurvivorsDragonUi, nfmous/nfui_AZSRV, oppahansi/azssaveeditor, Kindagrey/Azerloot. Azerloot forbids redistribution/derivatives without authorization.

Do not claim real-game tests before running them. The starter tests are offline validation only.


## Current handoff snapshot (2026-11-01)

- Draft PR #1 bootstrap: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/pull/1
- Draft PR #7 research/monitoring: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/pull/7
- Draft PR #8 exact original EXE talent families: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/pull/8
- Draft PR #9 safe addon installer: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/pull/9
- Draft PR #10 Build Studio/share codes/Lua export: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/pull/10

All are stacked and unmerged. The owner EXE hash is 2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a. Developer confirmed local read-only scan recovers 2632 English localization entries and 345 name candidates across 27 trees. Do not claim verified game talent point rules, race legality, FPS or build rankings.

Build Studio commands and caveats: docs/BUILD_STUDIO.md. Original assets remain private. The Github watcher schedule will not start until merged to main. The user expects active progress when requesting 'go further'; first verify current PRs/CI then improve tests, experience, compatibility and actual patch research. Record status to this file and the owner's PRIVATE Drive project-state doc. Protect original EXE, MPQs and saves.
