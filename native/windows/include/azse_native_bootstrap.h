#pragma once

#ifdef _WIN32
#ifdef AZSE_BUILDING_DLL
#define AZSE_EXPORT extern "C" __declspec(dllexport)
#else
#define AZSE_EXPORT extern "C" __declspec(dllimport)
#endif
#else
#define AZSE_EXPORT extern "C"
#endif

// Original Windows game 0.139.0 only; no fallback to guessed byte signatures.
// A successful verification allows read-only investigation, NOT code hooks.
AZSE_EXPORT const char* AZSE_OriginalClientSha256() noexcept;
AZSE_EXPORT unsigned long long AZSE_OriginalClientSize() noexcept;
AZSE_EXPORT int AZSE_VerifyOriginalExecutable(const wchar_t* path) noexcept;

// Deliberate no-op safety flags. No hooks, memory writes, menus or cheats.
AZSE_EXPORT int AZSE_NativeHookInstalled() noexcept;
AZSE_EXPORT int AZSE_NativeCheatsTabInstalled() noexcept;
