# Original Windows v0.139 native compatibility audit

Official release intelligence detected v0.139.0 without a user upload: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/issues/22

A GitHub Actions runner reconstructed the ORIGINAL author's Windows EXE from three official HTTPS GZIP parts, validated **whole-file SHA-256** and ran a read-only PE32+ metadata analyzer. The original executable was deleted from the runner; **no original EXE, binary chunks, MPQs or localization prose were committed or uploaded**.

**Release:** Windows 0.139.0, 150,595,584 bytes; original EXE SHA-256: 0e8e314df4d78ab211b1bef5c48d78d713ed64260894af342f998d298d74d274.

| Original native UI role (static candidate) | v0.138 RVA | v0.139 RVA |
|---|---:|---:|
| Central Options | 0x3F74C0 | **0x3F5D40** |
| Saves content | 0x1021E0 | **0x1DF770** |
| AddOns content | 0x1038D0 | **0x1E0E60** |

These derive from matching short public UI-key references inside PE unwind-bounded functions, **not** independent disassembly or a verified safe hook. Old addresses must never be reused in 0.139, especially because the official release notes mention an engine update and revised proc-hit attribution. The MPQ manifest stayed unchanged for all 10 update-managed archives.

The first large original EXE download exposed a critical update-format detail: GZIP is a **stream split across 20-MB HTTP parts**, not necessarily a complete individual GZIP member per part. We corrected both this read-only audit and the standalone optional updater in draft PR #19 to stream across all chunks. The updated [native audit passed](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41399754590), and the [updater tests passed](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41400136509).

The original-game native Cheats & Enhancements tab, button click-event dispatcher, Windows runtime smoke test and real HP/damage/gold cheats **remain unimplemented/unverified**. The next technical work must disassemble actual 0.139 UI calls and event ownership before introducing any native code into the owner's game.

The user's Google Drive still contained v0.138 EXE during this audit. Research no longer waits for a manual Drive upload.

## Additional independent x64 disassembly confirmation (2026-11-02)

After the exact v0.139 EXE was restored and authenticated, the runner checked original direct-call instruction boundaries with a native disassembler (LLVM objdump or GNU objdump fallback). Both page-construction calls within the candidate central Options function were actually observed as x64 call instructions:

| Callsite (RVA) | Confirmed destination RVA | Role |
|---|---|---|
| **0x3F6D43** | **0x1DF770** | Saves content |
| **0x3F6DA1** | **0x1E0E60** | AddOns content |

Only the derived site/destination RVAs and Boolean confirmation were reported. Original instruction bytes or a game executable were **not** uploaded to GitHub. Live Bevy click-event dispatch, tab creation and game-engine hook safety are still unknown, so **these are not usable native cheat integration points**.

Actual original v0.139 read-only disassembler crosscheck and synthetic tests succeeded: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41401071660 . The revised metadata-only report is archived as an Actions artifact for 14 days and the persistent address pairs are retained in catalog/options_code_graph_0139_summary.json.
