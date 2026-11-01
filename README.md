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

**Native 0.138 page-selector branch evidence:** the exact client reads a state byte at displacement `0x1DA` within the central Options function, compares it to `0x06`, `0x0A` and `0x0B`, and branches to observed Saves/AddOns handlers. `tools.native_options_dispatch` validates these original instruction patterns read-only against a strict SHA. It **does not** provide a safe write/hook API or any functional cheat toggle. Four re-uploaded small MPQs (8/9/A/B) are SHA-256 identical to earlier copies; the other seven remain unverified. See `docs/WINDOWS_0138_NATIVE_OPTIONS.md`.

### Native Options selector and menu-record model (0.138)

Directly verified on the user's **exact original** Windows 0.138 EXE, the Options selector at state+0x1DA also feeds an 11-entry jump table of **hint-label handlers**. Values 1/6/10/11 map to Gamepad/Keybindings/AddOns/Saves hints, and a 108-record UI iteration searches entries of 0x98 bytes by page ID at record+0x91. This advances the **actual native menu state/record model**, not a confirmed safe widget insertion mechanism. `tools.native_options_state_model` generates a strict SHA/instruction-validated read-only report. `tools.native_options_runtime_trace` optionally creates a **WinDbg hardware-breakpoint script** for expert offline solo testing (never automatically attaches). Details in `docs/OPTIONS_STATE_AND_DEBUGGER_0138.md`. The native Cheats page and combat cheats are **not yet implemented**.

### Correction: Options descriptor table is tooltip/control data, not a new-tab registry

Review of the exact original 0.138 EXE has identified all 108 descriptors at `.rdata` RVA `0x6316970`: 69 localization-key tooltip entries, 36 inline help records, three separators, with 152-byte stride. Records have page/group ID at `+0x91` and dependency byte at `+0x90`; group 6 (Keybindings) and 11 (Saves) have no descriptor rows because their pages use specialized handlers. Both original descriptor-consumer call sites (`0x3F8464`, `0x3F84A4`) invoke the same shared routine `0x105810`, **which is not a verified native page hook**. New `tools.native_options_descriptors` checks the actual original client's SHA, PE bounds, type fields, target calls and reports metadata without exporting proprietary UI prose. Details `docs/OPTIONS_DESCRIPTOR_RENDERER_0138.md`. This removes an incorrect candidate for creating a real Cheats page; native Bevy page insertion and real cheats remain unimplemented.

### Native 0.138 localized Options action-widget path: original footer buttons

Direct original Windows disassembly and SHA-gated binary read now identify **8 direct callers** of a shared localized-action-widget helper at RVA `0x107FA0`. In the central Options function, two exact calls instantiate **Defaults (low action tag 16)** and **Done (low action tag 17)**; a verified jump skips Defaults for Saves but still creates Done. This is **real clickable-control construction evidence**, unlike the prior 108-row tooltip array, but **not a verified click-event handler or new-tab API**. New `tools.native_options_actions` and 15 synthetic tests; see `docs/OPTIONS_ACTION_WIDGETS_0138.md`. The native Cheats page and gameplay cheats remain unavailable until actual Windows runtime integration.
