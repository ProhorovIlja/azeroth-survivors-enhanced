"""Synthetic tests for direct x64 caller provenance of 0.139 byte stores."""
import struct
import unittest

from tools import native_0139_selector_callers as x


def good_report():
    return {
        "status": "confirmed_full_displacement_inventory",
        "raw_prefilter_fully_examined": True,
        "access_records_truncated": False,
        "access_records": [
            {"function_begin_rva": "0x1200", "instruction_mnemonic": "movb",
             "access_candidate": "write_candidate", "disassembled_from_function_start": True},
            {"function_begin_rva": "0x1210", "instruction_mnemonic": "movl",
             "access_candidate": "write_candidate", "disassembled_from_function_start": True},
            {"function_begin_rva": "0x1220", "instruction_mnemonic": "movb",
             "access_candidate": "read_or_address_candidate",
             "disassembled_from_function_start": True}]}


def fixture():
    base = 0x1000
    raw = bytearray(b"\x90" * 0x300)
    for site in (0x1020, 0x1130):
        off = site - base
        raw[off:off+5] = b"\xe8" + struct.pack("<i", 0x1200 - site - 5)
    return raw


class SelectorCallerTests(unittest.TestCase):
    def test_only_confirmed_byte_store_owners_accepted(self):
        self.assertEqual({0x1200}, x.byte_writer_owners(good_report()))

    def test_partial_inventory_refused(self):
        data = good_report()
        data["status"] = "confirmed_partial_inventory"
        self.assertEqual(set(), x.byte_writer_owners(data))

    def test_truncated_event_report_refused(self):
        data = good_report()
        data["access_records_truncated"] = True
        self.assertEqual(set(), x.byte_writer_owners(data))

    def test_only_exact_direct_target_counted(self):
        result = x.scan_direct_calls(fixture(), 0x1000, [(0x1000, 0x1100),
                                                         (0x1100, 0x1200)],
                                     {0x1200})
        self.assertEqual(2, result["direct_e8_candidate_count"])
        self.assertEqual("0x1200", result["edges"][0]["target_byte_writer_function_rva"])
        self.assertFalse(result["edges_truncated"])

    def test_not_found_when_target_is_nearby_but_not_exact(self):
        self.assertEqual(0, x.scan_direct_calls(fixture(), 0x1000,
                                                 [(0x1000, 0x1200)], {0x1201})
                         ["direct_e8_candidate_count"])

    def test_call_outside_unwind_is_excluded(self):
        data = fixture()
        result = x.scan_direct_calls(data, 0x1000, [(0x1000, 0x1010),
                                                    (0x1100, 0x1120)], {0x1200})
        self.assertEqual(0, result["direct_e8_candidate_count"])

    def test_truncation_is_explicit(self):
        result = x.scan_direct_calls(fixture(), 0x1000, [(0x1000, 0x1100),
                                                         (0x1100, 0x1200)],
                                     {0x1200}, limit=1)
        self.assertTrue(result["edges_truncated"])
        self.assertEqual(2, result["direct_e8_candidate_count"])
        self.assertEqual(1, len(result["edges"]))

    def test_unknown_exe_sha_fails_without_touching_disk(self):
        result = x.audit_byte_writer_callers("/nonexistent.exe", "0"*64, good_report())
        self.assertEqual("wrong_client_identity", result["reason"])


if __name__ == "__main__":
    unittest.main()
