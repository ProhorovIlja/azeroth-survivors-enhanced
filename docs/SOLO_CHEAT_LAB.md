# Solo Cheat Lab (developer preview, 2026-11-01)

A local, **opt-in** environment for experimenting with game saves and mods on an owner-controlled **single-player** copy of original Azeroth Survivors. It is not a memory trainer or God Mode implementation. It does not auto-edit progression, grant gold or unlock achievements. Use a separate community editor on an **export made while running the sandbox**, then import the edited `.sav` into the sandboxed game.

## Why this tool exists

The original Windows game supports `WOW_ROGUE_SAVE`, an environment variable pointing at the primary `characters.txt` save. The name was verified as a literal in the user's 0.137.0 EXE and independently documented by [oppahansi's editor](https://github.com/oppahansi/azssaveeditor). We use it for a fresh, separate **sandbox save**. This does **not** sandbox settings, online/co-op services, network traffic, machine memory or any other storage the game might touch. Do not use cheats in shared/co-op or leaderboard runs.

### Start safely (Windows, Python 3.10+)

Close the game before preparing and editing. Open a PowerShell terminal in the Enhanced Edition repo root. Replace the game path below with your actual installation. The live save is normally `%APPDATA%\wenilla-rogue\characters.txt`; you may instead supply `--save-source` explicitly.

```powershell
py -m tools.solo_lab inspect --game-exe "C:\Games\AzerothSurvivors\AzerothSurvivors.exe"
py -m tools.solo_lab prepare --game-exe "C:\Games\AzerothSurvivors\AzerothSurvivors.exe" --sandbox-dir "$HOME\Documents\AZS-SoloLab-01" --yes
py -m tools.solo_lab status --sandbox-dir "$HOME\Documents\AZS-SoloLab-01"
py -m tools.solo_lab launch --sandbox-dir "$HOME\Documents\AZS-SoloLab-01" --yes
```

- `inspect` is **read-only**. `prepare` creates a NEW sandbox directory only, copies the current primary save to `characters.txt` and an unchanged baseline, checks both SHA-256, and stores a small `solo-lab.json` manifest. It never overwrites a pre-existing folder.
- `launch --yes` is Windows-only and starts your **verified original game EXE** with `WOW_ROGUE_SAVE` set to `<sandbox>/characters.txt`. The source game and normal save are not modified by our launcher. The game may affect OTHER configuration/online systems: use single-player mode, offline where available, and keep your main save backed up.
- If the game's EXE hash differs from the known 0.137.0 user snapshot, launch refuses. This is deliberate until the new update is audited. **No unknown-process injection, trainer or DLL loading**.
- When the sandboxed game is running, choose **Options → Saves → Export Save**, then use a trusted save editor to work on the exported copy. Import the edited `.sav` back **in the sandboxed game**. The import replaces the sandbox's saved progression; it does not merge newer progress.
- Fully exit the sandboxed game before snapshots/restores. Don't run the sandbox and main game at the same time.

### Undo, inspect, and compare

```powershell
py -m tools.solo_lab snapshot --sandbox-dir "$HOME\Documents\AZS-SoloLab-01"
py -m tools.solo_lab status --sandbox-dir "$HOME\Documents\AZS-SoloLab-01"
py -m tools.solo_lab restore --sandbox-dir "$HOME\Documents\AZS-SoloLab-01" --yes
```

`restore` first preserves the modified sandbox save in `snapshots/`, then resets only the sandbox `characters.txt` to the verified original baseline. It never writes the normal `%APPDATA%` save. Stop if the baseline checksum is invalid. Back up the entire original game save independently before importing third-party edits.

### Available cheat-editing workflows

- **Unlock gear, stars, class marks, zones**: see [FlixxFlix/AzerothSurvivors-SaveEditor](https://github.com/FlixxFlix/AzerothSurvivors-SaveEditor), an MIT source repo describing a local-only HTML export editor. *Current 0.137.0 compatibility has not been proven*. It uses RSE1 export verification and produces `.sav` files.
- **Talent XP, collection, 9 classes and zones**: [yssadora's browser-based editor](https://yssadora.github.io/azeroth-survivors-editor/) processes imported `.sav` locally in the browser. Its repo does not expose a clearly verified license; **link only, don't vendor its code**. Some edited progress has reportedly reverted after runs in Firefox. Use a private copy and test persistence.
- **Full 100% progression**: [oppahansi/azssaveeditor](https://github.com/oppahansi/azssaveeditor), MIT, supports Fill 100%, all three specs and a sealed RSE1 save, but last tested on original game **0.104.0**. High version-drift risk with 0.137.0; don't assume it works.
- **God Mode, one-hit kills, resource multipliers**: [Ffive55 trainer](https://github.com/Ffive55/azeroth-survivors-trainer) reports 36 functions but its v3.3.1 explicitly targets **0.119.0**. **Do not run on your 0.137.0 EXE** without current-source review, exact hash compatibility, antivirus checks and an isolated native sandbox. No code is integrated here.
- **Time dilation**: [AZS Speed Controller](https://github.com/Maidenquinn/AZS-Speed-Controller), MIT native hook, demonstrated at **0.127.0**, not validated on 0.137.0. [AzerothSurvivorsSpeedGear](https://github.com/fubukisama/AzerothSurvivorsSpeedGear) is GPL-3.0 and provides an in-game speed UI, but actual 0.137 compatibility and runtime behavior need verification. Do not install either automatically.

### Other enhancements you can audit safely

Run `py -m tools.addon_audit --game-root "C:\Games\AzerothSurvivors"` to report installed addon folders, TOC interface version (usually `11200`) and likely HUD, cursor or DPS-meter conflicts. This only reads plain-text TOC metadata. It cannot tell whether an addon is enabled or working, and does not execute Lua.

Recommended candidates for later manual testing: ECProbe (read-only API exploration), TotemWatch (totem caps), EnemyCounter (living enemies), LuckyOdds (card odds and caches), MoveUI and KeijinUI (HUD), ASBuilder v1.11.0 (0.137 Shaman), AZSMaxHit v1.3.3 (fixed proc attribution). See `catalog/cheat_tools.json` for provenance, licensing and current compatibility warnings. Competing HUD replacements should not all be enabled simultaneously.

## Privacy and distribution

Only your own game files should be edited. No original EXE/MPQ, unlock keys, personal saves, extracted WoW content or third-party binaries are distributed in this project. A public GitHub repository does not automatically grant permission to reuse code without a license. External editors and trainers are listed by reference, not bundled, auto-launched or trusted by default.

## Limitations

- Our tool protects the **primary game save path by redirecting it**, but the game may still write global settings or contact network services. This is not an OS-level sandbox, virtual machine, or airtight anti-cheat boundary.
- Read-only Python synthetic tests do **not** establish that 0.137.0 applies a sealed edited save correctly after a full run.
- No actual trainer, invulnerability, gold injection, speed modification or save decryption is performed by Solo Lab itself.
- The original game is updated frequently. Re-check EXE SHA and saved progress after each update.


## Optional graphical control panel

On Windows with Tkinter installed, run `py -m tools.solo_lab_gui` from this repository root. This opens a local, dark-themed Russian-language GUI for selecting the game EXE, save path and new sandbox directory, checking client SHA, creating the sandbox, launching explicitly, making snapshots, restoring only sandbox saves and auditing existing addon .toc files. The buttons for creation, launch and restore require explicit confirmation. External editor links open the verified project page, **not** downloaded installers. The GUI does not itself provide memory hooks, God Mode or save editing and has not been smoke-tested on an actual Windows display.
