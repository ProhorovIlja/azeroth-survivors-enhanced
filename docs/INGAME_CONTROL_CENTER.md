# AZSE In-Game Control Center (developer preview)

This is an **actual in-game** WoW 1.12 Lua addon for the Windows Azeroth Survivors client, not a separate app. There is a movable **AZSE** on-screen launcher and `/azcc` or `/azmenu` chat commands. It does not require Python or an external GUI.

## Installation (game fully closed)

In game choose **Options → AddOns → Open AddOns Folder** to discover your real AddOns directory, then quit the game. Copy the enclosed folder `AZSEControlCenter` (not the outer ZIP directory) into that AddOns folder. The result must be:

`benilla-config/AddOns/AZSEControlCenter/AZSEControlCenter.toc`

Restart the game and ensure **AZSE Control Center** is enabled in Options → AddOns. In the run, type `/azcc`. You can also drag and click the small **AZSE** button. To restore the game's HUD quickly, type `/azcc reset`.

## Working features

- In-game Dashboard displaying game phase, run time and damage meter statistics when the official API exposes them.
- Eight per-section HUD visibility toggles (clock, bosses, kills/gold, build, banners, loot, damage meter, level-up panel), using the *actual* `AZS_SetHudShown`/`AZS_IsHudShown` APIs.
- Show/hide all game HUD parts.
- Store new level-up choices and open stored level-up cards using `AZS_SetStoringLevels`, `AZS_OpenStoredLevels` and related getters, **not** spawning free levels.
- Built-in configuration: menu scaling, draggable menu and AZSE launcher, SavedVariables persistence (`AZSCC_DB`).
- Build status and diagnostics that don't modify the run.

## What about God Mode, money and unlocks?

The **Cheats** tab is a capability status page, not a pretend cheat engine. The public addon API reads game data and controls presentation and banked level-up UI, **not** health, damage, gold, XP, rerolls, loot or account unlocks. Each unavailable option explicitly states that no effect was applied. Full trainer functionality requires a separately validated original Windows 0.137-native integration, or changes to a backed-up single-player save via an editor. Old 0.119 and 0.127 DLL trainers must not be injected into 0.137 without compatibility research.

## Boundaries

- No EXE/MPQ changes, injected DLLs, memory hooks, save edits or game downloads.
- Lua 5.0 patterns, `## Interface: 11200`.
- UI has **not yet** been tested inside the user's actual running 0.137 client. Interface colors/spacing/controls may require compatibility fixes after a screenshot or error log.
- This is separate from `AZSEnhancedAdvisor` and can coexist if they don't overlap the same frame areas.
- No proprietary game assets or third-party addon code bundled.
