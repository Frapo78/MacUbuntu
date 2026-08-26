from __future__ import annotations

import json
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

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
        "transaction": None,
        "last_transaction": None,
    }


def _validate_pending_mutation(record: Any, *, path: Path) -> dict[str, Any] | None:
    if record is None:
        return None
    if not isinstance(record, dict):
        raise StateValidationError("pending mutation metadata must be an object or null", path=path)
    required_strings = ("id", "kind", "status", "prepared_at")
    if any(not isinstance(record.get(key), str) or not record.get(key) for key in required_strings):
        raise StateValidationError("pending mutation metadata is incomplete", path=path)
    if record.get("status") != "prepared":
        raise StateValidationError("pending mutation status must be prepared", path=path)
    resource = record.get("resource")
    if resource is not None and not isinstance(resource, str):
        raise StateValidationError("pending mutation resource must be a string or null", path=path)
    evidence = record.get("evidence", {})
    if not isinstance(evidence, dict):
        raise StateValidationError("pending mutation evidence must be an object", path=path)
    return deepcopy(record)


def _validate_transaction(record: Any, *, path: Path, active: bool) -> dict[str, Any] | None:
    if record is None:
        return None
    if not isinstance(record, dict):
        raise StateValidationError("transaction metadata must be an object or null", path=path)

    required_strings = ("id", "operation", "status", "started_at", "app_version")
    if any(not isinstance(record.get(key), str) or not record.get(key) for key in required_strings):
        raise StateValidationError("transaction metadata is incomplete", path=path)

    expected_status = "in_progress" if active else "committed"
    if record.get("status") != expected_status:
        raise StateValidationError(f"transaction status must be {expected_status}", path=path)

    baseline = record.get("baseline_operation_count")
    if not isinstance(baseline, int) or baseline < 0:
        raise StateValidationError("transaction baseline operation count is invalid", path=path)

    normalized = deepcopy(record)
    if active:
        normalized["pending_mutation"] = _validate_pending_mutation(
            record.get("pending_mutation"), path=path
        )
    else:
        if record.get("pending_mutation") is not None:
            raise StateValidationError("committed transaction cannot contain a pending mutation", path=path)
        if not isinstance(record.get("completed_at"), str) or not record.get("completed_at"):
            raise StateValidationError("committed transaction is missing completed_at", path=path)
        final_count = record.get("final_operation_count")
        if not isinstance(final_count, int) or final_count < 0:
            raise StateValidationError("committed transaction final operation count is invalid", path=path)
    return normalized


def _public_transaction(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(record, dict):
        return None
    summary = {
        key: record.get(key)
        for key in (
            "id",
            "operation",
            "status",
            "started_at",
            "app_version",
            "baseline_operation_count",
        )
    }
    pending = record.get("pending_mutation")
    if isinstance(pending, dict):
        summary["pending_mutation"] = {
            key: pending.get(key)
            for key in ("id", "kind", "status", "prepared_at")
        }
    else:
        summary["pending_mutation"] = None
    return summary


def privacy_safe_state(state: dict[str, Any]) -> dict[str, Any]:
    public = deepcopy(state)
    transaction = public.get("transaction")
    if isinstance(transaction, dict):
        transaction["pending_mutation"] = _public_transaction(transaction).get("pending_mutation")
    return public


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
    normalized["transaction"] = _validate_transaction(data.get("transaction"), path=path, active=True)
    normalized["last_transaction"] = _validate_transaction(data.get("last_transaction"), path=path, active=False)
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

    def load_backup(self) -> dict[str, Any] | None:
        if not self.backup_path.exists():
            return None
        return self._read_path(self.backup_path)

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

        transaction = state.get("transaction")
        if transaction:
            return {
                "ok": False,
                "status": "transaction_interrupted",
                "transaction": _public_transaction(transaction),
                "operation_count": len(state.get("operations", [])),
                "profile_applied": bool(state.get("profile", {}).get("applied")),
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

    def begin_transaction(self, state: dict[str, Any], app_version: str, operation: str) -> dict[str, Any]:
        if state.get("transaction"):
            raise StateValidationError("a transaction is already in progress", path=self.path)
        transaction = {
            "id": str(uuid4()),
            "operation": operation,
            "status": "in_progress",
            "started_at": now_iso(),
            "app_version": app_version,
            "baseline_operation_count": len(state.get("operations", [])),
            "pending_mutation": None,
        }
        state["transaction"] = transaction
        self.save(state, app_version)
        return deepcopy(transaction)

    def prepare_mutation(
        self,
        state: dict[str, Any],
        app_version: str,
        *,
        kind: str,
        resource: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        transaction = state.get("transaction")
        if not isinstance(transaction, dict):
            raise StateValidationError("no transaction is in progress", path=self.path)
        if transaction.get("pending_mutation"):
            raise StateValidationError("a mutation is already pending", path=self.path)
        if not isinstance(kind, str) or not kind:
            raise StateValidationError("mutation kind is required", path=self.path)
        if resource is not None and not isinstance(resource, str):
            raise StateValidationError("mutation resource must be a string or null", path=self.path)
        if evidence is not None and not isinstance(evidence, dict):
            raise StateValidationError("mutation evidence must be an object", path=self.path)
        pending = {
            "id": str(uuid4()),
            "kind": kind,
            "resource": resource,
            "status": "prepared",
            "prepared_at": now_iso(),
            "evidence": deepcopy(evidence or {}),
        }
        transaction["pending_mutation"] = pending
        self.save(state, app_version)
        return deepcopy(pending)

    def clear_pending_mutation(
        self,
        state: dict[str, Any],
        app_version: str,
        *,
        mutation_id: str | None = None,
    ) -> None:
        transaction = state.get("transaction")
        if not isinstance(transaction, dict):
            raise StateValidationError("no transaction is in progress", path=self.path)
        pending = transaction.get("pending_mutation")
        if not isinstance(pending, dict):
            raise StateValidationError("no mutation is pending", path=self.path)
        if mutation_id is not None and pending.get("id") != mutation_id:
            raise StateValidationError("pending mutation identity mismatch", path=self.path)
        transaction["pending_mutation"] = None
        self.save(state, app_version)

    def commit_transaction(self, state: dict[str, Any], app_version: str) -> dict[str, Any]:
        transaction = state.get("transaction")
        if not transaction:
            raise StateValidationError("no transaction is in progress", path=self.path)
        if transaction.get("pending_mutation"):
            raise StateValidationError("cannot commit while a mutation is pending", path=self.path)
        committed = {
            **transaction,
            "status": "committed",
            "completed_at": now_iso(),
            "final_operation_count": len(state.get("operations", [])),
        }
        committed.pop("pending_mutation", None)
        state["transaction"] = None
        state["last_transaction"] = committed
        self.save(state, app_version)
        return deepcopy(committed)

    def remove_if_empty(self, state: dict[str, Any]) -> None:
        if state.get("operations"):
            return
        if state.get("profile", {}).get("applied"):
            return
        if state.get("transaction"):
            return
        for path in (self.path, self.backup_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                raise StateWriteError(str(exc), path=path) from exc
