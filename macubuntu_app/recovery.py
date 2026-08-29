from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .external_core import (
    _enabled_extensions,
    _flatpak_app_installed,
    _flatpak_remote_exists,
    _tree_digest,
    apt_repository_present,
)
from .system import gsettings_get
from .util import Runner, package_installed


def _value_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _probe_pending_mutation(runner: Runner, pending: dict[str, Any]) -> dict[str, Any]:
    """Classify one durable pre-mutation intent without exposing raw evidence."""
    kind = pending.get("kind", "unknown")
    result: dict[str, Any] = {
        "id": pending.get("id"),
        "kind": kind,
        "status": "unverifiable",
    }
    resource = pending.get("resource")
    evidence = pending.get("evidence")
    if not isinstance(evidence, dict):
        return {**result, "reason": "invalid_pending_evidence"}

    if kind in {"gsettings_set", "gsettings_restore"}:
        if not isinstance(resource, str) or "::" not in resource:
            return {**result, "reason": "invalid_pending_resource"}
        schema, key = resource.split("::", 1)
        if not schema or not key:
            return {**result, "reason": "invalid_pending_resource"}
        current = gsettings_get(runner, schema, key)
        if current is None:
            return {
                **result,
                "resource": resource,
                "reason": "schema_or_key_missing",
            }
        before_digest = evidence.get("before_sha256")
        target_key = "desired_sha256" if kind == "gsettings_set" else "original_sha256"
        target_digest = evidence.get(target_key)
        if not isinstance(before_digest, str) or not isinstance(target_digest, str):
            return {
                **result,
                "resource": resource,
                "reason": "invalid_pending_evidence",
            }
        current_digest = _value_digest(current)
        if current_digest == target_digest:
            status = "applied"
        elif current_digest == before_digest:
            status = "original"
        else:
            status = "drifted"
        return {
            "id": pending.get("id"),
            "kind": kind,
            "resource": resource,
            "status": status,
        }

    if kind in {"apt_install", "apt_purge"}:
        evidence_key = "missing_before" if kind == "apt_install" else "packages_present_before"
        packages = evidence.get(evidence_key)
        if (
            not isinstance(packages, list)
            or not packages
            or any(not isinstance(package, str) or not package for package in packages)
        ):
            return {**result, "reason": "invalid_pending_evidence"}
        present = [package for package in packages if package_installed(runner, package)]
        if kind == "apt_install":
            if len(present) == len(packages):
                status = "applied"
            elif not present:
                status = "original"
            else:
                status = "partial"
        else:
            if not present:
                status = "applied"
            elif len(present) == len(packages):
                status = "original"
            else:
                status = "partial"
        return {
            "id": pending.get("id"),
            "kind": kind,
            "status": status,
            "packages_checked": len(packages),
            "packages_present": len(present),
        }

    if kind == "apt_repository_add":
        if not isinstance(resource, str) or not resource.startswith("ppa:"):
            return {**result, "reason": "invalid_pending_resource"}
        before_present = evidence.get("before_present")
        desired_present = evidence.get("desired_present")
        if not isinstance(before_present, bool) or not isinstance(desired_present, bool):
            return {**result, "resource": resource, "reason": "invalid_pending_evidence"}
        current_present = apt_repository_present(resource)
        if current_present == desired_present:
            status = "applied"
        elif current_present == before_present:
            status = "original"
        else:
            status = "drifted"
        return {
            "id": pending.get("id"),
            "kind": kind,
            "resource": resource,
            "status": status,
        }

    if kind in {"flatpak_remote_add", "flatpak_app_install"}:
        if not isinstance(resource, str) or not resource:
            return {**result, "reason": "invalid_pending_resource"}
        before_present = evidence.get("before_present")
        desired_present = evidence.get("desired_present")
        if not isinstance(before_present, bool) or not isinstance(desired_present, bool):
            return {**result, "reason": "invalid_pending_evidence"}
        if not runner.exists("flatpak"):
            return {**result, "reason": "flatpak_unavailable"}
        current_present = (
            _flatpak_remote_exists(runner, resource)
            if kind == "flatpak_remote_add"
            else _flatpak_app_installed(runner, resource)
        )
        if current_present == desired_present:
            status = "applied"
        elif current_present == before_present:
            status = "original"
        else:
            status = "drifted"
        return {
            "id": pending.get("id"),
            "kind": kind,
            "resource": resource,
            "status": status,
        }

    if kind == "service_enable_start":
        if not isinstance(resource, str) or ":" not in resource:
            return {**result, "reason": "invalid_pending_resource"}
        user = evidence.get("user")
        before_enabled = evidence.get("before_enabled")
        before_active = evidence.get("before_active")
        desired_enabled = evidence.get("desired_enabled")
        desired_active = evidence.get("desired_active")
        if not all(
            isinstance(value, bool)
            for value in (
                user,
                before_enabled,
                before_active,
                desired_enabled,
                desired_active,
            )
        ):
            return {**result, "reason": "invalid_pending_evidence"}
        prefix = "user:" if user else "system:"
        if not resource.startswith(prefix) or not resource[len(prefix):]:
            return {**result, "reason": "invalid_pending_resource"}
        unit = resource[len(prefix):]
        if "/" in unit or "\\" in unit or any(character.isspace() for character in unit):
            return {**result, "reason": "invalid_pending_resource"}
        systemctl = ["systemctl", "--user"] if user else ["systemctl"]
        probe_cp = runner.run(systemctl + ["cat", unit], check=False)
        if probe_cp.returncode != 0:
            return {
                **result,
                "resource": resource,
                "reason": "unit_missing_or_unreadable",
            }
        enabled_cp = runner.run(systemctl + ["is-enabled", unit], check=False)
        active_cp = runner.run(systemctl + ["is-active", unit], check=False)
        enabled = (enabled_cp.stdout or "").strip() == "enabled"
        active = (active_cp.stdout or "").strip() == "active"
        if enabled == desired_enabled and active == desired_active:
            status = "applied"
        elif enabled == before_enabled and active == before_active:
            status = "original"
        else:
            status = "partial"
        return {
            "id": pending.get("id"),
            "kind": kind,
            "resource": resource,
            "status": status,
            "enabled": enabled,
            "active": active,
        }

    # Pending evidence may contain private paths, commands or future resource
    # details. Unknown kinds are therefore summarized without echoing resource
    # or evidence fields until a dedicated privacy review exists.
    return {**result, "reason": "probe_not_implemented"}


def _probe_receipt(runner: Runner, op: dict[str, Any], index: int) -> dict[str, Any]:
    kind = op.get("kind", "unknown")
    result: dict[str, Any] = {"index": index, "kind": kind}

    if kind == "gsettings":
        schema = op.get("schema")
        key = op.get("key")
        if not isinstance(schema, str) or not isinstance(key, str):
            return {**result, "status": "unverifiable", "reason": "invalid_receipt"}
        result["resource"] = f"{schema}::{key}"
        current = gsettings_get(runner, schema, key)
        if current is None:
            return {**result, "status": "unverifiable", "reason": "schema_or_key_missing"}
        if current == op.get("applied"):
            return {**result, "status": "applied"}
        if current == op.get("original"):
            return {**result, "status": "original"}
        return {**result, "status": "drifted"}

    if kind == "apt_bundle":
        requested = [p for p in op.get("requested", []) if isinstance(p, str)]
        added = [p for p in op.get("added", []) if isinstance(p, str)]
        result["resource"] = ",".join(requested)
        if not added:
            return {**result, "status": "no_owned_delta"}
        present = [p for p in added if package_installed(runner, p)]
        if len(present) == len(added):
            return {**result, "status": "applied", "owned_packages_present": len(present)}
        if not present:
            return {**result, "status": "original", "owned_packages_present": 0}
        return {
            **result,
            "status": "partial",
            "owned_packages_present": len(present),
            "owned_packages_expected": len(added),
        }

    if kind == "owned_paths":
        entries = op.get("paths")
        if not isinstance(entries, list) or not entries:
            return {**result, "status": "unverifiable", "reason": "invalid_receipt"}
        matched = missing = drifted = 0
        for entry in entries:
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("path"), str)
                or not isinstance(entry.get("digest"), str)
            ):
                return {**result, "status": "unverifiable", "reason": "invalid_receipt"}
            try:
                current = _tree_digest(Path(entry["path"]))
            except (OSError, RuntimeError):
                return {**result, "status": "unverifiable", "reason": "managed_path_unreadable"}
            if current == "missing":
                missing += 1
            elif current == entry["digest"]:
                matched += 1
            else:
                drifted += 1
        summary = {
            **result,
            "managed_paths": len(entries),
            "matching_paths": matched,
            "missing_paths": missing,
        }
        if drifted:
            return {**summary, "status": "drifted", "drifted_paths": drifted}
        if matched == len(entries):
            return {**summary, "status": "applied"}
        if missing == len(entries):
            return {**summary, "status": "original"}
        return {**summary, "status": "partial"}

    if kind == "apt_repository":
        ppa = op.get("ppa")
        if not isinstance(ppa, str) or not ppa.startswith("ppa:"):
            return {**result, "status": "unverifiable", "reason": "invalid_receipt"}
        result["resource"] = ppa
        return {**result, "status": "applied" if apt_repository_present(ppa) else "original"}

    if kind == "flatpak_remote":
        name = op.get("resource")
        if not isinstance(name, str) or not name:
            return {**result, "status": "unverifiable", "reason": "invalid_receipt"}
        result["resource"] = name
        if not runner.exists("flatpak"):
            return {**result, "status": "unverifiable", "reason": "flatpak_unavailable"}
        return {**result, "status": "applied" if _flatpak_remote_exists(runner, name) else "original"}

    if kind == "flatpak_app":
        app_id = op.get("resource")
        if not isinstance(app_id, str) or not app_id:
            return {**result, "status": "unverifiable", "reason": "invalid_receipt"}
        result["resource"] = app_id
        if not runner.exists("flatpak"):
            return {**result, "status": "unverifiable", "reason": "flatpak_unavailable"}
        return {**result, "status": "applied" if _flatpak_app_installed(runner, app_id) else "original"}

    if kind == "gnome_extension":
        uuid = op.get("resource")
        if not isinstance(uuid, str) or not uuid:
            return {**result, "status": "unverifiable", "reason": "invalid_receipt"}
        result["resource"] = uuid
        enabled = uuid in _enabled_extensions(runner)
        installed_by_macubuntu = bool(op.get("installed_by_macubuntu"))
        if installed_by_macubuntu:
            path = op.get("path")
            digest = op.get("digest")
            if not isinstance(path, str) or not isinstance(digest, str):
                return {**result, "status": "unverifiable", "reason": "invalid_receipt"}
            try:
                current_digest = _tree_digest(Path(path))
            except (OSError, RuntimeError):
                return {**result, "status": "unverifiable", "reason": "extension_path_unreadable"}
            if current_digest == "missing":
                return {
                    **result,
                    "status": "partial" if enabled else "original",
                    "enabled": enabled,
                    "files": "missing",
                }
            if current_digest != digest:
                return {**result, "status": "drifted", "enabled": enabled, "files": "drifted"}
            return {
                **result,
                "status": "applied" if enabled else "partial",
                "enabled": enabled,
                "files": "matching",
            }
        original_enabled = bool(op.get("original_enabled"))
        applied_enabled = bool(op.get("applied_enabled", True))
        if enabled == applied_enabled:
            return {**result, "status": "applied", "enabled": enabled}
        if enabled == original_enabled:
            return {**result, "status": "original", "enabled": enabled}
        return {**result, "status": "drifted", "enabled": enabled}

    if kind == "service":
        unit = op.get("unit")
        user = op.get("user")
        if not isinstance(unit, str) or not unit or not isinstance(user, bool):
            return {**result, "status": "unverifiable", "reason": "invalid_receipt"}
        result["resource"] = ("user:" if user else "system:") + unit
        systemctl = ["systemctl", "--user"] if user else ["systemctl"]
        probe_cp = runner.run(systemctl + ["cat", unit], check=False)
        if probe_cp.returncode != 0:
            return {**result, "status": "unverifiable", "reason": "unit_missing_or_unreadable"}
        enabled_cp = runner.run(systemctl + ["is-enabled", unit], check=False)
        active_cp = runner.run(systemctl + ["is-active", unit], check=False)
        enabled = (enabled_cp.stdout or "").strip() == "enabled"
        active = (active_cp.stdout or "").strip() == "active"
        if (
            enabled == bool(op.get("applied_enabled", True))
            and active == bool(op.get("applied_active", True))
        ):
            return {**result, "status": "applied", "enabled": enabled, "active": active}
        if (
            enabled == bool(op.get("original_enabled"))
            and active == bool(op.get("original_active"))
        ):
            return {**result, "status": "original", "enabled": enabled, "active": active}
        return {**result, "status": "partial", "enabled": enabled, "active": active}

    # Unknown receipts can contain paths, commands or other local data. Do not
    # echo arbitrary fields until that kind has a dedicated privacy-reviewed
    # probe.
    return {**result, "status": "unverifiable", "reason": "probe_not_implemented"}


def inspect_recovery(runner: Runner, store: Any) -> dict[str, Any]:
    """Inspect an interrupted transaction without mutating machine or state.

    A crash may happen after a machine mutation but before the corresponding
    receipt is persisted. Durable pending intent narrows that ambiguity for
    privacy-reviewed mutation kinds, while unknown/external kinds still fail
    closed until they gain equivalent probes.
    """
    health = store.health()
    if health.get("status") != "transaction_interrupted":
        return {
            "ok": True,
            "required": False,
            "status": "none",
            "classification": "none",
            "decision": "no_recovery_needed",
            "transaction": None,
            "evidence": [],
        }

    state = store.load()
    transaction = state.get("transaction") or {}
    baseline = transaction.get("baseline_operation_count", 0)
    operations = state.get("operations", [])
    baseline = baseline if isinstance(baseline, int) and baseline >= 0 else 0
    transaction_receipts = operations[baseline:]

    backup = None
    backup_status = "absent"
    try:
        backup = store.load_backup()
        if backup is not None:
            backup_status = "valid"
    except Exception:
        backup_status = "invalid"

    evidence = [
        _probe_receipt(runner, op, baseline + offset)
        for offset, op in enumerate(transaction_receipts)
    ]
    pending = transaction.get("pending_mutation")
    pending_evidence = _probe_pending_mutation(runner, pending) if isinstance(pending, dict) else None
    inconsistent = any(
        item["status"] in {"original", "partial", "drifted", "unverifiable"}
        for item in evidence
    )
    if pending_evidence and pending_evidence.get("status") in {"partial", "drifted", "unverifiable"}:
        inconsistent = True

    backup_operation_count = None
    if isinstance(backup, dict):
        backup_operations = backup.get("operations", [])
        if isinstance(backup_operations, list):
            backup_operation_count = len(backup_operations)

    classification = "inconsistent" if inconsistent else "receipts_consistent"
    if not transaction_receipts:
        classification = "no_receipted_mutations"

    reason = "unreceipted_mutation_cannot_be_excluded"
    if pending_evidence:
        reason = "pending_mutation_requires_recovery"

    return {
        "ok": False,
        "required": True,
        "status": "transaction_interrupted",
        "classification": classification,
        "decision": "manual_review",
        "automatic_mutation": False,
        "reason": reason,
        "transaction": {
            "id": transaction.get("id"),
            "operation": transaction.get("operation"),
            "status": transaction.get("status"),
            "started_at": transaction.get("started_at"),
            "app_version": transaction.get("app_version"),
            "baseline_operation_count": baseline,
        },
        "counts": {
            "baseline_operations": baseline,
            "current_operations": len(operations),
            "transaction_receipts": len(transaction_receipts),
            "backup_operations": backup_operation_count,
        },
        "backup": {"status": backup_status},
        "pending_mutation": pending_evidence,
        "evidence": evidence,
    }
