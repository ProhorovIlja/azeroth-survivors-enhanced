# Offline addon-only installation and rollback

This tool is a developer preview for the self-authored AZSEnhancedAdvisor addon only. It never writes the original executable, MPQ files, saves, other addons or game data, and cannot automatically apply talents. A successful offline test is not proof that the addon runs in the game.

## Desktop installation workflow

Close the game completely. In Windows, check Options > AddOns > Open AddOns Folder to verify the actual AddOns directory. For a portable client, it is generally benilla-config/AddOns next to AzerothSurvivors.exe. Avoid installing into a different game copy by accident.

Run from the root of this repository:

1. Preview (no writes):
   py -m tools.addon_package plan --game-root "C:\Games\AzerothSurvivors"
2. Install the self-authored source after reviewing preview:
   py -m tools.addon_package install --game-root "C:\Games\AzerothSurvivors" --yes
3. View managed install status:
   py -m tools.addon_package status --game-root "C:\Games\AzerothSurvivors"
4. Restore previous addon or remove a newly installed one:
   py -m tools.addon_package rollback --game-root "C:\Games\AzerothSurvivors" --yes

By default install requires the exact original EXE SHA256
2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a.
For another manually verified game binary, use the explicit override
--allow-unknown-client. That is not a compatibility certificate.

If the addon already exists, installation refuses by default. For replacing an existing self-authored addon in an isolated copy, add --replace-existing. The old addon will be stored in a private .azse-enhanced/backup directory until rollback.

## Safety and recovery

- Requires manual --yes for install and rollback.
- Validates .toc interface 11200, matching files, file types, bounded size and SHA-256.
- Rejects symlinks, special files, nested folders, unknown EXE by default, and unknown receipt state.
- Stages files before changing the destination and stores an integrity receipt.
- Rollback refuses to remove a manually modified addon; preserve all unexpected files.
- State is kept in game-root/.azse-enhanced, and only this addon's destination is managed.
- No downloads, registry edits, native DLLs, trainer, MPQ edits, save edits or code from other addons.
- Synthetic filesystem tests exercise replacement, rollback, tampering and refusal.

If a crash/power failure leaves .azse-enhanced/prior-live, staging or backup and the tool reports an existing state without a valid receipt, STOP. Do not delete the state folder blindly. Close the game, make a full backup, then inspect prior-live and restore the original folder manually or with technical support. Never assume interrupted operations succeeded.

After a successful install the game should display the command /azse once this exact client supports the addon. This still requires a manual game smoke test. Do not claim runtime compatibility based only on Python tests.

Browser-based installation is separate: the original browser game has its own Options > AddOns > Install AddOns ZIP flow; this offline installer does not interact with the browser.
