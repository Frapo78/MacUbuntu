import os
import subprocess
import unittest
from unittest.mock import patch

from macubuntu_app.privilege import SudoSession, plan_requires_admin
from macubuntu_app.util import sudo_base_command


class FakeRunner:
    def __init__(self, cached_returncode=0, sudo_exists=True):
        self.cached_returncode = cached_returncode
        self.sudo_exists = sudo_exists
        self.calls = []

    def exists(self, command):
        return command == "sudo" and self.sudo_exists

    def run(self, args, *, check=True, capture=True, env=None):
        args = list(args)
        self.calls.append(args)
        if args[:3] == ["sudo", "-n", "-v"]:
            return subprocess.CompletedProcess(args, self.cached_returncode, stdout="", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")


class PrivilegeTests(unittest.TestCase):
    def test_plan_requires_admin_only_for_mutating_system_resources(self):
        self.assertTrue(plan_requires_admin({"changes": [
            {"kind": "package", "resource": "example", "action": "install"},
        ]}))
        self.assertTrue(plan_requires_admin({"changes": [
            {"kind": "service", "resource": "system:example.service", "action": "set"},
        ]}))
        self.assertFalse(plan_requires_admin({"changes": [
            {"kind": "package", "resource": "example", "action": "keep"},
            {"kind": "gsettings", "resource": "schema::key", "action": "set"},
            {"kind": "service", "resource": "user:example.service", "action": "set"},
        ]}))

    def test_cached_sudo_session_sets_noninteractive_mode_and_cleans_it(self):
        runner = FakeRunner(cached_returncode=0)
        with patch("macubuntu_app.privilege.os.geteuid", return_value=1000), patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MACUBUNTU_SUDO_READY", None)
            with SudoSession(runner, language="it", required=True, human=False, keepalive_seconds=9999) as session:
                self.assertTrue(session.ok)
                self.assertEqual(session.status, "ready")
                self.assertEqual(os.environ.get("MACUBUNTU_SUDO_READY"), "1")
                self.assertEqual(sudo_base_command(), ["sudo", "-n"])
            self.assertNotIn("MACUBUNTU_SUDO_READY", os.environ)

    def test_json_style_noninteractive_run_never_opens_password_prompt(self):
        runner = FakeRunner(cached_returncode=1)
        with patch("macubuntu_app.privilege.os.geteuid", return_value=1000):
            with SudoSession(runner, language="en", required=True, human=False) as session:
                self.assertFalse(session.ok)
                self.assertEqual(session.status, "sudo_auth_required")
        self.assertEqual(runner.calls, [["sudo", "-n", "-v"]])

    def test_missing_sudo_is_reported_without_attempting_commands(self):
        runner = FakeRunner(sudo_exists=False)
        with patch("macubuntu_app.privilege.os.geteuid", return_value=1000):
            with SudoSession(runner, language="it", required=True, human=True) as session:
                self.assertFalse(session.ok)
                self.assertEqual(session.status, "sudo_unavailable")
        self.assertEqual(runner.calls, [])

    def test_root_never_needs_sudo(self):
        runner = FakeRunner(cached_returncode=1)
        with patch("macubuntu_app.privilege.os.geteuid", return_value=0):
            with SudoSession(runner, language="it", required=True, human=True) as session:
                self.assertTrue(session.ok)
                self.assertEqual(session.status, "not_required")
        self.assertEqual(runner.calls, [])


if __name__ == "__main__":
    unittest.main()
