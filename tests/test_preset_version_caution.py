import json
import unittest
from pathlib import Path
from planner.azs_planner import load_catalog, export_addon


class PresetVersionCautionTests(unittest.TestCase):
    def test_no_claim_exact_browser_version(self):
        builds = load_catalog()
        self.assertEqual(11, len(builds))
        for p in builds:
            self.assertIn("UNKNOWN", p["baseline_game_version"])
            self.assertEqual("unverified_editorial", p["review_status"])

    def test_original_client_warlock_labels_are_conservative(self):
        builds = load_catalog()
        w = next(b for b in builds if b["id"] == "warlock-demonology-idle")
        self.assertEqual(["Summon Imp","Demonic Pact","Summon Felguard"], w["requires_observed_talents"])
        self.assertIn("UNVERIFIED", w["note"])

    def test_shipped_lua_catalogue_stays_in_sync(self):
        root = Path(__file__).resolve().parents[1]
        lua = (root/"addons"/"AZSEnhancedAdvisor"/"Presets.lua").read_text(encoding="utf-8")
        self.assertEqual(len(load_catalog()), lua.count("review_status = "))
        self.assertEqual(len(load_catalog()), lua.count("Windows EXE version UNKNOWN"))
        self.assertNotIn("0.135.1 (unverified community report)", lua)
