#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#include <array>
#include <cstring>
#include <iostream>
#include "azse_native_bootstrap.h"

namespace {
bool check(bool condition, const char* description) {
  if (!condition) std::cerr << "FAILED: " << description << '\n';
  return condition;
}
}

int main() {
  bool good = true;
  constexpr char expected[] =
      "0e8e314df4d78ab211b1bef5c48d78d713ed64260894af342f998d298d74d274";
  good &= check(std::strcmp(AZSE_OriginalClientSha256(), expected) == 0,
                "official SHA must remain exact");
  good &= check(AZSE_OriginalClientSize() == 150595584ULL,
                "official client size must remain exact");
  good &= check(AZSE_VerifyCurrentProcessOriginal() == 0,
                "a test host is NOT the original game even with a valid EXE path");
  good &= check(AZSE_NativeHookInstalled() == 0,
                "the test-only bootstrap MUST NOT install a hook");
  good &= check(AZSE_NativeCheatsTabInstalled() == 0,
                "MUST NOT misrepresent non-existent in-game native tab");
  good &= check(AZSE_VerifyOriginalExecutable(nullptr) == 0, "null path fails closed");
  good &= check(AZSE_VerifyOriginalExecutable(L"") == 0, "empty path fails closed");
  good &= check(AZSE_VerifyOriginalExecutable(
      L"Z:\\\\nonexistent\\\\AzerothSurvivors.exe") == 0, "unknown file fails closed");

  wchar_t folder[MAX_PATH]{};
  wchar_t file[MAX_PATH]{};
  const DWORD n = GetTempPathW(MAX_PATH, folder);
  if (!n || n >= MAX_PATH || !GetTempFileNameW(folder, L"AZE", 0, file)) {
    std::cerr << "could not create synthetic Windows file fixture\n";
    return 2;
  }
  HANDLE h = CreateFileW(file, GENERIC_WRITE, 0, nullptr,
                         TRUNCATE_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
  if (h == INVALID_HANDLE_VALUE) {
    DeleteFileW(file);
    return 2;
  }
  constexpr char fixture[] = "synthetic fixture only, NOT an original game executable";
  DWORD written = 0;
  const bool wrote = WriteFile(h, fixture, static_cast<DWORD>(sizeof(fixture)),
                               &written, nullptr) != 0;
  CloseHandle(h);
  if (!wrote || written != sizeof(fixture)) {
    DeleteFileW(file);
    return 2;
  }
  good &= check(AZSE_VerifyOriginalExecutable(file) == 0,
                "synthetic wrong-size and wrong-hash file MUST NOT pass");
  WIN32_FILE_ATTRIBUTE_DATA attrs{};
  good &= check(GetFileAttributesExW(file, GetFileExInfoStandard, &attrs) != 0,
                "verification MUST NOT mutate/delete the fixture");
  good &= check(attrs.nFileSizeLow == sizeof(fixture) && attrs.nFileSizeHigh == 0,
                "verification MUST preserve file size");
  DeleteFileW(file);

  // Optional positive whole-file identity test, executed only in the
  // quarantined Windows CI workflow with a genuine pinned original EXE.
  // The binary is never executed or patched. The workflow deletes it after.
  std::array<wchar_t, 32768> original_path{};
  const DWORD original_len = GetEnvironmentVariableW(
      L"AZSE_EXPECT_ORIGINAL_0139_PATH", original_path.data(),
      static_cast<DWORD>(original_path.size()));
  good &= check(original_len < original_path.size(),
                "positive test path must not be truncated");
  if (original_len > 0 && original_len < original_path.size()) {
    good &= check(AZSE_VerifyOriginalExecutable(original_path.data()) == 1,
                  "genuine original 0.139 must be accepted by native BCrypt SHA gate");
    WIN32_FILE_ATTRIBUTE_DATA original_attrs{};
    good &= check(GetFileAttributesExW(original_path.data(),
                                        GetFileExInfoStandard, &original_attrs) != 0,
                  "positive verifier must never remove the original fixture");
    good &= check(
        (static_cast<unsigned long long>(original_attrs.nFileSizeHigh) << 32) +
            original_attrs.nFileSizeLow == AZSE_OriginalClientSize(),
        "positive verifier must preserve original client length");
  }
  std::array<wchar_t, 32768> mutated_path{};
  const DWORD mutated_len = GetEnvironmentVariableW(
      L"AZSE_EXPECT_MUTATED_0139_PATH", mutated_path.data(),
      static_cast<DWORD>(mutated_path.size()));
  good &= check(mutated_len < mutated_path.size(),
                "modified-client path must not be truncated");
  if (mutated_len > 0 && mutated_len < mutated_path.size()) {
    WIN32_FILE_ATTRIBUTE_DATA modified_attrs{};
    good &= check(GetFileAttributesExW(mutated_path.data(),
                                        GetFileExInfoStandard, &modified_attrs) != 0,
                  "modified original-length fixture exists");
    good &= check(
        (static_cast<unsigned long long>(modified_attrs.nFileSizeHigh) << 32) +
            modified_attrs.nFileSizeLow == AZSE_OriginalClientSize(),
        "modified fixture must have exact original size to isolate SHA check");
    good &= check(AZSE_VerifyOriginalExecutable(mutated_path.data()) == 0,
                  "one-byte-changed original-sized EXE MUST fail SHA authorization");
  }
  return good ? 0 : 1;
}
