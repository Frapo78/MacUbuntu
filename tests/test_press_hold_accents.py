import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from macubuntu_app.modules.keyboard_accents_support import (
    LEGACY_SOURCE,
    migrate_legacy_input_source,
    parse_sources,
)
from macubuntu_app.modules.keyboard_press_hold import PressHoldAccentsModule

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "macubuntu_app" / "assets" / "macubuntu_accent_engine.py"


def load_engine_module():
    spec = importlib.util.spec_from_file_location("macubuntu_accent_engine", ENGINE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeStore:
    def __init__(self):
        self.saves = 0

    def save(self, _state, _version):
        self.saves += 1


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

    def test_standalone_engine_registers_live_component(self):
        source = ENGINE.read_text(encoding="utf-8")
        self.assertIn("bus.register_component(component)", source)
        self.assertIn("bus.request_name(SERVICE_NAME, 0)", source)
        self.assertIn("--standalone", source)

    def test_v061_does_not_advertise_an_english_keyboard(self):
        module = PressHoldAccentsModule()
        xml = module._component_xml()
        self.assertNotIn("<language>en</language>", xml)
        self.assertIn("<language>other</language>", xml)
        self.assertIn("<layout>default</layout>", xml)
        self.assertIn("--standalone --component", module._activation_script())
        self.assertNotIn("IBUS_COMPONENT_PATH", module._activation_script())

    def test_gvariant_source_prefix_is_supported(self):
        self.assertEqual(parse_sources("@a(ss) [('xkb', 'it')]") , [("xkb", "it")])

    def test_legacy_visible_source_is_removed_without_losing_other_keyboards(self):
        values = {
            "sources": "[('xkb', 'it'), ('ibus', 'macubuntu-accents'), ('xkb', 'us')]",
            "mru-sources": "[('ibus', 'macubuntu-accents'), ('xkb', 'it')]",
        }
        writes = {}
        state = {"operations": [
            {"kind": "gsettings", "schema": "org.gnome.desktop.input-sources", "key": "sources"},
            {"kind": "gsettings", "schema": "org.gnome.desktop.input-sources", "key": "mru-sources"},
            {"kind": "other"},
        ]}

        def fake_get(_runner, _schema, key):
            return values[key]

        def fake_set(_runner, _schema, key, value):
            writes[key] = value
            values[key] = value

        with patch("macubuntu_app.modules.keyboard_accents_support.gsettings_get", side_effect=fake_get), \
             patch("macubuntu_app.modules.keyboard_accents_support.gsettings_set", side_effect=fake_set):
            results = migrate_legacy_input_source(
                runner=object(), store=FakeStore(), state=state,
                app_version="0.6.1", dry_run=False,
            )

        self.assertEqual(writes["sources"], "[('xkb', 'it'), ('xkb', 'us')]")
        self.assertEqual(writes["mru-sources"], "[('xkb', 'it')]")
        self.assertEqual(state["operations"], [{"kind": "other"}])
        self.assertTrue(all(result["status"] == "legacy_source_removed" for result in results))
        self.assertNotIn(LEGACY_SOURCE, parse_sources(writes["sources"]))

    def test_bridge_is_xkb_only_and_respects_password_guard(self):
        for major in ("42", "46"):
            path = ROOT / "macubuntu_app" / "assets" / f"accent_bridge_gnome{major}.js"
            source = path.read_text(encoding="utf-8")
            self.assertIn("_disableIBus", source)
            self.assertIn("global-engine-changed", source)
            self.assertIn("macubuntu-accents", source)
            self.assertIn("xkb", source)


if __name__ == "__main__":
    unittest.main()
