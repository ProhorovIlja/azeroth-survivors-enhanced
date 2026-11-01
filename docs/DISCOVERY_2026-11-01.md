# Community discovery | 2026-11-01

This is a **selection**, not a claim to enumerate all GitHub or the internet. Results originated from GitHub repository/branch/PR searches, direct repository READMEs and dated public player guides. All third-party compatibility with the owner's EXE remains **untested**. Machine-readable registry: `catalog/upstreams.json`.

## High-value newly discovered projects

| Project | Useful feature | Decision |
|---|---|---|
| [cadoky/ASBuilder](https://github.com/cadoky/ASBuilder) | In-run priority planner, stages, spell/jewelry targets, ASB2 share/import, banish list | Link and evaluate. Repository root lacks a LICENSE file; do not copy code. Author released v1.10.0 on 2026-11-01 for 0.134 Shaman changes. |
| [Dalaxies/AZS-Card-Advisor](https://github.com/Dalaxies/AZS-Card-Advisor) | Predict possible draft upgrades from visible game data | MIT per README. Does **not** see actual dealt cards. Validate old-version power math. |
| [ghoulcompiler/AZSMaxHit](https://github.com/ghoulcompiler/AZSMaxHit) | Maximum hit, crit and burst logging by spell | MIT per README; 0.135.1 testing claimed by maintainer. Useful alongside AZSSpellMeter, not a substitute for performance benchmarks. |
| [Maidenquinn/AzerothStats](https://github.com/Maidenquinn/AzerothStats) | Run history, comparisons, configurable HUD | Attribution, privacy and review status require verification; no automatic code copying. |
| [BrickHouseWeb/SurvivorQoL](https://github.com/BrickHouseWeb/SurvivorQoL) | Nameplates, cursor, movable frames, metrics | Test against UI conflicts. |
| [JamieeLee/MoveUI](https://github.com/JamieeLee/MoveUI) | Move native interface frames | Check current frame API. |
| [JamieeLee/BigCursor](https://github.com/JamieeLee/BigCursor) | Larger cursor | Optional accessibility candidate. |
| [threenox/BordoUI](https://github.com/threenox/BordoUI) | HUD suite | GPL-3; inherited material and competing HUD require careful legal and technical review. |
| [Maidenquinn/AzerothHub](https://github.com/Maidenquinn/AzerothHub) | UI hub to open other addons | No libre license; requires consent for reuse. |
| [sandervspl/AzerothSurvivorsLogs-Addon](https://github.com/sandervspl/AzerothSurvivorsLogs-Addon) and [Desktop](https://github.com/sandervspl/AzerothSurvivorsLogs-Desktop) | Combat logs and desktop uploader | Mirrors of a separately named monorepo. Do not run desktop binaries without security evaluation. |
| [Zerosks471/AZSBuildBook](https://github.com/Zerosks471/AZSBuildBook) | Potential build UI | Root has no README; contents not audited and code/license not established. |
| [Halnatgit/AzerothSurvivors-Deathknight](https://github.com/Halnatgit/AzerothSurvivors-Deathknight) | Unofficial 10th class, three specs and MPQ modifications | **Quarantine**: patch-D.MPQ plus native loader; author's 0.118.0 target predates user's unverified client. Never install automatically. |
| [finalpantasy/azeroth-survivors-overhaul](https://github.com/finalpantasy/azeroth-survivors-overhaul) | HD conversion and transactional installer | Interesting design patterns, but binary/asset transforms and copyrights require independent review. |
| [bymarvin/azeroth-survivors-source](https://github.com/bymarvin/azeroth-survivors-source) | Co-op mod's DLL/launcher source | **Not original Aethus game source**; repository explicitly states it has no chosen license. |

## Forks, branches and pull requests
- GitHub branch checks: `OutThisLife/azeroth-survivors-re` main, `nfmous/nfui_AZSRV` main, our Enhanced Edition main/feature branch at discovery. Empty-query branch searches can paginate.
- Confirmed fork: `erjdev/azeroth-survivors-re` lists parent `OutThisLife/azeroth-survivors-re`; `dckthulhu/ASBuilder` lists parent `cadoky/ASBuilder`.
- OutThisLife PR [#17](https://github.com/OutThisLife/azeroth-survivors-re/pull/17) (Windows installer) and [#18](https://github.com/OutThisLife/azeroth-survivors-re/pull/18) (PowerShell setup) were **open** on 2026-11-01. They apply to the *independent Rust/Bevy engine*, not the Aethus Windows EXE.
- Similar-name repo search produced many possible forks and unrelated hits. Fork status cannot be inferred from names/search results alone. GitHub's authenticated direct fork list endpoint was unavailable, so no claim of exhaustive fork audit is made.

## Version-drift alerts
- Independent guide reported the **browser** game at v0.135.1 as of Nov 1; owner's **Windows EXE version is not established**. Never use browser version to prove binary compatibility.
- Warlock Demonology: public v0.129+ guide says `Pact of the Nathrezim` replaced `Pact of the Annihilan`, swapping Pit Lord for Dread Lord.
- Enhancement Shaman: major 0.134.0 rework uses Rockbiter Weapon / Stormstrike / Stormbound Echoes. Older Enhancement build scripts and talent allocations must be flagged stale.
- Read-only Lua addon API does **not expose the actual native level-up hand**: card advisors predict candidates rather than reading offered cards.
- Normal UI settings conflict potential: multiple addons simultaneously replacing nameplates, HUD clock, meter, cursor or moveable frames should have explicit winner selection.

## Sources
Primary project repository READMEs and releases linked above. Independent (non-authoritative) secondary version reports:
- https://survivorsdb.com/azeroth-survivors/classes
- https://azerothsurvivorsgame.com/patch-notes/
- https://azeroth-survivors.org/guides/builds/
- https://azeroth-survivors.org/guides/addons/

## Gaps / next checks
Verify exact LICENSE files (not badge text alone), compare release tags to supported game versions, record per-release checksums/signatures, inspect user game's MPQ/listfile metadata privately and test on copied game. Verify other forks by parent metadata, commit deltas and PR activity. Do not reuse untranslated or copied guide prose in presets.
