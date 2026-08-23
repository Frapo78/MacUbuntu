from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from macubuntu_app.engine import Engine
from macubuntu_app.state import StateStore


class _Runner:
    pass


class _FailingModule:
    id = "test.fail"
    title = "Failing test module"

    def apply(self, **kwargs):
        raise RuntimeError("simulated interruption")


class _ReceiptModule:
    id = "test.receipt"
    title = "Receipt test module"

    def apply(self, **kwargs):
        state = kwargs["state"]
        state["operations"].append({"kind": "test", "resource": "owned"})
        kwargs["store"].save(state, kwargs["app_version"])
        return [{"kind": "test", "resource": "owned", "status": "changed"}]


class EngineTransactionTests(unittest.TestCase):
    def make_engine(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        store = StateStore(Path(temp.name) / "state.json")
        return Engine(runner=_Runner(), store=store), store

    def test_failed_apply_leaves_durable_recovery_marker(self):
        engine, store = self.make_engine()
        audit = {"support": {"level": "supported"}}

        with patch("macubuntu_app.engine.audit_system", return_value=audit), patch(
            "macubuntu_app.engine.ALL_MODULES", [_FailingModule()]
        ):
            with self.assertRaises(RuntimeError):
                engine.apply()

        health = store.health()
        self.assertFalse(health["ok"])
        self.assertEqual(health["status"], "transaction_interrupted")
        self.assertEqual(health["transaction"]["operation"], "apply")

    def test_successful_apply_commits_after_receipt_persistence(self):
        engine, store = self.make_engine()
        audit = {"support": {"level": "supported"}}

        with patch("macubuntu_app.engine.audit_system", return_value=audit), patch(
            "macubuntu_app.engine.ALL_MODULES", [_ReceiptModule()]
        ):
            result = engine.apply()

        state = store.load()
        self.assertTrue(result["ok"])
        self.assertIsNone(state["transaction"])
        self.assertEqual(len(state["operations"]), 1)
        self.assertEqual(state["last_transaction"]["status"], "committed")
        self.assertEqual(state["last_transaction"]["final_operation_count"], 1)

    def test_dry_run_does_not_create_transaction_state(self):
        engine, store = self.make_engine()
        audit = {"support": {"level": "supported"}}

        with patch("macubuntu_app.engine.audit_system", return_value=audit), patch(
            "macubuntu_app.engine.ALL_MODULES", []
        ):
            engine.apply(dry_run=True)

        self.assertFalse(store.path.exists())


if __name__ == "__main__":
    unittest.main()
