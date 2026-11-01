# Original 0.138 Options descriptor table: not the native tab registry

**Source:** the owner's privately uploaded, unmodified, original Windows EXE **0.138.0**, full SHA-256 `eb5fd1c1b96e6180fcf5f3d685d90a61471af28d22e5f060c02b7b7663fbf79e`. This is read-only research, not a native Cheats page, trainer, DLL or patch. No game file or proprietary UI description is distributed.

## Primary finding

The array at original PE `.rdata` RVA **`0x6316970`** contains **108 contiguous 152-byte (`0x98`) descriptors**. The actual group ID is at descriptor offset **`0x91`**, and a conditional/dependency byte is at **`0x90`**. Descriptor offset `0x08` is a text pointer in the original loaded PE image; `0x10` is the text length. Kind byte `0x00` distinguishes *short tooltip localization identifiers*, *inline help prose*, and *separators*. This table is consumed when Options renders its existing controls; it is **not** the table of menu tabs or Bevy ECS entity constructors.

| Descriptor kind | Count |
| --- | ---: |
| Standard tooltip localization key | 69 |
| Inline help description | 36 |
| Separator/non-text entry | 3 |
| **Total** | **108** |

Group ID distribution, as derived directly from the original client (do not equate this to actual visible tab count):

| Group ID | Records |
| --- | ---: |
| 0 | 18 |
| 1 | 5 |
| 2 | 21 |
| 3 | 2 |
| 4 | 19 |
| 5 | 6 |
| 7 | 7 |
| 8 | 17 |
| 9 | 12 |
| 10 | 1 |

**IDs 6 and 11 have zero descriptor rows**. In prior original-client disassembly, value 6 has a separate helper path and value 11 calls the Saves page content handler directly. This is evidence of specialized page handling, **not** empty reusable slots, and changing those IDs is unsafe.

## Consumer cross-check in original machine code

The central Options routine at `0x3F74C0` has two independently decoded x86-64 **direct calls** into the **same helper at RVA `0x105810`**:

- Call site `0x3F8464` when the currently selected group matches a descriptor.
- Call site `0x3F84A4` for the AddOns-special-case descriptor path.

The helper reads the descriptor's **dependency byte at `+0x90`** (observed instructions at `0x105859` and `0x10587D`) and constructs data that flows to additional UI-related helpers. The complete ABI, lifetime, Bevy ECS widget/entity constructors and event ownership are **not verified**. Therefore this helper is a plausible *existing control/help renderer*, **not** a verified safe insertion hook for an additional native Options tab. In particular, adding a new row to `.rdata` without changing bounds, navigation dispatch, and Bevy entity creation would not give the user a working Cheats menu.

## New reproducible safety audit

`tools/native_options_descriptors.py` checks whole-file SHA-256, validated PE `.rdata` / `.text` bounds, table dimensions, strict pointer/length/UTF-8 validity, kind/page/dependency fields, observed per-group population and **both original direct call targets**. It writes *only counts, IDs and verified function RVAs*, **never the underlying UI prose**, and refuses unknown versions or output overwrite. The source-only synthetic tests include invalid kind, page, dependency, pointers, string lengths, UTF-8, tampering of a call target and symlink refusal.

```powershell
py -m tools.native_options_descriptors --game-exe "C:\Games\AzerothSurvivors\AzerothSurvivors.exe" --out "options-descriptors-0138.json"
```

The report in `catalog/options_descriptors_0138.json` is metadata-only. It was generated successfully from the user's real private 0.138 EXE without launching the process, modifying a game file or distributing proprietary content. The 15 synthetic new tests plus 40 earlier PR #18 tests pass locally.

## Next blocker: actual original-native Cheats page

Find the **navigation/tab button constructor and event handler** *separate from the descriptor/help renderer*, confirm its Bevy ECS ownership and lifecycle under Windows, then design a reversible 0.138-version-gated injection. Only after real in-client QA should menu actions attach to independently verified native gameplay hooks (God Mode, XP, damage, currency and unlocks). None of these are already implemented. Existing 0.119 or 0.100 native hooks are not compatible with 0.138.
