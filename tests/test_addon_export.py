import tempfile
import unittest
from pathlib import Path
from planner.addon_export import lua_quote, as_preset, to_lua, save_lua
from planner.build_studio import BuildError, make_draft


SHA = "a" * 64


def inventory():
    return {"client_sha256": SHA, "classes": {
        "warlock": {"Demonology": ["Summon Imp", "Demonic Pact", "Summon Felguard"]},
        "mage": {"Arcane": ["Arcane Focus"]},
    }}


class LuaExportTests(unittest.TestCase):
    def test_escaped_quotes_backslash_and_newline(self):
        s = lua_quote('hello "world" \\ slash\nend')
        self.assertEqual('"hello \\"world\\" \\\\ slash\\nend"', s)

    def test_safe_generated_advisor_fields(self):
        build = make_draft(inventory(), "warlock", "Idle Felguard", "low_input_minions")
        build["talents"] = [{"tree":"Demonology","name":"Summon Imp","points":1}]
        out = to_lua(build, inventory())
        self.assertIn('AZSE_PRESETS = {', out)
        self.assertIn('playstyle = "idle"', out)
        self.assertIn('review_status = "name_only_unverified"', out)
        self.assertIn('name = "Idle Felguard"', out)
        self.assertNotIn("0.135.1", out)

    def test_lua_injection_is_quoted_not_executable(self):
        b = make_draft(inventory(), "warlock", 'Name" }; malicious(); --')
        text = to_lua(b, inventory())
        self.assertIn('Name\\" }; malicious(); --', text)
        self.assertNotIn('name = "Name" }; malicious()', text)

    def test_other_client_rejected(self):
        b = make_draft(inventory(), "warlock")
        b["client_sha256"] = "b" * 64
        with self.assertRaisesRegex(BuildError, "CLIENT MISMATCH"):
            to_lua(b, inventory())

    def test_wrong_tree_rejected(self):
        b = make_draft(inventory(), "warlock")
        b["talents"] = [{"tree":"Arcane","name":"Arcane Focus","points":1}]
        with self.assertRaises(BuildError):
            to_lua(b, inventory())

    def test_no_auto_legal_ability_claim(self):
        b = make_draft(inventory(), "warlock")
        result = as_preset(b, inventory())
        self.assertIn("NOT LEGALITY-TESTED", result["note"])
        self.assertIn("UNKNOWN", result["baseline"])

    def test_refuses_overwrite_instead_of_mutating_game(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "Presets.lua"
            save_lua(file, "test")
            with self.assertRaises(BuildError):
                save_lua(file, "new")
            self.assertEqual("test", file.read_text())


if __name__ == "__main__":
    unittest.main()
