"""Synthetic version-specific native Saves footer branch cases."""
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools import native_0139_saves_branch as x


def fixture():
    code = bytearray(b"\x90" * 128)
    code[0:9] = b"\x80\xb8" + struct.pack("<i", 0x1DA) + b"\x0b\x74\x3c"
    return code


class SavesBranchTests(unittest.TestCase):
    def scan(self, data):
        return x.search_saves_footer_branch(data, 0x1000, 0x1009, 0x1045)

    def test_original_shape_saves_skips_defaults(self):
        r = self.scan(fixture())
        self.assertEqual("candidate_saves_branch", r["status"])
        self.assertEqual(11, r["saves_page_literal"])
        self.assertEqual("0x1da", r["page_selector_field_disp32"])
        self.assertEqual("0x1045", r["skip_defaults_to_done_rva"])

    def test_wrong_page_literal_rejected(self):
        data = fixture()
        data[6] = 0x0A
        self.assertEqual("unconfirmed", self.scan(data)["status"])

    def test_wrong_conditional_rejected(self):
        data = fixture()
        data[7] = 0x75
        self.assertEqual("unconfirmed", self.scan(data)["status"])

    def test_wrong_jump_target_rejected(self):
        data = fixture()
        data[8] = 0x3D
        self.assertEqual("unconfirmed", self.scan(data)["status"])

    def test_invalid_defaults_key_range_rejected(self):
        data = fixture()
        self.assertEqual("unconfirmed", x.search_saves_footer_branch(data, 0x1000, 0xFFF, 0x1045)["status"])

    def test_ambiguous_branch_rejected(self):
        code = bytearray(b"\x90" * 160)
        code[0:9] = b"\x80\xb8" + struct.pack("<i", 0x1DA) + b"\x0b\x74" + bytes([0x67])
        code[0x20:0x29] = b"\x80\xb8" + struct.pack("<i", 0x1DA) + b"\x0b\x74" + bytes([0x47])
        result = x.search_saves_footer_branch(code, 0x1000, 0x1030, 0x1070)
        self.assertEqual("unconfirmed", result["status"])
        self.assertEqual(2, result["candidate_count"])

    def test_actual_cmp_and_jump_must_be_disassembled(self):
        evidence = {"comparison_site_rva": "0x1000", "skip_defaults_to_done_rva": "0x1045"}
        output = "  140001000: 80 b8 da 01 00 00 0b cmpb $0xb,0x1da(%rax)\n  140001007: 74 3c je 0x140001045\n"
        with patch.object(x.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=output)):
            self.assertTrue(x._disassembler_confirms("objdump", 0x140000000, "original.exe", evidence))
        with patch.object(x.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=output.replace("je 0x140001045", "jne 0x140001045"))):
            self.assertFalse(x._disassembler_confirms("objdump", 0x140000000, "original.exe", evidence))

    def test_original_sha_required_before_read(self):
        self.assertEqual("footer_not_confirmed_for_this_client", x.probe_saves_branch("/missing.exe", "0"*64, {})["reason"])


if __name__ == "__main__":
    unittest.main()
