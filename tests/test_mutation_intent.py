import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from macubuntu_app.operations import apply_apt_bundle, apply_gsetting
from macubuntu_app.state import (
    StateStore,
    StateValidationError,
    default_state,
    privacy_safe_state,
)


class FakeRunner:
    def __init__(self):
        self.installed: set[str] = set()

    def exists(self, _name):
        return True

    def run(self, cmd, **_kwargs):
        if "install" in cmd:
            self.installed.update(item for item in cmd if item not in {"apt-get", "install", "-y"})
        return SimpleNamespace(returncode=0, stdout="", stderr="")


class RecordingStore(StateStore):
    def __init__(self, path):
        super().__init__(path)
        self.events: list[tuple[str, str | None]] = []

    def prepare_mutation(self, *args, **kwargs):
        self.events.append(("prepare", kwargs["kind"]))
        return super().prepare_mutation(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.events.append(("save", None))
        return super().save(*args, **kwargs)

    def clear_pending_mutation(self, *args, **kwargs):
        self.events.append(("clear", None))
        return super().clear_pending_mutation(*args, **kwargs)


class MutationIntentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = RecordingStore(Path(self.tmp.name) / "state.json")
        self.state = default_state()
        self.store.begin_transaction(self.state, "0.6.0", "apply")
        self.runner = FakeRunner()

    def tearDown(self):
        self.tmp.cleanup()

    def test_prepare_is_durable_and_commit_rejects_pending_mutation(self):
        pending = self.store.prepare_mutation(
            self.state,
            "0.6.0",
            kind="gsettings_set",
            resource="org.example::key",
            evidence={"before": "'a'", "desired": "'b'"},
        )
        loaded = self.store.load()
        self.assertEqual(loaded["transaction"]["pending_mutation"]["id"], pending["id"])
        with self.assertRaises(StateValidationError):
            self.store.commit_transaction(self.state, "0.6.0")

    def test_clear_requires_same_mutation_identity_then_allows_commit(self):
        pending = self.store.prepare_mutation(self.state, "0.6.0", kind="apt_install")
        with self.assertRaises(StateValidationError):
            self.store.clear_pending_mutation(self.state, "0.6.0", mutation_id="other")
        self.store.clear_pending_mutation(self.state, "0.6.0", mutation_id=pending["id"])
        committed = self.store.commit_transaction(self.state, "0.6.0")
        self.assertEqual(committed["status"], "committed")
        self.assertNotIn("pending_mutation", committed)

    def test_health_and_public_state_do_not_expose_pending_evidence(self):
        self.store.prepare_mutation(
            self.state,
            "0.6.0",
            kind="gsettings_set",
            resource="org.example::wallpaper",
            evidence={"before": "'file:///home/alice/private.jpg'", "desired": "'x'"},
        )
        health = self.store.health()
        public = privacy_safe_state(self.state)
        self.assertEqual(health["status"], "transaction_interrupted")
        self.assertEqual(health["transaction"]["pending_mutation"]["kind"], "gsettings_set")
        self.assertNotIn("alice", str(health))
        self.assertNotIn("alice", str(public))
        self.assertNotIn("evidence", str(public["transaction"]["pending_mutation"]))

    @patch("macubuntu_app.operations.gsettings_get", return_value="'file:///home/alice/private.jpg'")
    @patch("macubuntu_app.operations.gsettings_set")
    def test_gsettings_journal_is_persisted_before_mutation_hashes_values_and_clears_after_receipt(self, set_value, _get_value):
        self.store.events.clear()

        def assert_intent_precedes_mutation(*_args):
            self.assertEqual(self.store.events[0], ("prepare", "gsettings_set"))
            pending = self.state["transaction"]["pending_mutation"]
            evidence = pending["evidence"]
            self.assertEqual(set(evidence), {"before_sha256", "desired_sha256"})
            self.assertEqual(len(evidence["before_sha256"]), 64)
            self.assertNotIn("alice", str(evidence))

        set_value.side_effect = assert_intent_precedes_mutation
        result = apply_gsetting(
            runner=self.runner,
            store=self.store,
            state=self.state,
            app_version="0.6.0",
            schema="org.example",
            key="wallpaper",
            desired="'file:///tmp/macubuntu.jpg'",
            dry_run=False,
        )
        self.assertEqual(result["status"], "changed")
        self.assertIn(("clear", None), self.store.events)
        self.assertIsNone(self.state["transaction"]["pending_mutation"])

    def test_apt_install_journal_records_pre_install_missing_set(self):
        self.store.events.clear()
        with patch(
            "macubuntu_app.operations.package_installed",
            side_effect=lambda _runner, package: package in self.runner.installed,
        ), patch(
            "macubuntu_app.operations.installed_deb_packages",
            side_effect=lambda _runner: set(self.runner.installed),
        ), patch(
            "macubuntu_app.operations.apt_base_command",
            return_value=["apt-get"],
        ):
            result = apply_apt_bundle(
                runner=self.runner,
                store=self.store,
                state=self.state,
                app_version="0.6.0",
                requested=["alpha", "beta"],
                dry_run=False,
            )
        self.assertEqual(result["status"], "installed")
        self.assertEqual(self.store.events[0], ("prepare", "apt_install"))
        self.assertEqual(self.state["operations"][0]["added"], ["alpha", "beta"])
        self.assertIsNone(self.state["transaction"]["pending_mutation"])


if __name__ == "__main__":
    unittest.main()
