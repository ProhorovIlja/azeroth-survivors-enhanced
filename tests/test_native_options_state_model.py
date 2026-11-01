"""Public synthetic-only regression tests. No proprietary game EXE in CI."""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from tools import native_options_state_model as model
from tools.native_options_runtime_trace import build_script, validate_log_path, TraceError


HASH = model.KNOWN_0138_SHA
TEXT = {"name":".text", "rva":0x3F0000,"raw_offset":0,"raw_bytes":0x20000,"virtual_bytes":0x20000}
RDATA={"name":".rdata","rva":0x6300000,"raw_offset":0x20000,"raw_bytes":0x70000,"virtual_bytes":0x70000}


def file_offset(section, rva):
    return section["raw_offset"]+(rva-section["rva"])


def place(data, section, rva, blob):
    p=file_offset(section,rva)
    data[p:p+len(blob)]=blob


def synthetic_data():
    data=bytearray(RDATA["raw_offset"]+RDATA["raw_bytes"])
    ins={
        0x3F877C: '41 0f b6 85 da 01 00 00 ff c8 83 f8 0a 77 48',
        0x3F878B: '48 8d 0d de 41 f6 05 48 63 04 81 48 01 c8 ff e0',
        0x3F8420: '49 ff c7 49 81 c5 98 00 00 00 49 81 fd 20 40 00 00',
        0x3F8443: '3a 88 da 01 00 00',
        0x3F8487: '41 80 bc 3d 91 00 00 00 0a',
    }
    for rva, hexdump in ins.items():
        place(data, TEXT, rva, bytes.fromhex(hexdump))
    targets=[0x3F879B,0x3F87D3,0x3F87D3,0x3F87D3,0x3F87D3,
             0x3F87B7,0x3F87D3,0x3F87D3,0x3F87D3,0x3F87A9,0x3F87C5]
    jump_table=b''.join(struct.pack('<i',value-model.IMAGE_RVA_TABLE) for value in targets)
    place(data,RDATA,model.IMAGE_RVA_TABLE,jump_table)
    for rva,key in [(0x631A9D8,'options.hint.gamepad'),(0x631A9EC,'options.hint.keybindings'),
                    (0x631AA04,'options.hint.addons'),(0x631AA17,'options.hint.saves'),
                    (0x631AA29,'options.hint')]:
        place(data,RDATA,rva,key.encode('ascii'))
    return data


class PageStateModelTests(unittest.TestCase):
    def valid(self, data):
        with patch.object(model,"analyze_selector",return_value={
            "page_selector_field_offset":"0x1da","selector_fetch_rva":"0x3f83b3",
        }),patch.object(model,"read_pe_sections",return_value=[TEXT,RDATA]):
            return model.model_from_bytes(data,HASH)

    def test_realistic_synthetic_page_map(self):
        report=self.valid(synthetic_data())
        self.assertEqual(108,report['record_loop']['maximum_iterated_records'])
        self.assertEqual('0x91',report['record_loop']['selection_id_field_offset_in_record'])
        hints={item['selection_value']:item['hint_key'] for item in report['observed_selector_hints']}
        self.assertEqual('options.hint.addons',hints[10])
        self.assertEqual('options.hint.saves',hints[11])
        self.assertEqual('options.hint.keybindings',hints[6])
        self.assertEqual('options.hint.gamepad',hints[1])
        self.assertEqual('options.hint',hints[8])
        self.assertFalse(report['new_native_cheats_page_installed'])
        self.assertFalse(report['gameplay_cheat_effects_verified'])

    def test_reject_unknown_hash_before_pe_mapping(self):
        with self.assertRaisesRegex(model.ModelError,'Unknown'):
            model.model_from_bytes(b'hello','0'*64)

    def test_reject_malformed_selector_loop(self):
        data=synthetic_data()
        place(data,TEXT,0x3F8423,b'\x90')
        with self.assertRaisesRegex(model.ModelError,'instruction changed'):
            self.valid(data)

    def test_reject_fake_addons_record_id_offset(self):
        data=synthetic_data()
        place(data,TEXT,0x3F8487,b'\x90')
        with self.assertRaises(model.ModelError): self.valid(data)

    def test_reject_jump_target_outside_function(self):
        data=synthetic_data()
        place(data,RDATA,model.IMAGE_RVA_TABLE,struct.pack('<i',-1))
        with self.assertRaises(model.ModelError): self.valid(data)

    def test_reject_locale_key_tampering(self):
        data=synthetic_data()
        place(data,RDATA,0x631AA04,b'MODIFIED')
        with self.assertRaises(model.ModelError): self.valid(data)

    def test_read_rva_bounds_are_strict(self):
        with self.assertRaises(model.ModelError):
            model.read_rva(b'ABC', {"rva":1,"raw_offset":0,"virtual_bytes":3,"raw_bytes":3}, 1, 4)
        with self.assertRaises(model.ModelError):
            model.read_rva(b'ABC', {"rva":1,"raw_offset":0,"virtual_bytes":3,"raw_bytes":3}, 0, 1)

    def test_report_never_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'report.json'
            model.save_report(path,{'schema':1})
            with self.assertRaises(model.ModelError):model.save_report(path,{'schema':2})
            self.assertIn('"schema": 1',path.read_text())

    def test_reject_missing_original_exe(self):
        with self.assertRaises(model.ModelError):model.analyze_file('/nonexistent/azse-original.exe')


class WinDbgRecipeTests(unittest.TestCase):
    def evidence(self):
        return {'exe_sha256':HASH,'selection_read_rva':'0x3f83b3',
                'page_selector_byte_offset':'0x1da'}

    def test_recipe_is_hardware_breakpoint_and_never_executes(self):
        x=build_script(self.evidence(),r'C:\AZSE\trace.log')
        self.assertIn('ba e 1 AzerothSurvivors+0x3f83b3',x)
        self.assertIn('by(@r8+0x1da)',x)
        self.assertIn('.logopen /t',x)
        self.assertFalse(any(line.startswith(('eb ', 'ed ')) for line in x.splitlines()))
        self.assertNotIn('!load',x)
        self.assertNotIn('.call ',x)

    def test_reject_wrong_version_probe(self):
        data=self.evidence();data['exe_sha256']='a'*64
        with self.assertRaises(TraceError):build_script(data,r'C:\AZSE\trace.log')

    def test_reject_script_injection_path(self):
        with self.assertRaises(TraceError):validate_log_path(r'C:\AZSE\log.txt"; .shell -ci "bad"')
        with self.assertRaises(TraceError):validate_log_path(r'..\danger.log')
        with self.assertRaises(TraceError):validate_log_path(r'\\remote\share\trace.log')

    def test_accept_local_windows_log_path_with_spaces(self):
        self.assertEqual(r'C:\My Local Folder\AZSE\trace.log',
                         validate_log_path(r'C:\My Local Folder\AZSE\trace.log'))


if __name__ == '__main__': unittest.main()
