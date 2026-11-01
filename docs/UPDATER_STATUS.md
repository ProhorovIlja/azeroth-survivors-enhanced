# Original Windows updater: technical discovery (0.138.0)

The original user-provided executable embeds **two public creator-hosted update manifests**:

- `https://wow.aethus.pl/exe/latest.json`: game executable metadata, version and possibly downloadable chunks
- `https://wow.aethus.pl/exe/data/patches.json`: game data MPQ patch metadata

Nearby binary strings include `WOW_ROGUE_UPDATE_URL`, `WOW_ROGUE_DATA_URL`, `parts`, `size`, `sha256`, `version`, `notes` and a message indicating checksum verification failure. This is positive evidence the original has a chunked, checksum-verified update mechanism, but does not establish the exact JSON schema, downloaded part paths, rollback mechanics or its availability in the current release.

## Plan

1. Validate the **actual** JSON schema by read-only GitHub Actions probe: only fixed HTTPS manifest URLs, no redirections and no binary downloads. Print bounded shape, names, optional version and SHA field shapes. No secrets.
2. Compare user EXE SHA and local MPQ hashes with the manifest's expected finished-file checksums, not just downloaded-chunk SHA. If manifest does not provide complete-file checksum, do not auto-install.
3. Create opt-in `check`/`plan` command to list pending changes, local hashes and required parts; do not run game.
4. Add `download-to-staging` with destination confinement, per-part checksums and maximum sizes, **only once real schema is proven**.
5. Add `apply` only after original game is closed and explicit user confirmation, full backups, crash-safe atomic rename, complete-file checksum, rollback and integration tests on a disposable game copy. Never overwrite original saves/addons.

The repo already has a live official JSON change notifier tracking [issue #11](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/issues/11), scheduled four times daily. This probe investigates actual content and does not change or disable that notifier. The user EXE 0.138.0 was verified privately while the issue's last remote version was still 0.137.0, so they should not be presented as equivalent until a fresh server check succeeds.

**No natively integrated Cheats tab yet:** this update work is independent of the original Bevy `Options` reverse engineering in draft PR #18.

## Verified live server response (1 November 2026, GitHub Actions)

The schema probe reached both official Aethus endpoints successfully. The EXE JSON reports `version=0.138.0`, `size=147995648`, and SHA-256 `eb5fd1c1b96e6180fcf5f3d685d90a61471af28d22e5f060c02b7b7663fbf79e`: **identical to the user's Drive EXE**. There are three compressed EXE parts, named `0.138.0/part-000.bin` through `part-002.bin`. The MPQ JSON lists ten archives `patch-2.MPQ` through `patch-B.MPQ` (the initial large `patch.MPQ` is not in this incremental list). Each finished archive has `size`, `sha256`, and relative compressed `parts` with individual sizes.

A subsequent real GitHub Actions HTTP Range probe received `206 Partial Content` and the bytes `1f 8b 08` for the first EXE part and first MPQ part. **Both use GZIP**, with whole-finished-file SHA256 in the manifests. Merely concatenating compressed chunks does not make an EXE/MPQ. No part-specific SHA256 is provided in the current manifest; the independently reconstructed **complete file** must be verified.

## Verified Update Manager CLI

The separate source-only Python tool `tools/official_update_manager.py` supports `check`, `stage`, `apply`, `rollback`, using **only the author's HTTPS sources**. It uses no third-party trainer or binary, and does not modify saves, `patch.MPQ`, `benilla-config`, or addons. Its offline synthetic tests cover GZIP chunk assembly, bad URLs, checksum mismatches, backups, explicit consent, fail-closed SHA gating, rollback and game-file preservation.

**Prerequisites:** Python 3.10+; game fully closed for `apply`/`rollback`; sufficient free space for compressed downloads and complete-file backups. Open PowerShell at the repository root. For a portable game installed under `C:\Games\AzerothSurvivors`:

```powershell
# Read-only check: compares official finished-file hashes with local EXE and 10 named MPQs.
py -m tools.official_update_manager check --game-root "C:\Games\AzerothSurvivors"

# Explicitly stage only changed files in a NEW directory OUTSIDE the game folder.
py -m tools.official_update_manager stage --game-root "C:\Games\AzerothSurvivors" --stage-dir "$env:USERPROFILE\Documents\AZSE-Update-Staging" --yes

# After SHA verification, and with the game CLOSED, install while retaining original-file backups.
py -m tools.official_update_manager apply --game-root "C:\Games\AzerothSurvivors" --stage-dir "$env:USERPROFILE\Documents\AZSE-Update-Staging" --yes

# Roll back to backed-up original file versions from the same staging directory.
py -m tools.official_update_manager rollback --game-root "C:\Games\AzerothSurvivors" --stage-dir "$env:USERPROFILE\Documents\AZSE-Update-Staging" --yes
```

The stage directory must NOT exist yet; if staging fails, its incomplete contents are removed. `stage` downloads **only changed files** and checks full SHA256 of the reconstructed file. `apply` refuses when local files changed since staging, the selected game EXE is running on Windows, or any staged bytes changed. It creates and checksum-verifies backup copies before replacing affected files. The staging directory and backups must be kept until fully satisfied. If power failure leaves `state=applying`, **do not manually remove staging**: leave the game closed and run rollback. The first release should be tried on a DISPOSABLE COPY of the Windows installation, not on a working personal save.

**Limits:** The original client has its own in-game Check for Updates action. The Enhanced Edition CLI is an independent optional updater and is **not yet integrated as a native Bevy Options page**. It cannot guarantee game compatibility, internet availability, disk crash-atomicity across *multiple files*, or that a compromised creator server would be safe. File integrity is checked against HTTPS-delivered SHA256, not a separately signed developer release. GitHub Actions tests and a tiny public MPQ smoke check do **not** replace an actual Windows 0.138 offline runtime update/rollback test.
