# azeroth-survivors-enhanced

## Original Windows main Options menu reconnaissance (0.137.0)

The owner asked for an **actual Cheats tab in the original native menu**, not a Lua/desktop imitation. A read-only full-SHA-gated PE probe now maps the original client's Rust/Bevy ECS Options UI (`OptionsCanvas`, `OptionsRoot`, `PageList`, `Footer`) and existing save/import menu labels. No hook or native Cheats page is verified yet. It refuses unknown EXEs and never executes/patches the game.

```powershell
py -m tools.native_menu_probe --exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe" --out native-options-audit.json
```

See `docs/NATIVE_OPTIONS_0137.md`, `catalog/native_options_0137_audit.json` and [native menu issue #16](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/issues/16). Real native cheat toggles and main-menu insertion remain **unimplemented and untested**.
