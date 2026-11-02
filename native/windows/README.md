# Native Windows x64 bootstrap (research gate only)

**NOT an installer, working cheat, hook, native Options menu, Lua addon, external GUI or AVRT proxy. Do not copy the DLL into a game folder or inject it into the game.**

This source-owned, independently written C++ module establishes a Windows/MSVC build and regression-test path for a future in-game Cheats & Enhancements UI, without borrowing copyrighted original client code or third-party mod code.

## Verified original-client identity gate

Export AZSE_VerifyOriginalExecutable(path) reads a supplied file using a Win32 read-only handle, rejecting absent files, directories, reparse points, wrong sizes and wrong SHA. It accepts only the author's original Azeroth Survivors 0.139.0 Windows executable:

- Official SHA-256: 0e8e314df4d78ab211b1bef5c48d78d713ed64260894af342f998d298d74d274
- Official byte length: 150595584
- Hash implementation: Windows BCrypt SHA-256, streamed in bounded chunks.

A return value of 1 verifies *only that file's identity*. It is not proof the current process is the game or that any memory write is safe. The DLL has no injection, event hook, menu registration or gameplay modification code. AZSE_NativeHookInstalled() and AZSE_NativeCheatsTabInstalled() both always return zero. No code from other mods is copied.

The GitHub Actions Windows job builds the module on MSVC and runs invalid-path and synthetic-fixture tests. It never uploads or distributes a compiled DLL.

## Developer commands on Windows x64

    cmake -S native/windows -B build/native/windows -G "Visual Studio 17 2022" -A x64
    cmake --build build/native/windows --config Release
    ctest --test-dir build/native/windows -C Release --output-on-failure

**Do not install the build outputs as a mod.** There is no Windows game runtime integration yet.

## Exit criteria for a real original Options Cheats & Enhancements tab

1. Identify the original Bevy ECS button click-event consumer and selected-tab state writer on the exact client. Raw values 16/17 and +0x1DA memory displacement are insufficient.
2. Independently verify an exact-version, reversible interaction seam and lifecycle on a disposable owned Windows game copy. Account for an existing avrt.dll shim; never overwrite it or stack unknown proxies. Do not alter the real original EXE or saves.
3. Show the tab in the game's actual native Options menu, and independently validate each real offline single-player cheat toggle; no detached window or Lua-only substitute.
4. Add runtime evidence for menu entry, interaction, navigation, re-opening, safe exit and saved-game integrity. A compiled bootstrap alone satisfies none of these criteria.
5. Keep PR #23 DRAFT until those gates have been met. This module is not release ready.

See docs/WINDOWS_0139_NATIVE_AUDIT.md and catalog/options_code_graph_0139_summary.json for original-client static evidence.
