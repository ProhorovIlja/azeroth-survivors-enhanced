"""Synthetic tests for v0.139 original UI function pointer table analysis."""
import struct
import unittest

from tools import native_0139_function_pointer_tables as p


class OriginalFunctionPointerTableTests(unittest.TestCase):
    BASE = 0x140000000

    def test_exact_imagebase_plus_function_start_is_detected(self):
        data = bytearray(b"\x00" * 64)
        struct.pack_into("<Q", data, 16, self.BASE + 0x3f5d40)
        report = p.find_function_slots(data, 0x5000, self.BASE,
                                       {"options_renderer": 0x3f5d40})
        self.assertEqual(1, report["pointer_slot_count"])
        self.assertEqual("0x5010", report["pointer_slots"][0]["slot_rva"])
        self.assertTrue(report["pointer_slots"][0]["aligned_pointer_shape"])

    def test_unaligned_false_positive_rejected(self):
        data = b"\x00" + struct.pack("<Q", self.BASE + 0x3f5d40) + b"\x00" * 8
        report = p.find_function_slots(data, 0x5000, self.BASE,
                                       {"options_renderer": 0x3f5d40})
        self.assertEqual(0, report["pointer_slot_count"])

    def test_wrong_imagebase_or_rva_rejected(self):
        data = struct.pack("<Q", self.BASE + 0x3f5d40)
        report = p.find_function_slots(data, 0x5000, self.BASE + 0x1000,
                                       {"options_renderer": 0x3f5d40})
        self.assertEqual(0, report["pointer_slot_count"])

    def test_pointer_slots_explicitly_truncated(self):
        data = struct.pack("<Q", self.BASE + 0x3f5d40)*5
        report = p.find_function_slots(data, 0x5000, self.BASE,
                                       {"options_renderer": 0x3f5d40}, cap=2)
        self.assertEqual(5, report["pointer_slot_count"])
        self.assertEqual(2, len(report["pointer_slots"]))
        self.assertTrue(report["truncated"])

    def test_neighboring_function_entries_are_only_candidates(self):
        data = bytearray(b"\x00"*80)
        struct.pack_into("<Q", data, 8, self.BASE + 0x1000)
        struct.pack_into("<Q", data, 16, self.BASE + 0x3f5d40)
        struct.pack_into("<Q", data, 24, self.BASE + 0x2000)
        rows = p.nearest_function_pointer_neighbors(
            data, 0x5000, self.BASE, {0x1000, 0x2000, 0x3f5d40},
            [{"target_role": "options_renderer", "slot_rva": "0x5010"}])
        self.assertEqual(["0x1000", "0x2000"], [
            v["neighbor_function_rva"] for v in rows[0]["nearby_function_entry_pointer_shapes"]])

    def test_non_entry_pointer_is_not_neighbor(self):
        data = bytearray(b"\x00"*80)
        struct.pack_into("<Q", data, 8, self.BASE + 0x1001)
        struct.pack_into("<Q", data, 16, self.BASE + 0x3f5d40)
        rows = p.nearest_function_pointer_neighbors(
            data, 0x5000, self.BASE, {0x1000, 0x3f5d40},
            [{"target_role": "options_renderer", "slot_rva": "0x5010"}])
        self.assertEqual([], rows[0]["nearby_function_entry_pointer_shapes"])

    def test_rip_lea_to_known_pointer_slot(self):
        code = bytearray(b"\x90"*64)
        site = 0x1010
        target = 0x5008
        code[16:23] = b"\x48\x8d\x0d"+struct.pack("<i", target - site - 7)
        got = p.raw_rip_load_candidates(code, 0x1000,
                                        {target: "options_renderer"}, [(0x1000, 0x1040)])
        self.assertEqual(1, got["raw_candidate_count"])
        self.assertEqual("options_renderer", got["records"][0]["referenced_builder_role"])
        self.assertFalse(got["records"][0]["instruction_confirmed"])

    def test_rip_mov_to_known_pointer_slot(self):
        code = b"\x48\x8b\x05" + struct.pack("<i", 0x5000-0x1007)
        got = p.raw_rip_load_candidates(code, 0x1000,
                                        {0x5000: "options_parent"}, [(0x1000, 0x1020)])
        self.assertEqual(1, got["raw_candidate_count"])

    def test_rip_false_target_and_missing_unwind_function(self):
        code = b"\x48\x8b\x05" + struct.pack("<i", 0x5008-0x1007)
        got = p.raw_rip_load_candidates(code, 0x1000,
                                        {0x5000: "options_parent"}, [(0x1010, 0x1020)])
        self.assertEqual(0, got["raw_candidate_count"])

    def test_objdump_instruction_starts_are_separate_from_raw_byte_shapes(self):
        out = ("  140001000: mov 0x123(%rip),%rax\n"
               "  140001012: lea 0x123(%rip),%rdx\n"
               "  140001024: movzbl %al,%ecx\n")
        self.assertEqual({0x1000, 0x1012}, p.parse_disassembled_rip_loads(
            out, self.BASE, 0x1000, 0x1100))

    def test_wrong_client_refused_before_opening_any_exe(self):
        report = p.audit_function_pointer_tables("/missing-client.exe", "0"*64)
        self.assertEqual("unknown_original_client_identity", report["reason"])

    def test_cap_must_be_positive(self):
        with self.assertRaises(ValueError):
            p.find_function_slots(b"", 0x1000, self.BASE, {}, cap=0)


if __name__ == "__main__":
    unittest.main()
