import tempfile
import unittest
from pathlib import Path
from tools.solo_lab_gui import initial_paths, EDITORS


class GUIConfigTests(unittest.TestCase):
    def test_default_path_is_under_documents(self):
        p=initial_paths(home="C:/Users/Example",appdata="C:/Users/Example/AppData/Roaming")
        self.assertTrue(p["sandbox"].endswith("Documents/AZS-SoloLab-01"))
        self.assertTrue(p["save_source"].endswith("wenilla-rogue/characters.txt"))
        self.assertEqual("",p["game_exe"])

    def test_editor_links_are_allowlisted_https(self):
        self.assertEqual(3,len(EDITORS))
        self.assertTrue(all(v.startswith("https://") for v in EDITORS.values()))
        self.assertTrue(all("azerothsurvivors" in u.lower().replace("-", "") or "azssaveeditor" in u.lower() for u in EDITORS.values()))


if __name__=="__main__":unittest.main()
