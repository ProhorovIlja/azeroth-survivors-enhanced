# azeroth-survivors-enhanced

## Solo Cheat Lab (single-player, source-only preview)

Opt-in Windows sandbox for experimenting with **your own** Azeroth Survivors save, without writing to the default primary save file. Uses the game's `WOW_ROGUE_SAVE` override, a copy-on-create baseline, SHA-256 integrity checks, snapshot/restore and explicit local launch. The sandbox does **not** isolate global settings/network/co-op, and this source code does **not** itself grant invincibility, gold, achievements or alter combat.

```powershell
py -m tools.solo_lab inspect --game-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe"
py -m tools.solo_lab prepare --game-exe "C:\\Games\\AzerothSurvivors\\AzerothSurvivors.exe" --sandbox-dir "$HOME\\Documents\\AZS-SoloLab-01" --yes
py -m tools.solo_lab launch --sandbox-dir "$HOME\\Documents\\AZS-SoloLab-01" --yes
py -m tools.solo_lab restore --sandbox-dir "$HOME\\Documents\\AZS-SoloLab-01" --yes
py -m tools.addon_audit --game-root "C:\\Games\\AzerothSurvivors"
```

**Only original game EXEs with an audited SHA are allowed.** Run on a personal offline/single-player copy only, never in shared/competitive sessions. For save-editing and real cheat tool links, version risks and detailed commands, see `docs/SOLO_CHEAT_LAB.md` and `catalog/cheat_tools.json`. The official update JSON watcher in `main` remains independent and does not automatically patch game files.
