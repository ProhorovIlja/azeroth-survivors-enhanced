import tempfile
import unittest
from pathlib import Path
from tools.addon_audit import AuditError, scan


class AddonAuditTests(unittest.TestCase):
    def setUp(self):
        d=tempfile.TemporaryDirectory();self.addCleanup(d.cleanup)
        self.root=Path(d.name)
        self.addons=self.root/"benilla-config"/"AddOns"
        self.addons.mkdir(parents=True)

    def addon(self,name,interface="11200"):
        folder=self.addons/name
        folder.mkdir()
        (folder/(name+".toc")).write_text(
            f"## Interface: {interface}\n## Title: {name}\n## Version: 1.2.3\nMain.lua\n")

    def test_empty_directory(self):
        report=scan(self.root)
        self.assertEqual(0,report["installed_addon_folders"])
        self.assertEqual([],report["warnings"])

    def test_parse_toc_without_executing(self):
        self.addon("AZSEnhancedAdvisor")
        r=scan(self.root)
        self.assertEqual("1.2.3",r["entries"][0]["version"])
        self.assertTrue(r["entries"][0]["interface_11200"])
        self.assertFalse(r["game_files_modified"])

    def test_hud_conflict_warning(self):
        self.addon("nfUI");self.addon("SurvivorsDragonUi")
        self.assertTrue(any("HUD" in s for s in scan(self.root)["warnings"]))

    def test_meters_conflict_warning(self):
        self.addon("AZSSpellMeter");self.addon("AZSMaxHit")
        self.assertTrue(any("damage meters" in s for s in scan(self.root)["warnings"]))

    def test_missing_toc_warns(self):
        (self.addons/"AddonMain").mkdir()
        self.assertTrue(any("Missing matching TOC" in s for s in scan(self.root)["warnings"]))

    def test_wrong_interface_warns(self):
        self.addon("UnverifiedUI","11000")
        self.assertTrue(any("Interface 11200" in s for s in scan(self.root)["warnings"]))

    def test_reject_symlinked_addon(self):
        external=self.root/"elsewhere";external.mkdir()
        try:(self.addons/"BadAddon").symlink_to(external,target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest("no symlinks")
        with self.assertRaises(AuditError):scan(self.root)

    def test_cannot_mutate_toc(self):
        self.addon("AZSEnhancedAdvisor")
        toc=self.addons/"AZSEnhancedAdvisor"/"AZSEnhancedAdvisor.toc"
        original=toc.read_bytes()
        scan(self.root)
        self.assertEqual(original,toc.read_bytes())


if __name__=="__main__":unittest.main()
