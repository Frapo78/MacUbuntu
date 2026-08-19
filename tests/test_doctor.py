import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from macubuntu_app.doctor import run_doctor
from macubuntu_app.state import StateStore


class FakeRunner:
    def __init__(self, *, gsettings=True, package_tools=True, sudo=True):
        self.gsettings = gsettings
        self.package_tools = package_tools
        self.sudo = sudo

    def exists(self, command):
        if command == "gsettings":
            return self.gsettings
        if command in {"dpkg-query", "apt-get"}:
            return self.package_tools
        if command == "sudo":
            return self.sudo
        if command == "git":
            return False
        return False

    def run(self, args, check=True, capture=True, env=None):
        class CP:
            returncode = 0
            stdout = ""
            stderr = ""
        cp = CP()
        if args[:2] == ["gsettings", "list-schemas"]:
            cp.stdout = "org.gnome.desktop.interface\n"
        return cp


SUPPORTED_AUDIT = {
    "support": {"level": "supported"},
    "session": {"type": "x11"},
}


class DoctorTests(unittest.TestCase):
    def test_supported_machine_with_only_update_warning_is_usable(self):
        with tempfile.TemporaryDirectory() as td:
            store = StateStore(Path(td) / "state.json")
            with patch("macubuntu_app.doctor.audit_system", return_value=SUPPORTED_AUDIT):
                result = run_doctor(FakeRunner(), store, Path(td))

            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "degraded")
            self.assertEqual(result["summary"]["fail"], 0)
            self.assertGreaterEqual(result["summary"]["warn"], 1)
            ids = {item["id"] for item in result["checks"]}
            self.assertIn("state", ids)
            self.assertIn("repository", ids)

    def test_missing_gsettings_blocks_apply_preflight(self):
        with tempfile.TemporaryDirectory() as td:
            store = StateStore(Path(td) / "state.json")
            with patch("macubuntu_app.doctor.audit_system", return_value=SUPPORTED_AUDIT):
                result = run_doctor(FakeRunner(gsettings=False), store, Path(td))

            self.assertFalse(result["ok"])
            self.assertEqual(result["status"], "blocked")
            gsettings = next(item for item in result["checks"] if item["id"] == "gsettings")
            self.assertEqual(gsettings["status"], "fail")
            self.assertEqual(gsettings["code"], "missing")


if __name__ == "__main__":
    unittest.main()
