from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
from typing import Any, TextIO

from .util import xdg_state_home


class LockBusyError(RuntimeError):
    def __init__(self, path: Path, holder: dict[str, Any] | None = None):
        self.path = path
        self.holder = holder or {}
        super().__init__(f"MacUbuntu is already running: {path}")


class AppLock:
    """Non-blocking process lock for commands that mutate MacUbuntu state or source.

    The lock intentionally lives in the XDG state directory rather than inside the
    repository so different checkouts cannot mutate the same managed state at the
    same time.
    """

    def __init__(self, *, command: str, path: Path | None = None):
        self.command = command
        self.path = path or xdg_state_home() / "macubuntu" / "macubuntu.lock"
        self._handle: TextIO | None = None

    def __enter__(self) -> "AppLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            holder = self._read_holder(handle)
            handle.close()
            raise LockBusyError(self.path, holder) from exc

        handle.seek(0)
        handle.truncate()
        json.dump({"pid": os.getpid(), "command": self.command}, handle, sort_keys=True)
        handle.write("\n")
        handle.flush()
        self._handle = handle
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._handle is None:
            return
        try:
            self._handle.seek(0)
            self._handle.truncate()
            self._handle.flush()
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None

    @staticmethod
    def _read_holder(handle: TextIO) -> dict[str, Any]:
        try:
            handle.seek(0)
            raw = handle.read().strip()
            if not raw:
                return {}
            value = json.loads(raw)
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}
