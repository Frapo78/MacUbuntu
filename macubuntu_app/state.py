from __future__ import annotations

import json
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .util import atomic_json_write, xdg_state_home

SCHEMA_VERSION = 1


class StateError(RuntimeError):
    code = "state_error"

    def __init__(self, message: str, *, path: Path):
        self.path = path
        super().__init__(message)


class StateReadError(StateError):
    code = "state_read_error"


class StateWriteError(StateError):
    code = "state_write_error"


class StateCorruptError(StateError):
    code = "state_corrupt"


class StateSchemaError(StateError):
    code = "state_schema_unsupported"


class StateValidationError(StateError):
    code = "state_invalid"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_profile() -> dict[str, Any]:
    return {
        "applied": False,
        "applied_at": None,
        "last_apply_at": None,
        "version": None,
    }


def default_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "app_version": None,
        "created_at": None,
        "updated_at": None,
        "profile": default_profile(),
        "operations": [],
    }


def _validate_state(data: Any, *, path: Path) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise StateValidationError("state root must be an object", path=path)

    schema = data.get("schema_version")
    if schema != SCHEMA_VERSION:
        raise StateSchemaError(f"unsupported state schema: {schema}", path=path)

    operations = data.get("operations", [])
    if not isinstance(operations, list) or any(not isinstance(op, dict) for op in operations):
        raise StateValidationError("operations must be a list of objects", path=path)

    profile = data.get("profile", default_profile())
    if not isinstance(profile, dict):
        raise StateValidationError("profile must be an object", path=path)

    normalized = deepcopy(data)
    normalized["operations"] = operations
    normalized_profile = normalized.setdefault("profile", profile)
    for key, value in default_profile().items():
        normalized_profile.setdefault(key, value)
    return normalized


class StateStore:
    def __init__(self, path: Path | None = None):
        self.path = path or xdg_state_home() / "macubuntu" / "state.json"
        self.backup_path = self.path.with_suffix(self.path.suffix + ".bak")

    def _read_path(self, path: Path) -> dict[str, Any]:
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise StateReadError(str(exc), path=path) from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StateCorruptError(f"invalid JSON at line {exc.lineno}, column {exc.colno}", path=path) from exc
        return _validate_state(data, path=path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return default_state()
        return self._read_path(self.path)

    def health(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "path": str(self.path),
            "backup_path": str(self.backup_path),
            "backup_exists": self.backup_path.exists(),
        }
        if not self.path.exists():
            return {"ok": True, "status": "absent", **result}
        try:
            state = self.load()
        except StateError as exc:
            backup_ok = False
            if self.backup_path.exists():
                try:
                    self._read_path(self.backup_path)
                    backup_ok = True
                except StateError:
                    backup_ok = False
            return {
                "ok": False,
                "status": exc.code,
                "error": str(exc),
                "backup_valid": backup_ok,
                **result,
            }
        return {
            "ok": True,
            "status": "ok",
            "operation_count": len(state.get("operations", [])),
            "profile_applied": bool(state.get("profile", {}).get("applied")),
            **result,
        }

    def save(self, state: dict[str, Any], app_version: str) -> None:
        out = deepcopy(state)
        out["schema_version"] = SCHEMA_VERSION
        out["app_version"] = app_version
        if not out.get("created_at"):
            out["created_at"] = now_iso()
        out["updated_at"] = now_iso()
        out = _validate_state(out, path=self.path)

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists():
                # Never overwrite an unreadable state file. A broken receipt is safer
                # than silently replacing ownership history with incomplete data.
                self._read_path(self.path)
                shutil.copy2(self.path, self.backup_path)
            atomic_json_write(self.path, out)
        except StateError:
            raise
        except OSError as exc:
            raise StateWriteError(str(exc), path=self.path) from exc

    def remove_if_empty(self, state: dict[str, Any]) -> None:
        if state.get("operations"):
            return
        if state.get("profile", {}).get("applied"):
            return
        for path in (self.path, self.backup_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                raise StateWriteError(str(exc), path=path) from exc
