# Windows 0.138.0: original-game Options call graph and update audit

Date: 2026-11-01. Owner explicitly replaced their private Google Drive game files. **No original executable, MPQ, localization prose or trainer payload is included in this public source project.** Original game has not been launched, modified, or injected into.

## Verified owner-supplied client

| File evidence | Windows 0.137.0 prior | Windows 0.138.0 current |
| --- | --- | --- |
| `AzerothSurvivors.exe` size | 147,844,608 bytes | **147,995,648 bytes** |
| Whole-file SHA-256 | `aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8` | `eb5fd1c1b96e6180fcf5f3d685d90a61471af28d22e5f060c02b7b7663fbf79e` |
| Version embedded in compiled Windows executable | `0.137.0` | **`0.138.0`** |
| PE header linker timestamp (not a version guarantee) | previous snapshot | 2026-11-01 18:56:13 UTC |
| Original Bevy Options components | present | present |
| Embedded English locale keys | 3,334 | **3,334** |
| English locale added/removed/changed values | comparison basis | **0 / 0 / 0** |

The owner re-uploaded 11 MPQ patch archives into their private Drive folder; **all 11 currently match their earlier file sizes**. Re-upload timestamps and equal sizes do *not* establish identical content. No MPQ content or full hashes were re-audited in this turn.

## Native Options function positions changed again

The **new** exact-hash-gated x64 PE scanner verified `.pdata` unwind boundaries and 54 direct localized-key load patterns in 16 function clusters. Independent LLVM disassembly of **all three** direct calls confirms their machine instructions actually resolve to the expected functions. RVA denotes a relative virtual address, not a portable absolute memory address.

| Candidate role | Windows 0.137.0 RVA | Windows 0.138.0 RVA |
| --- | --- | --- |
| Parent function that calls central Options | `0x14F3F0` | `0x1229A0` |
| Central Options controls | `0x3F6A40` | **`0x3F74C0`** |
| Saves page content | `0x12ECB0` | **`0x1021E0`** |
| AddOns page content | `0x1303A0` | **`0x1038D0`** |
| Parent-to-Options call site | `0x14FBB5` | `0x123165` |
| Options-to-Saves call site | `0x3F7A43` | `0x3F84C3` |
| Options-to-AddOns call site | `0x3F7AA1` | `0x3F8521` |

These addresses are **metadata, not vetted detour instructions or an injectable ABI**. The Options UI is built by Rust/Bevy ECS systems. A concrete function call is a useful research seam, not a validated safe insertion point for a new panel or a read/write game cheat.

## External update-manifest caveat

The EXE still embeds `https://wow.aethus.pl/exe/latest.json` and `https://wow.aethus.pl/exe/data/patches.json`. The GitHub monitor in the default branch last recorded **0.137.0** at the time of this audit, not 0.138.0. Official JSON was not readable through the chat's public web connector; an upcoming GitHub Actions scheduled check can establish whether the remote manifests changed. Do not infer the hosted manifest version from the EXE or claim it is already updated.

## New tools and validation

- `tools/native_options_xrefs.py`: now accepts only explicitly reviewed 0.136, 0.137 and **0.138** EXE SHA-256s. Exact unknown versions still fail closed. No network, game launch, patch writing or native hooks.
- `tools/native_menu_probe.py`: supports the reviewed 0.137 and 0.138 clients. The original 0.137 name/field is retained for prior test compatibility; adds `known_owner_0138_client` and `observed_version_label`.
- `catalog/options_code_graph_0138.json`: derived counts and RVA/call-site evidence only.
- `catalog/locale_delta_0137_0138.json`: key *names* and aggregate counts, no proprietary localized text.
- Dedicated synthetic version-gating tests. The actual user EXE was also inspected **read-only** in the private analysis environment.

## What is still missing for a real original main-menu Cheats page

1. Confirm the Bevy ECS page state and event handler for selecting Options tabs with a **running** 0.138.0 Windows client.
2. Establish a version-locked, rollback-capable integration route into its native UI. Do not use offsets or original bytes from 0.119/0.137.
3. Wire only independently verified cheat actions with actual value readback (HP, gold, XP, damage) in **solo play**. No mock toggles, native DLL guesses or original game redistribution.
4. Record a genuine Windows screenshot and test result before describing the native menu or cheats as implemented.

The user's requested **native Cheats & Enhancements page is not yet installed or functional**. This document is an evidence-backed step toward it, not a release.
