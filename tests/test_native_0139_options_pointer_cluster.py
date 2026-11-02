"""Synthetic-only six-pointer Options cluster and callback profile tests."""
import struct
import unittest

from tools import native_0139_options_pointer_cluster as p


class PointerClusterTests(unittest.TestCase):
    BASE = 0x140000000
    SECTION = 0x652D000

    def fixture(self):
        raw = bytearray(b"\x00"*0x2000)
        for slot, function in p.KNOWN_SIX_SLOT_CLUSTER.items():
            struct.pack_into("<Q", raw, slot - self.SECTION, self.BASE + function)
        return raw

    def test_exact_all_six_pointers_confirmed_in_original_positions(self):
        x = p.exact_cluster_metadata(self.fixture(), self.SECTION, self.BASE)
        self.assertTrue(x["confirmed"])
        self.assertEqual(6, len(x["slots"]))
        self.assertEqual("0x652dc10", x["slots"][-1]["slot_rva"])

    def test_single_wrong_target_rejects_entire_cluster(self):
        raw = self.fixture()
        struct.pack_into("<Q", raw, 0x652DC08-self.SECTION, self.BASE+0x20e451)
        x = p.exact_cluster_metadata(raw, self.SECTION, self.BASE)
        self.assertFalse(x["confirmed"])
        self.assertEqual("pointer_value_does_not_match_official", x["reason"])

    def test_wrong_image_base_rejected(self):
        x = p.exact_cluster_metadata(self.fixture(), self.SECTION, self.BASE+0x10000)
        self.assertFalse(x["confirmed"])

    def test_missing_section_range_rejected(self):
        x = p.exact_cluster_metadata(b"\x00", self.SECTION, self.BASE)
        self.assertFalse(x["confirmed"])
        self.assertEqual("cluster_slot_outside_aligned_rdata", x["reason"])

    def test_profile_real_direct_calls_targets_are_metadata_only(self):
        instructions = "\n".join((
            "  14020e410: push %rbx",
            "  14020e411: call 0x1403f5d40",
            "  14020e416: cmpb $0xb,0x1da(%rax)",
            "  14020e41d: jmp 0x14020e450",
        ))
        r = p.profile_neighbor(instructions, self.BASE, 0x20e410, 0x20e430)
        self.assertEqual([{"site_rva":"0x20e411","called_rva":"0x3f5d40"}],
                         r["direct_call_targets"])
        self.assertEqual("0x20e450", r["direct_unconditional_jumps"][0]["target_rva"])
        self.assertFalse(r["native_event_dispatcher_identity_verified"])

    def test_profile_indirect_jump_observed_not_event_proof(self):
        output = "  14020e410: jmp *%rax\n"
        r = p.profile_neighbor(output, self.BASE, 0x20e410, 0x20e440)
        self.assertEqual(["0x20e410"], r["indirect_unconditional_jumps"])
        self.assertFalse(r["native_event_dispatcher_identity_verified"])

    def test_profile_ignores_instruction_outside_unwind_bounds(self):
        output = "  14020e410: call 0x1403f5d40\n"
        r = p.profile_neighbor(output, self.BASE, 0x20e420, 0x20e440)
        self.assertEqual([], r["direct_call_targets"])

    def test_wrong_game_sha_refused_before_opening_file(self):
        r = p.audit_options_six_pointer_cluster("/notfound", "0"*64, {})
        self.assertEqual("unknown_game_release", r["reason"])

    def test_missing_ancestor_static_profile_refused(self):
        r = p.audit_options_six_pointer_cluster("/notfound", p.EXPECTED_SHA, {})
        self.assertEqual("prior_pointer_inventory_missing", r["reason"])


if __name__ == "__main__":
    unittest.main()
