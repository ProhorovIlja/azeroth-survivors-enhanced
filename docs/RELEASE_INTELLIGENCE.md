# Autonomous release intelligence for Azeroth Survivors Enhanced Edition

**Purpose:** Give future project work a persistent, source-backed understanding of new original-game releases without asking the owner to manually discover each update, run a launcher, or report filenames.

## Authoritative inputs

The original privately provided Windows client embeds two first-party endpoints:

- `https://wow.aethus.pl/exe/latest.json`: released Windows EXE `version`, full `size`, `sha256`, release notes, compressed `parts`.
- `https://wow.aethus.pl/exe/data/patches.json`: authoritative per-file size/SHA/parts for update-managed `patch-*.MPQ` files.

The base `Data/patch.MPQ` is **not** listed in the incremental manifest. Absence from `patches.json` must **not** be interpreted as a deletion instruction. Existing `tools/official_update_watch.py` on `main` independently posts byte-level JSON hash alerts to issue #11; it should remain enabled.

## What is automated

The separate `release-intelligence.yml` scheduled job runs every six hours (04:11, 10:11, 16:11, 22:11 UTC), with manual dispatch and a push trigger. It:

1. Reads two fixed HTTPS author-hosted JSON manifests only. No arbitrary hosts, redirects, game binaries, or executable execution.
2. Validates bounded canonical metadata, relative part paths, full target hashes and unambiguous MPQ names.
3. Compares the exact EXE version/size/SHA and per-MPQ name/size/SHA to the **previous successful snapshot** stored as a marker in the issue called **AZSE official release intelligence ledger**.
4. On first run, records a baseline. On any substantive release change, creates a **new separate GitHub compatibility research issue**, with changed EXE/MPQ names, old/new hashes, short release notes and an explicit engineering checklist. Stores the new snapshot in the ledger only after the issue is created. A rerun avoids duplicate issue titles.
5. Saves metadata-only JSON and Markdown reports as GitHub Actions artifacts for 30 days, for inspection next time we work in this Project.

A version bump with the same EXE SHA is still noted. An unchanged version with a modified MPQ SHA is a real file-level delta and creates a task. A harmless JSON whitespace change is ignored by this release-intelligence job, unlike the separate byte-level watcher. A changed note creates a review task but never claims a gameplay change.

### What I can and cannot automate

GitHub Actions executes the monitor without the assistant running or the user asking. **It does not continuously run a ChatGPT reasoning session, modify gameplay code, reverse-engineer binary changes, or merge PRs autonomously.** Each new compatibility issue and report can be read at the next project interaction, where I can inspect the updated data and produce tested GitHub code. This distinction matters: detection and work item creation are automated; gameplay research and code authoring still require an active execution session.

An official update manifest describes released *files*, not all changed talents, AI or gameplay code. File-level SHA and the author's note can guide deeper read-only EXE/MPQ audits, but we do not claim an exact balance diff until it is verified.

## Privacy and safety

All tracked metadata originates from public author-hosted JSON. No user Drive files, original executable, MPQ bytes, saves, passwords, or proprietary game-localization texts are uploaded to the public repo. JSON notes are bounded and treated as untrusted text. The runner has `contents:read`, `issues:write`, no auto-patching permission. A manifest outage does **not** erase the previous snapshot. Each newly found version is treated as **incompatible by default** with native Windows RVA offsets, talent-index assumptions, and old cheat DLLs until reverified.

## Local test (no network needed)

`python -m unittest discover -s tests -p test_release_intelligence.py -v`

For an *ad hoc read-only* manifest snapshot from your computer: `python -m tools.release_intelligence --check-only --output-dir <new-folder>`.

Do not edit the ledger marker by hand. It is maintained by the scheduled workflow.
