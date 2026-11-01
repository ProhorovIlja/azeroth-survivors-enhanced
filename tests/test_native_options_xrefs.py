"""Fully synthetic x64 PE fixtures. Never runs, embeds or patches original game."""
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

from tools.native_options_xrefs import (
    KNOWN_EXES, XrefError, call_sites, code_references, map_binary,
    map_keys, unwind_functions, inspect_file, main,
)


def sample_pe():
    blob = bytearray(0x2800)
    blob[:2] = b"MZ"
    struct.pack_into("<I", blob, 0x3C, 0x80)
    blob[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", blob, 0x84, 0x8664, 3, 0, 0, 0, 0xF0, 0)
    struct.pack_into("<H", blob, 0x98, 0x20B)
    table = 0x80 + 24 + 0xF0
    for i, (name, size, rva, raw, virt) in enumerate((
        (".text", 0x1000, 0x1000, 0x400, 0x1000),
        (".rdata", 0x1000, 0x3000, 0x1400, 0x1000),
        (".pdata", 0x200, 0x4000, 0x2400, 48),
    )):
        at = table + 40 * i
        blob[at:at+8] = name.encode().ljust(8, b"\0")
        struct.pack_into("<IIII", blob, at+8, virt, rva, size, raw)
    # A realistic group of distinct original-schema key *names*, but fictional code.
    strings = ["options.defaults", "options.done", "options.save_files",
               "options.backups_about", "options.addon_missing", "options.addon_on_demand"]
    rvas = {}
    idx = 0
    for name in strings:
        data = name.encode() + b"\0"
        blob[0x1400+idx:0x1400+idx+len(data)] = data
        rvas[name] = 0x3000 + idx
        idx += len(data)
    # Functions: wrapper, main controls, saves, addons.
    functions = [(0x1100,0x1180),(0x1200,0x1280),(0x1300,0x1380),(0x1400,0x1480)]
    # main controls = 0x1200, saves = 0x1300, addons = 0x1400, parent=0x1100.
    for k,(start,end) in enumerate(functions):
        struct.pack_into("<III",blob,0x2400+12*k,start,end,0x4010)
    def lea(site,key):
        off = 0x400 + site - 0x1000
        disp = rvas[key] - (site + 7)
        blob[off:off+7] = b"\x48\x8d\x0d" + struct.pack("<i",disp)
    lea(0x1205,"options.defaults")
    lea(0x1215,"options.done")
    lea(0x1305,"options.save_files")
    lea(0x1315,"options.backups_about")
    lea(0x1405,"options.addon_missing")
    lea(0x1415,"options.addon_on_demand")
    def call(site,target):
        off = 0x400 + site - 0x1000
        blob[off:off+5] = b"\xe8" + struct.pack("<i", target-(site+5))
    call(0x1105,0x1200)
    call(0x1240,0x1300)
    call(0x1250,0x1400)
    return blob


class NativeOptionsXrefsTests(unittest.TestCase):
    def test_unknown_exe_rejected_by_default(self):
        b=sample_pe()
        with self.assertRaisesRegex(XrefError,"Unreviewed"):
            map_binary(b,hashlib.sha256(b).hexdigest())

    def test_synthetic_options_function_graph(self):
        b=sample_pe()
        result=map_binary(b,"a"*64,require_known=False)
        self.assertEqual(6,result["direct_key_xref_count"])
        self.assertEqual("0x1200",result["candidate_ui_entrypoints"]["options_page_controls"])
        self.assertEqual("0x1300",result["candidate_ui_entrypoints"]["saves_page_content"])
        self.assertEqual("0x1400",result["candidate_ui_entrypoints"]["addons_page_content"])
        sites={x["call_site_rva"] for x in result["direct_call_candidates"]}
        self.assertEqual({"0x1105","0x1240","0x1250"},sites)
        self.assertFalse(result["native_cheat_menu_implemented"])
        self.assertFalse(result["cheats_verified"])

    def test_no_fake_saves_key_from_saves_about_prefix(self):
        rdata=b"options.saves_about\x00options.export_saveoptions.done\x00"
        mapping=map_keys(rdata,0x3000)
        self.assertEqual("options.saves_about",mapping[0x3000])
        self.assertEqual("options.export_save",mapping[0x3000 + len(b"options.saves_about\x00")])
        self.assertNotIn("options.saves",mapping.values())

    def test_pdata_raw_padding_supported(self):
        code={"rva":0x1000,"virtual_bytes":0x1000}
        raw=struct.pack("<III",0x1200,0x1280,0x4010)+b"\0"*4
        funcs=unwind_functions(raw,code,virtual_bytes=12)
        self.assertEqual([(0x1200,0x1280)],funcs)

    def test_invalid_unwind_record_rejected(self):
        code={"rva":0x1000,"virtual_bytes":0x1000}
        with self.assertRaises(XrefError):
            unwind_functions(struct.pack("<III",0x2000,0x2100,0x4010),code)
        with self.assertRaises(XrefError):
            unwind_functions(b"\0"*13,code)

    def test_out_of_order_unwind_rejected(self):
        code={"rva":0x1000,"virtual_bytes":0x1000}
        data=struct.pack("<III",0x1400,0x1480,0x4010)+struct.pack("<III",0x1300,0x1380,0x4020)
        with self.assertRaises(XrefError):
            unwind_functions(data,code)

    def test_wrong_architecture_refused(self):
        blob=sample_pe()
        struct.pack_into("<H",blob,0x84,0x14c)
        with self.assertRaises(ValueError):
            map_binary(blob,"a"*64,require_known=False)

    def test_malformed_pe_boundary_refused(self):
        blob=sample_pe()
        # Redirect .rdata raw offset beyond the actual bytes.
        table=0x80+24+0xF0
        struct.pack_into("<I",blob,table+40+8+12,len(blob)+200)
        with self.assertRaises(ValueError):
            map_binary(blob,"a"*64,require_known=False)

    def test_cannot_extract_native_hook_proof_from_text(self):
        output=map_binary(sample_pe(),"a"*64,require_known=False)
        self.assertFalse(output["disassembler_or_hook_verification"])
        self.assertFalse(output["original_options_page_modified"])
        self.assertTrue(all(not c["menu_insertion_point_verified"] for c in output["function_clusters"]))

    def test_unknown_hash_registry_refuses_empty(self):
        self.assertNotIn("0"*64,KNOWN_EXES)

    def test_refuse_input_symlink_and_short_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"untrusted.exe"
            p.write_bytes(sample_pe())
            with self.assertRaises(XrefError):
                inspect_file(p)  # tiny synthetic, not a legitimate EXE
            link=Path(tmp)/"link.exe"
            try:link.symlink_to(p)
            except OSError:self.skipTest("Platform disallows symlinks")
            with self.assertRaises(XrefError):
                inspect_file(link)


if __name__=="__main__":unittest.main()
