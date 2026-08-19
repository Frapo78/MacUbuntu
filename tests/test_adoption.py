import subprocess
import tempfile
import unittest
from pathlib import Path

from macubuntu_app.operations import uninstall_operations
from macubuntu_app.state import StateStore, default_state


class FlatpakAdoptionRunner:
    def exists(self, command):
        return command in {"flatpak", "dpkg-query", "sudo", "apt-get"}

    def run(self, args, *, check=True, capture=True, env=None):
        args = list(args)
        if args[:2] == ["dpkg-query", "-W"] and args[-1] == "flatpak":
            return subprocess.CompletedProcess(args, 0, stdout="ii ", stderr="")
        if args[:4] == ["flatpak", "--user", "list", "--app"]:
            return subprocess.CompletedProcess(args, 0, stdout="com.example.UserApp\n", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")


class AdoptionTests(unittest.TestCase):
    def test_flatpak_runtime_is_released_when_user_has_adopted_it(self):
        with tempfile.TemporaryDirectory() as td:
            store = StateStore(Path(td) / "state.json")
            state = default_state()
            state["operations"].append({"kind": "apt_bundle", "requested": ["flatpak"], "added": ["flatpak"]})
            results = uninstall_operations(runner=FlatpakAdoptionRunner(), store=store, state=state, app_version="test", force=False, dry_run=False)
            self.assertEqual(results[0]["status"], "released")
            self.assertEqual(results[0]["reason"], "flatpak_runtime_adopted_by_user")
            self.assertEqual(state["operations"], [])


if __name__ == "__main__":
    unittest.main()
