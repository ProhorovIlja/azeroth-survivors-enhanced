"""Synthetic-only regression cases for native Options Rust pointer graph."""
import struct
import unittest

from tools import native_0139_reflection_pointer_graph as g


class RustOptionsPointerGraphTests(unittest.TestCase):
    def test_aligned_exact_virtual_address_pointer_with_str_length(self):
        raw = bytearray(b"\x00" * 80)
        base, marker = 0x140000000, 0x2000
        raw[16:32] = struct.pack("<QQ", base + marker, len(g.TYPE_PREFIX) + len("OptionsCanvas"))
        got = g.locate_type_pointer_slots(raw, 0x3000, {marker: "OptionsCanvas"}, base)
        self.assertEqual(1, got["pointer_slot_count"])
        self.assertTrue(got["pointer_slots"][0]["adjacent_exact_string_length"])
        self.assertEqual("0x3010", got["pointer_slots"][0]["data_pointer_slot_rva"])

    def test_nonmatching_length_still_pointer_but_not_str_descriptor(self):
        raw = struct.pack("<QQ", 0x140002000, 999)
        got = g.locate_type_pointer_slots(raw, 0x3000, {0x2000: "OptionsCanvas"}, 0x140000000)
        self.assertEqual(1, got["pointer_slot_count"])
        self.assertFalse(got["pointer_slots"][0]["adjacent_exact_string_length"])

    def test_different_executable_imagebase_rejected(self):
        raw = struct.pack("<Q", 0x140002000)
        got = g.locate_type_pointer_slots(raw, 0x3000, {0x2000: "OptionsCanvas"}, 0x180000000)
        self.assertEqual(0, got["pointer_slot_count"])

    def test_unaligned_value_shape_not_accepted(self):
        raw = b"\x00" + struct.pack("<Q", 0x140002000) + b"\x00" * 7
        got = g.locate_type_pointer_slots(raw, 0x3000, {0x2000: "OptionsCanvas"}, 0x140000000)
        self.assertEqual(0, got["pointer_slot_count"])

    def test_type_pointer_scan_truncation(self):
        raw = struct.pack("<Q", 0x140002000) * 3
        got = g.locate_type_pointer_slots(raw, 0x3000, {0x2000: "OptionsCanvas"},
                                          0x140000000, cap=1)
        self.assertTrue(got["pointer_slots_truncated"])
        self.assertEqual(3, got["pointer_slot_count"])

    def test_code_lea_to_exact_pointer_slot(self):
        code = bytearray(b"\x90" * 64)
        code[16:23] = b"\x48\x8d\x0d" + struct.pack("<i", 0x3000 - (0x1000 + 16 + 7))
        hits = g.direct_rip_slot_reads(code, 0x1000, {0x3000: "PageList"},
                                       [(0x1000, 0x1040)])
        self.assertEqual(1, hits["direct_rip_slot_xref_count"])
        self.assertEqual("PageList", hits["records"][0]["referenced_type_name"])
        self.assertFalse(hits["records"][0]["disassembled_instruction_start"])

    def test_code_mov_to_exact_pointer_slot(self):
        code = b"\x48\x8b\x05" + struct.pack("<i", 0x3000 - 0x1007)
        hits = g.direct_rip_slot_reads(code, 0x1000, {0x3000: "Footer"},
                                       [(0x1000, 0x1010)])
        self.assertEqual(1, hits["direct_rip_slot_xref_count"])

    def test_code_wrong_target_and_unwind_not_counted(self):
        code = b"\x48\x8d\x0d" + struct.pack("<i", 0x3001 - 0x1007)
        hits = g.direct_rip_slot_reads(code, 0x1000, {0x3000: "Footer"},
                                       [(0x1010, 0x1030)])
        self.assertEqual(0, hits["direct_rip_slot_xref_count"])

    def test_actual_instruction_disassembly_required(self):
        output = ("  140001000: mov 0x123(%rip),%rax\n"
                  "  140001010: lea 0x123(%rip),%rdx\n"
                  "  140001020: cmpb $0x6,%al\n")
        self.assertEqual({0x1000, 0x1010},
                         g.confirmed_rip_instructions(output, 0x140000000, 0x1000, 0x1100))

    def test_neighboring_code_pointer_distinct_from_type_pointer(self):
        functions = [(0x1000, 0x1040), (0x1100, 0x1140)]
        region = bytearray(b"\x00" * 80)
        struct.pack_into("<Q", region, 8, 0x140001000)
        struct.pack_into("<Q", region, 16, 0x140002000)
        struct.pack_into("<Q", region, 24, 0x140001100)
        ptr = [{"type_name": "OptionsCanvas", "data_pointer_slot_rva": "0x3010"}]
        evidence = g.function_pointers_near_slots(region, 0x3000, 0x140000000, functions, ptr)
        self.assertEqual(1, len(evidence))
        self.assertEqual(["0x1000", "0x1100"],
                         [x["code_function_entry_rva"] for x in evidence[0]["nearby_pdata_function_entry_pointer_candidates"]])

    def test_unrelated_code_pointer_not_callback_proof(self):
        functions = [(0x1000, 0x1040)]
        region = bytearray(b"\x00"*80)
        struct.pack_into("<Q", region, 16, 0x140002000)
        struct.pack_into("<Q", region, 24, 0x140001001)
        ptr = [{"type_name": "PageList", "data_pointer_slot_rva": "0x3010"}]
        evidence = g.function_pointers_near_slots(region, 0x3000, 0x140000000, functions, ptr)
        self.assertEqual([], evidence)

    def test_wrong_sha_refused_before_file_access(self):
        self.assertEqual("wrong_original_client_sha",
                         g.audit_options_reflection_pointer_graph("/absent", "0"*64, {})["reason"])

    def test_missing_verified_type_report_refused(self):
        self.assertEqual("original_type_markers_unverified",
                         g.audit_options_reflection_pointer_graph("/absent", g.EXPECTED_SHA, {})["reason"])


if __name__ == "__main__":
    unittest.main()
