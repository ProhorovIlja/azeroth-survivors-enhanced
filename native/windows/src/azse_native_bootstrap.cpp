#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>

#include <array>
#include <cstdint>
#include <cstring>

#include "azse_native_bootstrap.h"

#pragma comment(lib, "bcrypt.lib")

namespace {
constexpr std::uint64_t kOfficialSize = 150595584ULL;
constexpr char kOfficialSha[] =
    "0e8e314df4d78ab211b1bef5c48d78d713ed64260894af342f998d298d74d274";
constexpr unsigned int kShaSize = 32;
constexpr DWORD kChunkSize = 64 * 1024;

struct ScopedFile {
  HANDLE file = INVALID_HANDLE_VALUE;
  ~ScopedFile() {
    if (file != INVALID_HANDLE_VALUE) CloseHandle(file);
  }
};

struct ScopedHash {
  BCRYPT_ALG_HANDLE algorithm = nullptr;
  BCRYPT_HASH_HANDLE hash = nullptr;
  ~ScopedHash() {
    if (hash) BCryptDestroyHash(hash);
    if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0);
  }
};

int hex_value(char c) noexcept {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  return -1;
}

bool expected_digest(std::array<unsigned char, kShaSize>& digest) noexcept {
  if (std::strlen(kOfficialSha) != kShaSize * 2) return false;
  for (unsigned int i = 0; i < kShaSize; ++i) {
    int hi = hex_value(kOfficialSha[i * 2]);
    int lo = hex_value(kOfficialSha[i * 2 + 1]);
    if (hi < 0 || lo < 0) return false;
    digest[i] = static_cast<unsigned char>((hi << 4) | lo);
  }
  return true;
}
}  // namespace

const char* AZSE_OriginalClientSha256() noexcept { return kOfficialSha; }
unsigned long long AZSE_OriginalClientSize() noexcept { return kOfficialSize; }

int AZSE_VerifyOriginalExecutable(const wchar_t* path) noexcept {
  if (!path || !*path) return 0;

  // Reject filesystem redirections, directories, absent files and unknown builds.
  const DWORD attrs = GetFileAttributesW(path);
  if (attrs == INVALID_FILE_ATTRIBUTES ||
      (attrs & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT))) return 0;

  ScopedFile handle;
  handle.file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, nullptr,
                            OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
  if (handle.file == INVALID_HANDLE_VALUE) return 0;

  LARGE_INTEGER length{};
  if (!GetFileSizeEx(handle.file, &length) ||
      length.QuadPart != static_cast<LONGLONG>(kOfficialSize)) return 0;

  ScopedHash crypto;
  if (BCryptOpenAlgorithmProvider(&crypto.algorithm, BCRYPT_SHA256_ALGORITHM,
                                  nullptr, 0) != 0) return 0;
  if (BCryptCreateHash(crypto.algorithm, &crypto.hash, nullptr, 0,
                       nullptr, 0, 0) != 0) return 0;

  std::array<unsigned char, kChunkSize> block{};
  std::uint64_t read_total = 0;
  while (read_total < kOfficialSize) {
    DWORD bytes_read = 0;
    DWORD wanted = static_cast<DWORD>(
        (kOfficialSize - read_total < kChunkSize)
            ? (kOfficialSize - read_total) : kChunkSize);
    if (!ReadFile(handle.file, block.data(), wanted, &bytes_read, nullptr)
        || bytes_read == 0 || bytes_read > wanted) return 0;
    if (BCryptHashData(crypto.hash, block.data(), bytes_read, 0) != 0) return 0;
    read_total += bytes_read;
  }
  if (read_total != kOfficialSize) return 0;

  std::array<unsigned char, kShaSize> actual{}, expected{};
  if (BCryptFinishHash(crypto.hash, actual.data(), kShaSize, 0) != 0) return 0;
  if (!expected_digest(expected)) return 0;

  // The binary may have changed between the size and hash passes. The
  // descriptor only operates in read-only mode and never patches the client.
  return actual == expected ? 1 : 0;
}

int AZSE_VerifyCurrentProcessOriginal() noexcept {
  // Keep the original-client file check distinct from permission to install a
  // hook. An unrelated host/test program can never be authenticated by passing
  // a separate genuine EXE path to AZSE_VerifyOriginalExecutable().
  std::array<wchar_t, 32768> path{};
  const DWORD length = GetModuleFileNameW(
      nullptr, path.data(), static_cast<DWORD>(path.size()));
  if (!length || length >= static_cast<DWORD>(path.size())) return 0;
  return AZSE_VerifyOriginalExecutable(path.data());
}

int AZSE_NativeHookInstalled() noexcept { return 0; }
int AZSE_NativeCheatsTabInstalled() noexcept { return 0; }
