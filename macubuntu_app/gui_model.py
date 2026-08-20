from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


READ_ONLY_COMMANDS = {"audit", "doctor", "plan", "status"}
MUTATING_COMMANDS = {"apply", "macify", "update", "uninstall"}
ALL_COMMANDS = READ_ONLY_COMMANDS | MUTATING_COMMANDS


@dataclass(frozen=True)
class GuiCommandResult:
    command: str
    returncode: int
    payload: dict[str, Any] | None
    stderr: str

    @property
    def ok(self) -> bool:
        if self.payload is not None:
            data = self.payload.get("data")
            if isinstance(data, dict) and data.get("ok") is False:
                return False
        return self.returncode == 0


class CliGateway:
    """Thin GUI adapter over the existing CLI/JSON contract.

    The GUI deliberately does not implement mutations itself. Every action is
    delegated to the same CLI -> engine path used by terminal users and agents.
    """

    def __init__(
        self,
        executable: str | Path | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        if executable is None:
            executable = Path(__file__).resolve().parent.parent / "macubuntu"
        self.executable = str(executable)
        self._runner = runner

    def build_argv(
        self,
        command: str,
        *,
        language: str = "auto",
        dry_run: bool = False,
        confirmed: bool = False,
        force: bool = False,
        check_update: bool = False,
    ) -> list[str]:
        if command not in ALL_COMMANDS:
            raise ValueError(f"unsupported GUI command: {command}")
        if language not in {"auto", "it", "en"}:
            raise ValueError(f"unsupported language: {language}")
        if command in MUTATING_COMMANDS and not confirmed and not dry_run:
            raise PermissionError(f"confirmation required for {command}")

        argv = [self.executable, "--json", "--lang", language, command]
        if dry_run:
            argv.append("--dry-run")
        if confirmed and command in {"apply", "macify", "uninstall"}:
            argv.append("--yes")
        if force:
            if command != "uninstall":
                raise ValueError("force is valid only for uninstall")
            argv.append("--force")
        if check_update:
            if command != "update":
                raise ValueError("check_update is valid only for update")
            argv.append("--check")
        return argv

    def run(self, command: str, **options: Any) -> GuiCommandResult:
        argv = self.build_argv(command, **options)
        completed = self._runner(
            argv,
            text=True,
            capture_output=True,
            check=False,
        )
        payload: dict[str, Any] | None = None
        stdout = completed.stdout.strip()
        if stdout:
            try:
                decoded = json.loads(stdout)
                if isinstance(decoded, dict):
                    payload = decoded
            except json.JSONDecodeError:
                payload = None
        return GuiCommandResult(
            command=command,
            returncode=completed.returncode,
            payload=payload,
            stderr=completed.stderr.strip(),
        )


def summarize_payload(command: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    """Return privacy-safe, presentation-oriented data for the future GTK UI."""
    if payload is None:
        return {"command": command, "status": "error", "summary": {}}
    data = payload.get("data")
    if not isinstance(data, dict):
        data = {}

    if command == "plan":
        summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
        return {"command": command, "status": "ready", "summary": summary}
    if command == "doctor":
        return {
            "command": command,
            "status": data.get("status", "unknown"),
            "summary": data.get("summary", {}),
        }
    if command == "status":
        return {
            "command": command,
            "status": "converged" if data.get("converged") else "attention",
            "summary": {
                "profile_applied": bool(data.get("profile_applied")),
                "converged": bool(data.get("converged")),
                "operation_count": int(data.get("operation_count", 0) or 0),
            },
        }
    if command in MUTATING_COMMANDS:
        return {
            "command": command,
            "status": "ok" if data.get("ok", True) is not False else "error",
            "summary": {"result_count": len(data.get("results", [])) if isinstance(data.get("results"), list) else 0},
        }
    return {"command": command, "status": "ready", "summary": {}}
