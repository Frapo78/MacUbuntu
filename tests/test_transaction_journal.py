from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from macubuntu_app.state import StateStore, StateValidationError, default_state


class TransactionJournalTests(unittest.TestCase):
    def make_store(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return StateStore(Path(temp.name) / "state.json")

    def test_begin_transaction_is_persisted_before_mutation(self):
        store = self.make_store()
        state = default_state()

        transaction = store.begin_transaction(state, "0.test", "apply")
        persisted = store.load()

        self.assertEqual(persisted["transaction"]["id"], transaction["id"])
        self.assertEqual(persisted["transaction"]["status"], "in_progress")
        self.assertEqual(persisted["transaction"]["operation"], "apply")
        self.assertEqual(persisted["transaction"]["baseline_operation_count"], 0)
        self.assertEqual(state["transaction"]["id"], transaction["id"])

    def test_health_fails_closed_for_interrupted_transaction(self):
        store = self.make_store()
        state = default_state()
        store.begin_transaction(state, "0.test", "uninstall")

        health = store.health()

        self.assertFalse(health["ok"])
        self.assertEqual(health["status"], "transaction_interrupted")
        self.assertEqual(health["transaction"]["operation"], "uninstall")
        self.assertEqual(health["operation_count"], 0)

    def test_commit_moves_active_transaction_to_last_transaction(self):
        store = self.make_store()
        state = default_state()
        active = store.begin_transaction(state, "0.test", "macify")
        state["operations"].append({"kind": "test"})

        committed = store.commit_transaction(state, "0.test")
        persisted = store.load()

        self.assertIsNone(persisted["transaction"])
        self.assertEqual(persisted["last_transaction"]["id"], active["id"])
        self.assertEqual(persisted["last_transaction"]["status"], "committed")
        self.assertEqual(persisted["last_transaction"]["baseline_operation_count"], 0)
        self.assertEqual(persisted["last_transaction"]["final_operation_count"], 1)
        self.assertEqual(committed, persisted["last_transaction"])
        self.assertTrue(store.health()["ok"])

    def test_second_transaction_is_rejected_while_one_is_active(self):
        store = self.make_store()
        state = default_state()
        store.begin_transaction(state, "0.test", "apply")

        with self.assertRaises(StateValidationError):
            store.begin_transaction(state, "0.test", "uninstall")

    def test_legacy_schema_one_state_without_transaction_fields_is_accepted(self):
        store = self.make_store()
        store.path.parent.mkdir(parents=True, exist_ok=True)
        store.path.write_text(
            '{"schema_version":1,"profile":{},"operations":[]}',
            encoding="utf-8",
        )

        state = store.load()

        self.assertIsNone(state["transaction"])
        self.assertIsNone(state["last_transaction"])


if __name__ == "__main__":
    unittest.main()
