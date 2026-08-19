from __future__ import annotations

import os
import sys
import threading
from typing import Any

from .util import Runner


_MESSAGES = {
    "it": {
        "intro": "🔐 Prima di iniziare, MacUbuntu ha bisogno del permesso di fare qualche magia da amministratore.",
        "prompt": "Password sudo per MacUbuntu: ",
        "ready": "✓ Perfetto, chiavi del castello ottenute. Si parte.",
        "cached": "✓ Permessi amministrativi già disponibili. Si parte.",
        "required": "MacUbuntu ha bisogno dell'autorizzazione sudo prima di poter continuare.",
        "failed": "Autorizzazione sudo non riuscita. Nessuna modifica amministrativa è stata eseguita.",
        "unavailable": "sudo non è disponibile: MacUbuntu non può eseguire le modifiche amministrative previste.",
    },
    "en": {
        "intro": "🔐 Before we start, MacUbuntu needs permission for a little administrator magic.",
        "prompt": "Sudo password for MacUbuntu: ",
        "ready": "✓ Perfect, castle keys acquired. Off we go.",
        "cached": "✓ Administrator permission is already available. Off we go.",
        "required": "MacUbuntu needs sudo authorization before it can continue.",
        "failed": "Sudo authorization failed. No administrative changes were made.",
        "unavailable": "sudo is unavailable: MacUbuntu cannot perform the planned administrative changes.",
    },
}


def plan_requires_admin(plan: dict[str, Any]) -> bool:
    """Return whether the current plan contains a system-level mutation."""
    for change in plan.get("changes", []):
        if change.get("action") not in {"install", "set"}:
            continue
        kind = change.get("kind")
        resource = str(change.get("resource", ""))
        if kind in {"package", "apt_repository"}:
            return True
        if kind == "service" and resource.startswith("system:"):
            return True
    return False


class SudoSession:
    """Authenticate once, then keep sudo warm without ever handling the password.

    The password prompt belongs to sudo itself (`sudo -v -p ...`). Once
    validated, MacUbuntu marks subsequent sudo invocations as non-interactive
    via MACUBUNTU_SUDO_READY. A short-lived keepalive refreshes only the sudo
    timestamp and is stopped when the operation ends.
    """

    def __init__(
        self,
        runner: Runner,
        *,
        language: str,
        required: bool,
        human: bool,
        keepalive_seconds: float = 60.0,
    ):
        self.runner = runner
        self.language = language if language in _MESSAGES else "en"
        self.required = bool(required)
        self.human = bool(human)
        self.keepalive_seconds = keepalive_seconds
        self.ok = True
        self.status = "not_required"
        self.message = ""
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._set_ready = False

    def _msg(self, key: str) -> str:
        return _MESSAGES[self.language][key]

    def _keepalive(self) -> None:
        while not self._stop.wait(self.keepalive_seconds):
            self.runner.run(["sudo", "-n", "-v"], check=False, capture=True)

    def __enter__(self) -> "SudoSession":
        if not self.required or os.geteuid() == 0:
            return self
        if not self.runner.exists("sudo"):
            self.ok = False
            self.status = "sudo_unavailable"
            self.message = self._msg("unavailable")
            return self

        cached = self.runner.run(["sudo", "-n", "-v"], check=False, capture=True)
        if cached.returncode != 0:
            if not self.human or not sys.stdin.isatty():
                self.ok = False
                self.status = "sudo_auth_required"
                self.message = self._msg("required")
                return self
            print(self._msg("intro"), flush=True)
            auth = self.runner.run(
                ["sudo", "-v", "-p", self._msg("prompt")],
                check=False,
                capture=False,
            )
            if auth.returncode != 0:
                self.ok = False
                self.status = "sudo_auth_failed"
                self.message = self._msg("failed")
                return self
            print(self._msg("ready"), flush=True)
        elif self.human:
            print(self._msg("cached"), flush=True)

        os.environ["MACUBUNTU_SUDO_READY"] = "1"
        self._set_ready = True
        self.status = "ready"
        self._thread = threading.Thread(target=self._keepalive, name="macubuntu-sudo-keepalive", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        if self._set_ready:
            os.environ.pop("MACUBUNTU_SUDO_READY", None)
