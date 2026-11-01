import json
import unittest
from pathlib import Path


class ModernWarlockResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).resolve().parents[1]/"catalog"/"0137_warlock_afk_experiments.json"
        cls.data=json.loads(path.read_text(encoding="utf-8"))

    def test_includes_only_unverified_experiments(self):
        rows=self.data["build_experiments"]
        self.assertEqual(2,len(rows))
        self.assertFalse(self.data["performance_measured"])
        self.assertFalse(self.data["automatic_allocation"])
        self.assertFalse(self.data["ranks_known"])
        self.assertTrue(all(b["legal_51_point_build"] is False for b in rows))
        self.assertTrue(all(b["dps_measured"] is False for b in rows))

    def test_one_capstone_at_a_time(self):
        for row in self.data["build_experiments"]:
            self.assertTrue(row["capstones_exclusive"])
            self.assertEqual({"Butcher","Pact of the Nathrezim"},set(row["capstone_choices"]))
            self.assertFalse(set(row["capstone_choices"]).issubset(set(row["candidates"])))

    def test_supremacy_conflict_not_in_swarm_candidates(self):
        rows={x["id"]:x for x in self.data["build_experiments"]}
        swarm=rows["0137_warlock_lessers_swarm"]
        giant=rows["0137_warlock_permanent_greaters"]
        self.assertNotIn("Demonic Supremacy",swarm["candidates"])
        self.assertIn("Demonic Supremacy",giant["candidates"])
        self.assertIn("Legion Gate",giant["avoid_strategy_conflicts"])


if __name__=="__main__":
    unittest.main()
