from __future__ import annotations

import hashlib
from typing import Any

from .state import StateStore, now_iso
from .system import gsettings_get, gsettings_set
from .util import Runner, apt_base_command, installed_deb_packages, package_installed


def _value_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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
    pending = store.prepare_mutation(
        state,
        app_version,
        kind="gsettings_set",
        resource=f"{schema}::{key}",
        evidence={"before_sha256": _value_digest(current), "desired_sha256": _value_digest(desired)},
    )
    gsettings_set(runner, schema, key, desired)
    created_receipt = receipt is None
    previous_applied = receipt.get("applied") if receipt else None
    previous_updated_at = receipt.get("updated_at") if receipt else None
    if receipt is None:
        receipt = {"kind": "gsettings", "schema": schema, "key": key, "original": original, "applied": desired, "created_at": now_iso()}
        state["operations"].append(receipt)
    else:
        receipt["applied"] = desired
        receipt["updated_at"] = now_iso()
    try:
        store.save(state, app_version)
    except Exception:
        # GSettings is cheap to restore. Never leave a setting mutated merely
        # because its ownership receipt could not be persisted. The persisted
        # pending mutation is intentionally left in place if state persistence
        # is unhealthy, so doctor can fail closed on the next run.
        gsettings_set(runner, schema, key, current)
        if created_receipt:
            state["operations"].remove(receipt)
        else:
            receipt["applied"] = previous_applied
            if previous_updated_at is None:
                receipt.pop("updated_at", None)
            else:
                receipt["updated_at"] = previous_updated_at
        raise
    store.clear_pending_mutation(state, app_version, mutation_id=pending["id"])
    return {"kind": "gsettings", "resource": f"{schema}::{key}", "status": "changed", "from": current, "to": desired}


def apply_apt_bundle(*, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, requested: list[str], dry_run: bool) -> dict[str, Any]:
    missing = [p for p in requested if not package_installed(runner, p)]
    receipt = _find_apt_receipt(state, requested)
    if not missing:
        return {"kind": "apt_bundle", "resource": ",".join(requested), "status": "already_converged"}
    if dry_run:
        return {"kind": "apt_bundle", "resource": ",".join(requested), "status": "would_install", "packages": missing}

    before = installed_deb_packages(runner)
    pending = store.prepare_mutation(
        state,
        app_version,
        kind="apt_install",
        resource=",".join(requested),
        evidence={"missing_before": list(missing)},
    )
    runner.run(apt_base_command() + ["install", "-y", *missing], capture=None)
    after = installed_deb_packages(runner)
    added = sorted(after - before)
    if receipt is None:
        receipt = {"kind": "apt_bundle", "requested": list(requested), "added": added, "created_at": now_iso()}
        state["operations"].append(receipt)
    else:
        receipt["added"] = sorted(set(receipt.get("added", [])) | set(added))
        receipt["updated_at"] = now_iso()
    store.save(state, app_version)
    store.clear_pending_mutation(state, app_version, mutation_id=pending["id"])
    return {"kind": "apt_bundle", "resource": ",".join(requested), "status": "installed", "requested": missing, "added": added}


def uninstall_operations(*, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, force: bool, dry_run: bool) -> list[dict[str, Any]]:
    from .external import uninstall_external_operation

    results: list[dict[str, Any]] = []
    for op in list(reversed(state.get("operations", []))):
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
            pending = store.prepare_mutation(
                state,
                app_version,
                kind="gsettings_restore",
                resource=f"{schema}::{key}",
                evidence={"before_sha256": _value_digest(current), "original_sha256": _value_digest(original)},
            )
            gsettings_set(runner, schema, key, original)
            results.append({"kind": "gsettings", "resource": f"{schema}::{key}", "status": "restored", "from": current, "to": original, "forced": bool(drifted and force)})
            state["operations"].remove(op)
            store.save(state, app_version)
            store.clear_pending_mutation(state, app_version, mutation_id=pending["id"])

        elif op.get("kind") == "apt_bundle":
            added = [p for p in op.get("added", []) if package_installed(runner, p)]

            # Flatpak is an application runtime, not just a dependency. If the
            # user adopted a MacUbuntu-installed Flatpak setup by installing
            # another user app, removing the runtime would break that app even
            # though APT cannot see the semantic dependency. Release ownership
            # conservatively instead.
            if "flatpak" in added and runner.exists("flatpak"):
                flatpak_apps = runner.run(
                    ["flatpak", "--user", "list", "--app", "--columns=application"],
                    check=False,
                )
                user_apps = [line for line in (flatpak_apps.stdout or "").splitlines() if line.strip()]
                if user_apps:
                    results.append({
                        "kind": "apt_bundle",
                        "resource": ",".join(op.get("requested", [])),
                        "status": "would_release" if dry_run else "released",
                        "reason": "flatpak_runtime_adopted_by_user",
                        "user_apps": user_apps,
                    })
                    if not dry_run:
                        state["operations"].remove(op)
                        store.save(state, app_version)
                    continue

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
            pending = store.prepare_mutation(
                state,
                app_version,
                kind="apt_purge",
                resource=",".join(op.get("requested", [])),
                evidence={"packages_present_before": list(added)},
            )
            runner.run(apt_base_command() + ["purge", "-y", *added], capture=None)
            results.append({"kind": "apt_bundle", "resource": ",".join(op.get("requested", [])), "status": "removed", "packages": added, "forced": bool(extra and force)})
            state["operations"].remove(op)
            store.save(state, app_version)
            store.clear_pending_mutation(state, app_version, mutation_id=pending["id"])
        else:
            external = uninstall_external_operation(
                op=op, runner=runner, store=store, state=state, app_version=app_version,
                force=force, dry_run=dry_run,
            )
            if external is None:
                results.append({"kind": op.get("kind", "unknown"), "status": "kept", "reason": "unknown_operation_kind"})
            else:
                results.append(external)

    if not dry_run:
        store.remove_if_empty(state)
    return results
