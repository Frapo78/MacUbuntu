from __future__ import annotations

from typing import Any

from .state import StateStore, now_iso
from .system import gsettings_get, gsettings_set
from .util import Runner, apt_base_command, installed_deb_packages, package_installed


def _find_setting_receipt(state: dict[str, Any], schema: str, key: str) -> dict[str, Any] | None:
    for op in state.get("operations", []):
        if op.get("kind") == "gsettings" and op.get("schema") == schema and op.get("key") == key:
            return op
    return None


def _find_apt_receipt(state: dict[str, Any], requested: list[str]) -> dict[str, Any] | None:
    wanted = sorted(requested)
    for op in state.get("operations", []):
        if op.get("kind") == "apt_bundle" and sorted(op.get("requested", [])) == wanted:
            return op
    return None


def apply_gsetting(*, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, schema: str, key: str, desired: str, dry_run: bool) -> dict[str, Any]:
    current = gsettings_get(runner, schema, key)
    if current is None:
        return {"kind": "gsettings", "resource": f"{schema}::{key}", "status": "skipped", "reason": "schema_or_key_missing"}

    receipt = _find_setting_receipt(state, schema, key)
    if current == desired:
        return {"kind": "gsettings", "resource": f"{schema}::{key}", "status": "already_converged", "current": current}

    if dry_run:
        return {"kind": "gsettings", "resource": f"{schema}::{key}", "status": "would_change", "from": current, "to": desired, "managed": receipt is not None}

    original = receipt["original"] if receipt else current
    gsettings_set(runner, schema, key, desired)
    if receipt is None:
        receipt = {"kind": "gsettings", "schema": schema, "key": key, "original": original, "applied": desired, "created_at": now_iso()}
        state["operations"].append(receipt)
    else:
        receipt["applied"] = desired
        receipt["updated_at"] = now_iso()
    store.save(state, app_version)
    return {"kind": "gsettings", "resource": f"{schema}::{key}", "status": "changed", "from": current, "to": desired}


def apply_apt_bundle(*, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, requested: list[str], dry_run: bool) -> dict[str, Any]:
    missing = [p for p in requested if not package_installed(runner, p)]
    receipt = _find_apt_receipt(state, requested)
    if not missing:
        return {"kind": "apt_bundle", "resource": ",".join(requested), "status": "already_converged"}
    if dry_run:
        return {"kind": "apt_bundle", "resource": ",".join(requested), "status": "would_install", "packages": missing}

    before = installed_deb_packages(runner)
    runner.run(apt_base_command() + ["install", "-y", *missing], capture=False)
    after = installed_deb_packages(runner)
    added = sorted(after - before)
    if receipt is None:
        receipt = {"kind": "apt_bundle", "requested": list(requested), "added": added, "created_at": now_iso()}
        state["operations"].append(receipt)
    else:
        receipt["added"] = sorted(set(receipt.get("added", [])) | set(added))
        receipt["updated_at"] = now_iso()
    store.save(state, app_version)
    return {"kind": "apt_bundle", "resource": ",".join(requested), "status": "installed", "requested": missing, "added": added}


def uninstall_operations(*, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, force: bool, dry_run: bool) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for op in reversed(state.get("operations", [])):
        if op.get("kind") == "gsettings":
            schema, key = op["schema"], op["key"]
            current = gsettings_get(runner, schema, key)
            applied, original = op["applied"], op["original"]
            if current is None:
                results.append({"kind": "gsettings", "resource": f"{schema}::{key}", "status": "skipped", "reason": "schema_or_key_missing"})
                continue
            drifted = current != applied
            if drifted and not force:
                results.append({"kind": "gsettings", "resource": f"{schema}::{key}", "status": "kept", "reason": "drift_detected", "current": current, "macubuntu_applied": applied, "original": original})
                continue
            if dry_run:
                results.append({"kind": "gsettings", "resource": f"{schema}::{key}", "status": "would_restore", "from": current, "to": original, "forced": bool(drifted and force)})
                continue
            gsettings_set(runner, schema, key, original)
            results.append({"kind": "gsettings", "resource": f"{schema}::{key}", "status": "restored", "from": current, "to": original, "forced": bool(drifted and force)})
            state["operations"].remove(op)
            store.save(state, app_version)

        elif op.get("kind") == "apt_bundle":
            added = [p for p in op.get("added", []) if package_installed(runner, p)]
            if not added:
                results.append({"kind": "apt_bundle", "resource": ",".join(op.get("requested", [])), "status": "already_absent"})
                if not dry_run:
                    state["operations"].remove(op)
                    store.save(state, app_version)
                continue

            simulate = runner.run(apt_base_command() + ["-s", "purge", *added], check=False)
            removals: set[str] = set()
            for line in (simulate.stdout or "").splitlines():
                if line.startswith("Remv ") or line.startswith("Purg "):
                    parts = line.split()
                    if len(parts) >= 2:
                        removals.add(parts[1])
            extra = sorted(removals - set(added))
            if simulate.returncode != 0:
                results.append({"kind": "apt_bundle", "resource": ",".join(op.get("requested", [])), "status": "kept", "reason": "apt_simulation_failed"})
                continue
            if extra and not force:
                results.append({"kind": "apt_bundle", "resource": ",".join(op.get("requested", [])), "status": "kept", "reason": "dependency_conflict", "would_also_remove": extra})
                continue
            if dry_run:
                results.append({"kind": "apt_bundle", "resource": ",".join(op.get("requested", [])), "status": "would_remove", "packages": added, "would_also_remove": extra, "forced": bool(extra and force)})
                continue
            runner.run(apt_base_command() + ["purge", "-y", *added], capture=False)
            results.append({"kind": "apt_bundle", "resource": ",".join(op.get("requested", [])), "status": "removed", "packages": added, "forced": bool(extra and force)})
            state["operations"].remove(op)
            store.save(state, app_version)
        else:
            results.append({"kind": op.get("kind", "unknown"), "status": "kept", "reason": "unknown_operation_kind"})

    if not dry_run:
        store.remove_if_empty(state)
    return results
