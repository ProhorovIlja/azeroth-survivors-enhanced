"""All Build Studio CI tests use synthetic talent data; no game IP or EXE."""
import base64
import json
import tempfile
import unittest
from pathlib import Path
import zlib

from planner.build_studio import (
    BuildError, bounded_json, decode, encode, make_draft, save_new,
    validate_against_inventory, validate_schema,
)

FAKE_SHA = "a" * 64


def inventory():
    return {
        "client_sha256": FAKE_SHA,
        "classes": {
            "warlock": {
                "Affliction": ["Suppression"],
                "Demonology": ["Summon Imp", "Demonic Pact", "Summon Felguard"],
                "Destruction": ["Cataclysm"],
            },
            "shaman": {
                "Elemental": ["Convection"],
                "Enhancement": ["Windfury", "Feral Spirit"],
                "Restoration": ["Tidal Focus"],
            },
        },
    }


class BuildStudioTests(unittest.TestCase):
    def blank(self):
        return make_draft(inventory(), "warlock", "Imp / Felguard experiment", "low_input_minions")

    def test_blank_build_never_claims_legality(self):
        b = self.blank()
        r = validate_against_inventory(b, inventory())
        self.assertEqual("NAME_CHECK_ONLY", r["status"])
        self.assertFalse(r["legal_build_verified"])
        self.assertFalse(r["ready_to_apply_automatically"])
        self.assertEqual(0, r["points_requested"])

    def test_known_talents_in_correct_tree(self):
        b = self.blank()
        b["talents"] = [
            {"tree":"Demonology","name":"Summon Imp","points":1},
            {"tree":"Demonology","name":"Demonic Pact","points":1},
        ]
        r = validate_against_inventory(b, inventory())
        self.assertEqual(2, r["points_requested"])
        self.assertFalse(r["points_and_prerequisites_verified"])

    def test_wrong_tree_and_unknown_name_rejected(self):
        b = self.blank()
        b["talents"] = [{"tree":"Affliction","name":"Demonic Pact","points":1}]
        with self.assertRaises(BuildError):
            validate_against_inventory(b, inventory())
        b["talents"] = [{"tree":"Demonology","name":"Legion Gate","points":1}]
        with self.assertRaises(BuildError):
            validate_against_inventory(b, inventory())

    def test_exact_sha_required(self):
        b = self.blank()
        b["client_sha256"] = "b" * 64
        with self.assertRaisesRegex(BuildError, "CLIENT MISMATCH"):
            validate_against_inventory(b, inventory())

    def test_points_and_bool_invalid(self):
        b = self.blank()
        b["talents"] = [{"tree":"Demonology","name":"Summon Imp","points":True}]
        with self.assertRaises(BuildError):
            validate_schema(b)
        b["talents"] = [{"tree":"Demonology","name":"Summon Imp","points":52}]
        with self.assertRaises(BuildError):
            validate_schema(b)

    def test_overall_research_budget(self):
        b = self.blank()
        b["talents"] = [
            {"tree":"Demonology","name":"Summon Imp","points":40},
            {"tree":"Demonology","name":"Demonic Pact","points":20},
        ]
        with self.assertRaises(BuildError):
            validate_against_inventory(b, inventory())

    def test_duplicate_selection_rejected(self):
        b = self.blank()
        item = {"tree":"Demonology","name":"Summon Imp","points":1}
        b["talents"] = [item, item]
        with self.assertRaises(BuildError):
            validate_schema(b)

    def test_share_code_roundtrip_unicode(self):
        b = self.blank()
        b["notes"] = "Нужен тест на стоячий бой ⚔️"
        b["talents"] = [{"tree":"Demonology","name":"Summon Imp","points":1}]
        code = encode(b)
        self.assertTrue(code.startswith("AZSE3:"))
        self.assertEqual(b, decode(code))
        self.assertLess(len(code), 4000)

    def test_corrupted_share_code_rejected(self):
        b = self.blank()
        code = encode(b)
        with self.assertRaises(BuildError):
            decode(code[:-1] + ("0" if code[-1] != "0" else "1"))
        with self.assertRaises(BuildError):
            decode("NOT_A_CODE")

    def test_zlib_bomb_rejected_before_json_parse(self):
        raw = b"x" * (30_000)
        zipped = zlib.compress(raw)
        code = "AZSE3:" + base64.urlsafe_b64encode(zipped).decode("ascii").rstrip("=") + "." + "0" * 16
        with self.assertRaises(BuildError):
            decode(code)

    def test_share_code_cannot_claim_verified(self):
        b = self.blank()
        b["legal_tree_verified"] = True
        with self.assertRaises(BuildError):
            encode(b)

    def test_unknown_fields_rejected(self):
        b = self.blank()
        b["arbitrary_command"] = "do something unsafe"
        with self.assertRaises(BuildError):
            validate_schema(b)

    def test_save_never_overwrites_user_file(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "preset.json"
            save_new(p, self.blank())
            self.assertEqual(self.blank(), bounded_json(p))
            with self.assertRaises(BuildError):
                save_new(p, self.blank())
            self.assertEqual(self.blank(), bounded_json(p))

    def test_symlink_output_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "my-build.json"
            dest = Path(t) / "private.txt"
            dest.write_text("private data")
            try:
                p.symlink_to(dest)
            except (OSError, NotImplementedError):
                self.skipTest("No symlink capability")
            with self.assertRaises(BuildError):
                save_new(p, self.blank())
            self.assertEqual("private data", dest.read_text())

    def test_no_other_class_talents(self):
        b = self.blank()
        b["talents"] = [{"tree":"Enhancement","name":"Windfury","points":1}]
        with self.assertRaises(BuildError):
            validate_against_inventory(b, inventory())

    def test_style_and_race_are_only_text_not_legality_claims(self):
        b = self.blank()
        b["race"] = "Gnome"
        b["style"] = "farming"
        report = validate_against_inventory(b, inventory())
        self.assertFalse(report["legal_build_verified"])


if __name__ == "__main__":
    unittest.main()
