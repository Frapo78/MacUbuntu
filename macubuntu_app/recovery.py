from __future__ import annotations

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
        matched = 0
        missing = 0
        drifted = 0
        for entry in entries:
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("path"), str)
                or not isinstance(entry.get("digest"), str)
            ):
                return {**result, "status": "unverifiable", "reason": "invalid_receipt"}
            current = _tree_digest(Path(entry["path"]))
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
        return {**result, "status": "applied" if _flatpak_remote_exists(runner, name) else "original"}

    if kind == "flatpak_app":
        app_id = op.get("resource")
        if not isinstance(app_id, str) or not app_id:
            return {**result, "status": "unverifiable", "reason": "invalid_receipt"}
        result["resource"] = app_id
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
            current_digest = _tree_digest(Path(path))
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
    receipt is persisted. Current receipts can therefore prove inconsistencies,
    but cannot by themselves prove that no unreceipted change exists.
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
    inconsistent = any(
        item["status"] in {"original", "partial", "drifted", "unverifiable"}
        for item in evidence
    )

    backup_operation_count = None
    if isinstance(backup, dict):
        backup_operations = backup.get("operations", [])
        if isinstance(backup_operations, list):
            backup_operation_count = len(backup_operations)

    classification = "inconsistent" if inconsistent else "receipts_consistent"
    if not transaction_receipts:
        classification = "no_receipted_mutations"

    return {
        "ok": False,
        "required": True,
        "status": "transaction_interrupted",
        "classification": classification,
        "decision": "manual_review",
        "automatic_mutation": False,
        "reason": "unreceipted_mutation_cannot_be_excluded",
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
        "evidence": evidence,
    }
