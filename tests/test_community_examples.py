import json
import tempfile
import unittest
from pathlib import Path
from planner.community_examples import load_examples


class CommunityExamplesTests(unittest.TestCase):
    def test_all_records_have_patch_warning(self):
        builds = load_examples()
        self.assertGreaterEqual(len(builds), 6)
        self.assertTrue(all(x["known_obsolescence"] for x in builds))
        self.assertTrue(all(x["ranked_for_current_client"] is False for x in builds))

    def test_warlock_old_capstone_flag(self):
        w = next(x for x in load_examples() if x["id"].startswith("warlock-demonology"))
        self.assertEqual("0.114.2", w["observed_client_version"])
        self.assertEqual(51, sum(w["talent_split"].values()))
        self.assertIn("Dread Lord", w["known_obsolescence"])

    def test_priest_partial_not_faked_to_full(self):
        p = next(x for x in load_examples() if x["class"] == "priest")
        self.assertEqual(46, p["points_recorded"])
        self.assertEqual(46, sum(p["talent_split"].values()))

    def test_reject_points_above_limit(self):
        bad = dict(load_examples()[0])
        bad["talent_split"] = {"arms":11, "fury":42, "protection":0}
        bad["points_recorded"] = 53
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps({"schema_version":1,"examples":[bad]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_examples(path)


if __name__ == "__main__":
    unittest.main()
