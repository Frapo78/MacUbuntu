import hashlib
import unittest
from unittest.mock import patch

from macubuntu_app.recovery import _probe_pending_mutation, inspect_recovery


class FakeRunner:
    pass


class FakeStore:
    def __init__(self, state):
        self.state = state

    def health(self):
        return {"status": "transaction_interrupted"}

    def load(self):
        return self.state

    def load_backup(self):
        return {"operations": []}


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def transaction(pending):
    return {
        "id": "run-1",
        "operation": "apply",
        "status": "in_progress",
        "started_at": "now",
        "app_version": "0.6",
        "baseline_operation_count": 0,
        "pending_mutation": pending,
    }


class PendingRecoveryTests(unittest.TestCase):
    @patch("macubuntu_app.recovery.gsettings_get", return_value="'b'")
    def test_pending_gsettings_set_detects_applied_target(self, _get):
        pending = {
            "id": "mutation-1",
            "kind": "gsettings_set",
            "resource": "org.example::key",
            "evidence": {
                "before_sha256": digest("'a'"),
                "desired_sha256": digest("'b'"),
            },
        }
        out = inspect_recovery(
            FakeRunner(),
            FakeStore({"transaction": transaction(pending), "operations": []}),
        )
        self.assertEqual(out["pending_mutation"]["status"], "applied")
        self.assertEqual(out["reason"], "pending_mutation_requires_recovery")
        self.assertFalse(out["automatic_mutation"])

    @patch("macubuntu_app.recovery.gsettings_get", return_value="'a'")
    def test_pending_gsettings_restore_detects_applied_original(self, _get):
        pending = {
            "id": "mutation-2",
            "kind": "gsettings_restore",
            "resource": "org.example::key",
            "evidence": {
                "before_sha256": digest("'b'"),
                "original_sha256": digest("'a'"),
            },
        }
        out = _probe_pending_mutation(FakeRunner(), pending)
        self.assertEqual(out["status"], "applied")

    @patch("macubuntu_app.recovery.gsettings_get", return_value="'c'")
    def test_pending_gsettings_drift_is_fail_closed(self, _get):
        pending = {
            "id": "mutation-3",
            "kind": "gsettings_set",
            "resource": "org.example::key",
            "evidence": {
                "before_sha256": digest("'a'"),
                "desired_sha256": digest("'b'"),
            },
        }
        out = inspect_recovery(
            FakeRunner(),
            FakeStore({"transaction": transaction(pending), "operations": []}),
        )
        self.assertEqual(out["pending_mutation"]["status"], "drifted")
        self.assertEqual(out["classification"], "no_receipted_mutations")
        self.assertFalse(out["automatic_mutation"])

    @patch("macubuntu_app.recovery.package_installed", return_value=True)
    def test_pending_apt_install_detects_applied(self, _installed):
        pending = {
            "id": "mutation-4",
            "kind": "apt_install",
            "resource": "a,b",
            "evidence": {"missing_before": ["a", "b"]},
        }
        out = _probe_pending_mutation(FakeRunner(), pending)
        self.assertEqual(out["status"], "applied")
        self.assertEqual(out["packages_present"], 2)

    @patch("macubuntu_app.recovery.package_installed", side_effect=lambda _runner, package: package == "a")
    def test_pending_apt_install_detects_partial(self, _installed):
        pending = {
            "id": "mutation-5",
            "kind": "apt_install",
            "resource": "a,b",
            "evidence": {"missing_before": ["a", "b"]},
        }
        out = _probe_pending_mutation(FakeRunner(), pending)
        self.assertEqual(out["status"], "partial")

    @patch("macubuntu_app.recovery.package_installed", return_value=False)
    def test_pending_apt_purge_detects_applied(self, _installed):
        pending = {
            "id": "mutation-6",
            "kind": "apt_purge",
            "resource": "a,b",
            "evidence": {"packages_present_before": ["a", "b"]},
        }
        out = _probe_pending_mutation(FakeRunner(), pending)
        self.assertEqual(out["status"], "applied")
        self.assertEqual(out["packages_present"], 0)

    def test_unknown_pending_kind_does_not_leak_private_fields(self):
        pending = {
            "id": "mutation-7",
            "kind": "future_external_kind",
            "resource": "/home/alice/private",
            "evidence": {"command": "token=secret"},
        }
        out = _probe_pending_mutation(FakeRunner(), pending)
        rendered = str(out)
        self.assertEqual(out["status"], "unverifiable")
        self.assertEqual(out["reason"], "probe_not_implemented")
        self.assertNotIn("alice", rendered)
        self.assertNotIn("token=secret", rendered)


if __name__ == "__main__":
    unittest.main()
