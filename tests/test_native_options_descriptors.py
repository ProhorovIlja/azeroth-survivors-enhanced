"""Synthetic, game-asset-free tests for original Options descriptor classification."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import native_options_descriptors as m


def fixture():
    # These bytes are invented, not any game strings or original machine code.
    v = bytearray(0x9000)
    section = {"name":".rdata","rva":m.TABLE_RVA-0x100,
               "raw_offset":0,"raw_bytes":len(v),"virtual_bytes":len(v)}
    key_rva=m.TABLE_RVA+0x5000
    key=b"OPTION_TOOLTIP_FAKE_SETTING"
    prose=b"Synthetic original text for test only"
    key_off=key_rva-section["rva"]
    v[key_off:key_off+len(key)]=key
    v[key_off+0x100:key_off+0x100+len(prose)]=prose
    kinds=[0]*69+[1]*36+[2]*3
    page_ids=[]
    for page,n in m.EXPECTED_BY_PAGE.items():
        page_ids += [page]*n
    assert len(page_ids)==len(kinds)==108
    start=m.TABLE_RVA-section["rva"]
    for i,(page,kind) in enumerate(zip(page_ids,kinds)):
        off=start+i*m.STRIDE
        v[off]=kind
        v[off+m.FIELD_PAGE]=page
        v[off+m.FIELD_DEPENDENT]=1 if i%5==0 else 0
        if kind!=2:
            rva=key_rva+(0x100 if kind==1 else 0)
            encoded=prose if kind==1 else key
            struct.pack_into("<QQ",v,off+m.FIELD_POINTER,m.IMAGE_BASE+rva,len(encoded))
    return v,section


class DescriptorTests(unittest.TestCase):
    def test_original_counts_and_metadata_only(self):
        data,part=fixture(); summary=m.summarize(m.scan_records(data,part))
        self.assertEqual(108,summary["record_count"])
        self.assertEqual(69,summary["record_kinds"]["localization_key"])
        self.assertEqual(36,summary["record_kinds"]["inline_help_prose"])
        self.assertEqual(3,summary["record_kinds"]["separator"])
        self.assertEqual([6,11],summary["special_handled_ids_without_descriptor_rows"])
        self.assertNotIn("FAKE_SETTING",str(summary))
        self.assertFalse(summary["native_cheat_page_installed"])

    def test_descriptor_kind_is_bounded(self):
        d,p=fixture();d[m.TABLE_RVA-p["rva"]]=254
        with self.assertRaises(m.DescriptorError):m.scan_records(d,p)

    def test_page_id_rejects_unknown(self):
        d,p=fixture();d[m.TABLE_RVA-p["rva"]+m.FIELD_PAGE]=200
        with self.assertRaises(m.DescriptorError):m.scan_records(d,p)

    def test_dependency_flag_is_boolean(self):
        d,p=fixture();d[m.TABLE_RVA-p["rva"]+m.FIELD_DEPENDENT]=2
        with self.assertRaises(m.DescriptorError):m.scan_records(d,p)

    def test_pointer_must_be_in_rdata(self):
        d,p=fixture();struct.pack_into("<Q",d,m.TABLE_RVA-p["rva"]+m.FIELD_POINTER,0x1234)
        with self.assertRaises(m.DescriptorError):m.scan_records(d,p)

    def test_length_must_be_bounded(self):
        d,p=fixture();struct.pack_into("<Q",d,m.TABLE_RVA-p["rva"]+m.FIELD_LENGTH,999999)
        with self.assertRaises(m.DescriptorError):m.scan_records(d,p)

    def test_short_key_must_be_localization_id(self):
        d,p=fixture();off=m.TABLE_RVA+0x5000-p["rva"]
        d[off:off+6]=b"XXXXXX"
        with self.assertRaises(m.DescriptorError):m.scan_records(d,p)

    def test_separator_cannot_have_pointer(self):
        d,p=fixture();off=m.TABLE_RVA-p["rva"]+105*m.STRIDE
        struct.pack_into("<Q",d,off+m.FIELD_POINTER,m.IMAGE_BASE+m.TABLE_RVA)
        with self.assertRaises(m.DescriptorError):m.scan_records(d,p)

    def test_malformed_utf8_is_rejected(self):
        d,p=fixture();off=m.TABLE_RVA+0x5100-p["rva"];d[off]=0xff
        with self.assertRaises(m.DescriptorError):m.scan_records(d,p)

    def test_nonmatching_population_fails_closed(self):
        d,p=fixture();rows=m.scan_records(d,p);rows[0]["page_id"]=11
        with self.assertRaises(m.DescriptorError):m.summarize(rows)

    def test_wrong_sha_refused_before_content(self):
        d,p=fixture()
        with self.assertRaises(m.DescriptorError):m.analyze_bytes(d,"0"*64)

    def test_forged_sha_and_synthetic_pe_can_be_independently_tested(self):
        d,p=fixture()
        d.extend(b"\0"*1024)
        part={"name":".text","rva":0x3F8400,"raw_offset":0x9000,"raw_bytes":1024,"virtual_bytes":1024}
        for site in m.EMITTER_CALLS:
            off=part["raw_offset"]+site-part["rva"]
            d[off:off+5]=bytes([0xE8])+struct.pack("<i",m.EMITTER_RVA-(site+5))
        with patch.object(m,"read_pe_sections",return_value=[p,part]):
            result=m.analyze_bytes(d,m.KNOWN_0138_SHA)
        self.assertEqual(108,result["record_count"])
        self.assertEqual([hex(x) for x in m.EMITTER_CALLS],result["verified_descriptor_consumer_calls"])

    def test_wrong_call_target_fails_closed(self):
        data=bytearray(1024)
        part={"rva":0x3F8400,"raw_offset":0,"raw_bytes":1024,"virtual_bytes":1024}
        for site in m.EMITTER_CALLS:
            off=site-part["rva"]
            data[off:off+5]=bytes([0xE8])+struct.pack("<i",m.EMITTER_RVA-(site+5))
        self.assertEqual([hex(x) for x in m.EMITTER_CALLS],m.verify_emitter_calls(data,part))
        data[m.EMITTER_CALLS[1]-part["rva"]+1]^=1
        with self.assertRaises(m.DescriptorError):m.verify_emitter_calls(data,part)

    def test_output_never_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/"report.json"
            m.save_new(f,{"ok":True})
            self.assertTrue(json.loads(f.read_text())["ok"])
            with self.assertRaises(m.DescriptorError):m.save_new(f,{"ok":False})

    def test_symlink_output_refused(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);dest=p/"a";dest.write_text("original")
            link=p/"b"
            try:link.symlink_to(dest)
            except OSError:self.skipTest("Symlinks unavailable")
            with self.assertRaises(m.DescriptorError):m.save_new(link,{})
            self.assertEqual("original",dest.read_text())


if __name__=="__main__":unittest.main()
