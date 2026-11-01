"""Synthetic checks for exact version-gated 0.137 Windows client support."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from tools.extract_talent_names import ENGLISH_ANCHORS, KNOWN_SHAS, find_anchor_and_hash
from tools.client_guard import KNOWN_OWNER_EXE_SHAS
from tools.addon_package import KNOWN_OWNER_SHAS

NEW="aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8"
BACKUP="eb744751b4e17ec1397b0cdc85a22af63b6af63c1da1d9c2861762c3c4d8947c"


class Windows0137Tests(unittest.TestCase):
    def test_allowed_fingerprints_are_explicit(self):
        self.assertIn(NEW, KNOWN_SHAS)
        self.assertIn(BACKUP, KNOWN_SHAS)
        self.assertIn(NEW, KNOWN_OWNER_EXE_SHAS)
        self.assertIn(NEW, KNOWN_OWNER_SHAS)
        self.assertNotIn("0" * 64, KNOWN_SHAS)

    def test_crlf_english_dictionary_detected_near_chunk_edge(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/"synthetic.exe"
            data=b"x"*(1024*1024-18)+b'English{\r\n  "game.title": "Azeroth Survivors",\r\n  "key": "value"}'
            file.write_bytes(data)
            digest,start=find_anchor_and_hash(file)
            self.assertEqual(hashlib.sha256(data).hexdigest(),digest)
            self.assertEqual(data.index(b"{\r\n"), start)

    def test_old_lf_anchor_still_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/"older.exe"
            data=b"xyz"+b'{\n  "game.title": "Azeroth Survivors",\n  "key":"value"}'
            file.write_bytes(data)
            _,start=find_anchor_and_hash(file)
            self.assertEqual(3,start)

    def test_unrelated_exe_still_not_in_known_sha(self):
        self.assertNotIn(hashlib.sha256(b"MZtest").hexdigest(),KNOWN_SHAS)
        self.assertGreaterEqual(len(ENGLISH_ANCHORS),2)


if __name__=="__main__":
    unittest.main()
