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

### Reviewed original Windows 0.138.0 binary

The user's new Windows EXE (147,995,648 bytes, SHA-256 `eb5fd1c1b96e6180fcf5f3d685d90a61471af28d22e5f060c02b7b7663fbf79e`) contains the embedded version literal **0.138.0**. The native Options reference graph moved to central `0x3F74C0`, Saves `0x1021E0` and AddOns `0x1038D0`. All three direct call instructions were independently checked. The English text dictionary matches the prior 0.137.0 (3,334 keys, zero key or value changes). GitHub's last official manifest snapshot still reported 0.137.0, pending a later remote recheck. Strict SHA allowlisting protects against applying 0.137 offsets to 0.138. Details: `docs/WINDOWS_0138_NATIVE_OPTIONS.md`.

**Native original-game Cheats page and in-run gameplay cheats are not implemented yet.** This is source-only analysis, not a native trainer or DLL.
