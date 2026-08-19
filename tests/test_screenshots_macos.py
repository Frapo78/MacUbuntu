import unittest

from macubuntu_app.modules.screenshots_macos import ScreenshotsMacOSModule


class ScreenshotsMacOSTests(unittest.TestCase):
    def test_shortcut_contract_matches_macos_style(self):
        module = ScreenshotsMacOSModule()
        settings = {(schema, key): desired for schema, key, desired, _ in module.settings}
        self.assertEqual(
            settings[("org.gnome.shell.keybindings", "screenshot")],
            "['<Shift><Super>3', '<Shift>Print']",
        )
        self.assertEqual(
            settings[("org.gnome.shell.keybindings", "show-screenshot-ui")],
            "['<Shift><Super>4', '<Shift><Super>5', 'Print']",
        )
        self.assertEqual(
            settings[("org.gnome.shell.keybindings", "screenshot-window")],
            "['<Alt>Print']",
        )
        self.assertEqual(
            settings[("org.gnome.shell.keybindings", "show-screen-recording-ui")],
            "['<Ctrl><Shift><Alt>R']",
        )

    def test_module_has_no_external_package_dependency(self):
        module = ScreenshotsMacOSModule()
        self.assertFalse(hasattr(module, "dependencies"))
        self.assertEqual(module.id, "screenshots.macos")


if __name__ == "__main__":
    unittest.main()
