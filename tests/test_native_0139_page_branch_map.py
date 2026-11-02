"""Synthetic x64 validation for original Options numeric page-state branches."""
import unittest
from tools import native_0139_page_branch_map as m


def disassembly():
    return "\n".join([
        "  1403f662b: movzbl 0x1da(%rcx),%eax",
        "  1403f6c33: cmpb $0x4,0x1da(%rsi)",
        "  1403f6c3a: jne 0x1403f6ca0",
        "  1403f6cc3: cmpb $0x1f,0x1db(%rsi)",
        "  1403f6ffc: movb %al,0x1da(%rsi)",
        "  1403f738c: cmpb $0xb,0x1da(%rax)",
        "  1403f7393: je 0x1403f73d1",
    ])


class NativePageBranchTests(unittest.TestCase):
    def test_original_saves_baseline_shape_and_adjacent_branch(self):
        r = m.page_comparison_map(disassembly(), 0x140000000, 0x3f6600, 0x3f7500)
        cmp = r["candidate_page_comparisons"]
        self.assertEqual(2, len(cmp))
        self.assertEqual([4, 11], [x["page_state_value_candidate"] for x in cmp])
        saves = cmp[-1]
        self.assertEqual("0x3f738c", saves["comparison_site_rva"])
        self.assertEqual("0x3f7393", saves["immediately_following_conditional"]["branch_site_rva"])
        self.assertEqual("0x3f73d1", saves["immediately_following_conditional"]["branch_target_rva"])

    def test_counts_noncomparison_reads_without_asserting_page_id(self):
        r = m.page_comparison_map(disassembly(), 0x140000000, 0x3f6600, 0x3f7500)
        self.assertEqual(4, r["numeric_field_access_count"])
        self.assertEqual(2, r["numeric_field_comparison_count"])

    def test_rejects_comparison_of_other_memory_offset(self):
        r = m.page_comparison_map("  140001020: cmpb $0xb,0x1db(%rax)\n", 0x140000000, 0x1000, 0x1100)
        self.assertEqual([], r["candidate_page_comparisons"])

    def test_branch_must_be_immediately_adjacent(self):
        text = ("  140001020: cmpb $0xb,0x1da(%rax)\n"
                "  140001025: mov %rax,%rbx\n"
                "  140001030: je 0x140001080\n")
        r = m.page_comparison_map(text, 0x140000000, 0x1000, 0x1100)
        self.assertNotIn("immediately_following_conditional", r["candidate_page_comparisons"][0])

    def test_unrelated_register_comparison_not_considered_page_check(self):
        text = ("  140001020: cmpb $0xb,%al\n"
                "  140001025: je 0x140001080\n")
        r = m.page_comparison_map(text, 0x140000000, 0x1000, 0x1100)
        self.assertEqual([], r["candidate_page_comparisons"])

    def test_invalid_literal_is_not_page_byte(self):
        r = m.page_comparison_map("  140001020: cmpb $0x100,0x1da(%rax)\n", 0x140000000, 0x1000, 0x1100)
        self.assertEqual([], r["candidate_page_comparisons"])

    def test_truncation_is_explicit(self):
        r = m.page_comparison_map(disassembly(), 0x140000000, 0x3f6600, 0x3f7500, cap=1)
        self.assertEqual(1, len(r["candidate_page_comparisons"]))
        self.assertTrue(r["comparison_records_truncated"])
        self.assertTrue(r["field_access_records_truncated"])

    def test_cap_zero_fails_closed(self):
        with self.assertRaises(ValueError):
            m.page_comparison_map("", 0, 0, 1, cap=0)

    def test_disassembly_outside_function_ignored(self):
        r = m.page_comparison_map(disassembly(), 0x140000000, 0x3f7400, 0x3f7500)
        self.assertEqual(0, r["numeric_field_access_count"])

    def test_wrong_sha_refused_before_file_access(self):
        self.assertEqual("unknown_client_sha", m.audit_native_page_branches("/missing.exe", "0"*64)["reason"])


if __name__ == "__main__":
    unittest.main()
