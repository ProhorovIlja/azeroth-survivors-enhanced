# Public GitHub source monitoring

`tools.upstream_watch` performs **read-only** GitHub API queries for the first 30 curated repositories: metadata, current release, up to five open PRs, up to five branches, parent/fork status, and new repository candidates from two GitHub searches.

It **cannot and does not** crawl the entire internet, inspect binary safety, diff every commit, or confirm compatibility. New candidates require independent human review. The JSON report contains only public repository metadata, not user files or game assets.

Run manually without network: `python -m tools.upstream_watch` (prints dry-run only).

On a checkout with network and an authorized `GITHUB_TOKEN`, opt in: `python -m tools.upstream_watch --run --limit 30`. The output is ignored by Git and written to `artifacts/upstream-watch.json`. Do not commit raw report archives to `main` or use this as automatic approval for addons.

GitHub workflow `.github/workflows/upstream-watch.yml` has a daily UTC cron at 06:17 and manual dispatch, with `contents: read` permissions. **GitHub scheduled workflows run only from the default branch**: this is **NOT ACTIVE** until the PR chain is reviewed and merged to `main`. Workflow artifacts expire after 14 days. After initial merge, check GitHub Actions permissions and manually dispatch a first run.

Web search / player video research are separate human-reviewed tasks; this GitHub API watcher does not pretend to index Reddit or other sites.

To triage a change:
1. Compare previous JSON release tags and pushed timestamps, inspect actual changes and relevant PRs/branches.
2. Confirm exact upstream LICENSE, release asset hashes, source code and updater behavior.
3. Check patch/version compatibility against user's EXE fingerprint and isolated game build.
4. Prepare a separate PR with tests, version gate, rollback, attributable source link and implementation decisions. Never auto-install.
