import json
import tempfile
import unittest
from pathlib import Path
from planner.azs_planner import export_addon, load_catalog
from tools.log_summary import digest
from tools.inspect_archive import inventory
import zipfile


class CatalogTests(unittest.TestCase):
    def test_catalog_has_nine_classes(self):
        builds = load_catalog()
        self.assertEqual(9, len({p["class"] for p in builds}))
        self.assertEqual(11, len(builds))

    def test_unique_ids(self):
        builds = load_catalog()
        self.assertEqual(len(builds), len({p["id"] for p in builds}))

    def test_lua_export(self):
        with tempfile.TemporaryDirectory() as directory:
            path = export_addon(load_catalog(), Path(directory) / "Presets.lua")
            contents = path.read_text(encoding="utf-8")
            self.assertEqual(len(load_catalog()), contents.count("review_status = "))
            self.assertIn("warlock-demonology-idle", contents)

    def test_reject_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            builds = load_catalog()
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps({"schema_version": 1, "builds": builds + [builds[0]]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_catalog(path)

    def test_redact_and_cap_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "test.log"
            p.write_text(("WARNING password=mysecret person@example.com\n" * 1000), encoding="utf-8")
            result = digest(p, 4)
            self.assertEqual(1000, result["lines"])
            self.assertEqual(1000, result["issue_lines"])
            self.assertLessEqual(len(result["examples"]), 4)
            self.assertNotIn("mysecret", json.dumps(result))
            self.assertNotIn("person@example.com", json.dumps(result))

    def test_fingerprint_memory_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "errors.log"
            p.write_text("".join(f"ERROR incident number {i}\n" for i in range(700)), encoding="utf-8")
            result = digest(p, 4)
            self.assertLessEqual(result["unique_fingerprints_kept"], 512)
            self.assertGreater(result["overflow_unique_lines"], 0)

    def test_archive_inventory_no_extraction(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "data.zip"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("config/readme.txt", "example")
            result = inventory(p, 3)
            self.assertEqual(1, result["entries_total"])
            self.assertTrue(result["safe_no_extract"])


if __name__ == "__main__":
    unittest.main()
