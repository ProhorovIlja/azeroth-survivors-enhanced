# Attributed player build evidence (2026-11-01)

Community build research is stored separately from the original 11 *editorial* starting presets. These are **historical examples**, not valid modern 51-point allocations or measured optimal builds.

The first seven recorded splits are in `catalog/community_examples.json`, with source links, observed versions, patch warnings and missing-evidence flags. The sources currently are secondary summaries of videos and player build pages; primary video URLs and frame-level evidence still require independent verification. Nothing has been imported from other addon source code.

## Relevant playable routes to investigate
- **Warlock**: Holdherhand's reported 5 Affliction / 32 Demonology / 14 Destruction from v0.114.2 used Searing Pain and Pit Lord. That specific capstone no longer appears in reported browser v0.129+; now Nathrezim (Dread Lord). This is a **historical setup, not a current recommendation**. https://azeroth-survivors.org/guides/warlock-demonology-build/
- **Shaman**: Cadoky's reported 22 Elemental / 12 Enhancement / 17 Restoration aimed to stand on Magma Totems. Same guide says only upgrade Magma Totem, with Healing Wave/Lightning Bolt kept at rank 1, and banish certain off-build spells. Browser v0.134.0 changed Enhancement. Needs validation, especially totem caps and rank interactions. https://azeroth-survivors.org/guides/shaman-magma-totem-build/
- **Warrior**: reported Arms 11 / Fury 40 / Protection 0 from v0.102.0, with Whirlwind focus; old patch, full talents not transcribed or replayed. https://azeroth-survivors.org/guides/builds/
- **Rogue**: reported 5 Assassination / 15 Combat / 31 Subtlety, Shadow Dance focus, version not stated. No proof that 51 points remain legal today. https://azeroth-survivors.org/guides/builds/
- **Druid**: reported 33 Balance / 0 Feral / 18 Restoration, version unknown. https://azeroth-survivors.org/guides/builds/
- **Mage**: reported 41 Arcane / 0 Fire / 10 Frost, version unknown. https://azeroth-survivors.org/guides/builds/
- **Priest**: reported 15 Discipline / 0 Holy / 31 Shadow = **46**, not 51. Remaining 5 are unknown and are deliberately not invented. https://azeroth-survivors.org/guides/builds/

## Evidence grades
- `unverified_editorial`: independently proposed, not recorded or measured.
- `historical_secondary_record`: a dated public guide attributes a build to a player/video, but the original video and current compatibility were not independently validated.
- Future `primary_verified_snapshot`: requires original player source and exact in-game screenshot/version.
- Future `benchmark_verified`: requires repeated tests on owner's exact game SHA with score/KPI details.

No evidence-grade promotion without a reproducible source and test. A final 51-point allocation is **not** an ordered leveling route. New race/spec support must be learned from the exact client before generating legal recommendations.

You can inspect safely with `python -m planner.community_examples list --class warlock`.
