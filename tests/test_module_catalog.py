import unittest

from macubuntu_app.modules import ALL_MODULES


class ModuleCatalogTests(unittest.TestCase):
    def test_module_ids_are_unique_and_deep_stack_is_registered(self):
        ids = [module.id for module in ALL_MODULES]
        self.assertEqual(len(ids), len(set(ids)))
        for expected in {
            "core.gnome",
            "desktop.tools",
            "appearance.typography",
            "appearance.mactahoe",
            "appearance.wallpapers",
            "shell.enhancements",
            "gestures.x11",
            "spotlight.ulauncher",
            "sharing.warpinator",
            "phone.integration",
        }:
            self.assertIn(expected, ids)


if __name__ == "__main__":
    unittest.main()
