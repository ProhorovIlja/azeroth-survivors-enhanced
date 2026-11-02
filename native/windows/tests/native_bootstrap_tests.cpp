#define WIN32_LEAN_AND_MEAN
#include <windows.h>

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
  return good ? 0 : 1;
}
