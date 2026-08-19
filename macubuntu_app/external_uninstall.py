from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .external_core import (
    _enabled_extensions, _flatpak_app_installed, _flatpak_remote_exists, _set_enabled_extensions,
    _sudo, _tree_digest, apt_repository_present,
)
from .state import StateStore
from .util import Runner, apt_base_command

def uninstall_external_operation(
    *, op: dict[str, Any], runner: Runner, store: StateStore, state: dict[str, Any], app_version: str,
    force: bool, dry_run: bool
) -> dict[str, Any] | None:
    kind = op.get("kind")
    resource = op.get("resource", "unknown")

    if kind == "owned_paths":
        drifted: list[str] = []
        existing: list[Path] = []
        for entry in op.get("paths", []):
            path = Path(entry["path"])
            if not path.exists() and not path.is_symlink():
                continue
            existing.append(path)
            if _tree_digest(path) != entry.get("digest"):
                drifted.append(str(path))
        if drifted and not force:
            return {"kind": kind, "resource": resource, "status": "kept", "reason": "drift_detected", "paths": drifted}
        if dry_run:
            return {"kind": kind, "resource": resource, "status": "would_remove", "paths": [str(p) for p in existing], "forced": bool(drifted and force)}
        for path in sorted(existing, key=lambda p: len(str(p)), reverse=True):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
        state["operations"].remove(op)
        store.save(state, app_version)
        return {"kind": kind, "resource": resource, "status": "removed", "paths": [str(p) for p in existing], "forced": bool(drifted and force)}

    if kind == "apt_repository":
        ppa = op.get("ppa", resource)
        if not apt_repository_present(ppa):
            if not dry_run:
                state["operations"].remove(op); store.save(state, app_version)
            return {"kind": kind, "resource": resource, "status": "already_absent"}
        if dry_run:
            return {"kind": kind, "resource": resource, "status": "would_remove"}
        cp = runner.run(_sudo() + ["add-apt-repository", "-y", "--remove", ppa], check=False)
        if cp.returncode != 0:
            return {"kind": kind, "resource": resource, "status": "kept", "reason": "repository_remove_failed"}
        runner.run(apt_base_command() + ["update"], check=False, capture=None)
        state["operations"].remove(op); store.save(state, app_version)
        return {"kind": kind, "resource": resource, "status": "removed"}

    if kind == "flatpak_app":
        if not _flatpak_app_installed(runner, resource):
            if not dry_run:
                state["operations"].remove(op); store.save(state, app_version)
            return {"kind": kind, "resource": resource, "status": "already_absent"}
        if dry_run:
            return {"kind": kind, "resource": resource, "status": "would_remove"}
        runner.run(["flatpak", "--user", "uninstall", "-y", resource], capture=None)
        state["operations"].remove(op); store.save(state, app_version)
        return {"kind": kind, "resource": resource, "status": "removed"}

    if kind == "flatpak_remote":
        if not _flatpak_remote_exists(runner, resource):
            if not dry_run:
                state["operations"].remove(op); store.save(state, app_version)
            return {"kind": kind, "resource": resource, "status": "already_absent"}
        origins = runner.run(["flatpak", "--user", "list", "--app", "--columns=origin"], check=False)
        in_use = resource in (origins.stdout or "").splitlines()
        if in_use:
            if dry_run:
                return {"kind": kind, "resource": resource, "status": "would_release", "reason": "remote_adopted_by_user"}
            state["operations"].remove(op); store.save(state, app_version)
            return {"kind": kind, "resource": resource, "status": "released", "reason": "remote_adopted_by_user"}
        if dry_run:
            return {"kind": kind, "resource": resource, "status": "would_remove"}
        runner.run(["flatpak", "--user", "remote-delete", resource], capture=None)
        state["operations"].remove(op); store.save(state, app_version)
        return {"kind": kind, "resource": resource, "status": "removed"}

    if kind == "gnome_extension":
        uuid = resource
        path = Path(op["path"]) if op.get("path") else None
        if path and path.exists() and op.get("digest") and _tree_digest(path) != op["digest"] and not force:
            return {"kind": kind, "resource": resource, "status": "kept", "reason": "drift_detected"}
        enabled = _enabled_extensions(runner)
        if not op.get("original_enabled") and uuid in enabled:
            if not dry_run:
                enabled.remove(uuid); _set_enabled_extensions(runner, enabled)
        if dry_run:
            return {"kind": kind, "resource": resource, "status": "would_remove" if op.get("installed_by_macubuntu") else "would_restore"}
        if op.get("installed_by_macubuntu") and path and path.exists():
            shutil.rmtree(path)
        state["operations"].remove(op); store.save(state, app_version)
        return {"kind": kind, "resource": resource, "status": "removed" if op.get("installed_by_macubuntu") else "restored", "session_restart_required": True}

    if kind == "service":
        unit = op["unit"]
        user = bool(op.get("user"))
        systemctl = ["systemctl", "--user"] if user else _sudo() + ["systemctl"]
        if dry_run:
            return {"kind": kind, "resource": resource, "status": "would_restore"}
        if not op.get("original_enabled"):
            runner.run(systemctl + ["disable", unit], check=False, capture=None)
        if not op.get("original_active"):
            runner.run(systemctl + ["stop", unit], check=False, capture=None)
        state["operations"].remove(op); store.save(state, app_version)
        return {"kind": kind, "resource": resource, "status": "restored"}

    return None
