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


## Native footer action-widget calls identified in 0.139 (2026-11-02)

We added a read-only, **exact-SHA-pinned** footer probe (`tools/native_0139_footer_probe.py`) to the ephemeral original-client CI. It does not reuse v0.138 offsets. It bounds the central original Options function using PE `.pdata`, resolves the original public locale keys `options.defaults` and `options.done`, checks their high-bit action tags and requires a unique common helper. The two resulting direct calls were independently confirmed by native x64 disassembly.

| v0.139 native control | Public locale-key load RVA | High-bit action tag low ID | Actual direct call-site RVA |
|---|---:|---:|---:|
| Defaults | `0x3F7395` | `16` | `0x3F73CC` |
| Done | `0x3F73D1` | `17` | `0x3F7408` |

**Shared original action-widget creation helper: `0x1E5530`.** This differs from the v0.138 helper `0x107FA0`. The original v0.139 EXE was reconstructed only in ephemeral GitHub Actions and authenticated against whole-file official SHA-256 `0e8e314df4d78ab211b1bef5c48d78d713ed64260894af342f998d298d74d274`.

[Successful original-client run and synthetic tests](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41406510827); its metadata-only artifact records `footer_action_probe.status=candidate_same_helper` and `disassembler_confirmed_calls=true`. Persistent reviewed facts are in `catalog/options_code_graph_0139_summary.json`. The tests reject ambiguous key/tag/helper pairs, corrupted tags, altered calls and unknown SHA.

**Precise boundary:** this verifies **creation** of two existing clickable buttons, **not** the click-event consumer, Bevy entity ownership, new navigation-tab construction or in-run cheat semantics. Never call the native helper blindly or install hooks at these sites. No original EXE, MPQ, original instruction bytes, game saves or gameplay cheats were distributed or modified.

Next investigate consumers of the confirmed Defaults/Done action tags and identify the separate native navigation tab renderer; conduct disposable-copy Windows runtime tests before attempting a true Cheats & Enhancements page.


## Read-only original 0.139 action IDs and constructor call owners (2026-11-02)

The original menu action helper `0x1E5530` now has **8 direct call sites confirmed by objdump**, spread over **5 PE unwind-bounded functions**. Within just those five functions, the separate action-tag scan found **8 tagged `movabs` instructions**, each also independently confirmed at its original x64 instruction boundary by objdump. We deliberately scoped this probe: a global scan of tagged small ID values across the client has thousands of hits and is misleading.

| Candidate low ID | Enclosing native function RVA | Tagged instruction RVA | Widget helper direct-call RVA | Code-adjacent pair? |
| ---: | ---: | ---: | ---: | :---: |
| 9 | `0x1DF770` (Saves content) | `0x1DFBDD` | `0x1DFC00` | Yes |
| 13 | `0x1DF770` (Saves content) | `0x1DFC19` | `0x1DFC35` | Yes |
| 11 | `0x3F05F0` | `0x3F0998` | `0x3F09BB` | Yes |
| 14 | `0x3F0A20` | `0x3F0DE9` | `0x3F0E0F` | Yes |
| 15 | `0x3F0A20` | `0x3F0E28` | `0x3F0E47` | Yes |
| 8 | `0x3F0EB0` | `0x3F1051` | `0x3F10F1` | **Not yet established**, too distant for the narrow proximity criterion |
| 16 | `0x3F5D40` (central Options) | `0x3F73A9` | `0x3F73CC` | Yes, reviewed Defaults |
| 17 | `0x3F5D40` (central Options) | `0x3F73E5` | `0x3F7408` | Yes, reviewed Done |

Original exact-SHA 0.139.0 GitHub Actions test, including synthetic tests: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41409012753 . Source: `tools/native_0139_action_xrefs.py`, tests `tests/test_native_0139_action_xrefs.py`; source-only durable summary: `catalog/options_code_graph_0139_summary.json`.

**Interpretation:** This is a metadata-only **button creation** map. Even if a tag and a helper call are close in code, their semantic dataflow or the identity of the eventual click-event handler has not been established. The IDs **must not** be called cheat switches or unused IDs; none is a confirmed menu-extension slot. In particular, action ID 8 is an unassociated tagged instruction within a helper-calling function, not a verified pair.

**Next frontier:** identify the consumer of these actions in the native ECS event/update path, separate the actual Options tab navigation system from the reused localized action widget helper, and test any eventual native menu extension on a disposable copy of Windows 0.139 before enabling changes. No original EXE/MPQ, code bytes, save data, DLL proxy, or gameplay cheat was modified or released.


## New exact-original 0.139 Saves selector conditional confirmed (2026-11-02)

A separate read-only probe, `tools/native_0139_saves_branch.py`, bounded its scan to the small original code region preceding the independently authenticated `options.defaults` label load in original Windows 0.139. Its exact-client synthetic regression tests and SHA-pinned original EXE CI succeeded: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41409473700 .

The original code contains a disassembler-confirmed **byte comparison against Saves state 11** followed by a disassembler-confirmed **conditional jump to the existing Done button**, skipping Defaults:

| Observed structure | RVA / value |
| --- | --- |
| Original compare instruction | `0x3F738C` |
| Compared byte field displacement | **`+0x1DA`** |
| Compared Saves page value | **`0x0B` (11)** |
| Conditional JE instruction | `0x3F7393` |
| Original branch target / `options.done` text load | **`0x3F73D1`** |
| Effect supported by static branch | On Saves, skip Defaults, continue to Done |

This confirms one exact original **page-state read** continues to use the `+0x1DA` field in 0.139 despite the engine update. It does **not** identify who owns this state object, who writes the field on navigation, the full set of page IDs or how to register another Bevy page. **Do not write to that byte or reuse 0.138 RVA values**; a field read is not an injection ABI.

Next static/runtime task: identify actual writers to that state field and the UI tab-click consumers, then verify event ownership/lifetime on an isolated Windows copy. A genuine Cheats & Enhancements tab and real solo-only God Mode/XP/Gold/Damage toggles remain unimplemented.


## Complete original 0.139 Options selector access inventory and direct-call provenance (2026-11-02)

Continuing the original native Saves/Defaults selector read `cmpb $11, +0x1DA(...)` at `0x3F738C`, a new exact-SHA-pinned analysis scanned the entire original 0.139 x64 `.text` for the displacement value `+0x1DA`. Each byte-pattern hit was assigned, where possible, to a PE `.pdata` function. GNU objdump disassembled **every candidate function from its actual unwind entrypoint** before classifying genuine instruction accesses; disassembly from arbitrary candidate bytes was expressly avoided.

| Read-only original Windows client 0.139 result | Observed |
| --- | ---: |
| Raw `DA 01 00 00` displacement shapes in original x64 `.text` | 527 |
| Candidate PE functions, all disassembled from entry | **479 / 479** |
| Disassembly failures / oversized skipped functions | **0 / 0** |
| Real instructions mentioning memory displacement `+0x1DA` | **97** |
| Instruction accesses classified as possible writes | 44 |
| Explicit byte-sized `movb` write candidates | **13** |
| Distinct function owners of those 13 byte stores | **10** |
| Actual candidate `+0x1DA` reads in original central Options `0x3F5D40` | **5** |
| Direct `+0x1DA` stores in original central Options | **0** |

The five real read sites in central Options `0x3F5D40` are `0x3F662B`, `0x3F6C33`, `0x3F6CC3`, `0x3F6FFC`, and `0x3F738C`. The final site confirms the same `Saves = 11` comparison and skips Defaults, as independently checked in the earlier focused probe.

Some stores use immediate byte values **0, 1, 2, 4 and 255**, none of which by itself establishes an Options page ID: this literal memory displacement also occurs in unrelated types, including byte and wider-word fields. The verified `movb` function owners are listed in `catalog/options_code_graph_0139_summary.json`.

A separate new read-only cross-reference probe (`tools/native_0139_selector_callers.py`) scanned x64 direct E8 calls targeting exactly the ten byte-writer function entrypoints, then independently verified every potential call with objdump. **10 real direct calls confirmed**, but **none** came from the six already observed original UI builder/content functions (`0x3F5D40`, `0x1DF770`, `0x1E0E60`, `0x3F05F0`, `0x3F0A20`, `0x3F0EB0`). This is a negative finding **only for this narrow set of direct calls**. Other intermediate functions or indirect Bevy ECS event dispatch may exist.

Both the complete selector read/write probe (`tools/native_0139_selector_xrefs.py`) and caller graph run against the exact verified original 0.139 EXE, with synthetic regression tests: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41411047535 . Only derived RVA, value and classification metadata is archived, never any original client bytes. Details and flags are in `catalog/options_code_graph_0139_summary.json`. All work remains reversible research and PR #23 remains DRAFT.

**Do not treat the 13 `movb` sites or 10 caller edges as safe hooks.** We have not proven any byte store belongs to the same *runtime object instance* that central Options reads at `+0x1DA`; nor have we identified the handler that changes tabs on clicks. The next defensible investigation is the **OptionsCanvas/Bevy ECS update and interaction system**, particularly whether selected-page changes are performed through a dynamic dispatch, distinct state component, or copied memory. A working native Cheats & Enhancements tab, actual God Mode/Gold/XP/Damage toggles, and Windows runtime tests remain outstanding.


## Verified original 0.139 Options ancestry and parent-function profile (2026-11-02)

A new exact-SHA, read-only native Windows 0.139 analyzer `tools/native_0139_options_event_ancestry.py` traced the original central Options renderer through genuine x64 `E8` instructions, confirming each direct call site with GNU objdump on the SHA-authenticated original binary. This is a **static call graph, not proof of a UI click-event consumer**.

| Actual direct-call site RVA | Source function RVA | Destination function RVA |
| --- | --- | --- |
| `0x2005A5` | **`0x1FFDE0`** | **`0x3F5D40`** (previously verified central Options renderer) |
| `0x20E324` | **`0x20E0C0`** | `0x1FFDE0` |
| `0x2C19B2` | **`0x2C1710`** | `0x1FFDE0` |
| `0x2C1AE7` | **`0x2C1AD0`** | `0x2C1710` |

The two previously reviewed `options.defaults` and `options.done` creation tag loads at `0x3F73A9` (ID 16) and `0x3F73E5` (ID 17) were reconfirmed. The **global original-client scan** also found **152 actual `movabs` instructions** whose immediate values encode the same high-bit-plus-16/17 shapes, across **93 distinct PE functions** (86 instances with low ID 16, 66 with low ID 17). **150/152 are outside the original Options footer creation function.** These numeric values are therefore **not unique signatures of an Options click handler**. Never identify a consumer or claim a safe hook based solely on those tag bits. All findings were disassembled from their containing function's actual PE unwind start, with zero reported function disassembly failures. Verified read-only native original-client run: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41414687708 .

A second read-only analyzer, `tools/native_0139_parent_event_profile.py`, examines the four actual parent Options functions for instruction-shape evidence only, not bytes or code:

| Function RVA | x64 function length | Direct calls | Indirect calls | Indirect jumps | Instructions accessing `+0x1DA` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `0x1FFDE0` | 2,174 bytes | 12 | 0 | 0 | **1 read** at `0x20024A` |
| `0x20E0C0` | 804 bytes | 5 | 0 | 0 | 0 |
| `0x2C1710` | 950 bytes | 5 | 0 | 0 | 0 |
| `0x2C1AD0` | 134 bytes | 3 | 0 | 0 | 0 |

The parent function `0x1FFDE0` also contains a **`cmp` of immediate value 15 at RVA `0x200529`**. We have NOT traced this comparison to the `+0x1DA` read or proved it is a native tab ID, despite appearing in the same function; avoid speculative assignments. The four parents contain no `call *...` or computed `jmp *...` in the disassembled instruction profiles, so this **particular four-function chain** does not directly reveal an indirect Bevy ECS event dispatcher. Event handling could still be in a separate game system, including dynamically registered function pointers outside these render paths.

Exact original-client SHA pin, synthetic regression tests, metadata-only artifact and successful 0.139 CI: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41415142806 . Full derived address-only evidence persists in `catalog/options_code_graph_0139_summary.json`. Original EXE, MPQs, machine-code bytes and game saves were not uploaded, patched or executed. No native Cheats & Enhancements tab or actual gameplay cheat currently exists. Next step is to locate **Bevy ECS OptionsCanvas interaction/event systems**, tie a real click to a selected-page state mutation in a disposable Windows test, and only then design a reversible, exact-client native menu integration.


## Original 0.139 page-state register flow and Saves content skip (2026-11-02)

A new exact-SHA-pinned read-only disassembler tool, `tools/native_0139_page_branch_map.py`, enumerates numeric `+0x1DA` memory field accesses and actual **immediately adjacent** conditional branches from the original Windows client's `.pdata`-bounded Options renderer `0x3F5D40` and parent `0x1FFDE0`. Verified on official client in [successful CI](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41416651189):

- Central Options renderer has 5 numeric `+0x1DA` accesses: `movzbl` at `0x3F662B`, `0x3F6C33`, `0x3F6FFC`; a `cmp` at `0x3F6CC3`; and a direct `cmpb $11` at `0x3F738C`. The latter's `je` at `0x3F7393` branches to Done `0x3F73D1` on Saves, independently confirmed.
- The parent renderer `0x1FFDE0` has one numeric `+0x1DA` `movzbl` at `0x20024A`. Direct memory-immediate comparisons do not capture all page-state tests because registers carry the loaded values.

A second tool, `tools/native_0139_page_register_flow.py`, tracks GPR aliases from a specific `movzbl` field load through only one bounded straight-line instruction region, stopping on control-flow change or register mutation. It deliberately avoids claims about cross-block SSA/PHI, ECS object identity or copied values. Its genuine original-client [regression-tested CI](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41417139607) found one important sequence:

| Real original 0.139 instruction role | RVA |
| --- | ---: |
| Load original page-state byte from `+0x1DA` into GPR | **`0x3F6C33`** |
| Compare the same GPR against value **6** | **`0x3F6C3B`** |
| Immediately following **`je`** | **`0x3F6C3E`** |
| Conditional jump target | **`0x3F6D4A`** |
| Existing separately confirmed native **Saves** content-builder call that the branch skips | **`0x3F6D43`** (calls `0x1DF770`) |

Third-party-proof, exact-original disassembler crosscheck of the compare/jump plus previously verified Saves call was added to `tools.native_0139_page_register_flow.correlate_page_6_with_saves_builder`, with mutation/failure synthetic tests. The [successful exact-original-client CI](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41417815702) reports **`structurally_verified_skip: true`**. This is a *genuine control-flow branch of the renderer* testing value 6 and skipping the built-in Saves content builder along that branch. **It does not prove the human-readable tab name assigned to numeric 6, which entity owns the page field, how the tab is clicked, where its value is written or a hook ABI.**

For source-only third-party native research, license boundaries, AVRT DLL proxy collisions and a no-Lua native acceptance checklist, see `docs/NATIVE_WINDOWS_0139_INTEGRATION_RESEARCH.md`. A public co-op mod has a named `UI_COMMAND` hook on **older, differently hashed** game builds, but its published `LICENSE` explicitly grants no reuse rights; no code or hook table has been imported. No actual native Cheats & Enhancements page, actual God Mode/XP/Gold/Damage toggles or tested live Windows injection currently exists. Continue exact-SHA auditing and identify the actual Bevy ECS Options interaction/update system before writing game memory.


## Rust/Bevy Options type-name cross-references (2026-11-02)

An additional SHA-pinned read-only probe, `tools/native_0139_options_type_xrefs.py`, scans the original `.rdata` for an **exact allowlist** of original `wenilla_rogue_app::screens::options::` Rust type markers, then verifies x64 RIP-relative `lea` code references by disassembling from genuine PE unwind function boundaries. Original-client and synthetic tests, including a deliberately concatenated Rust string regression, succeeded: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41418182997 .

Markers identified in the exact original 0.139 `.rdata`: `OptionsCanvas` (1 occurrence), `OptionsRoot` (1), `PageList` (1), `Footer` (1), `Act` (4), `Fill` (1), `Readout` (1), `Track` (1), `TipText` (1). These are **type-name markers**, not confirmed registered Bevy ECS entities or update systems.

Just **one** x64 `lea` instruction directly referenced a detected type-name start: RVA `0x33768`, enclosing PE function RVA `0x33630`, referencing the **TipText** marker, corroborated by objdump. There were **zero direct `lea` references to OptionsCanvas** among the exact patterns scanned. This does not exclude indirect pointer tables, reflection type registration, dynamically generated Rust metadata, virtual dispatch or other kinds of direct/indirect references. It also does not establish `0x33630` as a click handler.

One false positive was caught in the first pass: adjacent Rust UTF-8 names had been conflated into the artificial type label `TipTextwenilla_rogue_app`. The revised scanner uses exact known type names with suffix checks; its synthetic tests reject this mistake and avoid overclaiming. The corrected final metadata is persisted in `catalog/options_code_graph_0139_summary.json`.

**Current next task:** locate the actual event system registered for Options/PageList (potentially indirect Bevy ECS reflection rather than an immediate string LEA), then trace which original function writes the selected tab when a real Options button is activated. A confirmed type marker, a constructor or a branch to a known page is **not** an ABI-safe native hook and is not a functioning Cheats tab.


## 2026-11-02: Static Rust Options pointer graph and first independently compiled Win64 native module

### Original 0.139 Rust/Bevy type pointer graph

A new exact-official-SHA, read-only probe `tools/native_0139_reflection_pointer_graph.py` checks whether native 64-bit virtual-address slots in the original client's `.rdata` or `.data` point to the **exact start** of known Rust Options marker strings: `OptionsCanvas`, `OptionsRoot`, `PageList`, `Footer`, `TipText`. It then checks plausible `&str` pointer/length descriptors, RIP-relative x64 code references to any discovered slots, and nearby function-entry virtual addresses. In the original 0.139 EXE **zero exact pointer slots** were found in the scanned static sections, and hence there were **zero direct code xrefs or nearby function-pointer candidates** of this constrained form. All synthetic pointer/descriptor tests and original EXE SHA gate passed: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41420600194 .

This negative result does **not** disprove Bevy ECS registration. Code may use other metadata layouts, inlined strings, hashed identifiers, pointer aliasing, dynamically generated structures, interior string references, etc. Do not claim any ECS event-consumer, direct pointer table or safe hook from this probe.

### First native Windows x64 code, compiled from our own sources

Instead of only adding further read-only Python scanners, we created **`native/windows`**, a clean-room C++17 Windows-native DLL bootstrap with a strictly gated Win32/BCrypt original-client SHA verifier. Public exports report the exact official 0.139 SHA and file size, verify a specified read-only EXE by full SHA/length, and truthfully report `AZSE_NativeHookInstalled() == 0` and `AZSE_NativeCheatsTabInstalled() == 0`. It has **no DLL proxy, loader, injection, Bevy hook, gameplay memory write or fake menu**.

The first Windows/MSVC build was rejected due to a duplicated `WIN32_LEAN_AND_MEAN` macro under `/WX`. We fixed the duplicate; the subsequent genuine **Windows Server 2022 / Visual Studio 2022 x64 Release** build and synthetic wrong-client fail-closed CTest succeeded: https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41421364850 . The job explicitly does not distribute the compiled DLL, execute the game, or patch an EXE. Original 0.139 file positive verification inside Windows is not yet runtime-tested; only negatives are exercised on synthetic files.

**Not a working mod:** this bootstrap must not be installed or renamed to `avrt.dll`. Current primary blockers remain identifying original Options Bevy ECS button click event consumer, selected-tab writer, a reversible exact-version-safe integration seam, and actual offline Windows game runtime tests. The original EXE/save data remains untouched; draft PR #23 must stay open. See `native/windows/README.md` and `docs/NATIVE_WINDOWS_0139_INTEGRATION_RESEARCH.md` for scope and acceptance gates.


## 2026-11-02: Native Windows bootstrap positively validated on genuine original v0.139 EXE

Previous MSVC Windows x64 CI proved that the clean-room native DLL compiled and rejected synthetic wrong-sized files, but did **not** prove the hash implementation could accept the real original EXE. That gap is now closed in [successful Windows CI](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41424601214) and strengthened in [subsequent successful Windows CI](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41424929306).

The Windows CI temporarily reconstructs the developer's official original 0.139.0 Windows EXE in the GitHub-hosted runner temporary directory using the existing author-manifest validator and whole GZIP-stream SHA gate (`tools/native_0139_windows_positive_fixture.py`). The original EXE is never executed and is removed in a PowerShell `finally` block; GitHub Actions publishes **no original game files or compiled native DLL**.

With MSVC x64 Release `/W4 /WX`, the native DLL's read-only **Win32 BCrypt SHA-256 whole-file** checker passed all of the following on Windows:

| Actual Windows-native regression | Outcome |
| --- | --- |
| Correct, authentic official v0.139.0 original EXE of 150,595,584 bytes, full pinned SHA | **ACCEPT (1)** |
| Separate temporary copy of that original, **exactly same size but one byte changed** | **REJECT (0)** |
| Synthetic files, null/empty/nonexistent paths | **REJECT (0)** |
| An unrelated Windows CTest host process, even while an authentic EXE exists separately on disk | **REJECT (0)** |
| Hook and native Cheats menu status | **Both remain 0; no hook/menu installed** |

New export `AZSE_VerifyCurrentProcessOriginal()` verifies **the current process's own main executable**, not an arbitrary genuine executable path. This is an additional future native safety gate, **not permission** to inject or hook. The independent compiled DLL is deliberately not installed or loaded into the game process. The temporary changed-byte copy and authentic official original are both deleted after tests; no game client or save modified.

**Still not achieved:** an original in-game Options Cheats & Enhancements page, event delivery, real offline God Mode/XP/Gold/Damage cheats, in-game hot-path safety or actual Windows game runtime. The user asked for the original game's native Options menu, not a Lua addon or separate GUI; this preflight work alone is not a feature release. Do not mark DRAFT PR #23 complete until those runtime gates pass.


## 2026-11-02: Exact original 0.139 six-function Options callback pointer cluster

A read-only SHA-pinned probe `tools/native_0139_function_pointer_tables.py` scanned actual 64-bit virtual-address pointers in the original Windows executable's `.rdata`/`.data` to the eight original Options-related function entrypoints already identified by PE unwind and call graph. Full original EXE SHA identity checked, no game original bytes exported, successful [CI run](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41439827358).

**Positive discovery:** three original .rdata pointers to previously confirmed Options render/caller chain functions occur within one adjacent cluster. Neighboring PE unwind function-entry pointers extend the cluster to six consecutive pointers, independently reread and validated from the exact original EXE in a dedicated [successfully tested probe](https://github.com/ProhorovIlja/azeroth-survivors-enhanced/actions/runs/41440327948):

| .rdata slot RVA | Pointed-to real original function RVA | Current evidence |
| --- | --- | --- |
| `0x652DBE8` | `0x20E0C0` | Known call-chain ancestor of Options |
| `0x652DBF0` | `0x2C1AD0` | Known call-chain ancestor of Options |
| `0x652DBF8` | `0x2C1710` | Known call-chain ancestor of Options |
| `0x652DC00` | `0x20E410` | Newly identified 55-byte function |
| `0x652DC08` | `0x20E450` | Newly identified 55-byte function |
| `0x652DC10` | `0x20E4A0` | Newly identified 283-byte function |

The last three code entries are disassembled from independent PE `.pdata` function starts by `tools/native_0139_options_pointer_cluster.py`, which requires all six exact slot values to match before doing any analysis. Their bounded original instruction profiles show **no direct numeric selector `+0x1DA` access** and **zero direct E8 callsites targeting the new three function entries across the original scanned code**. The two 55-byte wrappers branch to `0x5BD2760`/`0x5BD2A80` and each calls `0x64CE330`; the 283-byte function has two direct calls. Those are *code-level relationships only*, not proof of event consumers, drop functions or Bevy ECS registration.

A separate direct code-pattern scan found **zero RIP-relative `mov/lea` references to any of the eight named function *entrypoints***. This is narrower than whole-program dataflow and cannot disprove all indirect Rust function addresses or other forms of linking.

The cluster's semantics are unknown, but it is an actual original-client, highly specific structure and more useful than searching generic low action IDs 16/17 or string markers. `tools/native_0139_options_pointer_table_owners.py` now searches nearby code/data references to the six-function table itself, includes regression tests, and is wired to the SHA-pinned original-client audit. The existence of this table **does not validate an insertion hook** or prove a page-change event. No EXE or game save was modified, and there is still no live native Cheats tab.
