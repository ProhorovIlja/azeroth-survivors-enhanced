import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path
from tools.client_guard import inspect_exe, inspect_mpq, inspect_game, has_tokens, main


class ClientGuardTests(unittest.TestCase):
    def _sample_game(self, directory):
        root = Path(directory)
        exe = root / "AzerothSurvivors.exe"
        image = bytearray(512)
        image[:2] = b"MZ"
        struct.pack_into("<I", image, 0x3C, 128)
        image[128:132] = b"PE\x00\x00"
        struct.pack_into("<H", image, 132, 0x8664)
        struct.pack_into("<H", image, 152, 0x20B)
        exe.write_bytes(bytes(image) + b"AZS_GetPhase and AZS_GetMeter")
        return root, exe

    def test_pe_sha_and_caution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, exe = self._sample_game(tmp)
            result = inspect_exe(exe)
            self.assertEqual(result["sha256"], hashlib.sha256(exe.read_bytes()).hexdigest())
            self.assertEqual(result["format"], "PE32+")
            self.assertIn("AZS_GetPhase", result["api_strings_present"])
            self.assertFalse(result["runtime_api_verified"])
            self.assertFalse(result["safe_to_patch_automatically"])
            self.assertIsNone(result["exact_game_version"])

    def test_mpq_header_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            mpq = Path(tmp) / "patch-6.MPQ"
            header = b"MPQ\x1a" + struct.pack("<IIHHIIII", 32, 64, 0, 3, 32, 48, 1, 1)
            mpq.write_bytes(header + b"\x00" * 32)
            result = inspect_mpq(mpq, hash_contents=True)
            self.assertEqual(result["block_entries"], 1)
            self.assertEqual(result["archive_bytes"], 64)
            self.assertEqual(result["sha256"], hashlib.sha256(mpq.read_bytes()).hexdigest())
            self.assertEqual(result["files_extracted"], 0)

    def test_invalid_mpq_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            mpq = Path(tmp) / "patch.MPQ"
            mpq.write_bytes(b"MALFORMED")
            with self.assertRaises(ValueError):
                inspect_mpq(mpq)

    def test_hash_mismatch_returns_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, exe = self._sample_game(tmp)
            self.assertEqual(2, main(["--game-root", str(root), "--expected-sha", "0" * 64]))
            report = inspect_game(root)
            self.assertEqual([], report["mpq"])
            self.assertFalse(report["executed_client"])
            self.assertFalse(report["modified_client"])

    def test_string_crosses_chunk_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.bin"
            path.write_bytes(b"X" * (1024 * 1024 - 5) + b"AZS_GetPhase")
            self.assertIn("AZS_GetPhase", has_tokens(path))
            self.assertNotIn("AZS_GetMeter", has_tokens(path))


if __name__ == "__main__":
    unittest.main()
