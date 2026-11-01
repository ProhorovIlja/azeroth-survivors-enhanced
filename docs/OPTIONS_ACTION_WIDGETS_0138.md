# Original native Options 0.138: shared action-widget builder path

**Evidence source:** the owner's private, original, unmodified Windows 0.138.0 executable, SHA-256 `eb5fd1c1b96e6180fcf5f3d685d90a61471af28d22e5f060c02b7b7663fbf79e`. This document is metadata-level original-client research. It distributes no executable code, licensed assets, proprietary strings or altered binary.

## Why this matters

The previously found array of 108 `0x98`-byte records was identified as *Options tooltip/help descriptors*, not a tab registry. To find where actual native **clickable controls** arise, we traced direct x64 calls and localization key loads in the original `.text`. This establishes a different and more relevant construction path, without claiming a supported plugin ABI.

## Exact original 0.138 evidence

The original `.text` contains eight disassembler-confirmed `E8 rel32` calls to shared candidate localized-action-widget helper **RVA `0x107FA0`**. They are located at:

`0x102670`, `0x1026A5`, `0x3F213B`, `0x3F258F`, `0x3F25C7`, `0x3F2871`, `0x3F8B4C`, `0x3F8B88`.

Two of these are the **native Options footer controls** in the central Options routine (`0x3F74C0`):

| Label / public key | UI key load | Encoded action tag | Action widget call |
| --- | --- | --- | --- |
| `options.defaults` | `0x3F8B15` | high bit set, low ID **16** (`0x8000000000000010`) | `0x3F8B4C` |
| `options.done` | `0x3F8B51` | high bit set, low ID **17** (`0x8000000000000011`) | `0x3F8B88` |

At `0x3F8B0C`, an original byte comparison checks page selection state `+0x1DA` against `0x0B` (the Saves page). At `0x3F8B13`, a conditional branch jumps to the `options.done` key load at `0x3F8B51`: **Defaults is omitted on Saves, but Done is still built on that code path**. This branching was independently confirmed by disassembly and exact original-byte validation.

A second independent `options.done` localization-key load at `0x3C30EB` occurs in another function; it must **not** be conflated with this shared-widget call. Other calls to `0x107FA0` occur in Saves and confirmation-related paths. Their exact action semantics have not been established by observing clicks in the Windows client.

## Safety classification

What is supported: a shared action-control construction helper, two native footer labels, their encoded action tags, and the Saves conditional. What remains **unknown**: how user clicks are dispatched, the complete ABI of the helper, ownership/lifetime of the Bevy UI entity, action tag assignment, and how the original game creates new navigation tabs. **Do not inject arbitrary new tags or assume they grant gameplay effects.** Neither a native Cheats tab nor God Mode has been implemented.

The new source-only `tools/native_options_actions.py` validates the whole-file 0.138 SHA, PE section bounds, all eight E8 targets, both footer localization IDs, both immediate action tags, and the conditional-branch target. It writes only derived metadata to `catalog/options_footer_actions_0138.json`, never game code or text descriptions. `tests/test_native_options_actions.py` adds **15 synthetic cases** (unknown SHA, wrong branch target, changed action tag, corrupted call, invalid labels and safe report output). Running it never starts the game.

```powershell
py -m tools.native_options_actions --game-exe "C:\Games\AzerothSurvivors\AzerothSurvivors.exe" --out "native-actions-0138.json"
```

## What should be investigated next

1. Trace the **native click-event consumer** for these two existing action tags using an isolated original Windows 0.138 game, observing which event types and ECS resources they change.
2. Identify the **navigation-tab builder** (distinct from footer buttons and tooltip descriptors), then verify the ownership of the selected page byte.
3. Build a reversible, exact-version-gated native UI extension only after safe event integration and rollback checks exist. Attach real cheat implementations only when individually verified with value readbacks in offline solo play.

This report is a genuine static advance, not an installable game mod. Keep PR in draft until in-client functionality is demonstrated.
