import subprocess
import unittest

from macubuntu_app.external import apply_flatpak_app
from macubuntu_app.operations import apply_gsetting
from macubuntu_app.state import default_state


class FailingStore:
    def save(self, state, app_version):
        raise RuntimeError("state write failed")


class GSettingsRunner:
    def __init__(self): self.value = "false"
    def exists(self, command): return command == "gsettings"
    def run(self, args, *, check=True, capture=True, env=None):
        args = list(args)
        if args[:2] == ["gsettings", "list-schemas"]: return subprocess.CompletedProcess(args, 0, stdout="org.example\n", stderr="")
        if args[:3] == ["gsettings", "list-keys", "org.example"]: return subprocess.CompletedProcess(args, 0, stdout="enabled\n", stderr="")
        if args[:4] == ["gsettings", "get", "org.example", "enabled"]: return subprocess.CompletedProcess(args, 0, stdout=self.value + "\n", stderr="")
        if args[:4] == ["gsettings", "set", "org.example", "enabled"]:
            self.value = args[4]; return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(args, 1, stdout="", stderr="unexpected")


class FlatpakRunner:
    def __init__(self): self.installed = False
    def exists(self, command): return command == "flatpak"
    def run(self, args, *, check=True, capture=True, env=None):
        args = list(args)
        if args[:3] == ["flatpak", "--user", "info"]:
            return subprocess.CompletedProcess(args, 0 if self.installed else 1, stdout="", stderr="")
        if args[:4] == ["flatpak", "--user", "install", "-y"]:
            self.installed = True; return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[:4] == ["flatpak", "--user", "uninstall", "-y"]:
            self.installed = False; return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")


class ReceiptRollbackTests(unittest.TestCase):
    def test_gsetting_is_restored_when_receipt_cannot_be_saved(self):
        runner = GSettingsRunner(); state = default_state()
        with self.assertRaises(RuntimeError):
            apply_gsetting(runner=runner, store=FailingStore(), state=state, app_version="test", schema="org.example", key="enabled", desired="true", dry_run=False)
        self.assertEqual(runner.value, "false")
        self.assertEqual(state["operations"], [])

    def test_flatpak_app_is_removed_when_receipt_cannot_be_saved(self):
        runner = FlatpakRunner(); state = default_state()
        with self.assertRaises(RuntimeError):
            apply_flatpak_app(runner=runner, store=FailingStore(), state=state, app_version="test", remote="flathub", app_id="org.example.Test", dry_run=False)
        self.assertFalse(runner.installed)


if __name__ == "__main__":
    unittest.main()
