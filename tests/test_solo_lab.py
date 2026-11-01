import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools import solo_lab as x


class SoloLabTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.exe = self.dir / "game" / "AzerothSurvivors.exe"
        self.exe.parent.mkdir()
        self.exe.write_bytes(b"MZ" + b"synthetic-client-bytes")
        self.sav = self.dir / "source" / "characters.txt"
        self.sav.parent.mkdir()
        self.sav.write_bytes(b"fake-test-save-123")
        self.sandbox = self.dir / "lab"
        self.digest = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        self.old_shas = x.CLIENT_SHAS
        x.CLIENT_SHAS = {self.digest:"synthetic-client"}
        self.addCleanup(lambda: setattr(x,"CLIENT_SHAS",self.old_shas))

    def create(self):
        return x.prepare(self.exe,self.sav,self.sandbox,True)

    def test_inspect_is_read_only(self):
        data=x.inspect(self.exe,self.sav)
        self.assertTrue(data["read_only"])
        self.assertFalse(self.sandbox.exists())
        self.assertEqual(b"fake-test-save-123",self.sav.read_bytes())

    def test_create_requires_confirmation(self):
        with self.assertRaises(x.LabError):
            x.prepare(self.exe,self.sav,self.sandbox,False)
        self.assertFalse(self.sandbox.exists())

    def test_create_preserves_main_and_keeps_verified_baseline(self):
        self.create()
        self.assertTrue((self.sandbox/x.BASELINE).exists())
        self.assertEqual(self.sav.read_bytes(),(self.sandbox/x.SAVE).read_bytes())
        self.assertFalse(x.status(self.sandbox)["changed_from_baseline"])
        self.assertEqual(b"fake-test-save-123",self.sav.read_bytes())

    def test_restore_snapshot_uses_sandbox_not_main(self):
        self.create()
        (self.sandbox/x.SAVE).write_bytes(b"CHEAT-TEST-ONLY")
        self.assertTrue(x.status(self.sandbox)["changed_from_baseline"])
        restored=x.restore(self.sandbox,True)
        self.assertEqual("restored_sandbox_only",restored["status"])
        self.assertEqual(b"fake-test-save-123",(self.sandbox/x.SAVE).read_bytes())
        self.assertEqual(b"fake-test-save-123",self.sav.read_bytes())
        self.assertEqual(b"CHEAT-TEST-ONLY",(self.sandbox/"snapshots"/restored["preserved_previous"]).read_bytes())

    def test_restore_requires_yes(self):
        self.create()
        with self.assertRaises(x.LabError):
            x.restore(self.sandbox,False)

    def test_existing_sandbox_never_overwritten(self):
        self.create()
        with self.assertRaises(x.LabError):
            self.create()

    def test_unknown_game_sha_fails_closed(self):
        with patch.object(x,"CLIENT_SHAS",{}):
            with self.assertRaises(x.LabError):
                x.inspect(self.exe,self.sav)

    def test_reject_symlinked_input(self):
        target=self.dir/"source"/"input-link.txt"
        try: target.symlink_to(self.sav)
        except (OSError,NotImplementedError): self.skipTest("no symlinks")
        with self.assertRaises(x.LabError):
            x.prepare(self.exe,target,self.sandbox,True)

    def test_reject_sandbox_inside_game_root(self):
        with self.assertRaises(x.LabError):
            x.prepare(self.exe,self.sav,self.exe.parent/"lab",True)

    def test_baseline_tamper_prevents_restore(self):
        self.create()
        (self.sandbox/x.BASELINE).write_bytes(b"fake-but-changed")
        with self.assertRaises(x.LabError):
            x.restore(self.sandbox,True)

    def test_launch_requires_explicit_confirmation(self):
        self.create()
        with self.assertRaises(x.LabError):
            x.launch(self.sandbox,False,platform="win32")

    def test_launch_uses_only_original_exe_and_sandbox_save(self):
        self.create()
        observed={}
        class FakeProcess: pid=567
        def fake_spawn(args,**kwargs):
            observed.update({"args":args,**kwargs})
            return FakeProcess()
        answer=x.launch(self.sandbox,True,platform="win32",spawn=fake_spawn)
        self.assertEqual([str(self.exe)],observed["args"])
        self.assertEqual(str(self.sandbox/x.SAVE),observed["env"]["WOW_ROGUE_SAVE"])
        self.assertTrue(answer["primary_save_redirected"])
        self.assertFalse(answer["other_game_settings_isolated"])

    def test_changed_game_binary_disables_launch(self):
        self.create()
        self.exe.write_bytes(b"MZ"+b"different")
        with self.assertRaises(x.LabError):
            x.launch(self.sandbox,True,platform="win32",spawn=lambda *a,**k: None)

    def test_malformed_receipt_prevents_launch(self):
        self.create()
        (self.sandbox/x.MANIFEST).write_text("not json")
        with self.assertRaises(x.LabError):
            x.launch(self.sandbox,True,platform="win32")

    def test_snapshot_does_not_touch_original(self):
        self.create()
        record=x.snapshot(self.sandbox)
        self.assertTrue((self.sandbox/"snapshots"/record["snapshot_name"]).exists())
        self.assertEqual(b"fake-test-save-123",self.sav.read_bytes())


if __name__=="__main__":unittest.main()
