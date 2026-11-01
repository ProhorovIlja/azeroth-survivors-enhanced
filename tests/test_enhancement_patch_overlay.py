"""Patch overlay regression tests use synthetic inventories and text only."""
import unittest
from tools.extract_talent_names import extract_patch_overlay
from planner.build_studio import make_draft, validate_against_inventory, BuildError

NEW = "aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8"
OLD = "eb744751b4e17ec1397b0cdc85a22af63b6af63c1da1d9c2861762c3c4d8947c"


def data(names):
    # Maintain declared order of a synthetic localization table.
    entries = {"game.title":"Azeroth Survivors", "Enhancement":"Enhancement",
               "Windfury":"Windfury", "Feral Spirit":"Feral Spirit",
               "ability.stormstrike.name":"ability.stormstrike.name"}
    for name in names:
        entries[name] = name
    return entries


def inventory(overlay):
    return {
        "client_sha256": NEW,
        "classes":{"shaman":{
            "Enhancement":["Windfury","Feral Spirit","Ancestral Knowledge"],
            "Elemental":["Elemental Mastery"],"Restoration":["Healing Wave"]
        }},
        "patch_overlay":{"shaman":{"Enhancement":overlay}},
    }


class EnhancementPatchOverlayTests(unittest.TestCase):
    old_names = ["Earthen Bulwark","Resonant Shocks","Shattering Elements",
                 "Rockbiter Initiation","Windfury Weapon","Flametongue Weapon",
                 "Frostbrand Weapon","Unleashed Weapons","Ancestral Fortitude",
                 "Sweeping Storm","Stormbound Echoes","Eye of the Tempest"]
    new_names = ["Resonant Shocks","Shattering Elements","Rockbiter Initiation",
                 "Windfury Weapon","Flametongue Weapon","Frostbrand Weapon",
                 "Ancestral Fortitude","Sweeping Storm","Stormbound Echoes",
                 "Eye of the Tempest","Stormguard","Elemental Sunder",
                 "Heart of the Earthbreaker"]

    def test_0136_has_twelve_appended_labels(self):
        result=extract_patch_overlay(data(self.old_names),OLD)
        self.assertEqual(self.old_names,result["shaman"]["Enhancement"])
        self.assertIn("Unleashed Weapons",result["shaman"]["Enhancement"])

    def test_0137_has_thirteen_newer_appended_labels(self):
        result=extract_patch_overlay(data(self.new_names),NEW)
        actual=result["shaman"]["Enhancement"]
        self.assertEqual(13,len(actual))
        self.assertIn("Stormguard",actual)
        self.assertIn("Elemental Sunder",actual)
        self.assertIn("Heart of the Earthbreaker",actual)
        self.assertNotIn("Earthen Bulwark",actual)
        self.assertNotIn("Unleashed Weapons",actual)

    def test_unknown_sha_does_not_claim_patch_block(self):
        self.assertEqual({},extract_patch_overlay(data(self.new_names),"0"*64))

    def test_patch_overlay_selected_and_not_legality_verified(self):
        inv=inventory(self.new_names)
        draft=make_draft(inv,"shaman")
        draft["talents"]=[{"tree":"Enhancement","name":"Elemental Sunder","points":1}]
        report=validate_against_inventory(draft,inv)
        self.assertEqual("NAME_CHECK_ONLY",report["status"])
        self.assertEqual(["Elemental Sunder"],report["appended_patch_candidates_selected"])
        self.assertFalse(report["patch_overlay_runtime_verified"])
        self.assertFalse(report["ready_to_apply_automatically"])

    def test_legacy_shaman_label_needs_warning(self):
        inv=inventory(self.new_names)
        draft=make_draft(inv,"shaman")
        draft["talents"]=[{"tree":"Enhancement","name":"Feral Spirit","points":1}]
        report=validate_against_inventory(draft,inv)
        self.assertEqual("NAME_CHECK_WITH_PATCH_WARNINGS",report["status"])
        self.assertEqual(["Feral Spirit"],report["older_dictionary_candidates_selected"])
        self.assertFalse(report["legal_build_verified"])

    def test_0137_old_overlay_only_name_rejected(self):
        inv=inventory(self.new_names)
        draft=make_draft(inv,"shaman")
        draft["talents"]=[{"tree":"Enhancement","name":"Unleashed Weapons","points":1}]
        with self.assertRaises(BuildError):
            validate_against_inventory(draft,inv)

    def test_regular_class_still_passes_without_overlay(self):
        inv={"client_sha256":NEW,
             "classes":{"warlock":{"Demonology":["Summon Imp","Demonic Pact"]}}}
        draft=make_draft(inv,"warlock")
        draft["talents"]=[{"tree":"Demonology","name":"Summon Imp","points":1}]
        report=validate_against_inventory(draft,inv)
        self.assertEqual("NAME_CHECK_ONLY",report["status"])
        self.assertFalse(report["legal_build_verified"])


if __name__ == "__main__":
    unittest.main()
