"""Synthetic-only exact original 0.139 six-function table ownership xrefs."""
import struct
import unittest

from tools import native_0139_options_pointer_table_owners as m


class TableOwnersTests(unittest.TestCase):
    BASE = 0x140000000

    def test_code_rip_reference_to_table_begin_confirmed_as_candidate(self):
        code = bytearray(b"\x90" * 64)
        start = 0x1000
        code[16:23] = b"\x48\x8d\x0d" + struct.pack("<i", m.TABLE_BEGIN-(start+16+7))
        p = m.potential_rip_references(
            code, start, m.TABLE_BEGIN-96, m.TABLE_END+96, [(0x1000,0x1040)])
        self.assertEqual(1, p["raw_rip_target_count"])
        self.assertEqual(0, p["records"][0]["target_offset_from_table_begin"])
        self.assertFalse(p["records"][0]["instruction_confirmed"])

    def test_code_references_nearby_accepted_and_outside_rejected(self):
        code = bytearray(b"\x90"*64)
        code[0:7] = b"\x48\x8b\x05"+struct.pack("<i",m.TABLE_BEGIN-60-(0x1000+7))
        code[16:23] = b"\x48\x8d\x15"+struct.pack("<i",m.TABLE_BEGIN-200-(0x1010+7))
        p = m.potential_rip_references(
            code,0x1000,m.TABLE_BEGIN-96,m.TABLE_END+96,[(0x1000,0x1040)])
        self.assertEqual(1,p["raw_rip_target_count"])
        self.assertEqual(-60,p["records"][0]["target_offset_from_table_begin"])

    def test_code_call_bytes_not_rip_mem_load(self):
        code = b"\xe8"+struct.pack("<i", m.TABLE_BEGIN-0x1005)
        p = m.potential_rip_references(
            code, 0x1000, m.TABLE_BEGIN-96,m.TABLE_END+96,[(0x1000,0x1010)])
        self.assertEqual(0,p["raw_rip_target_count"])

    def test_rip_shape_outside_unwind_function_rejected(self):
        code = b"\x48\x8d\x0d"+struct.pack("<i",m.TABLE_BEGIN-0x1007)
        p=m.potential_rip_references(
            code, 0x1000,m.TABLE_BEGIN-96,m.TABLE_END+96,[(0x1010,0x1030)])
        self.assertEqual(0,p["raw_rip_target_count"])

    def test_bounded_raw_candidate_limit(self):
        code = bytearray(b"\x90"*48)
        for pos in (0, 16, 32):
            code[pos:pos+7]=b"\x48\x8d\x0d"+struct.pack(
                "<i", m.TABLE_BEGIN-(0x1000+pos+7))
        r=m.potential_rip_references(code,0x1000,m.TABLE_BEGIN-96,
                                      m.TABLE_END+96,[(0x1000,0x1040)],cap=1)
        self.assertEqual(3,r["raw_rip_target_count"])
        self.assertTrue(r["truncated"])
        self.assertEqual(1,len(r["records"]))

    def test_pointer_to_table_found_with_correct_imagebase(self):
        data=bytearray(b"\x00"*64)
        struct.pack_into("<Q",data,8,self.BASE+m.TABLE_BEGIN)
        x=m.static_references_to_table(data,0x2000,self.BASE,{m.TABLE_BEGIN})
        self.assertEqual(1,x["pointer_count"])
        self.assertEqual("0x2008",x["records"][0]["pointer_slot_rva"])

    def test_unaligned_pointer_and_wrong_target_rejected(self):
        data=b"\x00"+struct.pack("<Q",self.BASE+m.TABLE_BEGIN)+b"\x00"*8
        x=m.static_references_to_table(data,0x2000,self.BASE,{m.TABLE_BEGIN})
        self.assertEqual(0,x["pointer_count"])

    def test_cap_validation(self):
        with self.assertRaises(ValueError):
            m.potential_rip_references(b"",0,100,1,[])
        with self.assertRaises(ValueError):
            m.potential_rip_references(b"",0,100,150,[],cap=0)

    def test_refuse_unknown_original_before_open(self):
        x=m.audit_pointer_table_owners("/missing.exe","0"*64,{})
        self.assertEqual("unknown_original_client",x["reason"])

    def test_requires_prior_six_pointer_confirmation(self):
        x=m.audit_pointer_table_owners("/missing.exe",m.EXPECTED_SHA,{})
        self.assertEqual("six_pointer_baseline_missing",x["reason"])


if __name__ == "__main__":
    unittest.main()
