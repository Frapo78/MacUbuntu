import unittest

from macubuntu_app.external_gnome import EGO_REVIEW_DOWNLOAD
from macubuntu_app.modules.gestures_x11 import GesturesX11Module
from macubuntu_app.modules.phone_integration import PhoneIntegrationModule
from macubuntu_app.modules.shell_extensions import ShellExtensionsModule


class GnomeExtensionPinTests(unittest.TestCase):
    def test_gnome46_extension_versions_and_reviews_are_pinned(self):
        expected = {
            "blur-my-shell@aunetx": (72, 69740),
            "just-perfection-desktop@just-perfection": (36, 68110),
            "clipboard-indicator@tudmotu.com": (71, 70694),
        }
        for uuid, (version, review_id) in expected.items():
            pin = ShellExtensionsModule.EXTENSIONS[uuid]["46"]
            self.assertEqual(pin["version"], version)
            self.assertEqual(pin["review_id"], review_id)
            url = EGO_REVIEW_DOWNLOAD.format(review_id=review_id)
            self.assertEqual(
                url,
                f"https://extensions.gnome.org/review/download/{review_id}.shell-extension.zip",
            )

        self.assertEqual(GesturesX11Module.PINS["46"], {"version": 25, "review_id": 63139})
        self.assertEqual(PhoneIntegrationModule.GS_PINS["46"], {"version": 72, "review_id": 70399})

    def test_gnome42_extension_versions_and_reviews_are_pinned(self):
        expected = {
            "blur-my-shell@aunetx": (47, 42627),
            "just-perfection-desktop@just-perfection": (26, 43626),
            "clipboard-indicator@tudmotu.com": (47, 43380),
        }
        for uuid, (version, review_id) in expected.items():
            pin = ShellExtensionsModule.EXTENSIONS[uuid]["42"]
            self.assertEqual(pin["version"], version)
            self.assertEqual(pin["review_id"], review_id)

        self.assertEqual(GesturesX11Module.PINS["42"], {"version": 17, "review_id": 41094})
        self.assertEqual(PhoneIntegrationModule.GS_PINS["42"], {"version": 68, "review_id": 66552})


if __name__ == "__main__":
    unittest.main()
