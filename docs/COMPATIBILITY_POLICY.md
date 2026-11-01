# Compatibility policy and safe install gates

## Absolute rules
- **Source identity**: original Aethus game from wow.aethus.pl vs. independent engines (e.g. OutThisLife/azeroth-survivors-re) must never be conflated.
- **Runtime compatibility is not implied** by matching a file name or by an upstream README.
- **Unknown version = no automatic patching.** A binary SHA-256 identifies an exact file but does not prove game version. An observed hash is not enough to certify any addon.
- **Original assets stay private** in Google Drive or the owner's installation. No binary redistribution.
- **Before installing anything**: backup saves, stock config and touched game files; verify source/license, author release, exact version, file checksum and rollback.
- **Risk order**: read-only .toc/.lua addons < UI replacements < save editors < native DLLs / executable injection / modified MPQs. Require independent isolated testing for last categories.

## Source-selection
1. Prefer maintained author repositories over aggregator download sites.
2. Compare latest release date, change logs, commit head, branches, PR and forks.
3. For each repo, record author, license, version, game version checked, entrypoints, permissions, and potential overlaps with installed addons.
4. Preserve explicit permission/attribution if copying. 'Public on GitHub' does not grant permission to redistribute source.
5. Never auto-install a native trainer, unofficial multiplayer server, unknown DLL, or binary patch based on stars or marketing.

## HUD collision domains
- **Nameplates**: SurvivorQoL, BordoUI, nfUI, Dragon UI, other replacements.
- **Combat numbers / stats**: AZSSpellMeter, AZSMaxHit, AzerothStats, other metric overlays.
- **Build card guidance**: ASBuilder, AZS Card Advisor, Enhanced Advisor. Some features overlap; don't show competing overlays by default.
- **Frame moving**: MoveUI, UI suite integrated layout editor.
- **Cursor**: BigCursor, SurvivorQoL, custom UI skins.
Resolve to one owner per shared native frame and restore any HUD settings on disable/uninstall.

## Preflight tool
`python -m tools.client_guard --game-root "C:\\path\\to\\game"`
This reads only PE/MPQ metadata and hashes and outputs a brief summary. Set `--all-mpq` to hash MPQs, and `--out artifacts/client-report.json` for a local structured report. Neither action runs the client nor proves compatibility.

## Release and source policy
Third-party code is **not vendored** as part of initial discovery. Upstream registry entries are metadata only.
