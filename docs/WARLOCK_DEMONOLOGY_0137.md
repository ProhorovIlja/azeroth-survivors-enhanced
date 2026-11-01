# Windows 0.137 Demonology Warlock | low-input / AFK research

This document is **not a best-in-slot or full 51-point talent build**. It is an actionable research protocol using short names and mechanical restrictions observed in the user's exact original Windows 0.137 EXE, plus public checks of the [0.137 browser state](https://survivorsdb.com/azeroth-survivors/tier-list) and [Demonology patch notes](https://azeroth-survivors.org/blog/patch-notes/). Original binary SHA-256: `aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8`.

## Why the earlier Imp/Felguard build no longer suffices

The game binary contains an older, retained 27-tree English dictionary, including `Demonic Pact`, `Summon Imp` and `Summon Felguard`. It **also** contains a newer Demonology name set: `Demonic Familiar`, `Legion Gate`, `Summon Infernal`, `Summon Doomguard`, `Demonic Supremacy`, `Pact of the Nathrezim` and `Butcher`. The older strings should be treated as **historical localization evidence**, not current class nodes.

## Two candidate experiments

**A. Constant stream of lesser demons (hypothesis).** Explore `Demonic Familiar` plus `Legion Gate` with a carefully chosen capstone. The candidate plan relies on an Imp and a stream of smaller temporary summons. Verify actual talent prerequisites and minion caps in-game. Do **not** assume it combines usefully with `Demonic Supremacy`.

**B. Permanent major demons (hypothesis).** Explore `Summon Infernal`, `Summon Doomguard`, then `Demonic Supremacy` if the original 0.137 in-game talent tree permits it. The client's text states that Supremacy makes the Infernal/Doomguard permanent but prevents lesser demons from being summoned. This may better support remaining stationary, but there are **no measured numbers** yet. Again, choose **one**, not both, of `Butcher` or `Pact of the Nathrezim`.

**Known source-based restriction:** The 0.137 description explicitly marks `Butcher` and `Pact of the Nathrezim` as exclusive capstones. Build Studio now rejects a draft containing both. Supremacy vs `Legion Gate` is marked as a *strategic warning*, not a proven exclusive talent edge.

## Experimental protocol (to decide the actual winner)

Use an isolated copy of Windows 0.137 and fix character level, race, difficulty, zone, hero perks, equipment, and card/upgrade priorities as far as the game permits. For each candidate run:

1. Confirm talents are genuinely visible, allocatable and their prerequisites/ranks. Screenshot the exact tree. Invalid routes stop immediately.
2. Record identical target duration and run at least three comparable trials per candidate where practical. Maintain **zero movement** for the main trial except a separately logged item-collection variant.
3. Record survival time, kills per minute, boss kill time, damage by source, minion uptime, healing, and unavoidable/avoidable deaths. Never claim total DPS from screenshot alone.
4. Compare against at least Affliction and a low-input Shaman experiment under similar conditions. Note differences in RNG and any player interaction.
5. Keep checksums and game version fixed. Stop using data across an update boundary until the new client and addon behavior are verified.

**Metric reliability note:** AZSMaxHit v1.3.3 fixes proc/overkill attribution; a largest-hit record is not the same as sustained DPS. Use per-spell damage meters with explicit methodology rather than relying on one lucky critical hit.

Neither path is automatically best. A legal 51-point allocation, BiS race/items, passive ratios, survivability and actual damage ranking still require the real game.
