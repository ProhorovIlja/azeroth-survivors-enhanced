import json
import tempfile
import unittest
from pathlib import Path
from tools.extract_talent_names import (
    TREE_SECTIONS, build_index, decode_english_map, extract,
    find_anchor_and_hash, is_short_talent_label
)


class TalentNameExtractorTests(unittest.TestCase):
    def test_tree_sections_cover_all_nine_classes(self):
        self.assertEqual(27, len(TREE_SECTIONS))
        self.assertEqual(9, len({t[0] for t in TREE_SECTIONS}))
        self.assertEqual(["Affliction", "Demonology", "Destruction"], [
            t[1] for t in TREE_SECTIONS if t[0] == "warlock"
        ])

    def test_description_is_not_a_talent_name(self):
        self.assertTrue(is_short_talent_label("Demonic Pact", "Demonic Pact"))
        self.assertFalse(is_short_talent_label(
            "Your demons deal {v}% more damage.", "Your demons deal {v}% more damage."
        ))
        self.assertFalse(is_short_talent_label("Demonology", "Demonologia"))

    def test_unknown_binary_cannot_extract_tree(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "unknown.exe"
            file.write_bytes(b"MZ" + b"not the owner's executable")
            with self.assertRaises(ValueError):
                extract(file)

    def test_english_dictionary_is_bounded_and_validated(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "fixture.bin"
            mapping = {"game.title":"Azeroth Survivors"}
            mapping.update({f"test{k}":f"test{k}" for k in range(800)})
            file.write_bytes(b"not code\n" + json.dumps(mapping, indent=2).encode())
            with self.assertRaises(ValueError):
                decode_english_map(file, 0)  # Not anchored to a JSON object

    def test_publish_summary_counts_not_local_game_text(self):
        root = Path(__file__).resolve().parents[1]
        summary = json.loads((root / "catalog" / "original_client_tree_counts.json").read_text())
        self.assertFalse(summary["runtime_verified"])
        self.assertEqual(9, len(summary["classes"]))
        self.assertEqual(27, sum(len(x) for x in summary["classes"].values()))
        self.assertEqual(345, sum(sum(x.values()) for x in summary["classes"].values()))
