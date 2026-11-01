"""Original-client patch taxonomy tests use synthetic dictionaries and build data."""
import unittest

from tools.extract_talent_names import (
    extract_patch_overlay, extract_gear_overlay, MODERN_DEMONOLOGY_CANDIDATES,
    SHAMAN_GEAR_LABELS,
)
from planner.build_studio import make_draft, validate_against_inventory, BuildError

NEW = "aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8"
OLD = "eb744751b4e17ec1397b0cdc85a22af63b6af63c1da1d9c2861762c3c4d8947c"


def data(names):
    # Simulates exact recorded label ordering, with modern warlock elsewhere.
    entries = {"game.title": "Azeroth Survivors",
               "Enhancement": "Enhancement", "Windfury": "Windfury",
               "Feral Spirit": "Feral Spirit"}
    for name in MODERN_DEMONOLOGY_CANDIDATES:
        entries[name] = name
    entries["ability.stormstrike.name"] = "Stormstrike"
    for name in names:
        entries[name] = name
    return entries


def inventory(names):
    overlay = [name for name in names if name not in SHAMAN_GEAR_LABELS]
    gear = [name for name in names if name in SHAMAN_GEAR_LABELS]
    return {
        "client_sha256": NEW,
        "classes": {
            "shaman": {"Enhancement": ["Windfury", "Feral Spirit", "Ancestral Knowledge"],
                       "Elemental": ["Elemental Mastery"], "Restoration": ["Healing Wave"]},
            "warlock": {"Demonology": ["Summon Imp", "Demonic Pact", "Summon Felguard"]}
        },
        "patch_overlay": {
            "shaman": {"Enhancement": overlay},
            "warlock": {"Demonology": list(MODERN_DEMONOLOGY_CANDIDATES)}
        },
        "gear_overlay": {"shaman": {"amulet_candidates": gear}},
    }


class EnhancementPatchOverlayTests(unittest.TestCase):
    old_names = [
        "Earthen Bulwark", "Resonant Shocks", "Shattering Elements",
        "Rockbiter Initiation", "Windfury Weapon", "Flametongue Weapon",
        "Frostbrand Weapon", "Unleashed Weapons", "Ancestral Fortitude",
        "Sweeping Storm", "Stormbound Echoes", "Eye of the Tempest",
    ]
    new_names = [
        "Resonant Shocks", "Shattering Elements", "Rockbiter Initiation",
        "Windfury Weapon", "Flametongue Weapon", "Frostbrand Weapon",
        "Ancestral Fortitude", "Sweeping Storm", "Stormbound Echoes",
        "Eye of the Tempest", "Stormguard", "Elemental Sunder",
        "Heart of the Earthbreaker",
    ]

    def test_0136_identifies_eleven_talent_candidates_and_one_amulet(self):
        mapping = data(self.old_names)
        result = extract_patch_overlay(mapping, OLD)
        talents = result["shaman"]["Enhancement"]
        self.assertEqual(11, len(talents))
        self.assertIn("Unleashed Weapons", talents)
        self.assertNotIn("Eye of the Tempest", talents)
        self.assertEqual(["Eye of the Tempest"],
                         extract_gear_overlay(mapping, OLD)["shaman"]["amulet_candidates"])

    def test_0137_identifies_eleven_candidates_and_two_amulets(self):
        mapping = data(self.new_names)
        result = extract_patch_overlay(mapping, NEW)
        talents = result["shaman"]["Enhancement"]
        self.assertEqual(11, len(talents))
        self.assertIn("Stormguard", talents)
        self.assertIn("Elemental Sunder", talents)
        self.assertNotIn("Heart of the Earthbreaker", talents)
        self.assertNotIn("Eye of the Tempest", talents)
        self.assertEqual(["Eye of the Tempest", "Heart of the Earthbreaker"],
                         extract_gear_overlay(mapping, NEW)["shaman"]["amulet_candidates"])

    def test_recent_warlock_names_are_separate_from_legacy_labels(self):
        result = extract_patch_overlay(data(self.new_names), NEW)
        self.assertEqual(list(MODERN_DEMONOLOGY_CANDIDATES), result["warlock"]["Demonology"])
        self.assertIn("Pact of the Nathrezim", result["warlock"]["Demonology"])
        self.assertNotIn("Summon Felguard", result["warlock"]["Demonology"])

    def test_unknown_sha_returns_no_patch_or_gear_overlay(self):
        self.assertEqual({}, extract_patch_overlay(data(self.new_names), "0" * 64))
        self.assertEqual({}, extract_gear_overlay(data(self.new_names), "0" * 64))

    def test_current_shaman_candidate_remains_unverified(self):
        inv = inventory(self.new_names)
        draft = make_draft(inv, "shaman")
        draft["talents"] = [{"tree": "Enhancement", "name": "Elemental Sunder", "points": 1}]
        report = validate_against_inventory(draft, inv)
        self.assertEqual("NAME_CHECK_ONLY", report["status"])
        self.assertEqual(["Elemental Sunder"], report["appended_patch_candidates_selected"])
        self.assertFalse(report["ready_to_apply_automatically"])

    def test_obsolete_shaman_name_warns(self):
        inv = inventory(self.new_names)
        draft = make_draft(inv, "shaman")
        draft["talents"] = [{"tree": "Enhancement", "name": "Feral Spirit", "points": 1}]
        report = validate_against_inventory(draft, inv)
        self.assertEqual("NAME_CHECK_WITH_PATCH_WARNINGS", report["status"])
        self.assertEqual(["Feral Spirit"], report["older_dictionary_candidates_selected"])

    def test_amulett_is_rejected_as_talent_but_allowed_in_gear_notes(self):
        inv = inventory(self.new_names)
        draft = make_draft(inv, "shaman")
        draft["talents"] = [{"tree": "Enhancement", "name": "Heart of the Earthbreaker", "points": 1}]
        with self.assertRaises(BuildError):
            validate_against_inventory(draft, inv)
        draft["talents"] = []
        draft["gear"]["amulet"] = ["Heart of the Earthbreaker"]
        self.assertFalse(validate_against_inventory(draft, inv)["legal_build_verified"])

    def test_superseded_unleashed_weapons_rejected(self):
        inv = inventory(self.new_names)
        draft = make_draft(inv, "shaman")
        draft["talents"] = [{"tree": "Enhancement", "name": "Unleashed Weapons", "points": 1}]
        with self.assertRaises(BuildError):
            validate_against_inventory(draft, inv)

    def test_newer_warlock_name_passes_name_check_only(self):
        inv = inventory(self.new_names)
        draft = make_draft(inv, "warlock")
        draft["talents"] = [{"tree": "Demonology", "name": "Pact of the Nathrezim", "points": 1}]
        result = validate_against_inventory(draft, inv)
        self.assertEqual(["Pact of the Nathrezim"], result["appended_patch_candidates_selected"])
        self.assertFalse(result["legal_build_verified"])

    def test_legacy_warlock_name_warns_in_0137(self):
        inv = inventory(self.new_names)
        draft = make_draft(inv, "warlock")
        draft["talents"] = [{"tree": "Demonology", "name": "Summon Felguard", "points": 1}]
        result = validate_against_inventory(draft, inv)
        self.assertEqual("NAME_CHECK_WITH_PATCH_WARNINGS", result["status"])
        self.assertEqual(["Summon Felguard"], result["older_dictionary_candidates_selected"])

    def test_warlock_exclusive_capstones_rejected_for_0137(self):
        inv = inventory(self.new_names)
        draft = make_draft(inv, "warlock")
        draft["talents"] = [
            {"tree": "Demonology", "name": "Butcher", "points": 1},
            {"tree": "Demonology", "name": "Pact of the Nathrezim", "points": 1},
        ]
        with self.assertRaisesRegex(BuildError, "Exclusive"):
            validate_against_inventory(draft, inv)

    def test_warlock_supremacy_gate_returns_swarm_warning(self):
        inv = inventory(self.new_names)
        draft = make_draft(inv, "warlock")
        draft["talents"] = [
            {"tree": "Demonology", "name": "Demonic Supremacy", "points": 1},
            {"tree": "Demonology", "name": "Legion Gate", "points": 1},
            {"tree": "Demonology", "name": "Demonic Familiar", "points": 1},
        ]
        result = validate_against_inventory(draft, inv)
        self.assertEqual(2, len(result["mechanics_cautions"]))
        self.assertFalse(result["legal_build_verified"])
        self.assertFalse(result["ready_to_apply_automatically"])

    def test_warlock_no_conflicts_for_single_capstone(self):
        inv = inventory(self.new_names)
        draft = make_draft(inv, "warlock")
        draft["talents"] = [
            {"tree": "Demonology", "name": "Butcher", "points": 1},
        ]
        result = validate_against_inventory(draft, inv)
        self.assertEqual([], result["mechanics_cautions"])

    def test_no_patch_data_preserves_existing_unverified_behavior(self):
        inv = {"client_sha256": NEW,
               "classes": {"warlock": {"Demonology": ["Summon Imp"]}}}
        draft = make_draft(inv, "warlock")
        draft["talents"] = [{"tree": "Demonology", "name": "Summon Imp", "points": 1}]
        result = validate_against_inventory(draft, inv)
        self.assertEqual("NAME_CHECK_ONLY", result["status"])
        self.assertFalse(result["legal_build_verified"])


if __name__ == "__main__":
    unittest.main()
