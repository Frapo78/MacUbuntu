import unittest
from types import SimpleNamespace
from unittest.mock import ANY, patch

from macubuntu_app.recovery import _probe_receipt, inspect_recovery


class FakeRunner:
    def __init__(self, enabled="enabled", active="active"):
        self.enabled = enabled
        self.active = active

    def run(self, cmd, check=False):
        if "is-enabled" in cmd:
            return SimpleNamespace(stdout=self.enabled + "\n", returncode=0)
        if "is-active" in cmd:
            return SimpleNamespace(stdout=self.active + "\n", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)


class FakeStore:
    def __init__(self, state, backup=None, health_status="transaction_interrupted", backup_error=None):
        self.state = state
        self.backup = backup
        self.health_status = health_status
        self.backup_error = backup_error

    def health(self):
        return {"status": self.health_status}

    def load(self):
        return self.state

    def load_backup(self):
        if self.backup_error:
            raise self.backup_error
        return self.backup


def transaction(baseline=0):
    return {
        "id": "run-1",
        "operation": "apply",
        "status": "in_progress",
        "started_at": "now",
        "app_version": "0.6",
        "baseline_operation_count": baseline,
    }


class RecoveryTests(unittest.TestCase):
    def test_no_recovery_needed(self):
        out = inspect_recovery(FakeRunner(), FakeStore({}, health_status="ok"))
        self.assertTrue(out["ok"])
        self.assertFalse(out["required"])
        self.assertEqual(out["status"], "none")

    @patch("macubuntu_app.recovery.gsettings_get", return_value="'b'")
    def test_gsetting_applied_is_consistent_evidence(self, _get):
        op = {
            "kind": "gsettings",
            "schema": "org.example",
            "key": "x",
            "original": "'a'",
            "applied": "'b'",
        }
        out = inspect_recovery(
            FakeRunner(),
            FakeStore({"transaction": transaction(), "operations": [op]}, {"operations": []}),
        )
        self.assertEqual(out["status"], "transaction_interrupted")
        self.assertEqual(out["classification"], "receipts_consistent")
        self.assertEqual(out["evidence"][0]["status"], "applied")
        self.assertFalse(out["automatic_mutation"])

    @patch("macubuntu_app.recovery.gsettings_get", return_value="'c'")
    def test_gsetting_drift_is_inconsistent(self, _get):
        op = {
            "kind": "gsettings",
            "schema": "org.example",
            "key": "x",
            "original": "'a'",
            "applied": "'b'",
        }
        out = inspect_recovery(
            FakeRunner(),
            FakeStore({"transaction": transaction(), "operations": [op]}),
        )
        self.assertEqual(out["classification"], "inconsistent")
        self.assertEqual(out["evidence"][0]["status"], "drifted")

    @patch("macubuntu_app.recovery.package_installed", side_effect=lambda _runner, package: package == "a")
    def test_apt_partial_is_inconsistent(self, _installed):
        op = {"kind": "apt_bundle", "requested": ["a", "b"], "added": ["a", "b"]}
        out = inspect_recovery(
            FakeRunner(),
            FakeStore({"transaction": transaction(), "operations": [op]}),
        )
        self.assertEqual(out["evidence"][0]["status"], "partial")
        self.assertEqual(out["classification"], "inconsistent")

    @patch("macubuntu_app.recovery.gsettings_get", return_value="2")
    def test_only_receipts_after_transaction_baseline_are_inspected(self, get_value):
        old = {"kind": "gsettings", "schema": "old", "key": "k", "original": "1", "applied": "2"}
        new = {"kind": "gsettings", "schema": "new", "key": "k", "original": "1", "applied": "2"}
        out = inspect_recovery(
            FakeRunner(),
            FakeStore(
                {"transaction": transaction(1), "operations": [old, new]},
                {"operations": [old]},
            ),
        )
        self.assertEqual(out["counts"]["transaction_receipts"], 1)
        self.assertEqual(out["evidence"][0]["resource"], "new::k")
        get_value.assert_called_once_with(ANY, "new", "k")

    def test_unknown_receipt_does_not_leak_arbitrary_fields(self):
        op = {
            "kind": "managed_file",
            "path": "/home/alice/secret",
            "command": "token=secret",
        }
        out = inspect_recovery(
            FakeRunner(),
            FakeStore({"transaction": transaction(), "operations": [op]}),
        )
        rendered = str(out)
        self.assertNotIn("alice", rendered)
        self.assertNotIn("token=secret", rendered)
        self.assertEqual(out["evidence"][0]["reason"], "probe_not_implemented")

    def test_invalid_backup_is_reported_without_mutation(self):
        out = inspect_recovery(
            FakeRunner(),
            FakeStore(
                {"transaction": transaction(), "operations": []},
                backup_error=RuntimeError("broken backup"),
            ),
        )
        self.assertEqual(out["backup"]["status"], "invalid")
        self.assertFalse(out["automatic_mutation"])

    def test_no_receipts_still_requires_manual_review(self):
        out = inspect_recovery(
            FakeRunner(),
            FakeStore({"transaction": transaction(), "operations": []}, {"operations": []}),
        )
        self.assertEqual(out["status"], "transaction_interrupted")
        self.assertEqual(out["classification"], "no_receipted_mutations")
        self.assertEqual(out["decision"], "manual_review")

    @patch("macubuntu_app.recovery._tree_digest", side_effect=["abc", "abc"])
    def test_owned_paths_applied_without_path_leak(self, _digest):
        op = {
            "kind": "owned_paths",
            "resource": "theme",
            "paths": [
                {"path": "/home/alice/.local/a", "digest": "abc"},
                {"path": "/home/alice/.local/b", "digest": "abc"},
            ],
        }
        out = _probe_receipt(FakeRunner(), op, 0)
        self.assertEqual(out["status"], "applied")
        self.assertEqual(out["managed_paths"], 2)
        self.assertNotIn("alice", str(out))

    @patch("macubuntu_app.recovery._tree_digest", side_effect=["abc", "missing"])
    def test_owned_paths_partial_is_inconsistent(self, _digest):
        op = {
            "kind": "owned_paths",
            "paths": [
                {"path": "/tmp/a", "digest": "abc"},
                {"path": "/tmp/b", "digest": "abc"},
            ],
        }
        out = inspect_recovery(
            FakeRunner(),
            FakeStore({"transaction": transaction(), "operations": [op]}),
        )
        self.assertEqual(out["evidence"][0]["status"], "partial")
        self.assertEqual(out["classification"], "inconsistent")

    @patch("macubuntu_app.recovery.apt_repository_present", return_value=True)
    def test_apt_repository_applied(self, _present):
        out = _probe_receipt(FakeRunner(), {"kind": "apt_repository", "ppa": "ppa:owner/archive"}, 0)
        self.assertEqual(out["status"], "applied")

    @patch("macubuntu_app.recovery._flatpak_remote_exists", return_value=False)
    def test_flatpak_remote_absent_is_original(self, _present):
        out = _probe_receipt(FakeRunner(), {"kind": "flatpak_remote", "resource": "flathub"}, 0)
        self.assertEqual(out["status"], "original")

    @patch("macubuntu_app.recovery._flatpak_app_installed", return_value=True)
    def test_flatpak_app_present_is_applied(self, _present):
        out = _probe_receipt(FakeRunner(), {"kind": "flatpak_app", "resource": "org.example.App"}, 0)
        self.assertEqual(out["status"], "applied")

    @patch("macubuntu_app.recovery._enabled_extensions", return_value=["test@example"])
    @patch("macubuntu_app.recovery._tree_digest", return_value="good")
    def test_owned_extension_applied_without_path_leak(self, _digest, _enabled):
        op = {
            "kind": "gnome_extension",
            "resource": "test@example",
            "installed_by_macubuntu": True,
            "path": "/home/alice/.local/share/gnome-shell/extensions/test@example",
            "digest": "good",
        }
        out = _probe_receipt(FakeRunner(), op, 0)
        self.assertEqual(out["status"], "applied")
        self.assertNotIn("/home/alice", str(out))

    @patch("macubuntu_app.recovery._enabled_extensions", return_value=[])
    @patch("macubuntu_app.recovery._tree_digest", return_value="good")
    def test_owned_extension_disabled_with_matching_files_is_partial(self, _digest, _enabled):
        op = {
            "kind": "gnome_extension",
            "resource": "test@example",
            "installed_by_macubuntu": True,
            "path": "/tmp/test@example",
            "digest": "good",
        }
        out = _probe_receipt(FakeRunner(), op, 0)
        self.assertEqual(out["status"], "partial")

    def test_service_partial_state_is_detected_without_sudo(self):
        op = {
            "kind": "service",
            "unit": "example.service",
            "user": False,
            "original_enabled": False,
            "original_active": False,
            "applied_enabled": True,
            "applied_active": True,
        }
        runner = FakeRunner(enabled="enabled", active="inactive")
        out = _probe_receipt(runner, op, 0)
        self.assertEqual(out["status"], "partial")
        self.assertEqual(out["resource"], "system:example.service")


if __name__ == "__main__":
    unittest.main()
