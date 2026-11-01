# Build Studio alpha | exact original Windows client

This is an offline **draft editor / source-backed name validator / portable share-code tool**. It does not load the game, install addons, change talents, or certify optimal damage. It accepts only the owner-executable's verified English talent-name inventory. It is not a web UI yet.

## Requirements

- Python 3.10+; no pip dependencies.
- A local copy of the user's original AzerothSurvivors.exe, SHA-256:
  2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a.
- Run commands from the repository root.
- Keep your saved game, EXE, MPQs and local drafts private. Do not upload proprietary game data in a public PR.

Create a local output folder manually:
  mkdir artifacts

Create a blank Warlock draft for the exact original game:
  py -m planner.build_studio init --game-exe "C:\Games\AzerothSurvivors\AzerothSurvivors.exe" --class warlock --style low_input_minions --name "Imp and Felguard trial" --out artifacts\my-warlock.json

Edit only the new JSON build file with your preferred text editor. An example of the *shape*, not a recommendation for allocation:

  "talents": [
    {"tree":"Demonology","name":"Summon Imp","points":1},
    {"tree":"Demonology","name":"Demonic Pact","points":1}
  ]

Those names are present in this client's English localization. **The 1-point values are only illustrative**. They have not been shown to be legal or reachable in the actual talent tree. Start with an empty talent array if you haven't personally validated your allocation.

Then verify the exact-client SHA and tree/name presence:
  py -m planner.build_studio validate --game-exe "C:\Games\AzerothSurvivors\AzerothSurvivors.exe" --build artifacts\my-warlock.json

The result is NAME_CHECK_ONLY. A passing result **does not** establish rank caps, point prerequisites, class/race legality, 51-point balance, real items, or DPS. A 51-point budget is merely a conservative research guard, based on old public examples, not proof of a rank ceiling in the owner's binary.

Export a compact portable code:
  py -m planner.build_studio encode --game-exe "C:\Games\AzerothSurvivors\AzerothSurvivors.exe" --build artifacts\my-warlock.json

The output begins with AZSE3:. It contains a zlib-compressed JSON draft plus a truncated SHA-256 for **error detection only** (not a digital signature or privacy guarantee). **Share codes contain your build notes and selections in readable/decompressible form. Never put secrets in them.** No account or network request is used.

Import another person's shared draft:
  py -m planner.build_studio decode --code "AZSE3:..." --out artifacts\received-build.json

Decode refuses malformed, oversized, trailing or corrupted payloads and never replaces an existing draft. Next run validate with your exact EXE. A share code from another binary hash is rejected by validate.

## JSON fields

- client_sha256: exact file fingerprint, never a guessed game version.
- class: must exist in the extracted nine-class talent inventory.
- race: an optional textual note, **not** a verified race/class unlock.
- talents: a list of tree, exact name and requested points. The validator rejects wrong class/tree/names, duplicates, noninteger points and totals above an assumed 51.
- spells / passives / gear.rings / gear.trinkets / gear.amulet: ordered optional research notes. Their game availability and stats are **not yet verified**.
- style: experimental, low_input_minions, farming, damage, survival or bosses.
- evidence_level: deliberately fixed to name_only_unverified.
- legal_tree_verified: deliberately false to prevent accidental promotion of an untested build.

For deeper inspection of talent-name candidates in a *private* output, use:
  py -m tools.extract_talent_names --game-exe "C:\Games\AzerothSurvivors\AzerothSurvivors.exe" --class warlock --out artifacts\warlock-tree-names.json

That inspection is also name-only, not a complete game rules database.

## Planned upgrades

- Discover max rank and prerequisite edges on a copy of the original Windows client.
- Add visual 27-tree allocation editing and an explicit validation tier that requires live game checks.
- Test race/class unlocks, spell ranks, items and import/export with real screenshots and observable run data.
- Integrate optional, properly licensed addon UIs without assuming they expose level-up card options.
- Benchmark low-input Warlock Imp/Felguard and Shaman Wolves under controlled identical runs.

**Safety:** all game assets remain in the owner's private game copy; this repository only contains open code and aggregate metadata.

## Optional read-only Lua advisor export

Once you have edited and validated a draft, export a **single custom preset** as a self-contained Lua 5.0 table for our self-authored `AZSEnhancedAdvisor`:

```powershell
py -m planner.addon_export --game-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe" --build artifacts\\my-warlock.json --out artifacts\\CustomPresets.lua
```

This produces **only a new local source file**, never touches the game or an existing addon. It escapes user-controlled strings and refuses to overwrite any file. For later in-game testing, make a **separate disposable copy** of the advisor's source folder, replace that copy's `Presets.lua` with the generated `CustomPresets.lua`, and manually install the test copy with backups/rollback enabled. There is **no automatic talent allocation**, no guarantee a custom build is legal and no proven runtime compatibility yet. The output's UI fields explicitly say `name_only_unverified` and `NOT LEGALITY-TESTED`.
