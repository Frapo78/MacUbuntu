import tempfile
import unittest
from pathlib import Path

from macubuntu_app.operations import uninstall_operations
from macubuntu_app.state import StateStore


class FakeRunner:
    def __init__(self, current=None):
        self.current = current or {}
        self.sets = []

    def exists(self, command):
        return command in {"gsettings", "dpkg-query", "apt-get", "sudo"}

    def run(self, args, check=True, capture=True, env=None):
        class CP:
            returncode = 0
            stdout = ""
            stderr = ""
        cp = CP()
        if args[:2] == ["gsettings", "list-schemas"]:
            cp.stdout = "\n".join(sorted({s for s, _ in self.current}))
        elif len(args) >= 3 and args[:2] == ["gsettings", "list-keys"]:
            schema = args[2]
            cp.stdout = "\n".join(k for s, k in self.current if s == schema)
        elif len(args) >= 4 and args[:2] == ["gsettings", "get"]:
            cp.stdout = self.current[(args[2], args[3])] + "\n"
        elif len(args) >= 5 and args[:2] == ["gsettings", "set"]:
            self.current[(args[2], args[3])] = args[4]
            self.sets.append((args[2], args[3], args[4]))
        elif "dpkg-query" in args[0]:
            cp.returncode = 1
        return cp


class ReceiptTests(unittest.TestCase):
    def test_safe_uninstall_restores_unmodified_setting(self):
        with tempfile.TemporaryDirectory() as td:
            store = StateStore(Path(td) / "state.json")
            state = {"schema_version": 1, "operations": [{"kind": "gsettings", "schema": "org.example", "key": "demo", "original": "'before'", "applied": "'after'"}]}
            runner = FakeRunner({("org.example", "demo"): "'after'"})
            results = uninstall_operations(runner=runner, store=store, state=state, app_version="0.1.0", force=False, dry_run=False)
            self.assertEqual(results[0]["status"], "restored")
            self.assertEqual(runner.current[("org.example", "demo")], "'before'")

    def test_safe_uninstall_protects_drift(self):
        with tempfile.TemporaryDirectory() as td:
            store = StateStore(Path(td) / "state.json")
            state = {"schema_version": 1, "operations": [{"kind": "gsettings", "schema": "org.example", "key": "demo", "original": "'before'", "applied": "'after'"}]}
            runner = FakeRunner({("org.example", "demo"): "'user-choice'"})
            results = uninstall_operations(runner=runner, store=store, state=state, app_version="0.1.0", force=False, dry_run=False)
            self.assertEqual(results[0]["status"], "kept")
            self.assertEqual(results[0]["reason"], "drift_detected")
            self.assertEqual(runner.current[("org.example", "demo")], "'user-choice'")


if __name__ == "__main__":
    unittest.main()
