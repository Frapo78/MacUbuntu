from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DebianPackagingTests(unittest.TestCase):
    def test_control_declares_gui_runtime_dependencies(self) -> None:
        control = (ROOT / "debian/control").read_text(encoding="utf-8")
        for dependency in ("python3", "python3-gi", "gir1.2-gtk-4.0", "gir1.2-adw-1"):
            self.assertIn(dependency, control)
        self.assertIn("Architecture: all", control)

    def test_payload_keeps_cli_and_gui_on_same_engine_tree(self) -> None:
        install = (ROOT / "debian/install").read_text(encoding="utf-8")
        self.assertIn("macubuntu usr/lib/macubuntu/", install)
        self.assertIn("macubuntu-gui usr/lib/macubuntu/", install)
        self.assertIn("macubuntu_app usr/lib/macubuntu/", install)
        links = (ROOT / "debian/links").read_text(encoding="utf-8")
        self.assertIn("usr/lib/macubuntu/macubuntu usr/bin/macubuntu", links)
        self.assertIn("usr/lib/macubuntu/macubuntu-gui usr/bin/macubuntu-gui", links)

    def test_desktop_integration_and_credits_are_packaged(self) -> None:
        install = (ROOT / "debian/install").read_text(encoding="utf-8")
        for path in (
            "packaging/io.github.Frapo78.MacUbuntu.desktop",
            "packaging/io.github.Frapo78.MacUbuntu.metainfo.xml",
            "packaging/io.github.Frapo78.MacUbuntu.svg",
            "docs/CREDITS.md",
            "docs/COMPONENTS.md",
        ):
            self.assertIn(path, install)
        copyright_text = (ROOT / "debian/copyright").read_text(encoding="utf-8")
        self.assertIn("Francesco Poltero", copyright_text)
        self.assertIn("Third-party components", copyright_text)

    def test_package_removal_does_not_ship_mutating_maintainer_scripts(self) -> None:
        for name in ("preinst", "postinst", "prerm", "postrm"):
            self.assertFalse((ROOT / f"debian/{name}").exists())


if __name__ == "__main__":
    unittest.main()
