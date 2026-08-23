from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from .state import StateStore
from .system import audit_system
from .updater import is_official_remote
from .util import Runner

PASS = "pass"
WARN = "warn"
FAIL = "fail"


def _check(check_id: str, status: str, code: str, **data: Any) -> dict[str, Any]:
    return {"id": check_id, "status": status, "code": code, "data": data}


def _git(runner: Runner, root: Path, *args: str):
    return runner.run(["git", "-C", str(root), *args], check=False)


def _repository_check(runner: Runner, root: Path) -> dict[str, Any]:
    if not runner.exists("git"):
        return _check("repository", WARN, "git_missing")

    inside = _git(runner, root, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or (inside.stdout or "").strip() != "true":
        return _check("repository", WARN, "not_git_checkout", root=str(root))

    origin = _git(runner, root, "remote", "get-url", "origin")
    if origin.returncode != 0:
        return _check("repository", WARN, "origin_missing", root=str(root))
    remote_url = (origin.stdout or "").strip()
    if not is_official_remote(remote_url):
        return _check("repository", WARN, "unofficial_remote", remote_url=remote_url)

    branch_cp = _git(runner, root, "symbolic-ref", "--short", "-q", "HEAD")
    branch = (branch_cp.stdout or "").strip()
    if branch_cp.returncode != 0 or not branch:
        return _check("repository", WARN, "detached_head", remote_url=remote_url)
    if branch != "main":
        return _check("repository", WARN, "wrong_branch", branch=branch, remote_url=remote_url)

    status_cp = _git(runner, root, "status", "--porcelain", "--untracked-files=normal")
    if status_cp.returncode != 0:
        return _check("repository", WARN, "status_failed", branch=branch, remote_url=remote_url)
    dirty = [line for line in (status_cp.stdout or "").splitlines() if line.strip()]
    if dirty:
        return _check("repository", WARN, "dirty_worktree", branch=branch, dirty_paths=dirty)

    return _check("repository", PASS, "official_clean", branch=branch, remote_url=remote_url)


def run_doctor(runner: Runner, store: StateStore, root: Path) -> dict[str, Any]:
    """Run local, non-mutating readiness checks.

    Doctor deliberately avoids network access. The dedicated `update --check` command
    remains responsible for contacting GitHub.
    """
    audit = audit_system(runner)
    checks: list[dict[str, Any]] = []

    support = audit["support"]["level"]
    if support == "supported":
        checks.append(_check("platform", PASS, "supported", support_level=support))
    elif support == "experimental":
        checks.append(_check("platform", WARN, "experimental", support_level=support))
    else:
        checks.append(_check("platform", FAIL, "unsupported", support_level=support))

    session_type = (audit["session"].get("type") or "").lower()
    if session_type in {"x11", "wayland"}:
        checks.append(_check("session", PASS, session_type, session_type=session_type))
    else:
        checks.append(_check("session", WARN, "unknown", session_type=session_type or None))

    if runner.exists("gsettings"):
        probe = runner.run(["gsettings", "list-schemas"], check=False)
        if probe.returncode == 0 and (probe.stdout or "").strip():
            checks.append(_check("gsettings", PASS, "available"))
        else:
            checks.append(_check("gsettings", FAIL, "broken", returncode=probe.returncode))
    else:
        checks.append(_check("gsettings", FAIL, "missing"))

    missing_pkg_tools = [tool for tool in ("dpkg-query", "apt-get") if not runner.exists(tool)]
    if missing_pkg_tools:
        checks.append(_check("package_manager", FAIL, "missing", missing=missing_pkg_tools))
    else:
        checks.append(_check("package_manager", PASS, "available"))

    if os.geteuid() == 0:
        checks.append(_check("privilege", PASS, "root"))
    elif runner.exists("sudo"):
        checks.append(_check("privilege", PASS, "sudo_available"))
    else:
        checks.append(_check("privilege", FAIL, "sudo_missing"))

    state_health = store.health()
    state_data = {key: value for key, value in state_health.items() if key not in {"ok", "status"}}
    recovery_required = state_health.get("status") == "transaction_interrupted"
    if recovery_required:
        # Keep the human-facing doctor message on an existing localized key while
        # exposing the precise recovery reason as structured JSON data.
        state_data["recovery_status"] = "transaction_interrupted"
        checks.append(_check("state", FAIL, "state_invalid", **state_data))
    elif state_health["ok"]:
        checks.append(_check("state", PASS, state_health["status"], **state_data))
    else:
        checks.append(_check("state", FAIL, state_health["status"], **state_data))

    try:
        free_bytes = shutil.disk_usage(Path.home()).free
    except OSError:
        checks.append(_check("storage", WARN, "unknown"))
    else:
        if free_bytes < 512 * 1024 * 1024:
            checks.append(_check("storage", FAIL, "critical", free_bytes=free_bytes))
        elif free_bytes < 2 * 1024 * 1024 * 1024:
            checks.append(_check("storage", WARN, "low", free_bytes=free_bytes))
        else:
            checks.append(_check("storage", PASS, "sufficient", free_bytes=free_bytes))

    checks.append(_repository_check(runner, root.resolve()))

    counts = {
        PASS: sum(1 for item in checks if item["status"] == PASS),
        WARN: sum(1 for item in checks if item["status"] == WARN),
        FAIL: sum(1 for item in checks if item["status"] == FAIL),
    }
    if counts[FAIL]:
        status = "blocked"
    elif counts[WARN]:
        status = "degraded"
    else:
        status = "healthy"

    recovery = {
        "required": recovery_required,
        "status": "transaction_interrupted" if recovery_required else "none",
        "transaction": state_health.get("transaction") if recovery_required else None,
    }

    return {
        "ok": counts[FAIL] == 0,
        "status": status,
        "summary": counts,
        "checks": checks,
        "recovery": recovery,
        "audit": audit,
    }
