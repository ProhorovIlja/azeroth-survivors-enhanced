"""Synthetic-only tests of native 0.139 selector displacement analysis."""
import unittest
from tools import native_0139_selector_xrefs as x


class SelectorCrossReferenceTests(unittest.TestCase):
    def test_scan_raw_displacement_owner_dedup(self):
        blob = bytearray(b"\x90" * 80)
        blob[10:14] = x.DISP_BYTES
        blob[20:24] = x.DISP_BYTES
        blob[60:64] = x.DISP_BYTES
        result = x.find_displacement_functions(blob, 0x1000,
                                                [(0x1000, 0x1030), (0x1030, 0x1050)])
        self.assertEqual(3, result["raw_displacement_hit_count"])
        self.assertEqual(2, result["candidate_function_count"])
        self.assertFalse(result["truncated"])

    def test_outside_unwind_rejected(self):
        blob = b"\x90" * 10 + x.DISP_BYTES
        result = x.find_displacement_functions(blob, 0x1000, [(0x1000, 0x1008)])
        self.assertEqual(0, result["candidate_function_count"])
        self.assertEqual(1, result["outside_unwind_functions"])

    def test_scanning_truncation_is_explicit(self):
        blob = bytearray(b"\x90" * 80)
        blob[10:14] = x.DISP_BYTES
        blob[50:54] = x.DISP_BYTES
        result = x.find_displacement_functions(blob, 0x1000,
                                                [(0x1000, 0x1020), (0x1020, 0x1050)],
                                                max_functions=1)
        self.assertTrue(result["truncated"])
        self.assertEqual([0x1000], result["sampled_owner_rvas"])

    def test_zero_function_cap_is_rejected(self):
        with self.assertRaises(ValueError):
            x.find_displacement_functions(b"", 0, [], max_functions=0)

    def test_at_t_register_to_selector_memory_is_a_writer(self):
        self.assertEqual("write_candidate",
                         x.classify_instruction("movb", "%al,0x1da(%rcx)"))

    def test_at_t_immediate_to_selector_memory_is_a_writer(self):
        self.assertEqual("write_candidate",
                         x.classify_instruction("movb", "$0x7,0x1da(%rdi)"))

    def test_selector_comparison_is_a_reader(self):
        self.assertEqual("read_or_address_candidate",
                         x.classify_instruction("cmpb", "$0xb,0x1da(%rax)"))

    def test_selector_register_load_is_a_reader(self):
        self.assertEqual("read_or_address_candidate",
                         x.classify_instruction("movzbl", "0x1da(%rax),%ecx"))

    def test_selector_read_modify_write_is_distinct(self):
        self.assertEqual("read_modify_write_candidate",
                         x.classify_instruction("orb", "$0x1,0x1da(%rax)"))

    def test_nonmatching_displacement_is_ignored(self):
        self.assertIsNone(x.classify_instruction("movb", "%al,0x1db(%rcx)"))

    def test_parse_real_objdump_instruction_starts_only(self):
        disassembly = "\n".join([
            "  1403f738c:    cmpb $0xb,0x1da(%rax)",
            "  1403f7393:    je 0x1403f73d1",
            "  1403f7400:    movb %cl,0x1da(%rdi)",
            "  1403f7410:    movzbl 0x1da(%rax),%ecx",
            "  1403f7420:    movb %al,0x1db(%rax)",
        ])
        events, count = x.parse_accesses(disassembly, 0x140000000, 0x3f7300, 0x3f7500)
        self.assertEqual(3, count)
        self.assertEqual(["read_or_address_candidate", "write_candidate",
                          "read_or_address_candidate"],
                         [v["access_candidate"] for v in events])
        self.assertEqual("0x3f738c", events[0]["instruction_rva"])

    def test_out_of_function_instruction_rejected(self):
        text = "  1403f738c:    cmpb $0xb,0x1da(%rax)"
        self.assertEqual(([], 0), x.parse_accesses(text, 0x140000000, 0x3f7400, 0x3f7500))

    def test_parser_caps_output_without_lying_about_total(self):
        text = "\n".join("  %x:    movb $0x1,0x1da(%%rax)" % (0x140001010 + j)
                         for j in range(4))
        events, total = x.parse_accesses(text, 0x140000000, 0x1000, 0x1100, cap=1)
        self.assertEqual(1, len(events))
        self.assertEqual(4, total)

    def test_byte_literals_in_byte_store_or_comparison_are_explicit(self):
        self.assertEqual(11, x.selector_literal("cmpb", "$0xb,0x1da(%rax)"))
        self.assertEqual(17, x.selector_literal("movb", "$0x11,0x1da(%rdi)"))
        self.assertIsNone(x.selector_literal("movl", "$0xb,0x1da(%rax)"))
        self.assertIsNone(x.selector_literal("cmpb", "%al,0x1da(%rdi)"))
        self.assertIsNone(x.selector_literal("cmpb", "$0x100,0x1da(%rdi)"))

    def test_parser_records_literal_only_for_confirmed_instruction_line(self):
        lines = ("  1403f738c:    cmpb $0xb,0x1da(%rax)\n"
                 "  1403f739c:    movb $0xc,0x1da(%rdx)\n")
        records, total = x.parse_accesses(lines, 0x140000000, 0x3f7300, 0x3f7500)
        self.assertEqual(2, total)
        self.assertEqual([(11, "comparison"), (12, "possible_byte_store")],
                         [(r["immediate_byte_value"], r["immediate_role"]) for r in records])

    def test_unknown_client_sha_refused_before_opening_file(self):
        r = x.analyze_selector_xrefs("/no/file", "0" * 64)
        self.assertEqual("wrong_client_identity", r["reason"])
        self.assertEqual("unconfirmed", r["status"])


if __name__ == "__main__":
    unittest.main()
