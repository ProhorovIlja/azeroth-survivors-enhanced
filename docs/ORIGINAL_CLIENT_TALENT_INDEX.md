# Original Windows talent index (private extraction, 2026-11-01)

Without executing the user-uploaded EXE or opening MPQ payloads, a bounded read-only parser located its embedded English localization JSON. The JSON contains 2632 dictionary keys. We extracted **only short talent-name candidates** by tree, not proprietary descriptions, game art, ability definitions or raw contents.

**Observed:** 9 classes, 27 tree sections, 345 candidate names. We store only these aggregate **counts** in the public GitHub project (`catalog/original_client_tree_counts.json`). Counts come from a heuristic and are not equivalent to a validated complete talent graph: repeated names, absent labels, branches and game version can affect completeness.

The local extraction CLI is `python -m tools.extract_talent_names --game-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe" --class warlock --out artifacts/warlock-name-candidates.json`. The generated JSON is ignored by Git and remains on the user's computer. Without `--out`, the CLI prints only compact per-tree counts.

The extractor verifies **exact executable SHA-256** `2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a` first. A different build is rejected instead of blindly applying name boundaries. No code paths execute the game. No level prerequisites, max ranks, complete spell stats, game content or client version are inferred.

## Why static strings help and where they stop

- Warlock's Demonology tree has 13 candidate talent labels in this EXE, including `Summon Imp`, `Demonic Pact`, and `Summon Felguard` (observed localization).
- Shaman's Enhancement section has 10 candidate talents including `Windfury` and `Feral Spirit`.
- The public v0.135.1 **browser** game has materially different Warlock/Shaman talent trees, so current browser builds should not be applied blindly to this Windows installation.

For a verified Build Studio model, we still need rank caps, dependency graph, talent point progression, spell/item/race stats, actual in-game legality and test evidence. Do not publish best-in-slot claims on string observations alone.
