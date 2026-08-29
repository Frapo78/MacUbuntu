import unittest
from types import SimpleNamespace
from unittest.mock import patch

from macubuntu_app.recovery import _probe_pending_mutation


class FakeRunner:
    def __init__(self, *, enabled="disabled", active="inactive", flatpak=True):
        self.enabled = enabled
        self.active = active
        self.flatpak = flatpak

    def exists(self, command):
        return self.flatpak if command == "flatpak" else True

    def run(self, cmd, **_kwargs):
        if "cat" in cmd:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if "is-enabled" in cmd:
            return SimpleNamespace(returncode=0, stdout=self.enabled + "\n", stderr="")
        if "is-active" in cmd:
            return SimpleNamespace(returncode=0, stdout=self.active + "\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")


class ExternalPendingRecoveryTests(unittest.TestCase):
    @patch("macubuntu_app.recovery.apt_repository_present", return_value=True)
    def test_apt_repository_add_detects_applied(self, _present):
        out = _probe_pending_mutation(
            FakeRunner(),
            {
                "id": "mutation-1",
                "kind": "apt_repository_add",
                "resource": "ppa:example/stable",
                "evidence": {"before_present": False, "desired_present": True},
            },
        )
        self.assertEqual(out["status"], "applied")

    @patch("macubuntu_app.recovery._flatpak_remote_exists", return_value=False)
    def test_flatpak_remote_add_detects_original(self, _exists):
        out = _probe_pending_mutation(
            FakeRunner(),
            {
                "id": "mutation-2",
                "kind": "flatpak_remote_add",
                "resource": "flathub",
                "evidence": {"before_present": False, "desired_present": True},
            },
        )
        self.assertEqual(out["status"], "original")

    @patch("macubuntu_app.recovery._flatpak_app_installed", return_value=True)
    def test_flatpak_app_install_detects_applied(self, _installed):
        out = _probe_pending_mutation(
            FakeRunner(),
            {
                "id": "mutation-3",
                "kind": "flatpak_app_install",
                "resource": "org.example.App",
                "evidence": {"before_present": False, "desired_present": True},
            },
        )
        self.assertEqual(out["status"], "applied")

    def test_flatpak_unavailable_stays_privacy_safe(self):
        out = _probe_pending_mutation(
            FakeRunner(flatpak=False),
            {
                "id": "mutation-4",
                "kind": "flatpak_app_install",
                "resource": "org.private.App",
                "evidence": {"before_present": False, "desired_present": True},
            },
        )
        self.assertEqual(out["status"], "unverifiable")
        self.assertEqual(out["reason"], "flatpak_unavailable")
        self.assertNotIn("resource", out)

    def test_service_enable_start_detects_partial(self):
        out = _probe_pending_mutation(
            FakeRunner(enabled="enabled", active="inactive"),
            {
                "id": "mutation-5",
                "kind": "service_enable_start",
                "resource": "user:example.service",
                "evidence": {
                    "before_enabled": False,
                    "before_active": False,
                    "desired_enabled": True,
                    "desired_active": True,
                    "user": True,
                },
            },
        )
        self.assertEqual(out["status"], "partial")
        self.assertTrue(out["enabled"])
        self.assertFalse(out["active"])

    def test_invalid_service_scope_does_not_echo_resource(self):
        out = _probe_pending_mutation(
            FakeRunner(),
            {
                "id": "mutation-6",
                "kind": "service_enable_start",
                "resource": "system:/home/alice/private.service",
                "evidence": {
                    "before_enabled": False,
                    "before_active": False,
                    "desired_enabled": True,
                    "desired_active": True,
                    "user": True,
                },
            },
        )
        rendered = str(out)
        self.assertEqual(out["status"], "unverifiable")
        self.assertNotIn("alice", rendered)


if __name__ == "__main__":
    unittest.main()
