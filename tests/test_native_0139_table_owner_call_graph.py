"""Synthetic tests for verified v0.139 native pointer-table owner calls."""
import unittest

from tools import native_0139_table_owner_call_graph as m


class NativeOriginalOwnerCallGraphTests(unittest.TestCase):
    BASE=0x140000000

    def fixture(self):
        return "\n".join([
            "  1401e3bc0: push %rbp",
            "  1401e3bd0: movabs $0x8000000000000011,%rax",
            "  1401e3de0: cmp $0xf,%r8b",
            "  1401e3e00: call 0x1401e5530",
            "  1401e4100: call 0x1403f5d40",
            "  1401e4135: lea 0x1234(%rip),%rax",
            "  1401e4140: call 0x1401e0e60",
            "  1401e4385: mov 0x5678(%rip),%rcx",
            "  1401e438f: call 0x1401df770",
        ])

    def test_original_owner_calls_and_helper_role(self):
        r=m.profile_owner(self.fixture(),self.BASE,m.OWNER_RVA,0x1e5000,b"",0)
        self.assertEqual(4,r["direct_call_count_bounded"])
        self.assertEqual("action_widget_constructor",r["direct_call_sites"][0]["known_role"])
        self.assertEqual("options_renderer",r["direct_call_sites"][1]["known_role"])
        self.assertTrue(r["small_integer_15_comparison"]["is_small_15"])

    def test_both_table_references_must_be_real_rip_instructions(self):
        r=m.profile_owner(self.fixture(),self.BASE,m.OWNER_RVA,0x1e5000,b"",0)
        self.assertTrue(all(x["validated_rip_instruction"]
                            for x in r["known_table_reference_near_call_context"]))
        self.assertEqual("0x1e4140",
                         r["known_table_reference_near_call_context"][0]["nearest_following_call_site_rva"])

    def test_generic_tag_not_a_click_consumer(self):
        r=m.profile_owner(self.fixture(),self.BASE,m.OWNER_RVA,0x1e5000,b"",0)
        self.assertEqual([17],[x["generic_low_id"] for x in r["generic_highbit_tag_candidates"]])
        self.assertFalse(r["original_click_event_consumer_verified"])

    def test_nonmatching_opcode_does_not_confirm_table_reference(self):
        broken=self.fixture().replace("1401e4135: lea 0x1234(%rip),%rax",
                                      "1401e4135: mov $0x1234,%rax")
        r=m.profile_owner(broken,self.BASE,m.OWNER_RVA,0x1e5000,b"",0)
        self.assertFalse(r["known_table_reference_near_call_context"][0]["validated_rip_instruction"])

    def test_wrong_address_inside_same_function_is_not_valid(self):
        broken=self.fixture().replace("1401e4135:", "1401e4136:")
        r=m.profile_owner(broken,self.BASE,m.OWNER_RVA,0x1e5000,b"",0)
        self.assertFalse(r["known_table_reference_near_call_context"][0]["validated_rip_instruction"])

    def test_ignores_direct_calls_outside_function(self):
        r=m.profile_owner(self.fixture(),self.BASE,0x1e4100,0x1e4500,b"",0)
        self.assertEqual(3,r["direct_call_count_bounded"])

    def test_invalid_cap(self):
        with self.assertRaises(ValueError):
            m.profile_owner("",self.BASE,1,2,b"",0,cap=0)

    def test_sha_rejected_before_open(self):
        x=m.audit_table_owner_call_graph("/missing.exe","0"*64,{})
        self.assertEqual("unexpected_original_client",x["reason"])

    def test_owner_provenance_required(self):
        x=m.audit_table_owner_call_graph("/missing.exe",m.EXPECTED_SHA,{})
        self.assertEqual("missing_confirmed_table_ownership",x["reason"])


if __name__=="__main__":
    unittest.main()
