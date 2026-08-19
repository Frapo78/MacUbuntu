import json
import tempfile
import unittest
from pathlib import Path

from macubuntu_app.state import (
    StateCorruptError,
    StateStore,
    StateValidationError,
    default_state,
)


class StateResilienceTests(unittest.TestCase):
    def test_corrupt_state_is_reported_without_being_replaced(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            path.write_text("{broken", encoding="utf-8")
            store = StateStore(path)

            with self.assertRaises(StateCorruptError):
                store.load()

            health = store.health()
            self.assertFalse(health["ok"])
            self.assertEqual(health["status"], "state_corrupt")
            self.assertEqual(path.read_text(encoding="utf-8"), "{broken")

    def test_invalid_operations_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            path.write_text(json.dumps({"schema_version": 1, "operations": "wrong"}), encoding="utf-8")
            store = StateStore(path)
            with self.assertRaises(StateValidationError):
                store.load()

    def test_second_save_keeps_last_known_good_backup(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            store = StateStore(path)
            state = default_state()
            store.save(state, "0.3.0")
            self.assertFalse(store.backup_path.exists())

            state = store.load()
            state["profile"]["applied"] = True
            store.save(state, "0.3.0")

            self.assertTrue(store.backup_path.exists())
            backup = json.loads(store.backup_path.read_text(encoding="utf-8"))
            self.assertFalse(backup["profile"]["applied"])
            self.assertTrue(store.load()["profile"]["applied"])

    def test_save_refuses_to_overwrite_corrupt_existing_state(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "state.json"
            path.write_text("not-json", encoding="utf-8")
            store = StateStore(path)
            with self.assertRaises(StateCorruptError):
                store.save(default_state(), "0.3.0")
            self.assertEqual(path.read_text(encoding="utf-8"), "not-json")


if __name__ == "__main__":
    unittest.main()
