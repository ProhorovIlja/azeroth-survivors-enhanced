# Original Windows Options menu: code-level call graph, 0.136 vs 0.137

**Investigation date:** 2026-11-01. **Scope:** user's exact original Windows executables, inspected locally without running or changing them. This is an audit of the native original game's UI, not a Lua addon or a standalone external menu.

## Key advance

The game's `Options` subsystem contains a candidate **central Options controls/page-dispatch function**, with direct calls to separate **Saves page** and **AddOns page** code. This is substantially narrower evidence than Bevy type names alone. The candidate code is still **not an approved detour point, public API, or tested native-menu injection hook**.

### Candidate functions and disassembled call edges

| Inferred role, not a symbol name | Windows 0.136.0 backup | Windows 0.137.0 current |
| --- | --- | --- |
| Options page/control function | `0x3F5D60–0x3F7498` | `0x3F6A40–0x3F8178` |
| Saves content function | `0x12ED20–0x130155` | `0x12ECB0–0x1300E5` |
| AddOns content function | `0x130410–0x130F33` | `0x1303A0–0x130EC3` |
| Candidate parent function | `0x14F460` (start only) | `0x14F3F0–0x14FC6E` |

Windows 0.137 direct instruction sites, verified through an independent x86-64 disassembler:

1. Parent function `0x14F3F0` → Options controls `0x3F6A40`: `call` at `0x14FBB5`.
2. Options controls `0x3F6A40` → Saves content `0x12ECB0`: `call` at `0x3F7A43`.
3. Options controls `0x3F6A40` → AddOns content `0x1303A0`: `call` at `0x3F7AA1`.

The `.pdata` Windows unwind entries validate **function boundaries** for each code site. For 0.136, the corresponding call instructions also exist but at **different RVAs**: `0x14FC25`, `0x3F6D63`, `0x3F6DC1`. Addresses must never be reused between versions.

**Important correction to the earlier report:** The key at `0x12ED30` in 0.137 is `options.saves_about`, not `options.saves`; the latter was a partial prefix in the first scanner. The new longest-key-first parser avoids this false classification. This matters because a bad substring match can lead to a false hooking conclusion.

The probe finds **54 direct RIP-relative LEA candidates across 16 `.pdata` function clusters** in both exact EXEs, including a strongly related group of UI keys (`options.defaults`, `options.done`, `options.hint.*`) in the central Options function. The scan deliberately labels generic LEA matches as candidates because a byte-pattern search alone does not prove every match is a complete valid instruction. Three call edges above received independent disassembly confirmation.

## Why this is not a finished Cheats menu

- We have not identified the complete Bevy ECS page state, registration mechanism, event handler ABI or safe way to allocate/add a native node without disrupting existing event flow.
- No compatible **0.137.0** native DLL has been built and verified in a Windows game runtime.
- No God Mode, gold, XP, damage, save-change or other cheat backend is attached to the original Options UI.
- No original game's EXE, MPQ or save files were modified or published.
- The public co-op `avrt.dll` design is a technical reference only; its version profiles are not for 0.137.0, and the upstream repo currently does not grant a general code-reuse license.

## Reproduce safely

From this source project with an independently verified, private, user-owned game copy:

```powershell
py -m tools.native_options_xrefs --game-exe "C:\Games\AzerothSurvivors\AzerothSurvivors.exe" --out fresh-0137-options-refs.json
py -m tools.native_options_xrefs --game-exe "C:\Games\AzerothSurvivors\AzerothSurvivors.old" --out fresh-0136-options-refs.json
py -m unittest discover -s tests -v
```

The tool accepts **only** the following SHA256 fingerprints: 0.137 current `aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8` and 0.136 backup `eb744751b4e17ec1397b0cdc85a22af63b6af63c1da1d9c2861762c3c4d8947c`. It reads PE metadata, `.rdata` key names, `.text` reference candidates and `.pdata` bounds. Output is metadata only, not original machine bytes. Refuses unknown binary hashes and overwritten outputs.

`catalog/options_code_graph_0136_0137.json` contains small derived metadata only: both versions' candidate function clusters and call edges, not EXE contents.

## Next concrete engineering gate

Inspect **the central Options controls function and its call-site caller on a disposable Windows 0.137 copy**, identify page-state enum/dispatch, determine the Bevy ECS node creation and lifetime expectations, and implement a reversible native page-extension prototype. Only after a *real game* screenshot verifies a Cheats page inside the original menu should any actual cheat backend be connected. Keep permanent save/progress edits separately version-gated and backed up; never pass 0.119 trainer addresses into 0.137.
