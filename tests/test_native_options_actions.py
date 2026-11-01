"""Fully invented PE-section fixtures for exact-sha-gated native action research."""
from pathlib import Path
import json
import struct
import tempfile
import unittest
from unittest.mock import patch
from tools import native_options_actions as m

T={"name":".text","rva":0x100000,"raw_offset":0,"raw_bytes":0x300000,"virtual_bytes":0x300000}
R={"name":".rdata","rva":0x6300000,"raw_offset":0x300000,"raw_bytes":0x70000,"virtual_bytes":0x70000}


def put(buf,part,rva,raw):
    offset=part['raw_offset']+rva-part['rva']
    assert 0<=offset<=len(buf)-len(raw)
    buf[offset:offset+len(raw)]=raw


def invented_data():
    data=bytearray(R['raw_offset']+R['raw_bytes'])
    for site in m.OBSERVED_CALL_SITES:
        put(data,T,site,b'\xe8'+struct.pack('<i',m.SHARED_WIDGET_HELPER-(site+5)))
    put(data,T,m.SELECTOR_CHECK_RVA,bytes.fromhex('80 b8 da 01 00 00 0b 74 3c'))
    put(data,T,m.OTHER_DONE_TEXT_SITE_RVA,b'\x48\x8d\x0d')
    for row in m.FOOTER:
        key_rva=0x63572f4 if row['action_id']==16 else 0x6357304
        put(data,R,key_rva,row['key'].encode('ascii'))
        site=row['key_load_rva']
        put(data,T,site,b'\x48\x8d\x0d'+struct.pack('<i',key_rva-(site+7)))
        put(data,T,row['action_imm_rva'],b'\x48\xb9'+struct.pack('<Q',(1<<63)|row['action_id']))
    return data


class NativeButtonActionTests(unittest.TestCase):
    def audit(self,data):
        with patch.object(m,'read_pe_sections',return_value=[T,R]):
            return m.analyze_bytes(data,m.KNOWN_0138_SHA)

    def test_original_8_button_calls_and_footer_tags(self):
        result=self.audit(invented_data())
        self.assertEqual(8,result['observed_call_site_count'])
        self.assertEqual([16,17],[x['action_tag_low_id'] for x in result['options_footer_action_items']])
        self.assertEqual(['options.defaults','options.done'],[x['public_localization_key'] for x in result['options_footer_action_items']])
        self.assertFalse(result['native_cheats_verified'])
        self.assertFalse(result['runtime_event_abi_verified'])
        self.assertTrue(result['defaults_hidden_for_saves_page'])

    def test_wrong_sha_fail_closed(self):
        with self.assertRaisesRegex(m.ActionAuditError,'Unreviewed'):
            m.analyze_bytes(invented_data(),'0'*64)

    def test_each_callsite_must_target_widget_helper(self):
        for site in m.OBSERVED_CALL_SITES:
            with self.subTest(site=site):
                d=invented_data(); d[site-T['rva']+1]^=1
                with self.assertRaises(m.ActionAuditError): self.audit(d)

    def test_unexpected_opcode_not_accepted(self):
        d=invented_data();d[m.OBSERVED_CALL_SITES[0]-T['rva']]=0x90
        with self.assertRaises(m.ActionAuditError):self.audit(d)

    def test_wrong_defaults_action_id_fails(self):
        d=invented_data();d[m.FOOTER[0]['action_imm_rva']-T['rva']+2]^=1
        with self.assertRaises(m.ActionAuditError):self.audit(d)

    def test_wrong_done_action_id_fails(self):
        d=invented_data();d[m.FOOTER[1]['action_imm_rva']-T['rva']+2]^=1
        with self.assertRaises(m.ActionAuditError):self.audit(d)

    def test_missing_key_fails(self):
        d=invented_data();d[R['raw_offset']+0x63572f4-R['rva']]=ord('x')
        with self.assertRaises(m.ActionAuditError):self.audit(d)

    def test_mutated_key_lea_fails(self):
        d=invented_data();d[m.FOOTER[1]['key_load_rva']-T['rva']]=0x90
        with self.assertRaises(m.ActionAuditError):self.audit(d)

    def test_selector_branch_must_be_exact(self):
        d=invented_data();d[m.SELECTOR_CHECK_RVA-T['rva']+6]^=1
        with self.assertRaises(m.ActionAuditError):self.audit(d)

    def test_missing_conditional_jump_is_rejected(self):
        d=invented_data();d[m.SELECTOR_CHECK_RVA-T['rva']+7]=0x90
        with self.assertRaises(m.ActionAuditError):self.audit(d)

    def test_wrong_jump_destination_is_rejected(self):
        d=invented_data();d[m.SELECTOR_CHECK_RVA-T['rva']+8]^=1
        with self.assertRaises(m.ActionAuditError):self.audit(d)

    def test_other_done_text_path_not_conflated(self):
        d=invented_data();d[m.OTHER_DONE_TEXT_SITE_RVA-T['rva']]=0x90
        with self.assertRaises(m.ActionAuditError):self.audit(d)

    def test_bounds_checked(self):
        with self.assertRaises((ValueError,m.ActionAuditError)):
            m.direct_target(b'\x90'*3,{"rva":0,"raw_offset":0,"raw_bytes":3,"virtual_bytes":3},0)

    def test_output_is_metadata_only(self):
        report=self.audit(invented_data())
        self.assertNotIn('inline',json.dumps(report).lower())
        self.assertFalse(report['native_cheats_page_installed'])

    def test_refuse_overwriting_existing_report(self):
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/'report.json';m.save_new(file,self.audit(invented_data()))
            with self.assertRaises(ValueError):m.save_new(file,{})

if __name__=='__main__':unittest.main()
