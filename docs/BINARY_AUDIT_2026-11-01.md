# Original binary audit: first safe inspection (2026-11-01)

## Source / handling
Original files were received from the owner's private Google Drive. They were downloaded into an isolated read-only analysis workspace. **Nothing was executed, modified, decompiled into source, extracted into this repository or redistributed.** Game proprietary bytes remain private.

## Windows client
- File: `AzerothSurvivors.exe`
- Size: 139691008 bytes
- SHA-256: `2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a`
- File signature: `MZ` / `PE\0\0`
- PE machine: `0x8664` (x86-64), optional header `0x20b` (PE32+)
- PE timestamp field: 2026-10-19T18:16:50Z. **This is only a header field, not a reliable game version or verified build date.**
- Embedded symbol/text matches: `AZS_GetPhase`, `AZS_GetMeter`, `wenilla-rogue`, `benilla-config`, `AddOns`.
- No reliable `VS_VERSION_INFO` / `FileVersion` resource found by basic signature search. Version `0.135.1` not found as a literal ASCII string, but **absence does not prove a different build**.

These checks confirm strings exist in the binary, not that APIs behave correctly at runtime.

## Sample MPQ index check
- File: `Data/patch-6.MPQ`
- Size: 212228 bytes
- SHA-256: `cad6ff59b5df028a507581befb836fce07894057e15fe63d9fdc553a95b7ceb5`
- Header begins `4d 50 51 1a` (MPQ magic).
- Declared archive size in MPQ header equals file size.
- Archive format field `0`, with 16 hash-table entries and 4 block-table entries.

No MPQ payload files were extracted.

## Pending validation
- Compute hash and inspect remaining six MPQs if required, without shipping them.
- Determine true game version from authoritative in-game or internal version source, not inference.
- Verify Lua 1.12 addon load and documented API in an isolated running game.
- Check any game-content modifications only when license and technical constraints permit.
