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
