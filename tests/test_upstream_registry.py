import json
import tempfile
import unittest
from pathlib import Path
from tools.upstream_registry import load_registry


class UpstreamRegistryTests(unittest.TestCase):
    def test_coverage_and_dont_assume_runtime(self):
        data = load_registry()
        self.assertGreaterEqual(len(data), 25)
        self.assertTrue(all(x["compatible_with_user_exe"] == "untested" for x in data))
        self.assertIn("cadoky/ASBuilder", {x["repo"] for x in data})

    def test_restricted_code_not_marked_permissive(self):
        data = load_registry()
        for repo in ("Kindagrey/Azerloot", "Maidenquinn/AzerothHub", "bymarvin/azeroth-survivors-source"):
            row = next(x for x in data if x["repo"] == repo)
            self.assertEqual("restricted", row["license_status"])

    def test_duplicates_rejected(self):
        src = load_registry()[0]
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "test.json"
            file.write_text(json.dumps({"schema_version": 1, "sources": [src, src]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_registry(file)


if __name__ == "__main__":
    unittest.main()
