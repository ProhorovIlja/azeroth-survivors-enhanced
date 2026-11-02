"""Synthetic tests for original Bevy Options type-marker code references."""
import struct
import unittest

from tools import native_0139_options_type_xrefs as m


class BevyOptionsTypeTests(unittest.TestCase):
    def test_collect_names_without_copying_game_text(self):
        region = (b"wenilla_rogue_app::screens::options::OptionsCanvas\x00"
                  b"wenilla_rogue_app::screens::options::OptionsRoot\x00"
                  b"wenilla_rogue_app::screens::options::OptionsCanvas\x00")
        names = m.find_type_names(region, 0x2000)
        self.assertEqual(2, len(names["OptionsCanvas"]))
        self.assertEqual(1, len(names["OptionsRoot"]))

    def test_concatenated_names_do_not_create_fabricated_long_type(self):
        packed = (b"wenilla_rogue_app::screens::options::TipText"
                  b"wenilla_rogue_app::screens::options::OptionsCanvas\x00")
        names = m.find_type_names(packed, 0x2000)
        self.assertIn("TipText", names)
        self.assertIn("OptionsCanvas", names)
        self.assertNotIn("TipTextwenilla_rogue_app", names)

    def test_partial_prefix_of_longer_name_refused(self):
        packed = (b"wenilla_rogue_app::screens::options::OptionsCanvasExtra\x00"
                  b"wenilla_rogue_app::screens::options::Footer\x00")
        names = m.find_type_names(packed, 0x2000)
        self.assertNotIn("OptionsCanvas", names)
        self.assertEqual(1, len(names["Footer"]))

    def test_raw_lea_reference_has_correct_rip_relative_target(self):
        start = 0x1000
        target = 0x2000
        code = bytearray(b"\x90" * 64)
        site = start + 10
        code[10:17] = b"\x48\x8d\x0d" + struct.pack("<i", target - site - 7)
        result = m.find_exact_lea_xrefs(code, start, {target: "OptionsCanvas"},
                                         [(start, start + len(code))])
        self.assertEqual(1, result["raw_lea_xref_count"])
        self.assertEqual("0x100a", result["records"][0]["lea_rva"])

    def test_nonmatching_target_not_accepted(self):
        code = b"\x48\x8d\x0d" + struct.pack("<i", 0x2000 - 0x1007)
        result = m.find_exact_lea_xrefs(code, 0x1000,
                                        {0x2001: "OptionsCanvas"},
                                        [(0x1000, 0x1010)])
        self.assertEqual(0, result["raw_lea_xref_count"])

    def test_unwind_entry_required(self):
        code = b"\x48\x8d\x0d" + struct.pack("<i", 0x2000 - 0x1007)
        result = m.find_exact_lea_xrefs(code, 0x1000,
                                        {0x2000: "OptionsCanvas"},
                                        [(0x1010, 0x1030)])
        self.assertEqual(0, result["raw_lea_xref_count"])

    def test_raw_xref_is_not_implicitly_confirmed(self):
        code = b"\x48\x8d\x0d" + struct.pack("<i", 0x2000 - 0x1007)
        result = m.find_exact_lea_xrefs(code, 0x1000,
                                        {0x2000: "OptionsCanvas"},
                                        [(0x1000, 0x1010)])
        self.assertFalse(result["records"][0]["instruction_confirmed"])

    def test_objdump_mnemonic_required_on_instruction_boundary(self):
        text = "  140001005: lea 0x1ffa(%rip),%rax\n  140001020: mov %rcx,%rax\n"
        self.assertEqual({0x1005},
                         m.confirmed_lea_sites(text, 0x140000000, 0x1000, 0x1100))

    def test_wrong_client_sha_refused_before_binary_open(self):
        out = m.audit_options_type_xrefs("/does-not-exist", "0"*64)
        self.assertEqual("unknown_client_identity", out["reason"])

    def test_too_many_xrefs_explicitly_truncated(self):
        code = bytearray(b"\x90"*64)
        for offset in (0, 16, 32):
            site = 0x1000 + offset
            code[offset:offset+7] = b"\x48\x8d\x0d" + struct.pack("<i", 0x2000 - site - 7)
        r = m.find_exact_lea_xrefs(code, 0x1000,
                                   {0x2000:"OptionsCanvas"},
                                   [(0x1000, 0x1040)],limit=1)
        self.assertTrue(r["truncated"])
        self.assertEqual(3, r["raw_lea_xref_count"])
        self.assertEqual(1, len(r["records"]))


if __name__ == "__main__":
    unittest.main()
