# Exact original Windows client talent fingerprint | 2026-11-01

## Why this matters

The player's uploaded `AzerothSurvivors.exe` (SHA-256 `2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a`) contains an **English localization name table** representing older talent definitions than the publicly documented browser v0.135.1 game. This is genuine read-only inspection of the uploaded EXE, **not an in-game runtime test**. We do **not** claim an exact Windows version from this evidence.

### Original binary string evidence

| Talent name / feature label | Original uploaded Windows EXE |
| --- | --- |
| `Demonic Pact` | present as English localization label |
| `Summon Imp` | present |
| `Summon Felguard` | present; nearby English localization calls it a capstone |
| `Legion Gate` | not found as an ASCII or UTF-16LE literal |
| `Demonic Supremacy` | not found as a literal |
| `Pact of the Nathrezim` | not found as a literal |
| `Windfury` | present; nearby English localization calls it a milestone |
| `Feral Spirit` | present; nearby English localization calls it a capstone |
| `Rockbiter Weapon` | not found as a literal |
| `Stormstrike` | not found as a literal |
| `Stormbound Echoes` | not found as a literal |

The absence of a string is **not proof a mechanic is impossible** (content may be encoded, generated or localized differently). A match supports an observed label, **not** confirmed active gameplay or talent availability. However paired legacy-positive and newer-negative labels are reliable enough to **warn against recommending modern-only builds**.

### Public browser guide comparison

[Warlock guide](https://azerothsurvivorsgame.com/builds/warlock/) (published November 1, version stated v0.135.1) lists Legion Gate, Pact of the Nathrezim and the different Demonology summons. [SurvivorsDB v0.135.1](https://survivorsdb.com/azeroth-survivors) reports v0.134 Enhancement restructuring to Rockbiter/Stormstrike. These are third-party observations of the browser client, not proof of a version number for the supplied Windows EXE.

### What can be recommended safely

Legacy Demonology **research starting points**: `Summon Imp`, `Demonic Pact` and `Summon Felguard` are named in the owner's binary. The English strings suggest an Imp permanent minion, additional temporary Imps from kills, and a Felguard capstone with cleave; these interactions are **not runtime verified**. A planned 51-point talent route, best race, best gear and damage output are not yet verified, and should not be invented.

Legacy Enhancement **research starting points**: `Windfury` and `Feral Spirit` appear in the owner's binary; the older Feral Spirit entry mentions two wolf companions and Windfury interaction. Do not recommend the newer Rockbiter/Stormbound capstone until the actual client supports it.

### Implemented safeguard

`python -m tools.talent_probe --game-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe"`

The tool streams binary content, reports observed English-label groups and a **tentative family** (legacy/modern/mixed/unknown). It gives no auto-patching permission. For strict modern-profile requirement use `--require-modern`; that fails closed on legacy/mixed/unknown.

`catalog/client_profiles.json` keeps only the known SHA and small labels, no original localization text/MPQ or executable bytes. The profile is not an OS executable signature or proof of game version.

### Follow-up

1. Run game in isolated Windows copy for version dialog, talent tree and addon API testing.
2. Capture sanitized screenshots and read-only performance trace of Warlock and Shaman; confirm exact 51-point legality.
3. Keep browser-modern and desktop-legacy build alternatives **separate** until measured.
4. Compare current download's EXE SHA to the owner snapshot if a new archive arrives.
