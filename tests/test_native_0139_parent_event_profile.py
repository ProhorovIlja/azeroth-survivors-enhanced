"""Synthetic tests for original Options parent instruction-shape profiles."""
import unittest

from tools import native_0139_parent_event_profile as p


class ParentEventProfileTests(unittest.TestCase):
    def test_direct_and_indirect_call_shapes(self):
        sample = "\n".join([
            "  140001020: call 0x140002000",
            "  140001030: callq *%rax",
            "  140001040: jmp *0x90(%rdx)",
            "  140001050: cmpb $0x10,%al",
            "  140001060: cmpb $0x11,%bl",
            "  140001070: cmpb $0x12,%cl",
        ])
        r = p.profile_disassembly(sample, 0x140000000, 0x1000, 0x1100)
        self.assertEqual(1, r["instruction_shape_counts"]["direct_calls"])
        self.assertEqual(1, r["instruction_shape_counts"]["indirect_calls"])
        self.assertEqual(1, r["instruction_shape_counts"]["indirect_jumps"])
        self.assertEqual([16, 17],
                         [e["compared_small_integer"]
                          for e in r["small_action_range_comparison_sites"]])

    def test_selector_access_direction(self):
        sample = "\n".join([
            "  140001040: cmpb $0xb,0x1da(%rax)",
            "  140001060: movb %cl,0x1da(%rdx)",
            "  140001080: movzbl 0x1da(%rdi),%edx",
        ])
        r = p.profile_disassembly(sample, 0x140000000, 0x1000, 0x1100)
        self.assertEqual(3, r["instruction_shape_counts"]["selector_displacement_accesses"])
        self.assertEqual(["read_or_address_candidate", "write_candidate",
                          "read_or_address_candidate"],
                         [e["role"] for e in r["selector_displacement_access_sites"]])

    def test_prevents_out_of_range_instruction_metadata(self):
        r = p.profile_disassembly("  140002000: cmpb $0x10,%al", 0x140000000,
                                  0x1000, 0x1100)
        self.assertEqual([], r["small_action_range_comparison_sites"])

    def test_non_instruction_text_ignored(self):
        r = p.profile_disassembly("not an instruction with call 0x140002000", 0x140000000,
                                  0x1000, 0x1100)
        self.assertEqual(0, r["instruction_shape_counts"]["direct_calls"])

    def test_records_are_capped(self):
        sample = "\n".join("  %x: cmpb $0x10,%%al" % (0x140001020 + i*4)
                           for i in range(4))
        r = p.profile_disassembly(sample, 0x140000000, 0x1000, 0x1100, cap=2)
        self.assertEqual(2, len(r["small_action_range_comparison_sites"]))
        self.assertTrue(r["comparison_records_may_be_capped"])

    def test_bad_record_cap_fails_closed(self):
        with self.assertRaises(ValueError):
            p.profile_disassembly("", 0, 0, 1, cap=0)

    def test_unknown_sha_rejected_before_opening_file(self):
        result = p.probe_parent_profiles("/no/file", "0" * 64, {})
        self.assertEqual("wrong_client_identity", result["reason"])

    def test_missing_verified_ancestry_rejected(self):
        result = p.probe_parent_profiles("/no/file", p.EXPECTED_SHA, {})
        self.assertEqual("options_ancestry_not_verified", result["reason"])


if __name__ == "__main__":
    unittest.main()
