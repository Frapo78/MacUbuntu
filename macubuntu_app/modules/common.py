from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..system import gsettings_get
from ..util import Runner, package_installed


def shell_major(runner: Runner) -> str | None:
    if not runner.exists("gnome-shell"):
        return None
    cp = runner.run(["gnome-shell", "--version"], check=False)
    match = re.search(r"(\d+)(?:\.\d+)?", cp.stdout or "")
    return match.group(1) if match else None


def session_type() -> str:
    import os
    return (os.environ.get("XDG_SESSION_TYPE") or "").lower()


def package_change(runner: Runner, package: str, module: str) -> dict[str, Any]:
    return {
        "module": module,
        "kind": "package",
        "resource": package,
        "action": "keep" if package_installed(runner, package) else "install",
    }


def setting_change(runner: Runner, module: str, schema: str, key: str, desired: str, description: str) -> dict[str, Any]:
    current = gsettings_get(runner, schema, key)
    if current is None:
        action = "skip"
    elif current == desired:
        action = "keep"
    else:
        action = "set"
    return {
        "module": module,
        "kind": "gsettings",
        "resource": f"{schema}::{key}",
        "description": description,
        "current": current,
        "desired": desired,
        "action": action,
    }


def path_change(module: str, resource: str, path: Path) -> dict[str, Any]:
    return {
        "module": module,
        "kind": "managed_path",
        "resource": resource,
        "path": str(path),
        "action": "keep" if path.exists() else "install",
    }


def package_version(runner: Runner, package: str) -> str | None:
    cp = runner.run(["dpkg-query", "-W", "-f=${Version}", package], check=False)
    if cp.returncode != 0:
        return None
    return (cp.stdout or "").strip() or None


def package_available(runner: Runner, package: str) -> bool:
    cp = runner.run(["apt-cache", "show", package], check=False)
    return cp.returncode == 0 and bool((cp.stdout or "").strip())


def service_change(runner: Runner, module: str, unit: str, *, user: bool) -> dict[str, Any]:
    prefix = ["systemctl", "--user"] if user else ["systemctl"]
    cat = runner.run(prefix + ["cat", unit], check=False)
    resource = ("user:" if user else "system:") + unit
    if cat.returncode != 0:
        return {"module": module, "kind": "service", "resource": resource, "action": "skip", "reason": "unit_missing"}
    enabled = runner.run(prefix + ["is-enabled", unit], check=False)
    active = runner.run(prefix + ["is-active", unit], check=False)
    converged = (enabled.stdout or "").strip() == "enabled" and (active.stdout or "").strip() == "active"
    return {"module": module, "kind": "service", "resource": resource, "action": "keep" if converged else "set"}
