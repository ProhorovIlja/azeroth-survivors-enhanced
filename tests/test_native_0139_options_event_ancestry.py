"""Synthetic-only tests for original Windows 0.139 Options event ancestry."""
import struct
import unittest

from tools import native_0139_options_event_ancestry as x


def fixture():
    raw = bytearray(b"\x90" * 512)
    for id_, off in ((16, 20), (17, 56), (16, 300)):
        raw[off:off + 10] = b"\x48\xb9" + struct.pack("<Q", (1 << 63) | id_)
    for site, dest in ((0x1050, 0x2000), (0x1170, 0x2000),
                       (0x11a0, 0x2100)):
        off = site - 0x1000
        raw[off:off + 5] = b"\xe8" + struct.pack("<i", dest - site - 5)
    return raw


class OptionsEventAncestryTests(unittest.TestCase):
    def test_two_original_high_bit_action_ids_are_found(self):
        r = x.find_tagged_actions(fixture(), 0x1000, [(0x1000, 0x1100),
                                                       (0x1100, 0x1200)])
        self.assertEqual([16, 17, 16], [t["action_low_id"] for t in r])
        self.assertEqual("0x1000", r[0]["function_begin_rva"])
        self.assertEqual("0x1100", r[2]["function_begin_rva"])

    def test_related_but_different_literal_not_matched(self):
        raw = bytearray(fixture())
        raw[22:30] = struct.pack("<Q", (1 << 63) | 18)
        r = x.find_tagged_actions(raw, 0x1000, [(0x1000, 0x1100), (0x1100, 0x1200)])
        self.assertEqual([17, 16], [t["action_low_id"] for t in r])

    def test_e8_exact_function_target_only(self):
        r = x.find_e8_edges(fixture(), 0x1000,
                            [(0x1000, 0x1100), (0x1100, 0x1200)],
                            {0x2000})
        self.assertEqual(2, r["total_e8_shapes"])
        self.assertEqual(["0x1050", "0x1170"], [v["site_rva"] for v in r["edges"]])

    def test_nonmatching_target_not_selected(self):
        r = x.find_e8_edges(fixture(), 0x1000,
                            [(0x1000, 0x1100), (0x1100, 0x1200)], {0x2001})
        self.assertEqual(0, r["total_e8_shapes"])

    def test_direct_call_cap_keeps_truncation_visible(self):
        r = x.find_e8_edges(fixture(), 0x1000,
                            [(0x1000, 0x1100), (0x1100, 0x1200)], {0x2000},
                            limit=1)
        self.assertEqual(1, len(r["edges"]))
        self.assertTrue(r["truncated"])
        self.assertEqual(2, r["total_e8_shapes"])

    def test_unwind_boundary_prevents_cross_function_instruction(self):
        self.assertIsNone(x.unwind_owner(0x10FF, [0x1000], [(0x1000, 0x1100)], 5))

    def test_actual_disassembled_tag_requires_original_instruction_start(self):
        output = ("  140003020:  movabs $0x8000000000000010,%rcx\n"
                  "  140003030:  movabs $0x8000000000000011,%r9\n"
                  "  140003040:  nop\n")
        real = x.parse_tag_instructions(output, 0x140000000, 0x3000, 0x3100,
                                        (16, 17))
        self.assertEqual([(0x3020, 16), (0x3030, 17)], real)

    def test_disassembled_move_not_any_text_containing_tag(self):
        raw = "  140003020:    cmpb $0x8000000000000010,%al\n"
        self.assertEqual([], x.parse_tag_instructions(raw, 0x140000000,
                                                       0x3000, 0x3100, (16, 17)))

    def test_out_of_function_tag_is_rejected(self):
        raw = "  140003020:  movabs $0x8000000000000010,%rcx\n"
        self.assertEqual([], x.parse_tag_instructions(raw, 0x140000000,
                                                       0x3050, 0x3100, (16, 17)))

    def test_wrong_sha_refuses_before_reading_file(self):
        result = x.analyze_options_event_ancestry("/does/not/exist", "0" * 64)
        self.assertEqual("unconfirmed", result["status"])
        self.assertEqual("wrong_client_identity", result["reason"])


if __name__ == "__main__":
    unittest.main()
