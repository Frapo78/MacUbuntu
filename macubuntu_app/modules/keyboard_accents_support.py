from __future__ import annotations

import ast
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

from ..external import apply_managed_text_file, uninstall_external_operation
from ..external_core import _tree_digest
from ..state import StateStore, now_iso
from ..system import gsettings_get, gsettings_set
from ..util import Runner

INPUT_SCHEMA = "org.gnome.desktop.input-sources"
LEGACY_SOURCE = ("ibus", "macubuntu-accents")


def parse_sources(raw: str | None) -> list[tuple[str, str]] | None:
    if raw is None:
        return None
    text = raw.strip()
    if text.startswith("@a(ss) "):
        text = text[len("@a(ss) "):]
    try:
        value = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None
    if not isinstance(value, list):
        return None
    result: list[tuple[str, str]] = []
    for item in value:
        if not isinstance(item, tuple) or len(item) != 2:
            return None
        result.append((str(item[0]), str(item[1])))
    return result


def migrate_legacy_input_source(
    *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str,
    dry_run: bool,
) -> list[dict[str, Any]]:
    """Remove v0.6's visible IBus source and release its stale snapshots."""
    results: list[dict[str, Any]] = []
    for key in ("sources", "mru-sources"):
        raw = gsettings_get(runner, INPUT_SCHEMA, key)
        current = parse_sources(raw)
        receipts = [
            op for op in state.get("operations", [])
            if op.get("kind") == "gsettings"
            and op.get("schema") == INPUT_SCHEMA
            and op.get("key") == key
        ]
        resource = f"{INPUT_SCHEMA}::{key}"
        if current is None:
            results.append({"kind": "gsettings", "resource": resource, "status": "skipped", "reason": "input_sources_unreadable"})
            continue

        present = LEGACY_SOURCE in current
        desired = [source for source in current if source != LEGACY_SOURCE]
        if key == "sources" and present and not desired:
            results.append({"kind": "gsettings", "resource": resource, "status": "kept", "reason": "no_fallback_input_source"})
            continue

        if dry_run:
            status = "would_remove_legacy_source" if present else (
                "would_release_legacy_receipt" if receipts else "already_converged"
            )
            results.append({"kind": "gsettings", "resource": resource, "status": status})
            continue

        before = list(state.get("operations", []))
        changed = False
        try:
            if present:
                gsettings_set(runner, INPUT_SCHEMA, key, repr(desired))
                changed = True
            if receipts:
                state["operations"] = [op for op in state.get("operations", []) if op not in receipts]
                store.save(state, app_version)
        except Exception:
            state["operations"] = before
            if changed and raw is not None:
                gsettings_set(runner, INPUT_SCHEMA, key, raw)
            raise

        results.append({
            "kind": "gsettings", "resource": resource,
            "status": "legacy_source_removed" if present else (
                "legacy_receipt_released" if receipts else "already_converged"
            ),
        })
    return results


def _owned_receipt(state: dict[str, Any], resource: str) -> dict[str, Any] | None:
    for op in state.get("operations", []):
        if op.get("kind") == "owned_paths" and op.get("resource") == resource:
            return op
    return None


def apply_or_upgrade_text_file(
    *, store: StateStore, state: dict[str, Any], app_version: str,
    resource: str, path: Path, content: str, mode: int, dry_run: bool,
) -> dict[str, Any]:
    """Update an unchanged MacUbuntu-owned v0.6 file, never user drift."""
    receipt = _owned_receipt(state, resource)
    if not path.exists() or receipt is None:
        return apply_managed_text_file(
            store=store, state=state, app_version=app_version, resource=resource,
            path=path, content=content, mode=mode, dry_run=dry_run,
        )

    entries = receipt.get("paths", [])
    if not entries:
        return {"kind": "owned_paths", "resource": resource, "status": "kept", "reason": "receipt_incomplete"}
    entry = entries[0]
    expected = entry.get("digest")
    if not expected or _tree_digest(path) != expected:
        return {"kind": "owned_paths", "resource": resource, "status": "kept", "reason": "drift_detected", "path": str(path)}

    try:
        current_text = path.read_text(encoding="utf-8")
        current_mode = stat.S_IMODE(path.stat().st_mode)
    except OSError as exc:
        return {"kind": "owned_paths", "resource": resource, "status": "kept", "reason": "owned_file_unreadable", "error": str(exc)}
    if current_text == content and current_mode == mode:
        return {"kind": "owned_paths", "resource": resource, "status": "already_converged"}
    if dry_run:
        return {"kind": "owned_paths", "resource": resource, "status": "would_update", "path": str(path)}

    old_bytes = path.read_bytes()
    old_mode = current_mode
    old_digest = expected
    old_updated = receipt.get("updated_at")
    temp: Path | None = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.macubuntu-", dir=str(path.parent))
        os.close(fd)
        temp = Path(temp_name)
        temp.write_text(content, encoding="utf-8")
        temp.chmod(mode)
        os.replace(temp, path)
        temp = None
        entry["digest"] = _tree_digest(path)
        receipt["updated_at"] = now_iso()
        store.save(state, app_version)
    except Exception:
        if temp is not None:
            temp.unlink(missing_ok=True)
        restore = path.with_name(path.name + ".macubuntu-restore")
        restore.write_bytes(old_bytes)
        restore.chmod(old_mode)
        os.replace(restore, path)
        entry["digest"] = old_digest
        if old_updated is None:
            receipt.pop("updated_at", None)
        else:
            receipt["updated_at"] = old_updated
        raise
    return {"kind": "owned_paths", "resource": resource, "status": "updated", "path": str(path)}


def retire_owned_resource(
    *, resource: str, runner: Runner, store: StateStore, state: dict[str, Any],
    app_version: str, dry_run: bool,
) -> dict[str, Any] | None:
    op = _owned_receipt(state, resource)
    if op is None:
        return None
    return uninstall_external_operation(
        op=op, runner=runner, store=store, state=state, app_version=app_version,
        force=False, dry_run=dry_run,
    )
