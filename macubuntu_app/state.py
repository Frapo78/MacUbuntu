from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .util import atomic_json_write, xdg_state_home

SCHEMA_VERSION = 1


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


class StateStore:
    def __init__(self, path: Path | None = None):
        self.path = path or xdg_state_home() / "macubuntu" / "state.json"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return default_state()
        import json
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_version") != SCHEMA_VERSION:
            raise RuntimeError(f"unsupported state schema: {data.get('schema_version')}")
        data.setdefault("operations", [])
        profile = data.setdefault("profile", default_profile())
        for key, value in default_profile().items():
            profile.setdefault(key, value)
        return data

    def save(self, state: dict[str, Any], app_version: str) -> None:
        out = deepcopy(state)
        out["schema_version"] = SCHEMA_VERSION
        out["app_version"] = app_version
        if not out.get("created_at"):
            out["created_at"] = now_iso()
        out["updated_at"] = now_iso()
        atomic_json_write(self.path, out)

    def remove_if_empty(self, state: dict[str, Any]) -> None:
        if state.get("operations"):
            return
        if state.get("profile", {}).get("applied"):
            return
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
