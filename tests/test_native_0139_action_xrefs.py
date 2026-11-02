"""No game assets: synthetic x64 byte shapes for action-ID / widget inventory."""
import struct
import unittest

from tools import native_0139_action_xrefs as x

BASE = 0x1000
FUNC_A = (0x1000, 0x1180)
FUNC_B = (0x1180, 0x1300)
FUNCS = [FUNC_A, FUNC_B]


def fixture():
    code = bytearray(b"\x90" * 0x300)
    for ident, pos in [(16, 0x20), (17, 0x80), (2, 0x1A0)]:
        code[pos:pos + 10] = b"\x48\xb9" + struct.pack("<Q", (1 << 63) | ident)
    for pos in (0x50, 0xB0, 0x1D0):
        site = BASE + pos
        code[pos:pos + 5] = b"\xe8" + struct.pack("<i", x.HELPER_RVA - site - 5)
    return code


class NativeActionXrefTests(unittest.TestCase):
    def test_tag_ids_and_function_bounds(self):
        result = x.scan_action_tag_moves(fixture(), BASE, FUNCS)
        self.assertEqual([2, 16, 17], result["ids_seen"])
        self.assertEqual(3, result["total_candidate_count"])
        self.assertEqual(hex(FUNC_B[0]), result["records"][2]["owner_begin_rva"])

    def test_detects_widget_calls_only_in_functions(self):
        result = x.scan_helper_calls(fixture(), BASE, FUNCS)
        self.assertEqual(3, result["total_candidate_count"])
        self.assertEqual(hex(x.HELPER_RVA), result["records"][0]["target_rva"])

    def test_each_tag_can_be_linked_to_nearby_helper_call_without_claiming_a_click(self):
        c = fixture()
        t = x.scan_action_tag_moves(c, BASE, FUNCS)
        calls = x.scan_helper_calls(c, BASE, FUNCS)
        links = x.correlate_tag_to_button_builder(t["records"], calls["records"])
        self.assertEqual([16, 17, 2], [v["action_low_id_candidate"] for v in links])
        self.assertTrue(all(v["relationship"].startswith("same_function") for v in links))

    def test_mutated_call_is_not_accepted(self):
        c = fixture()
        c[0x50 + 1] ^= 1
        result = x.scan_helper_calls(c, BASE, FUNCS)
        self.assertEqual(2, result["total_candidate_count"])

    def test_non_tagged_or_high_id_values_are_ignored(self):
        c = fixture()
        c[0x20 + 2:0x20 + 10] = struct.pack("<Q", 0x8000000000000050)
        result = x.scan_action_tag_moves(c, BASE, FUNCS)
        self.assertEqual([2, 17], result["ids_seen"])

    def test_boundaries_prevent_false_owner(self):
        c = fixture()
        tags = x.scan_action_tag_moves(c, BASE, [(0x1000, 0x1010), FUNC_B])
        self.assertEqual([2], tags["ids_seen"])

    def test_small_output_caps_are_explicit(self):
        c = fixture()
        tags = x.scan_action_tag_moves(c, BASE, FUNCS, limit=1)
        calls = x.scan_helper_calls(c, BASE, FUNCS, limit=1)
        self.assertTrue(tags["truncated"])
        self.assertTrue(calls["truncated"])
        self.assertEqual(1, len(tags["records"]))
        self.assertEqual(1, len(calls["records"]))

    def test_unknown_sha_rejected_before_opening_game(self):
        self.assertEqual("wrong_client_identity",
                         x.analyze_action_flow("/nonexistent", "0" * 64)["reason"])

    def test_invalid_reversed_range_has_no_owner(self):
        self.assertIsNone(x.owner_of(0x1050, [0x1000], [(0x1000, 0x1040)], 10))

    def test_tag_away_from_call_is_not_linked(self):
        c = fixture()
        # Make the last helper call 144 bytes after the tagged value.
        c[0x1D0] = 0x90
        site = BASE + 0x240
        c[0x240:0x245] = b"\xe8" + struct.pack("<i", x.HELPER_RVA - site - 5)
        t = x.scan_action_tag_moves(c, BASE, FUNCS)
        calls = x.scan_helper_calls(c, BASE, FUNCS)
        links = x.correlate_tag_to_button_builder(t["records"], calls["records"])
        self.assertEqual([16, 17], [v["action_low_id_candidate"] for v in links])


if __name__ == "__main__":
    unittest.main()
