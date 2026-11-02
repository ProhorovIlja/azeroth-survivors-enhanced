"""Synthetic-only original x64 Options page GPR dataflow regression tests."""
import unittest

from tools import native_0139_page_register_flow as flow


def audit(s):
    return flow.register_comparison_paths(s, 0x140000000, 0x1000, 0x2000)


class PageRegisterFlowTests(unittest.TestCase):
    def test_same_gpr_alias_recognizes_page_value_and_branch(self):
        output = "\n".join((
            "  140001010: movzbl 0x1da(%rax),%ecx",
            "  140001015: cmp $0xf,%cl",
            "  14000101a: ja 0x140001080",
        ))
        r = audit(output)
        self.assertEqual(1, len(r))
        self.assertEqual("rcx", r[0]["destination_gpr"])
        self.assertEqual(15, r[0]["candidate_comparisons"][0]["literal"])
        self.assertEqual("0x1080", r[0]["candidate_comparisons"][0]["following_conditional"]["branch_target_rva"])
        self.assertEqual("control_transfer", r[0]["tracking_boundary"])

    def test_other_register_comparison_does_not_count(self):
        output = ("  140001010: movzbl 0x1da(%rax),%ecx\n"
                  "  140001015: cmp $0xf,%eax\n")
        self.assertEqual([], audit(output)[0]["candidate_comparisons"])

    def test_control_transfer_stops_tracking(self):
        output = ("  140001010: movzbl 0x1da(%rax),%eax\n"
                  "  140001013: je 0x140001050\n"
                  "  140001020: cmp $0xb,%al\n")
        r = audit(output)
        self.assertEqual([], r[0]["candidate_comparisons"])
        self.assertEqual("control_transfer", r[0]["tracking_boundary"])

    def test_register_mutation_stops_tracking(self):
        output = ("  140001010: movzbl 0x1da(%rax),%eax\n"
                  "  140001018: mov %edx,%eax\n"
                  "  140001020: cmp $0xf,%eax\n")
        r = audit(output)
        self.assertEqual([], r[0]["candidate_comparisons"])
        self.assertEqual("register_overwrite_or_possible_mutation", r[0]["tracking_boundary"])

    def test_movzbl_of_unrelated_field_rejected(self):
        self.assertEqual([], audit("  140001010: movzbl 0x1db(%rax),%eax\n"))

    def test_immediate_must_be_byte_range(self):
        output = ("  140001010: movzbl 0x1da(%rax),%eax\n"
                  "  140001015: cmp $0x100,%eax\n")
        self.assertEqual([], audit(output)[0]["candidate_comparisons"])

    def test_unknown_register_not_assumed(self):
        self.assertEqual([], audit("  140001010: movzbl 0x1da(%rax),%xmm0\n"))

    def test_none_if_unsupported_derived_copy(self):
        output = ("  140001010: movzbl 0x1da(%rax),%eax\n"
                  "  140001015: mov %eax,%ecx\n"
                  "  140001018: cmp $0xf,%ecx\n")
        self.assertEqual([], audit(output)[0]["candidate_comparisons"])

    def test_capped_proximity_window(self):
        output = ["  140001010: movzbl 0x1da(%rax),%eax"]
        output.extend("  %x: nop" % (0x140001020 + i) for i in range(40))
        output.append("  140001100: cmp $0xb,%al")
        self.assertEqual([], audit("\n".join(output))[0]["candidate_comparisons"])

    def test_invalid_max_forward(self):
        with self.assertRaises(ValueError):
            flow.register_comparison_paths("", 0, 0, 1, max_forward=0)

    def test_structural_page_six_skip_requires_independent_saves_call(self):
        register_report = {"function_profiles": [{
            "owner_function_rva": "0x3f5d40",
            "candidate_same_gpr_paths": [{
                "field_load_rva": "0x3f6c33",
                "candidate_comparisons": [{
                    "compare_site_rva": "0x3f6c3b", "literal": 6,
                    "following_conditional": {
                        "branch_site_rva": "0x3f6c3e",
                        "branch_condition": "je",
                        "branch_target_rva": "0x3f6d4a"}}]}]}]}
        calls = {"checked": [{"role": "saves_page_content",
                              "site_rva": "0x3f6d43",
                              "target_rva": "0x1df770",
                              "call_instruction_confirmed": True}]}
        result = flow.correlate_page_6_with_saves_builder(register_report, calls)
        self.assertTrue(result["structurally_verified_skip"])
        self.assertFalse(result["page_label_of_value_6_confirmed"])
        self.assertFalse(result["tab_change_event_consumer_confirmed"])
        calls["checked"][0]["call_instruction_confirmed"] = False
        self.assertFalse(flow.correlate_page_6_with_saves_builder(
            register_report, calls)["structurally_verified_skip"])
        calls["checked"][0]["call_instruction_confirmed"] = True
        register_report["function_profiles"][0]["candidate_same_gpr_paths"][0]["candidate_comparisons"][0]["literal"] = 5
        self.assertFalse(flow.correlate_page_6_with_saves_builder(
            register_report, calls)["structurally_verified_skip"])

    def test_sha_rejected_without_opening_game(self):
        self.assertEqual("unknown_client_sha", flow.audit_page_register_flow(
            "/missing.exe", "0"*64, {})["reason"])

    def test_page_baseline_required(self):
        self.assertEqual("page_branch_baseline_not_verified",
                         flow.audit_page_register_flow("/missing.exe", flow.EXPECTED_SHA, {})["reason"])


if __name__ == "__main__":
    unittest.main()
