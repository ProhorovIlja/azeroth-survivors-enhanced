"""Only synthetic checks and committed, derived metadata. No original EXE bytes."""
import json
from pathlib import Path
import unittest

from tools.native_menu_probe import KNOWN_OWNER_EXE_SHAS, collect_static_evidence
from tools.native_options_xrefs import KNOWN_EXES, XrefError, map_binary

SHA_0137 = "aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8"
SHA_0138 = "eb5fd1c1b96e6180fcf5f3d685d90a61471af28d22e5f060c02b7b7663fbf79e"


class Windows0138OptionsTests(unittest.TestCase):
    def test_both_exact_executables_allowed(self):
        self.assertEqual("0.138.0-current", KNOWN_EXES[SHA_0138])
        self.assertEqual("0.138.0", KNOWN_OWNER_EXE_SHAS[SHA_0138])
        self.assertIn(SHA_0137, KNOWN_EXES)
        self.assertIn(SHA_0137, KNOWN_OWNER_EXE_SHAS)
        self.assertNotIn("0" * 64, KNOWN_EXES)

    def test_reviewed_new_metadata_has_consistent_saves_and_addons_edges(self):
        path = Path(__file__).resolve().parents[1] / "catalog" / "options_code_graph_0138.json"
        audit = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(SHA_0138, audit["exe_sha256"])
        self.assertEqual("0.138.0-current", audit["observed_binary_label"])
        self.assertEqual(54, audit["direct_key_xref_count"])
        self.assertEqual(16, audit["unique_function_clusters"])
        entry = audit["candidate_ui_entrypoints"]
        self.assertEqual({"options_page_controls", "saves_page_content", "addons_page_content"}, set(entry))
        calls = audit["direct_call_candidates"]
        self.assertEqual({"options_page_controls", "saves_page_content", "addons_page_content"},
                         {x["function"] for x in calls})
        self.assertFalse(audit["native_cheat_menu_implemented"])
        self.assertFalse(audit["cheats_verified"])
        self.assertFalse(audit["disassembler_or_hook_verification"])

    def test_new_english_catalog_had_no_changes_from_prior(self):
        report = json.loads((Path(__file__).resolve().parents[1] / "catalog" /
                             "locale_delta_0137_0138.json").read_text(encoding="utf-8"))
        self.assertEqual(SHA_0138, report["new_source_sha256"])
        self.assertEqual(3334, report["new_keys"])
        self.assertEqual(3334, report["old_keys"])
        for f in ("added_keys_count", "removed_keys_count", "changed_common_values_count"):
            self.assertEqual(0, report[f])

    def test_old_138_hash_cannot_be_inferred_from_an_arbitrary_binary(self):
        with self.assertRaises(XrefError):
            map_binary(b"MZ" + b"\x00" * 2048, "0" * 64)


if __name__ == "__main__":
    unittest.main()
