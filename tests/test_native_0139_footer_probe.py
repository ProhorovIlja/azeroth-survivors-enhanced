"""Synthetic original-free tests for 0.139 Options footer research."""
import struct
import unittest
from tools import native_0139_footer_probe as p

BASE = 0x1000
RBASE = 0x8000
HELPER = 0x2200


def fixture(extra_done=False):
    code = bytearray(b"\x90" * 0x240)
    strings = bytearray(b"\x00" * 0x100)
    starts = {HELPER}
    for key, off, dst in (
        ("options.defaults", 0x20, 0x00),
        ("options.done", 0xA0, 0x40),
    ) + ((("options.done", 0x140, 0x40),) if extra_done else ()):
        strings[dst:dst + len(key)] = key.encode("ascii")
        code[off:off + 7] = b"\x48\x8d\x0d" + struct.pack("<i", RBASE + dst - (BASE + off + 7))
        tag = off + 0x12
        code[tag:tag + 10] = b"\x48\xb9" + struct.pack("<Q", (1 << 63) | p.TAGS[key])
        call = off + 0x35
        code[call:call + 5] = b"\xe8" + struct.pack("<i", HELPER - (BASE + call + 5))
    return code, strings, starts


class FooterProbeTests(unittest.TestCase):
    def read(self, code, strings, starts):
        return p.infer_action_pairs(code, BASE, strings, RBASE, starts)

    def test_strict_two_button_pair(self):
        code, strings, starts = fixture()
        result = self.read(code, strings, starts)
        self.assertEqual(result["status"], "candidate_same_helper")
        self.assertEqual(result["shared_helper_rva"], hex(HELPER))
        self.assertEqual([16, 17], [x["tag_low_id"] for x in result["buttons"]])
        self.assertFalse(result["runtime_event_dispatcher_verified"])
        self.assertTrue(result["byte_pattern_only"])

    def test_reject_corrupt_tag(self):
        code, strings, starts = fixture()
        code[0xA0 + 0x12 + 2] ^= 1
        self.assertEqual("unconfirmed", self.read(code, strings, starts)["status"])

    def test_reject_unbounded_helper(self):
        code, strings, starts = fixture()
        self.assertEqual("unconfirmed", self.read(code, strings, set())["status"])

    def test_reject_wrong_call_target(self):
        code, strings, starts = fixture()
        code[0x20 + 0x35 + 1] ^= 1
        self.assertEqual("unconfirmed", self.read(code, strings, starts)["status"])

    def test_reject_missing_key(self):
        code, strings, starts = fixture()
        strings[0x40] = ord("X")
        self.assertEqual("unconfirmed", self.read(code, strings, starts)["status"])

    def test_reject_ambiguous_second_done(self):
        code, strings, starts = fixture(extra_done=True)
        report = self.read(code, strings, starts)
        self.assertEqual("unconfirmed", report["status"])
        self.assertGreater(report["joint_candidates"], 1)

    def test_reject_oversize(self):
        code, strings, starts = fixture()
        report = self.read(code + b"\x00" * p.MAX_FUNCTION_BYTES, strings, starts)
        self.assertEqual("unconfirmed", report["status"])

    def test_unknown_sha_fails_closed_without_opening_file(self):
        self.assertEqual("unknown_client_sha",
                         p.probe_file("/does/not/exist", "0" * 64, "0x1000")["reason"])


if __name__ == "__main__":
    unittest.main()
