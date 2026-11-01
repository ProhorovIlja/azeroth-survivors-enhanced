import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from tools.native_menu_probe import (
    ProbeError, OWNER_EXE_SHA256, read_pe_sections, collect_static_evidence, analyze,
)


def fake_pe(section_blob):
    """Synthetic tiny x64 PE, without any original executable content."""
    src = bytearray(4096)
    src[:2] = b"MZ"
    struct.pack_into("<I", src, 0x3C, 0x80)
    src[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", src, 0x84, 0x8664, 2, 0, 0, 0, 0xF0, 0)
    struct.pack_into("<H", src, 0x98, 0x20B)
    pos = 0x80 + 24 + 0xF0
    for i, (name, raw, rva) in enumerate((('.text', 0x400, 0x1000), ('.rdata', 0x800, 0x2000))):
        off = pos + 40 * i
        src[off:off+8] = name.encode() + b'\0' * (8 - len(name))
        struct.pack_into('<IIII', src, off+8, 1024, rva, 1024, raw)
    src[0x800:0x800+len(section_blob)] = section_blob
    return src


class NativeMenuProbeTests(unittest.TestCase):
    def test_exact_client_is_version_gated(self):
        d = fake_pe(b"wenilla_rogue_app::screens::options::OptionsCanvas options.saves")
        with self.assertRaisesRegex(ProbeError, 'Unreviewed'):
            collect_static_evidence(d, hashlib.sha256(d).hexdigest())

    def test_bevy_native_menu_proven_but_hooks_not_claimed(self):
        d = fake_pe(b"wenilla_rogue_app::screens::options::OptionsCanvas\0"
                    b"wenilla_rogue_app::screens::options::SettingsButton\0"
                    b"options.saves\0options.import_save\0")
        report = collect_static_evidence(d, OWNER_EXE_SHA256)
        self.assertTrue(report["menu_framework_anchor_verified"])
        self.assertIn("OptionsCanvas", report["options_component_type_candidates"])
        self.assertFalse(report["hook_addresses_verified"])
        self.assertFalse(report["can_install_native_menu"])
        self.assertEqual([], report["native_cheat_actions_verified"])

    def test_nested_data_not_mistaken_for_active_native_cheat(self):
        d = fake_pe(b"Game cheats death!\0options.saves\0")
        result = collect_static_evidence(d, OWNER_EXE_SHA256)
        self.assertFalse(result["native_cheat_menu_present"])

    def test_bad_pe_rejected(self):
        with self.assertRaises(ProbeError):
            read_pe_sections(b"not an exe")

    def test_wrong_pe_machine_rejected(self):
        d = fake_pe(b"options.saves")
        struct.pack_into('<H', d, 0x84, 0x14C)
        with self.assertRaises(ProbeError):
            read_pe_sections(d)

    def test_bad_section_bounds_rejected(self):
        d = fake_pe(b"options.saves")
        table = 0x80+24+0xF0
        struct.pack_into('<I', d, table+40+8+12, len(d)+1000)
        with self.assertRaises(ProbeError):
            read_pe_sections(d)

    def test_no_output_overwrite(self):
        with tempfile.TemporaryDirectory() as dir:
            bogus = Path(dir)/'fake.exe'
            bogus.write_bytes(fake_pe(b'options.saves'))
            with self.assertRaisesRegex(ProbeError, 'Expected bounded'):
                analyze(bogus)

if __name__ == '__main__':
    unittest.main()
