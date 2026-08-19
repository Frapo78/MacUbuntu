import os
import subprocess
import unittest
from pathlib import Path

from macubuntu_app.i18n import Translator, detect_language

ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def run_cli(self, *args, env=None):
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run([str(ROOT / "macubuntu"), *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=merged_env)

    def test_help(self):
        cp = self.run_cli("--help")
        self.assertEqual(cp.returncode, 0)
        self.assertIn("doctor", cp.stdout)
        self.assertIn("macify", cp.stdout)
        self.assertIn("update", cp.stdout)
        self.assertIn("uninstall", cp.stdout)

    def test_doctor_help_is_localized(self):
        cp = self.run_cli("doctor", "--lang", "it", "--help")
        self.assertEqual(cp.returncode, 0)
        self.assertIn("output JSON stabile", cp.stdout)
        self.assertIn("mostra dettagli tecnici", cp.stdout)

    def test_update_help_is_localized(self):
        cp = self.run_cli("update", "--lang", "it", "--help")
        self.assertEqual(cp.returncode, 0)
        self.assertIn("controlla soltanto", cp.stdout)
        self.assertIn("--check", cp.stdout)

    def test_italian_help_can_be_selected(self):
        cp = self.run_cli("--lang", "it", "--help")
        self.assertEqual(cp.returncode, 0)
        self.assertIn("Trasforma Ubuntu GNOME", cp.stdout)
        self.assertIn("mostra dettagli tecnici", cp.stdout)

    def test_english_help_can_be_selected(self):
        cp = self.run_cli("--lang", "en", "--help")
        self.assertEqual(cp.returncode, 0)
        self.assertIn("Turn Ubuntu GNOME", cp.stdout)
        self.assertIn("show technical details", cp.stdout)

    def test_common_flags_work_after_subcommand(self):
        cp = self.run_cli("status", "--lang", "it", "--verbose", "--help")
        self.assertEqual(cp.returncode, 0)
        self.assertIn("mostra dettagli tecnici", cp.stdout)
        self.assertIn("lingua dell'interfaccia", cp.stdout)

    def test_locale_auto_selects_italian(self):
        previous = os.environ.get("LANG")
        previous_all = os.environ.pop("LC_ALL", None)
        previous_messages = os.environ.pop("LC_MESSAGES", None)
        try:
            os.environ["LANG"] = "it_IT.UTF-8"
            self.assertEqual(detect_language(), "it")
        finally:
            if previous is None:
                os.environ.pop("LANG", None)
            else:
                os.environ["LANG"] = previous
            if previous_all is not None:
                os.environ["LC_ALL"] = previous_all
            if previous_messages is not None:
                os.environ["LC_MESSAGES"] = previous_messages

    def test_translator_keeps_machine_independent_messages_separate(self):
        self.assertNotEqual(Translator("it")("plan_nothing"), Translator("en")("plan_nothing"))

    def test_failure_messages_are_localized(self):
        self.assertIn("operazione di sistema", Translator("it")("command_failed"))
        self.assertIn("system operation", Translator("en")("command_failed"))
        self.assertIn("salvare", Translator("it")("state_error_state_write_error"))

    def test_version(self):
        cp = self.run_cli("--version")
        self.assertEqual(cp.returncode, 0)
        self.assertIn("0.4.0", cp.stdout)


if __name__ == "__main__":
    unittest.main()
