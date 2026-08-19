import unittest

from macubuntu_app.external_gnome import EGO_REVIEW_DOWNLOAD
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


if __name__ == "__main__":
    unittest.main()
