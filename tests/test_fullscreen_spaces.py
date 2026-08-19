import unittest
from pathlib import Path

from macubuntu_app.modules.spaces_fullscreen import FullscreenSpacesModule


class FullscreenSpacesTests(unittest.TestCase):
    def setUp(self):
        self.module = FullscreenSpacesModule()

    def test_supported_gnome_generations_are_explicit(self):
        self.assertEqual(self.module.SUPPORTED_MAJORS, {"42", "46"})
        self.assertEqual(self.module.UUID, "macubuntu-fullscreen-spaces@francescopoltero")

    def test_each_generation_always_creates_a_fresh_fullscreen_workspace(self):
        for major in ("42", "46"):
            source = self.module._source_file(major).read_text(encoding="utf-8")
            self.assertIn("append_new_workspace", source)
            self.assertIn("originalWorkspace", source)
            self.assertIn("originalIndex", source)
            self.assertIn("_restoreWindow", source)
            self.assertIn("Meta.SizeChange.FULLSCREEN", source)
            self.assertIn("Meta.SizeChange.UNFULLSCREEN", source)
            self.assertNotIn("Meta.SizeChange.MAXIMIZE", source)
            self.assertNotIn("list_windows().length === 1", source)

    def test_metadata_is_scoped_to_target_shell_generation(self):
        for major in ("42", "46"):
            metadata = self.module._metadata(major)
            self.assertIn(f'"shell-version": [\n    "{major}"', metadata)
            self.assertIn(self.module.UUID, metadata)


if __name__ == "__main__":
    unittest.main()
