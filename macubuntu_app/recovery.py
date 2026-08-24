from __future__ import annotations

from typing import Any

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

    # Unknown/external receipts can contain paths, commands or other local data.
    # Do not echo them into recovery JSON until that kind has a dedicated,
    # privacy-reviewed probe.
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
        if store.backup_path.exists():
            backup = store._read_path(store.backup_path)
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

    status = "inconsistent" if inconsistent else "receipts_consistent"
    if not transaction_receipts:
        status = "no_receipted_mutations"

    return {
        "ok": False,
        "required": True,
        "status": status,
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
