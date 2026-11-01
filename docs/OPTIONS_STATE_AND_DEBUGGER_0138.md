# Original Windows 0.138 Options: verified native page model

**Status:** evidence-based **read-only** analysis of the user's exact original Windows EXE. This document does **not** claim a native Cheats page, a working native hook, God Mode, or in-game testing.

The reviewed original user executable is 147,995,648 bytes; SHA-256 `eb5fd1c1b96e6180fcf5f3d685d90a61471af28d22e5f060c02b7b7663fbf79e`. Analysis is strictly version gated. No original binaries, MPQs, saves or proprietary UI text descriptions are distributed.

## New evidence beyond the page-call graph

Within the already-confirmed central Options function (RVA `0x3F74C0`), an additional independent selector read at `0x3F877C` performs `movzx eax, byte ptr [r13+0x1DA]`, subtracts 1, checks the index against 10 and jumps through a **signed 32-bit 11-entry jump table in `.rdata`, RVA `0x635C970`**. The jump-table entries lead to separate UI-hint construction handlers.

| Observed selection value | Key chosen by original machine code | Local hint-handler RVA |
| ---: | --- | --- |
| `1` | `options.hint.gamepad` | `0x3F879B` |
| `6` | `options.hint.keybindings` | `0x3F87B7` |
| `10` | `options.hint.addons` | `0x3F87A9` |
| `11` | `options.hint.saves` | `0x3F87C5` |
| `2–5`, `7–9` | Generic `options.hint` | `0x3F87D3` |

The keys were checked against original **key identifiers**, without copying the actual proprietary display text. This establishes the page-selector-to-hint relationship, not which hidden Bevy ECS action constructs a new tab.

The same Options routine loops over UI **records**, with stride `0x98` (152 bytes) and byte bound `0x4020`, or **108 record slots**, checking record ID at `record+0x91` against the selected page byte at `state+0x1DA`. The loop instructions were checked at `0x3F8420`, `0x3F8443`, and `0x3F8487`. **108 is NOT the number of pages/tabs**; these are internal UI record slots. Their record type and writable state layout have *not* been proven.

Direct page-content calls from earlier verified work remain: Saves `0x1021E0` from `0x3F84C3` and AddOns `0x1038D0` from `0x3F8521`. The pointer and layout changes between Windows versions; never apply 0.137 addresses on 0.138.

## Reproducible offline source-only checks

Run from the repository root, Python 3.10+:

```powershell
py -m tools.native_options_state_model --game-exe 'C:\Games\AzerothSurvivors\AzerothSurvivors.exe' --out 'options-state-0138.json'
```

The utility checks the entire EXE SHA, exact reviewed x64 instruction encodings, image-section bounds, jump-table targets, and individual public UI key names before reporting. Unknown EXEs or altered signatures fail closed. `--out` must be a NEW file, never an overwrite. The example output is in `catalog/options_state_model_0138.json`.

### Optional *non-shipping* Windows debugger investigation

A separate helper can generate a WinDbg command file:

```powershell
py -m tools.native_options_runtime_trace --game-exe 'C:\Games\AzerothSurvivors\AzerothSurvivors.exe' --out 'azse-options-trace.txt' --log-path 'C:\AZSE\options-page-trace.log'
```

**The command above only generates text. It does not attach to the game or change any file except its new output text file.** The resulting script is provided as a research recipe, **not validated on a live Windows 0.138 process**.

If an advanced tester chooses to try it, they should first create a disposable, fully backed-up **offline solo copy** of their Windows game, create the `C:\AZSE` log directory, attach WinDbg to that process, then execute `$$< azse-options-trace.txt` in the debugger. The script uses a single **hardware execution breakpoint** (`ba e 1`), not an executable-code patch. At the known selector read, it attempts to record **changes of the numeric selected page** only. It never writes a gameplay value. The debugger still **pauses/interferes with game timing** and could crash a run. Do not attach in co-op/online or competitive sessions. Never share whole debugger logs blindly.

For the exact command reference, see official Microsoft WinDbg documentation: [hardware breakpoint `ba`](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/ba--break-on-access-), [user pseudo-registers](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/pseudo-register-syntax), [scripts](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/using-script-files), and [`gc` continuation](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/gc--go-from-conditional-breakpoint-).

**No user needs to run this diagnostic to use the game.** Do not mistake it for a downloadable mod or working in-game Cheats toggle.

## Actual remaining blockers for requested native Cheats page

1. Verify the runtime selector's owning Bevy resource/entity and actual page-state transitions while the genuine main Options menu is open, preferably using safe diagnostic logging on a fully backed-up offline Windows test copy.
2. Identify the actual Bevy widget/entity construction and event/dispatch lifecycle with a unique, version-validated insertion point. The jump table above selects *hint labels*, **not** a complete page creation function.
3. Implement a reversible native menu insertion with failure rollback and input handling, unique to the reviewed EXE. Never substitute Lua frames or a separately layered Windows window when the user requested native Options.
4. Independently locate/verify single-player cheat backends for 0.138 (HP, damage, loot, currency, unlocks). Existing old trainers are for 0.119 and have **not** been ported or run on 0.138.
5. Only call a cheat functional after direct on-screen proof and readback in the actual original game, and preserve private saves, original EXE and MPQs.

Source-only tests are synthetic. A successful test suite does not establish real-game integration or gameplay effects.
