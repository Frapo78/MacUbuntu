from __future__ import annotations

import json
import subprocess
import unittest

from macubuntu_app.gui_model import CliGateway, summarize_payload


class GuiGatewayTests(unittest.TestCase):
    def test_read_only_command_uses_json_contract(self) -> None:
        gateway = CliGateway(executable="/opt/macubuntu")
        self.assertEqual(
            gateway.build_argv("plan", language="it"),
            ["/opt/macubuntu", "--json", "--lang", "it", "plan"],
        )

    def test_mutation_requires_explicit_confirmation(self) -> None:
        gateway = CliGateway(executable="macubuntu")
        with self.assertRaises(PermissionError):
            gateway.build_argv("apply", language="en")
        self.assertEqual(
            gateway.build_argv("apply", language="en", confirmed=True),
            ["macubuntu", "--json", "--lang", "en", "apply", "--yes"],
        )

    def test_dry_run_does_not_require_confirmation(self) -> None:
        gateway = CliGateway(executable="macubuntu")
        self.assertEqual(
            gateway.build_argv("uninstall", language="en", dry_run=True),
            ["macubuntu", "--json", "--lang", "en", "uninstall", "--dry-run"],
        )

    def test_force_is_limited_to_uninstall(self) -> None:
        gateway = CliGateway(executable="macubuntu")
        with self.assertRaises(ValueError):
            gateway.build_argv("apply", confirmed=True, force=True)

    def test_runner_parses_existing_json_envelope(self) -> None:
        envelope = {
            "macubuntu_version": "0.test",
            "command": "status",
            "interface": {"language": "en", "verbose": False},
            "data": {"profile_applied": True, "converged": True, "operation_count": 4},
        }

        def runner(argv, **kwargs):
            self.assertIn("--json", argv)
            return subprocess.CompletedProcess(argv, 0, json.dumps(envelope), "")

        result = CliGateway(executable="macubuntu", runner=runner).run("status", language="en")
        self.assertTrue(result.ok)
        self.assertEqual(result.payload, envelope)
        summary = summarize_payload("status", result.payload)
        self.assertEqual(summary["status"], "converged")
        self.assertEqual(summary["summary"]["operation_count"], 4)

    def test_summary_does_not_echo_arbitrary_machine_fields(self) -> None:
        payload = {
            "data": {
                "status": "healthy",
                "summary": {"pass": 4, "warn": 0, "fail": 0},
                "secret_path": "/home/alice/private",
                "token": "should-not-be-present",
            }
        }
        rendered = summarize_payload("doctor", payload)
        self.assertNotIn("secret_path", rendered)
        self.assertNotIn("token", rendered)


if __name__ == "__main__":
    unittest.main()
