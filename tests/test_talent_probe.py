import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from tools.talent_probe import _label_bytes, classify, fingerprint, main


class TalentProbeTests(unittest.TestCase):
    def _fixture(self, path, labels):
        data = b"MZ" + b"." * (1024 * 1024 - 8)
        data += b"\n".join(_label_bytes(label) for label in labels)
        path.write_bytes(data)

    def test_known_legacy_label_families(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "AzerothSurvivors.exe"
            self._fixture(p, ["Demonic Pact","Summon Imp","Summon Felguard","Windfury","Feral Spirit"])
            info = fingerprint(p)
            self.assertEqual("legacy_label_family", info["warlock_demonology_family"])
            self.assertEqual("legacy_label_family", info["shaman_enhancement_family"])
            self.assertFalse(info["automatic_patching_allowed"])
            self.assertFalse(info["runtime_verified"])
            self.assertIsNone(info["exact_version"])
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), info["sha256"])
            self.assertEqual(2, main(["--game-exe", str(p), "--require-modern"]))

    def test_modern_pair_is_hint_not_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "client.exe"
            self._fixture(p, ["Legion Gate", "Pact of the Nathrezim", "Demonic Supremacy",
                              "Rockbiter Weapon", "Stormstrike", "Stormbound Echoes"])
            info = fingerprint(p)
            self.assertEqual("modern_label_family", info["warlock_demonology_family"])
            self.assertEqual("modern_label_family", info["shaman_enhancement_family"])
            self.assertEqual(0, main(["--game-exe", str(p), "--require-modern"]))
            self.assertFalse(info["automatic_patching_allowed"])

    def test_mixed_and_unknown_conservative(self):
        self.assertEqual("mixed", classify(True, True))
        self.assertEqual("unknown", classify(False, False))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "fake.exe"
            self._fixture(p, ["Demonic Pact","Summon Imp","Summon Felguard",
                              "Legion Gate", "Pact of the Nathrezim", "Demonic Supremacy"])
            info = fingerprint(p)
            self.assertEqual("mixed", info["warlock_demonology_family"])
            self.assertEqual("unknown", info["shaman_enhancement_family"])

    def test_partial_label_does_not_trigger_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "partial.exe"
            self._fixture(p, ["Summon Imp","Windfury"])
            info = fingerprint(p)
            self.assertEqual("unknown", info["warlock_demonology_family"])
            self.assertEqual("unknown", info["shaman_enhancement_family"])

    def test_preserve_exact_only_quoted_english_label(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.exe"
            p.write_bytes(b"Legacy Summon Felguard and Demonic Pact and Windfury and Feral Spirit")
            info = fingerprint(p)
            self.assertEqual("unknown", info["warlock_demonology_family"])
            self.assertEqual([], info["labels_found"]["legacy_demonology"])

    def test_known_profile_and_candidate_routes_have_no_fake_measured_dps(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / "catalog" / "client_profiles.json").read_text(encoding="utf-8"))
        self.assertEqual(None, data["profiles"][0]["exact_version"])
        self.assertFalse(data["profiles"][0]["verified_in_game"])
        candidate = json.loads((root / "catalog" / "original_client_archetypes.json").read_text(encoding="utf-8"))
        self.assertEqual(data["profiles"][0]["sha256"], candidate["target_client_sha256"])
        for route in candidate["class_routes"]:
            self.assertIsNone(route["numbered_spend_sequence"])
            self.assertFalse(route["performance_measured"])
            self.assertFalse(route["legal_51_point_build"])
