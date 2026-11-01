# Native Options menu audit: owner's original Windows 0.137.0

## Current state

**We have NOT installed a native Cheats page or live God Mode into the original game.** The game is closed-source and no verified native menu insertion hook is available. This is a reproducible **read-only** map of the real, existing Options UI and the technical prerequisites for implementing the user's requested original-main-menu Cheats tab. The older in-game Lua Control Center (#15) and separate trainer GUI (#14) are *not* substitutes for that request.

### Original client evidence

Read-only inspection of the owner's exact 147,844,608-byte original `AzerothSurvivors.exe`, SHA-256 `aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8`, finds a native **Rust / Bevy ECS (`bevy_ui`)** UI, including the type and menu text evidence listed below. This distinguishes the main Options menu from WoW 1.12 Lua `FrameXML`, which controls addon frames and the in-run HUD.

Native type names seen in the original PE `.rdata`:

- `wenilla_rogue_app::screens::options::OptionsCanvas`
- `wenilla_rogue_app::screens::options::OptionsRoot`
- `wenilla_rogue_app::screens::options::PageList`
- `wenilla_rogue_app::screens::options::Footer`
- `wenilla_rogue_app::screens::options::Readout`, `Track`, `Fill`, `Act`, `TipText`
- `bevy_ui::ui_node::Node` appears in Bevy ECS registration strings.

The same data region includes `menu.main_menu`, `options.saves`, `options.import_save`, `options.export_save`, and `options.open_saves_folder` strings. **The mere existence of a type-name string is not proof of a callable extension API or of the runtime layout of the component.** The static scanner does not identify a verified hook or native cheat UI action.

The user's backup 0.136.0 has the *same counts of these particular UI registration and menu label strings* as 0.137.0, but this does **not** establish that their machine addresses or implementations are compatible.

### Reproducible owner-side probe

```powershell
py -m tools.native_menu_probe --exe "C:\Games\AzerothSurvivors\AzerothSurvivors.exe" --out native-options-audit.json
```

The command reads the file, verifies its *full original SHA-256*, checks PE32+ x64 section boundaries, and reports **metadata only** (component names, section names, string offsets/counts). It **never launches the game, changes bytes, loads any DLL, contacts a server or writes an existing file**. An unknown EXE fails closed. The output `native-options-audit.json` is a new file and can be reviewed without sending the original EXE anywhere. Synthetic tests validate the source.

### Existing community native infrastructure: not plug-and-play

- [Ffive55 trainer v3.3.1](https://github.com/Ffive55/azeroth-survivors-trainer) has *actual* invulnerability, one-hit and run-stat hooks, but **only for the specific original game 0.119.0 executable**; offsets/machine patterns are unsafe to reuse for 0.137.0.
- [Azeroth Survivors Together audit source](https://github.com/bymarvin/azeroth-survivors-source) exposes its `avrt.dll` proxy design, byte verification and rollback checks, but public `payload/builds` contained only **0.99.0 / 0.100.1** during this review, not a 0.137 profile. It hooks gameplay for an independent co-op mod, not a ready-made native Options extension.
- [OutThisLife/azeroth-survivors-re](https://github.com/outthislife/azeroth-survivors-re) is a **different independent recreation**, *not* source code of Aethus's executable; modifying its Rust Options menus would not add a page to the user's original EXE.

No external source is copied into our project by this audit.

## Gates for the genuine requested result

1. Find and **uniquely verify** the exact original 0.137.0 Options page-construction and event-dispatch logic, including its expected prologue bytes and thread context.
2. Prototype a native Rust/Bevy UI insert point for the **existing** Options page without replacing the Lua addon UI, and verify in an isolated Windows copy that the new menu opens/closes and remains input-safe.
3. Hook a real 0.137 gameplay operation only after finding unique, independently validated state addresses, with reversible changes and immediate failure when unsupported patches or versions are detected.
4. Integrate separately tested persistent-progress changes, with private backups and **readback** from the original game, and no automated changes to any public/co-op session or original saves.
5. Demonstrate actual in-game native UI screenshots and exact client version, end-to-end test results and restoration before any release.

**No game runtime tests or native hook installation were performed for this audit.** Older experimental branch and Lua addons remain separate and do not satisfy this task.
