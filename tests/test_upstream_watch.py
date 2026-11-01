import unittest
from tools.upstream_watch import collect, snapshot_one, main


class UpstreamWatchTests(unittest.TestCase):
    @staticmethod
    def fake_get(url):
        if url == "/repos/demo/azeroth-addon":
            return {
                "default_branch":"main", "archived":False, "fork":True,
                "parent":{"full_name":"demo/base"}, "pushed_at":"2026-11-01T11:00:00Z",
                "forks_count":3, "license":{"spdx_id":"MIT"}
            }
        if url.endswith("/releases/latest"):
            return {"tag_name":"v1.2", "published_at":"2026-11-01T10:00:00Z"}
        if "/pulls?" in url:
            return [{"number":3}, {"number":4}]
        if "/branches?" in url:
            return [{"name":"main"}, {"name":"fix"}]
        if url.startswith("/search/repositories?"):
            return {"items":[{"full_name":"demo/brand-new-addon","html_url":"https://github.com/demo/brand-new-addon","fork":False}]}
        return None

    def test_snapshot_meta_and_samples(self):
        result = snapshot_one("demo/azeroth-addon", self.fake_get)
        self.assertEqual("demo/base", result["parent"])
        self.assertEqual([3, 4], result["sample_open_prs"])
        self.assertEqual(["main", "fix"], result["sample_branches"])
        self.assertEqual("v1.2", result["latest_release"]["tag"])

    def test_collect_dedup_search(self):
        report = collect([{"repo":"demo/azeroth-addon"}], self.fake_get)
        self.assertEqual(1, report["repository_count"])
        self.assertEqual(1, len(report["potential_new_repositories"]))
        self.assertEqual("demo/brand-new-addon", report["potential_new_repositories"][0]["repo"])
        self.assertIn("Samples only", report["limitations"])

    def test_default_never_uses_network(self):
        self.assertEqual(0, main(["--limit", "2"]))


if __name__ == "__main__":
    unittest.main()
