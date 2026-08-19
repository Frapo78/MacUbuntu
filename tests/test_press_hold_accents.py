import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

from macubuntu_app.modules.keyboard_press_hold import PressHoldAccentsModule

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "macubuntu_app" / "assets" / "macubuntu_accent_engine.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location("macubuntu_accent_engine", ENGINE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AccentEngineTests(unittest.TestCase):
    def test_accent_tables_work_without_loading_ibus(self):
        engine = load_engine_module()
        self.assertEqual(engine.variants_for("e")[0], "è")
        self.assertIn("é", engine.variants_for("e"))
        self.assertIn("É", engine.variants_for("E"))
        self.assertIn("ñ", engine.variants_for("n"))
        self.assertEqual(engine.variants_for("q"), ())

    def test_bundled_engine_self_test(self):
        cp = subprocess.run(
            [sys.executable, str(ENGINE), "--self-test"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("macubuntu-accent-engine: ok", cp.stdout)

    def test_original_input_sources_are_never_removed(self):
        original = [("xkb", "it"), ("xkb", "us")]
        original_mru = [("xkb", "it")]
        sources, mru = PressHoldAccentsModule._merge_source_lists(original, original_mru)
        for source in original:
            self.assertIn(source, sources)
            self.assertIn(source, mru)
        self.assertEqual(sources[-1], PressHoldAccentsModule.INPUT_SOURCE)
        self.assertEqual(mru[0], PressHoldAccentsModule.INPUT_SOURCE)

    def test_source_merge_is_idempotent(self):
        source = PressHoldAccentsModule.INPUT_SOURCE
        sources, mru = PressHoldAccentsModule._merge_source_lists(
            [("xkb", "it"), source],
            [source, ("xkb", "it")],
        )
        self.assertEqual(sources.count(source), 1)
        self.assertEqual(mru.count(source), 1)

    def test_component_and_autostart_point_to_macubuntu_engine(self):
        module = PressHoldAccentsModule()
        xml = module._component_xml()
        desktop = module._autostart()
        self.assertIn("macubuntu-accents", xml)
        self.assertIn("Frapo78/MacUbuntu", xml)
        self.assertIn(str(module.engine_file), xml)
        self.assertIn(str(module.activation_file), desktop)
        self.assertIn("X-GNOME-Autostart-enabled=true", desktop)


if __name__ == "__main__":
    unittest.main()
