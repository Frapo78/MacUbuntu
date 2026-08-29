from __future__ import annotations

from typing import Any

from .external_core import (
    _flatpak_app_installed, _flatpak_remote_exists, _save_receipt, _sudo,
    apt_repository_present,
)
from .state import StateStore
from .util import Runner, apt_base_command


def _prepare_external_mutation(
    *, store: StateStore, state: dict[str, Any], app_version: str,
    kind: str, resource: str, evidence: dict[str, Any],
) -> str:
    pending = store.prepare_mutation(
        state,
        app_version,
        kind=kind,
        resource=resource,
        evidence=evidence,
    )
    return str(pending["id"])


def _finish_external_mutation(
    *, store: StateStore, state: dict[str, Any], app_version: str, mutation_id: str,
) -> None:
    store.clear_pending_mutation(state, app_version, mutation_id=mutation_id)


def apply_apt_repository(
    *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, ppa: str, dry_run: bool
) -> dict[str, Any]:
    resource = ppa
    if apt_repository_present(ppa):
        return {"kind": "apt_repository", "resource": resource, "status": "already_converged"}
    if dry_run:
        return {"kind": "apt_repository", "resource": resource, "status": "would_install"}
    mutation_id = _prepare_external_mutation(
        store=store, state=state, app_version=app_version,
        kind="apt_repository_add", resource=resource,
        evidence={"before_present": False, "desired_present": True},
    )
    runner.run(_sudo() + ["add-apt-repository", "-y", ppa], capture=None)
    runner.run(apt_base_command() + ["update"], capture=None)
    try:
        _save_receipt(store, state, app_version, {"kind": "apt_repository", "resource": resource, "ppa": ppa})
    except Exception:
        # This repository was created by this call. If ownership cannot be
        # persisted, remove it again rather than leaving an untracked
        # privileged mutation behind. Keep the pending intent durable: after
        # any failure recovery must verify the real machine state explicitly.
        runner.run(_sudo() + ["add-apt-repository", "-y", "--remove", ppa], check=False, capture=None)
        runner.run(apt_base_command() + ["update"], check=False, capture=None)
        raise
    _finish_external_mutation(
        store=store, state=state, app_version=app_version, mutation_id=mutation_id
    )
    return {"kind": "apt_repository", "resource": resource, "status": "installed"}


def apply_flatpak_remote(
    *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, name: str, url: str, dry_run: bool
) -> dict[str, Any]:
    if _flatpak_remote_exists(runner, name):
        return {"kind": "flatpak_remote", "resource": name, "status": "already_converged"}
    if dry_run:
        return {"kind": "flatpak_remote", "resource": name, "status": "would_install"}
    mutation_id = _prepare_external_mutation(
        store=store, state=state, app_version=app_version,
        kind="flatpak_remote_add", resource=name,
        evidence={"before_present": False, "desired_present": True},
    )
    runner.run(["flatpak", "--user", "remote-add", "--if-not-exists", name, url], capture=None)
    try:
        _save_receipt(store, state, app_version, {"kind": "flatpak_remote", "resource": name, "url": url})
    except Exception:
        runner.run(["flatpak", "--user", "remote-delete", name], check=False, capture=None)
        raise
    _finish_external_mutation(
        store=store, state=state, app_version=app_version, mutation_id=mutation_id
    )
    return {"kind": "flatpak_remote", "resource": name, "status": "installed"}


def apply_flatpak_app(
    *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, remote: str, app_id: str, dry_run: bool
) -> dict[str, Any]:
    if _flatpak_app_installed(runner, app_id):
        return {"kind": "flatpak_app", "resource": app_id, "status": "already_converged"}
    if dry_run:
        return {"kind": "flatpak_app", "resource": app_id, "status": "would_install"}
    mutation_id = _prepare_external_mutation(
        store=store, state=state, app_version=app_version,
        kind="flatpak_app_install", resource=app_id,
        evidence={"before_present": False, "desired_present": True},
    )
    runner.run(["flatpak", "--user", "install", "-y", remote, app_id], capture=None)
    try:
        _save_receipt(store, state, app_version, {"kind": "flatpak_app", "resource": app_id, "remote": remote})
    except Exception:
        runner.run(["flatpak", "--user", "uninstall", "-y", app_id], check=False, capture=None)
        raise
    _finish_external_mutation(
        store=store, state=state, app_version=app_version, mutation_id=mutation_id
    )
    return {"kind": "flatpak_app", "resource": app_id, "status": "installed"}


def apply_service_state(
    *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str,
    unit: str, user: bool, dry_run: bool
) -> dict[str, Any]:
    resource = ("user:" if user else "system:") + unit
    systemctl = ["systemctl", "--user"] if user else _sudo() + ["systemctl"]
    probe = runner.run(systemctl + ["cat", unit], check=False)
    if probe.returncode != 0:
        return {"kind": "service", "resource": resource, "status": "skipped", "reason": "unit_missing"}
    enabled_cp = runner.run(systemctl + ["is-enabled", unit], check=False)
    active_cp = runner.run(systemctl + ["is-active", unit], check=False)
    original_enabled = (enabled_cp.stdout or "").strip() == "enabled"
    original_active = (active_cp.stdout or "").strip() == "active"
    if original_enabled and original_active:
        return {"kind": "service", "resource": resource, "status": "already_converged"}
    if dry_run:
        return {"kind": "service", "resource": resource, "status": "would_change", "to": "enabled+active"}
    mutation_id = _prepare_external_mutation(
        store=store, state=state, app_version=app_version,
        kind="service_enable_start", resource=resource,
        evidence={
            "before_enabled": original_enabled,
            "before_active": original_active,
            "desired_enabled": True,
            "desired_active": True,
            "user": user,
        },
    )
    runner.run(systemctl + ["enable", "--now", unit], capture=None)
    try:
        _save_receipt(store, state, app_version, {
            "kind": "service", "resource": resource, "unit": unit, "user": user,
            "original_enabled": original_enabled, "original_active": original_active,
            "applied_enabled": True, "applied_active": True,
        })
    except Exception:
        if not original_enabled:
            runner.run(systemctl + ["disable", unit], check=False, capture=None)
        if not original_active:
            runner.run(systemctl + ["stop", unit], check=False, capture=None)
        raise
    _finish_external_mutation(
        store=store, state=state, app_version=app_version, mutation_id=mutation_id
    )
    return {"kind": "service", "resource": resource, "status": "changed", "to": "enabled+active"}
