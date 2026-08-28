import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from macubuntu_app.external_packages import (
    apply_apt_repository,
    apply_flatpak_app,
    apply_flatpak_remote,
    apply_service_state,
)
from macubuntu_app.state import StateStore, default_state, privacy_safe_state


class RecordingStore(StateStore):
    def __init__(self, path):
        super().__init__(path)
        self.events = []

    def prepare_mutation(self, *args, **kwargs):
        self.events.append(("prepare", kwargs["kind"]))
        return super().prepare_mutation(*args, **kwargs)

    def clear_pending_mutation(self, *args, **kwargs):
        self.events.append(("clear", None))
        return super().clear_pending_mutation(*args, **kwargs)


class FakeRunner:
    def __init__(self):
        self.commands = []

    def run(self, cmd, **_kwargs):
        self.commands.append(list(cmd))
        if "cat" in cmd:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if "is-enabled" in cmd:
            return SimpleNamespace(returncode=1, stdout="disabled\n", stderr="")
        if "is-active" in cmd:
            return SimpleNamespace(returncode=1, stdout="inactive\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")


class ExternalMutationIntentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = RecordingStore(Path(self.tmp.name) / "state.json")
        self.state = default_state()
        self.store.begin_transaction(self.state, "0.6.0", "apply")
        self.store.events.clear()
        self.runner = FakeRunner()

    def tearDown(self):
        self.tmp.cleanup()

    def _assert_finished(self, kind):
        self.assertEqual(self.store.events[0], ("prepare", kind))
        self.assertIn(("clear", None), self.store.events)
        self.assertIsNone(self.state["transaction"]["pending_mutation"])

    @patch("macubuntu_app.external_packages.apt_repository_present", return_value=False)
    @patch("macubuntu_app.external_packages.apt_base_command", return_value=["apt-get"])
    def test_apt_repository_intent_precedes_mutation(self, _apt, _present):
        apply_apt_repository(
            runner=self.runner, store=self.store, state=self.state, app_version="0.6.0",
            ppa="ppa:example/stable", dry_run=False,
        )
        self._assert_finished("apt_repository_add")
        self.assertEqual(self.state["operations"][0]["kind"], "apt_repository")

    @patch("macubuntu_app.external_packages._flatpak_remote_exists", return_value=False)
    def test_flatpak_remote_intent_precedes_mutation(self, _exists):
        apply_flatpak_remote(
            runner=self.runner, store=self.store, state=self.state, app_version="0.6.0",
            name="flathub", url="https://example.invalid/remote", dry_run=False,
        )
        self._assert_finished("flatpak_remote_add")

    @patch("macubuntu_app.external_packages._flatpak_app_installed", return_value=False)
    def test_flatpak_app_intent_precedes_mutation(self, _installed):
        apply_flatpak_app(
            runner=self.runner, store=self.store, state=self.state, app_version="0.6.0",
            remote="flathub", app_id="org.example.App", dry_run=False,
        )
        self._assert_finished("flatpak_app_install")

    def test_service_intent_records_original_state(self):
        apply_service_state(
            runner=self.runner, store=self.store, state=self.state, app_version="0.6.0",
            unit="example.service", user=True, dry_run=False,
        )
        self._assert_finished("service_enable_start")
        receipt = self.state["operations"][0]
        self.assertFalse(receipt["original_enabled"])
        self.assertFalse(receipt["original_active"])

    @patch("macubuntu_app.external_packages._flatpak_app_installed", return_value=False)
    def test_failed_external_mutation_keeps_durable_pending_intent(self, _installed):
        def fail_install(cmd, **_kwargs):
            if "install" in cmd:
                raise RuntimeError("simulated crash boundary")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        self.runner.run = fail_install
        with self.assertRaises(RuntimeError):
            apply_flatpak_app(
                runner=self.runner, store=self.store, state=self.state, app_version="0.6.0",
                remote="flathub", app_id="org.example.App", dry_run=False,
            )
        loaded = self.store.load()
        pending = loaded["transaction"]["pending_mutation"]
        self.assertEqual(pending["kind"], "flatpak_app_install")
        public = privacy_safe_state(loaded)
        self.assertNotIn("evidence", public["transaction"]["pending_mutation"])


if __name__ == "__main__":
    unittest.main()
