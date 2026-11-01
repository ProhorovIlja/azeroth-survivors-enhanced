import json
import tempfile
import unittest
from pathlib import Path
from tools.benchmark_compare import BenchmarkError, analyze, validate_run, load_runs

SHA="a"*64

def run(i,build="warlock",version=SHA,actions=0,mode="stand_still",zone="Elwynn"):
    return {"run_id":"r"+str(i),"build_id":build,"client_sha256":version,
            "zone":zone,"difficulty":"Normal","race":"Orc","settings_id":"fixed-v1",
            "interaction_mode":mode,"survival_seconds":300,"kills":100,
            "boss_defeated":False,"boss_kill_seconds":None,"manual_actions":actions,
            "notes":""}


class BenchmarkCompareTests(unittest.TestCase):
    def test_run_rejects_movement_in_standstill(self):
        x=run(1,actions=1)
        with self.assertRaises(BenchmarkError):
            validate_run(x)

    def test_boss_data_consistent(self):
        x=run(1)
        x["boss_kill_seconds"]=100
        with self.assertRaises(BenchmarkError):
            validate_run(x)
        x["boss_defeated"]=True
        self.assertEqual(x,validate_run(x))

    def test_mixed_versions_never_compared(self):
        runs=[run(1,"a"),run(2,"b",version="b"*64)]
        report=analyze(runs)
        self.assertEqual(2,len(report["comparisons"]))
        self.assertTrue(all(x["status"]=="INSUFFICIENT_COMPARABLE_TRIALS" for x in report["comparisons"]))

    def test_mixed_zone_and_mode_never_compared(self):
        rows=[run(1),run(2,zone="Westfall"),run(3,mode="pickup_only")]
        self.assertEqual(3,len(analyze(rows)["comparisons"]))

    def test_three_trials_per_each_candidate_are_descriptive_only(self):
        rows=[run(i,build="imp") for i in range(3)]
        rows += [run(i+3,build="giant") for i in range(3)]
        result=analyze(rows)
        self.assertEqual("DESCRIPTIVE_COMPARISON_ONLY",result["comparisons"][0]["status"])
        self.assertEqual(20.0,result["comparisons"][0]["candidates"][0]["median_kills_per_minute"])
        self.assertFalse(result["overall_winner_certified"])
        self.assertFalse(result["comparisons"][0]["winner_certified"])

    def test_insufficient_sample_does_not_promote_winner(self):
        rows=[run(1,"imp"),run(2,"giant"),run(3,"giant")]
        self.assertEqual("INSUFFICIENT_COMPARABLE_TRIALS",analyze(rows)["comparisons"][0]["status"])

    def test_reject_bool_as_time_or_kills(self):
        x=run(1);x["survival_seconds"]=True
        with self.assertRaises(BenchmarkError):validate_run(x)
        x=run(2);x["kills"]=False
        with self.assertRaises(BenchmarkError):validate_run(x)

    def test_duplicate_run_ids_refused(self):
        with tempfile.TemporaryDirectory() as t:
            file=Path(t)/"runs.json"
            file.write_text(json.dumps({"schema_version":1,"runs":[run(1),run(1)]}))
            with self.assertRaises(BenchmarkError):load_runs(file)

    def test_raw_input_fields_rejected(self):
        x=run(1);x["remote_url"]="https://example.com"
        with self.assertRaises(BenchmarkError):validate_run(x)

    def test_output_does_not_reveal_notes(self):
        x=run(1);x["notes"]="some private observation"
        self.assertNotIn("some private observation",str(analyze([x])))


if __name__=="__main__":
    unittest.main()
