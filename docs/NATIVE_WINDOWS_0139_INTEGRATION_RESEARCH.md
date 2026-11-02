# Native original Windows Options integration research (0.139.0)

**Scope:** user-requested **Cheats & Enhancements inside the original game's own main Options menu**, not a Lua addon, an external window or an isolated launcher. Current state is research-only; this file is not an installation guide, hook approval or claim of working cheats.

## Current original-client boundary

- Author's verified exact 0.139.0 Windows EXE SHA-256: `0e8e314df4d78ab211b1bef5c48d78d713ed64260894af342f998d298d74d274`. Do not transfer offsets from 0.137/0.138 or from a different community build.
- Central original Options renderer `0x3F5D40`, original Saves content `0x1DF770`, AddOns content `0x1E0E60`, native footer action-widget helper `0x1E5530`. These are observed **construction/render paths**, not confirmed event consumers.
- The original `+0x1DA` memory byte is read at five x64 instruction sites in the central renderer; independently verified Saves state 11 controls hiding Defaults. A second straight-line GPR comparison tests **6** at `0x3F6C3B` and conditionally jumps to `0x3F6D4A`, past the confirmed original Saves builder call site `0x3F6D43`. This is a rendering-branch observation, **not proof of the human-readable tab name of page 6**.
- An actual native tab click handler, world access contract, version-safe hook ABI, exact live object pointer and game-process runtime test are **not known**.

## Public GitHub research, with separate provenance

### Azeroth Survivors Together (third-party source-available audit copy)

- Public repo: https://github.com/bymarvin/azeroth-survivors-source
- The authors describe a native Windows `avrt.dll` proxy that forwards all original system exports, checks the running game build's full SHA, and installs reviewed hooks only for matching known builds; it operates on a separate game copy. This demonstrates a technically viable **class** of native instrumentation, not compatibility with our client.
- The disclosed supported SHA list in `src/lib.rs` covers versions **0.84.3, 0.93.1, 0.95.0, 0.97.1**, none of which match 0.139.0. The published common hook-table reference SHA also differs from our target. In particular, its `UI_COMMAND` label **does not establish a hook address** for original 0.139.
- **Crucial license boundary:** the repository's `LICENSE` expressly says licensing has **not been chosen** and grants no code reuse rights. This project must **not copy, vendor, modify, relicense or bundle** its code, hook bytes, table data or DLL. Research here is conceptual and factual only.

### Other native AVRT shims and Bevy

- The independent `SurvivorsDragonUi` optional updater also documents using `avrt.dll` beside `AzerothSurvivors.exe`. Its README says DLL chaining is unsupported. A user may already have a different AVRT shim; **never overwrite or silently stack an existing DLL**.
  https://github.com/migwynkriid13/SurvivorsDragonUi/blob/main/updater/README.md
- Official Bevy's public UI docs explain that `Interaction::Pressed` describes an interaction state, and **is not itself a guaranteed press-and-release click**. Some Bevy versions implement interaction via `Changed<Interaction>`, other versions have event/observer APIs. The original game-specific Bevy version and event wiring remain unknown; do not copy a newer API example into a native Windows hook.
  https://docs.rs/bevy_ui/latest/bevy_ui/enum.Interaction.html
  https://bevy.org/examples-webgpu/ui-user-interface/button/

## Native-only implementation safety contract

1. Research remains read-only until an exact original-client SHA match and every selected instruction/ABI has a concrete, separately disassembler-reviewed provenance. A released update invalidates all unreviewed RVAs.
2. A future **opt-in** native integration must support only **single-player offline** use; never apply it to online/co-op or bypass anti-cheat. Don't mutate XP, gold, health or damage until their owning game systems and save semantics are confirmed.
3. Identify actual UI **event consumer**, selected-page mutation and Bevy entity lifetime. Observing a button constructor or numeric page-state compare is insufficient. Add a real native Options page only after a disposable-copy Windows runtime test confirms display, click, navigation, reopen and close.
4. Do not replace or coexist implicitly with another local `avrt.dll`. A future loader requires explicit collision detection, clean rollback, signature validation and separate copies of original game data and saves. Never patch the real installed EXE or distribute copyrighted EXE/MPQs.
5. Cheats must live **inside the original Options interface** with toggles representing actual hooked, tested solo behavior. No external cheats GUI or faux Lua-only setup is acceptable as completion.
6. Keep the GitHub draft PR open until these conditions are testable; original-source code and metadata can be reviewed without claiming live functionality.

## Next research gate

Find the game-specific Bevy OptionsCanvas event/interaction system, not generic low IDs 16/17 (already observed across 93 unrelated functions). Trace the selected tab's actual write path from button activation to original renderer, then review a reversible native extension on the pinned original 0.139 Windows process. Keep per-run audit artifacts metadata-only.
