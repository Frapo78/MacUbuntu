import unittest

from macubuntu_app.recovery import inspect_recovery


class FakeRunner:
    def __init__(self, gsettings=None, packages=None):
        self.gsettings = gsettings or {}
        self.packages = set(packages or [])


class FakeStore:
    def __init__(self, state, backup=None, health_status="transaction_interrupted", backup_error=None):
        self.state = state
        self.backup = backup
        self.health_status = health_status
        self.backup_error = backup_error

        class BackupPath:
            def __init__(self, exists):
                self._exists = exists

            def exists(self):
                return self._exists

        self.backup_path = BackupPath(backup is not None or backup_error is not None)

    def health(self):
        return {"status": self.health_status}

    def load(self):
        return self.state

    def _read_path(self, path):
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

    def test_gsetting_applied_is_consistent_evidence(self):
        op = {
            "kind": "gsettings",
            "schema": "org.example",
            "key": "x",
            "original": "'a'",
            "applied": "'b'",
        }
        out = inspect_recovery(
            FakeRunner({("org.example", "x"): "'b'"}),
            FakeStore({"transaction": transaction(), "operations": [op]}, {"operations": []}),
        )
        self.assertEqual(out["status"], "receipts_consistent")
        self.assertEqual(out["evidence"][0]["status"], "applied")
        self.assertFalse(out["automatic_mutation"])

    def test_gsetting_drift_is_inconsistent(self):
        op = {
            "kind": "gsettings",
            "schema": "org.example",
            "key": "x",
            "original": "'a'",
            "applied": "'b'",
        }
        out = inspect_recovery(
            FakeRunner({("org.example", "x"): "'c'"}),
            FakeStore({"transaction": transaction(), "operations": [op]}),
        )
        self.assertEqual(out["status"], "inconsistent")
        self.assertEqual(out["evidence"][0]["status"], "drifted")

    def test_apt_partial_is_inconsistent(self):
        op = {"kind": "apt_bundle", "requested": ["a", "b"], "added": ["a", "b"]}
        out = inspect_recovery(
            FakeRunner(packages={"a"}),
            FakeStore({"transaction": transaction(), "operations": [op]}),
        )
        self.assertEqual(out["evidence"][0]["status"], "partial")
        self.assertEqual(out["status"], "inconsistent")

    def test_only_receipts_after_transaction_baseline_are_inspected(self):
        old = {"kind": "gsettings", "schema": "old", "key": "k", "original": "1", "applied": "2"}
        new = {"kind": "gsettings", "schema": "new", "key": "k", "original": "1", "applied": "2"}
        out = inspect_recovery(
            FakeRunner({("new", "k"): "2"}),
            FakeStore(
                {"transaction": transaction(1), "operations": [old, new]},
                {"operations": [old]},
            ),
        )
        self.assertEqual(out["counts"]["transaction_receipts"], 1)
        self.assertEqual(out["evidence"][0]["resource"], "new::k")

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

    def test_no_receipts_still_requires_manual_review(self):
        out = inspect_recovery(
            FakeRunner(),
            FakeStore({"transaction": transaction(), "operations": []}, {"operations": []}),
        )
        self.assertEqual(out["status"], "no_receipted_mutations")
        self.assertEqual(out["decision"], "manual_review")


if __name__ == "__main__":
    unittest.main()
