# azeroth-survivors-enhanced

## Original Windows main Options menu reconnaissance (0.137.0)

The owner asked for an **actual Cheats tab in the original native menu**, not a Lua/desktop imitation. A read-only full-SHA-gated PE probe now maps the original client's Rust/Bevy ECS Options UI (`OptionsCanvas`, `OptionsRoot`, `PageList`, `Footer`) and existing save/import menu labels. No hook or native Cheats page is verified yet. It refuses unknown EXEs and never executes/patches the game.

```powershell
py -m tools.native_menu_probe --exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe" --out native-options-audit.json
```

See `docs/NATIVE_OPTIONS_0137.md`, `catalog/native_options_0137_audit.json` and [native menu issue #16](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/issues/16). Real native cheat toggles and main-menu insertion remain **unimplemented and untested**.


### Verified native Options call graph, original Windows 0.137

Read-only inspection of the user's exact original EXE identified a candidate central Options function `0x3F6A40–0x3F8178`; its direct x64 calls to Saves (`0x12ECB0`) and AddOns (`0x1303A0`) were independently disassembled. The 0.136 backup has **different addresses**. `tools.native_options_xrefs` now maps exact-key references and `.pdata` function bounds without any binary edits or installing a DLL. The two known snapshots have **54 direct key-reference candidates in 16 function clusters** each.

```powershell
py -m tools.native_options_xrefs --game-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe" --out options-xrefs-0137.json
```

See `docs/OPTIONS_CODE_GRAPH_0137.md`. The original native Cheats page, God Mode and in-run edits are **not yet implemented**; a candidate function is not a safe hook until the Bevy ECS page lifecycle and Windows runtime have been verified.
