"""Synthetic filesystem tests. Never uses or runs the owner's real EXE."""
import tempfile
import unittest
from pathlib import Path

from tools.addon_package import SafetyError, install, plan, rollback, status


class AddonPackageTests(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        root = Path(workspace.name)
        self.game = root / "game"
        self.game.mkdir()
        self.exe = self.game / "AzerothSurvivors.exe"
        self.exe.write_bytes(b"FAKE-TEST-EXECUTABLE")
        (self.game / "Data").mkdir()
        self.source = root / "source" / "AZSEnhancedAdvisor"
        self.source.mkdir(parents=True)
        (self.source / "AZSEnhancedAdvisor.toc").write_text(
            "## Interface: 11200\nCore.lua\n", encoding="utf-8"
        )
        (self.source / "Core.lua").write_text("local name = 'test'\n", encoding="utf-8")
        self.target = self.game / "benilla-config" / "AddOns" / "AZSEnhancedAdvisor"

    def test_plan_never_creates_folders(self):
        data = plan(self.game, self.source)
        self.assertEqual("read_only_plan", data["mode"])
        self.assertFalse(data["known_owner_client"])
        self.assertFalse((self.game / "benilla-config").exists())
        self.assertFalse((self.game / ".azse-enhanced").exists())

    def test_unknown_client_fails_closed(self):
        with self.assertRaises(SafetyError):
            install(self.game, self.source, yes=True)
        self.assertFalse(self.target.exists())

    def test_explicit_confirmation_required(self):
        with self.assertRaises(SafetyError):
            install(self.game, self.source, allow_unknown_client=True)

    def test_install_rollback_preserves_game(self):
        exe_before = self.exe.read_bytes()
        result = install(self.game, self.source, yes=True, allow_unknown_client=True)
        self.assertFalse(result["game_files_modified"])
        self.assertEqual((self.source / "Core.lua").read_bytes(),
                         (self.target / "Core.lua").read_bytes())
        self.assertTrue(status(self.game)["files_unchanged"])
        undone = rollback(self.game, yes=True)
        self.assertEqual("rolled_back", undone["status"])
        self.assertFalse(self.target.exists())
        self.assertFalse((self.game / ".azse-enhanced").exists())
        self.assertEqual(exe_before, self.exe.read_bytes())

    def test_existing_addon_requires_replace(self):
        self.target.mkdir(parents=True)
        (self.target / "existing.lua").write_text("original", encoding="utf-8")
        with self.assertRaises(SafetyError):
            install(self.game, self.source, yes=True, allow_unknown_client=True)
        self.assertEqual("original", (self.target / "existing.lua").read_text())

    def test_existing_addon_backed_up_and_restored(self):
        self.target.mkdir(parents=True)
        (self.target / "existing.lua").write_text("original", encoding="utf-8")
        install(self.game, self.source, yes=True, replace_existing=True,
                allow_unknown_client=True)
        self.assertTrue((self.game / ".azse-enhanced" / "backup" / "existing.lua").exists())
        rollback(self.game, yes=True)
        self.assertEqual("original", (self.target / "existing.lua").read_text())
        self.assertFalse((self.target / "Core.lua").exists())

    def test_modified_addon_refuses_destructive_rollback(self):
        install(self.game, self.source, yes=True, allow_unknown_client=True)
        (self.target / "Core.lua").write_text("user changed the file", encoding="utf-8")
        with self.assertRaises(SafetyError):
            rollback(self.game, yes=True)
        self.assertTrue(self.target.exists())

    def test_no_second_install_until_rollback(self):
        install(self.game, self.source, yes=True, allow_unknown_client=True)
        with self.assertRaises(SafetyError):
            install(self.game, self.source, yes=True, allow_unknown_client=True)

    def test_refuse_source_executable(self):
        (self.source / "payload.exe").write_bytes(b"MZ")
        with self.assertRaises(SafetyError):
            plan(self.game, self.source)

    def test_refuse_source_archive(self):
        (self.source / "patch.MPQ").write_bytes(b"MPQ")
        with self.assertRaises(SafetyError):
            plan(self.game, self.source)

    def test_refuse_toc_escape(self):
        (self.source / "AZSEnhancedAdvisor.toc").write_text(
            "## Interface: 11200\n../../Data/patch.MPQ\n", encoding="utf-8"
        )
        with self.assertRaises(SafetyError):
            plan(self.game, self.source)

    def test_symlinked_source_rejected(self):
        link = self.source / "outside.lua"
        try:
            link.symlink_to(self.exe)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unsupported on this test machine")
        with self.assertRaises(SafetyError):
            plan(self.game, self.source)

    def test_original_mpq_and_sav_stay_unchanged(self):
        mpq, save = self.game / "Data" / "patch.MPQ", self.game / "char.sav"
        mpq.write_bytes(b"ORIGINAL-MPQ")
        save.write_bytes(b"ORIGINAL-SAVE")
        install(self.game, self.source, yes=True, allow_unknown_client=True)
        rollback(self.game, yes=True)
        self.assertEqual(b"ORIGINAL-MPQ", mpq.read_bytes())
        self.assertEqual(b"ORIGINAL-SAVE", save.read_bytes())

    def test_manual_unknown_receipt_is_not_deleted(self):
        self.target.mkdir(parents=True)
        (self.target / "Existing.lua").write_text("not ours", encoding="utf-8")
        with self.assertRaises(SafetyError):
            rollback(self.game, yes=True)
        self.assertTrue((self.target / "Existing.lua").exists())


if __name__ == "__main__":
    unittest.main()
