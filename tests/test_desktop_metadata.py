from __future__ import annotations

import configparser
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class DesktopMetadataTests(unittest.TestCase):
    def test_desktop_entry_launches_gui_without_terminal(self) -> None:
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(ROOT / "packaging" / "io.github.Frapo78.MacUbuntu.desktop", encoding="utf-8")
        entry = parser["Desktop Entry"]
        self.assertEqual(entry["Type"], "Application")
        self.assertEqual(entry["Exec"], "macubuntu-gui")
        self.assertEqual(entry["Terminal"].lower(), "false")
        self.assertEqual(entry["Icon"], "io.github.Frapo78.MacUbuntu")

    def test_appstream_metadata_keeps_creator_credit_and_launcher_id(self) -> None:
        root = ET.parse(ROOT / "packaging" / "io.github.Frapo78.MacUbuntu.metainfo.xml").getroot()
        self.assertEqual(root.findtext("id"), "io.github.Frapo78.MacUbuntu")
        self.assertEqual(root.findtext("launchable"), "io.github.Frapo78.MacUbuntu.desktop")
        text = " ".join("".join(root.itertext()).split())
        self.assertIn("Francesco Poltero", text)


if __name__ == "__main__":
    unittest.main()
