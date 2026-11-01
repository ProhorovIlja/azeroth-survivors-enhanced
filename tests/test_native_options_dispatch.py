"""Synthetic control-flow and safety tests, no proprietary executable bytes."""
import unittest
from tools.native_options_dispatch import KNOWN_0138_SHA, decode_jcc, analyze_selector
from tools.native_options_xrefs import XrefError


class OptionsDispatchTests(unittest.TestCase):
    def test_only_exact_original_138_allowed(self):
        with self.assertRaises(XrefError):
            analyze_selector(b'not a game', '0' * 64)
        self.assertEqual(64, len(KNOWN_0138_SHA))

    def test_decode_near_je_target(self):
        data = bytearray(128)
        sec = {'rva': 0x1000, 'raw_offset': 0, 'virtual_bytes': len(data)}
        data[10:16] = bytes.fromhex('0f 84 06 00 00 00')
        self.assertEqual(0x1016, decode_jcc(data, sec, 0x100a))

    def test_decode_short_jne_target(self):
        data = bytearray(128)
        sec = {'rva': 0x1000, 'raw_offset': 0, 'virtual_bytes': len(data)}
        data[10:12] = bytes.fromhex('75 15')
        self.assertEqual(0x1021, decode_jcc(data, sec, 0x100a))

    def test_unknown_jump_opcode_rejected(self):
        data = b'\x90' * 80
        sec = {'rva': 0x1000, 'raw_offset': 0, 'virtual_bytes': len(data)}
        with self.assertRaises(XrefError):
            decode_jcc(data, sec, 0x100a)

    def test_out_of_bounds_instruction_rejected(self):
        sec = {'rva': 0x1000, 'raw_offset': 0, 'virtual_bytes': 8}
        with self.assertRaises(XrefError):
            decode_jcc(b'\x90' * 8, sec, 0x1006)


if __name__ == '__main__':
    unittest.main()
