"""No private EXE or localization content is ever in these tests."""
import unittest
from tools.compare_game_versions import compare_inventories


def example(sha, legacy=None, overlay=None, amulets=None):
    if legacy is None:
        legacy=["Windfury","Feral Spirit"]
    if overlay is None:
        overlay=[]
    return {"client_sha256":sha,"classes":{"shaman":{"Enhancement":legacy}},
            "patch_overlay":{"shaman":{"Enhancement":overlay}},
            "gear_overlay":{"shaman":{"amulet_candidates":amulets or []}}}


class CompareGameVersionTests(unittest.TestCase):
    def test_0137_overlay_changes_even_when_ordered_tree_unchanged(self):
        old=example("a"*64,overlay=["Earthen Bulwark","Unleashed Weapons","Stormbound Echoes"],amulets=["Eye of the Tempest"])
        new=example("b"*64,overlay=["Stormguard","Elemental Sunder","Stormbound Echoes"],amulets=["Eye of the Tempest","Heart of the Earthbreaker"])
        summary=compare_inventories(old,new,{"game.title":"AZS","A":"A"},
                                    {"game.title":"AZS","B":"B"})
        self.assertTrue(summary["older_ordered_tree_names_unchanged"])
        self.assertEqual(["Elemental Sunder","Stormguard"],
                         summary["shaman_appended_names_added"])
        self.assertEqual(["Earthen Bulwark","Unleashed Weapons"],
                         summary["shaman_appended_names_removed"])
        self.assertEqual(["Heart of the Earthbreaker"],
                         summary["shaman_amulet_names_added"])
        self.assertNotIn("Heart of the Earthbreaker",summary["shaman_appended_names_added"])
        self.assertEqual(1,summary["added_dictionary_keys"])
        self.assertFalse(summary["gameplay_verified"])
        self.assertFalse(summary["binary_modified"])

    def test_same_binary_yields_no_changes(self):
        a=example("c"*64,overlay=["Rockbiter Initiation"])
        summary=compare_inventories(a,a,{"same":"same"},{"same":"same"})
        self.assertTrue(summary["same_executable"])
        self.assertEqual([],summary["shaman_appended_names_added"])
        self.assertEqual(0,summary["changed_retained_dictionary_values"])

    def test_changed_value_count_without_copying_values(self):
        old=example("d"*64)
        new=example("e"*64)
        summary=compare_inventories(old,new,{"x":"private older text"},{"x":"private newer text"})
        self.assertEqual(1,summary["changed_retained_dictionary_values"])
        self.assertNotIn("private",str(summary))

    def test_legacy_tree_name_change_flagged(self):
        old=example("f"*64)
        new=example("0"*64,legacy=["Stormguard"])
        summary=compare_inventories(old,new,{}, {})
        self.assertFalse(summary["older_ordered_tree_names_unchanged"])
        self.assertEqual(1,summary["new_ordered_tree_candidates"])

    def test_missing_overlay_is_safe_empty_set(self):
        old={"client_sha256":"a"*64,"classes":{"shaman":{"Enhancement":["Windfury"]}}}
        new={"client_sha256":"b"*64,"classes":{"shaman":{"Enhancement":["Windfury"]}}}
        report=compare_inventories(old,new,{}, {})
        self.assertEqual([],report["shaman_appended_names_added"])
        self.assertTrue(report["older_ordered_tree_names_unchanged"])


if __name__=="__main__":
    unittest.main()
