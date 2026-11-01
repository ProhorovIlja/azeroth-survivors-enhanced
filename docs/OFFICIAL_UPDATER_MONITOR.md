# Official game updater monitoring

**Source discovery from user's private original Windows client, not guesswork.** The newly uploaded `AzerothSurvivors.exe` includes these embedded URLs:

- EXE manifest: https://wow.aethus.pl/exe/latest.json
- MPQ manifest: https://wow.aethus.pl/exe/data/patches.json

The observed binary also contains `WOW_ROGUE_UPDATE_URL`, `parts`, `size`, `sha256`, `version`, `notes`, integrity-error strings, and the UI command `Check for Updates`. The downloaded new EXE reports a literal `0.137.0`; backup `AzerothSurvivors.old` reports `0.136.0`. Those version labels have not been confirmed in a running game.

The online JSON responses could **not** be fetched from the analysis container as of 2026-11-01. Consequently no exact JSON schema or current remote version is claimed. The monitor accepts JSON objects/arrays with bounded size and hashes the complete UTF-8 JSON payload. No remote download URL, binary, save or file path inside a manifest is followed.

## Monitoring

A dedicated, minimal GitHub Actions job runs every six hours UTC on the **default main branch** once this independent feature PR is merged. It performs strictly read-only HTTPS GETs of the two whitelisted official URLs, does not follow redirects, and **never downloads or installs EXE, RAR, MPQ or additional URLs from either manifest**. It compares SHA-256 of official JSON bytes to the last successful check. JSON reformatting may trigger a false-positive change alert; it is still an accurate byte-level change. Changes produce a short comment in [tracking issue #11](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/issues/11). The issue body stores only last good manifest hashes, byte sizes and optional reported version. First successful check creates a baseline without an alert; errors preserve the last known state.

GitHub schedule may be delayed, disabled for inactive repos, or unavailable if Actions permissions are restricted. To receive notifications, watch/subscribe to issue #11 and make sure GitHub email/mobile notifications are enabled. The watcher does not send emails directly. GitHub Actions workflow_dispatch allows manual testing after the merge, and push to main starts an immediate first check.

The monitor uses a GitHub Actions token with **issues:write** (for posting comments and state) and **contents:read** only. No additional secrets, external updater binaries or third-party GitHub Actions are required beyond official checkout/setup-python actions.

### Security / limits

No automated installing or updating of the original game. Always back up EXE, MPQs, Saves, and benilla-config before manually following any release. Match full SHA-256 of the downloaded components with a trustworthy manifest if available; do not trust a version string alone. If both official endpoints are offline, workflow reports failure rather than claiming nothing changed. If the server returns malformed/oversized JSON, the result is rejected.

For local manual read-only check (network required): `python -m tools.official_update_watch --check-only`.

The Windows archive linked on the official site, `AzerothSurvivorsWindowsNew.rar`, is a separate redistribution snapshot and may lag or lead the embedded update manifests. Do not treat the browser WASM version as proof of Windows compatibility.

## Owner's file comparison | 2026-11-01

| Item | Observed SHA-256 | Size |
| --- | --- | ---: |
| New EXE (literal 0.137.0) | `aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8` | 147844608 |
| Backup .old (literal 0.136.0) | `eb744751b4e17ec1397b0cdc85a22af63b6af63c1da1d9c2861762c3c4d8947c` | 147811840 |
| patch-8.MPQ | `ae3aaa29cadb7aeba8255f5b4a8305c7cbecfe8f0d3ed9646522113d16c3e12e` | 4155417 |
| patch-9.MPQ | `ffff8ea890bdaf91a1680543ac60106db92132bc2210105279610fa73661a524` | 5739608 |
| patch-A.MPQ | `350cde8cd0f76e5246a663eb3811f5a7b1a9c75e4e699190208c9299177b8d90` | 1453122 |
| patch-B.MPQ | `e9d074b012078efc1c1c8c729bf94d28b1d213d5fcb721dc4370a142f98834bd` | 2935 |

These are private files' **metadata only**. Original EXE, MPQs, localization texts and saved variables were **not** pushed into the public repository.

Previous project EXE was 139691008 bytes, SHA256 `2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a`. Older tools hard-coding this hash need a separate patch compatibility update. Do not silently disable version-gating.
