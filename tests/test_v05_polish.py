import os
import tempfile
import unittest
from pathlib import Path

from macubuntu_app.modules.appearance_mactahoe import AppearanceMacTahoeModule
from macubuntu_app.modules.core_gnome import CoreGnomeModule
from macubuntu_app.modules.wallpaper_macos import WallpaperMacCollectionModule


class V05PolishTests(unittest.TestCase):
    def test_mactahoe_release_is_pinned_and_titlebar_is_mac_like(self):
        module = AppearanceMacTahoeModule()
        self.assertEqual(
            module.GTK_COMMIT,
            "ae82d8ea6a7eba42b9bf375ec602538c34fdabab",
        )
        settings = {(schema, key): desired for schema, key, desired, _ in module.settings}
        self.assertEqual(
            settings[("org.gnome.desktop.wm.preferences", "titlebar-uses-system-font")],
            "false",
        )
        self.assertEqual(
            settings[("org.gnome.desktop.wm.preferences", "titlebar-font")],
            "'Inter Semi-Bold 11'",
        )
        self.assertEqual(
            settings[("org.gnome.desktop.wm.preferences", "action-double-click-titlebar")],
            "'toggle-maximize'",
        )
        self.assertEqual(
            settings[("org.gnome.desktop.wm.preferences", "action-middle-click-titlebar")],
            "'none'",
        )
        self.assertEqual(
            settings[("org.gnome.shell.extensions.user-theme", "name")],
            "'MacUbuntu-MacTahoe-Dark-solid'",
        )

    def test_titlebar_installer_pins_normal_traffic_lights_and_rounding(self):
        source = Path(__file__).resolve().parents[1] / "macubuntu_app/modules/appearance_mactahoe.py"
        text = source.read_text(encoding="utf-8")
        self.assertIn('"-a",\n                "normal"', text)
        self.assertIn('"--round"', text)

    def test_gtk4_titlebar_bridge_uses_theme_imports_and_preserves_user_css(self):
        previous_data = os.environ.get("XDG_DATA_HOME")
        previous_config = os.environ.get("XDG_CONFIG_HOME")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            os.environ["XDG_DATA_HOME"] = str(root / "data")
            os.environ["XDG_CONFIG_HOME"] = str(root / "config")
            module = AppearanceMacTahoeModule()
            try:
                self.assertIn("MacUbuntu-MacTahoe-Light-solid/gtk-4.0/gtk.css", module._gtk4_import_css(dark=False))
                self.assertIn("MacUbuntu-MacTahoe-Dark-solid/gtk-4.0/gtk.css", module._gtk4_import_css(dark=True))
                module.gtk4_config_dir.mkdir(parents=True)
                module.gtk4_css.write_text("/* user css */\n", encoding="utf-8")
                self.assertEqual(module._unmanaged_gtk4_css({"operations": []}), [str(module.gtk4_css)])
                self.assertEqual(module.gtk4_css.read_text(encoding="utf-8"), "/* user css */\n")
            finally:
                if previous_data is None:
                    os.environ.pop("XDG_DATA_HOME", None)
                else:
                    os.environ["XDG_DATA_HOME"] = previous_data
                if previous_config is None:
                    os.environ.pop("XDG_CONFIG_HOME", None)
                else:
                    os.environ["XDG_CONFIG_HOME"] = previous_config

    def test_core_keeps_mac_controls_left_and_extensions_persistent(self):
        settings = {(schema, key): desired for schema, key, desired, _ in CoreGnomeModule.settings}
        self.assertEqual(
            settings[("org.gnome.desktop.wm.preferences", "button-layout")],
            "'close,minimize,maximize:'",
        )
        self.assertEqual(
            settings[("org.gnome.shell", "disable-user-extensions")],
            "false",
        )

    def test_wallpaper_collection_contains_pinned_big_sur_monterey_and_tahoe_set(self):
        collection = WallpaperMacCollectionModule.WALLPAPERS
        self.assertEqual(len(collection), 6)
        self.assertIn("WhiteSur-light.jpg", collection)
        self.assertIn("WhiteSur-dark.jpg", collection)
        self.assertIn("Monterey-light.jpg", collection)
        self.assertIn("Monterey-dark.jpg", collection)
        self.assertEqual(
            collection["MacTahoe-day.jpeg"]["blob"],
            "fb4a50aa1eddb93d2e3d901e6bf001e89fec84bd",
        )
        self.assertEqual(
            collection["MacTahoe-night.jpeg"]["blob"],
            "c516afb27d3d7c2713a0ab4468941631d75e0415",
        )


if __name__ == "__main__":
    unittest.main()
