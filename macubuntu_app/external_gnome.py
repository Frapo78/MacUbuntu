from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .external_core import (
    ExternalOperationError, _download, _enabled_extensions,
    _extension_known, _extension_user_dir, _find_receipt, _safe_extract,
    _save_receipt, _set_enabled_extensions, _tree_digest,
)
from .state import StateStore
from .util import Runner

EGO_REVIEW_DOWNLOAD = "https://extensions.gnome.org/review/download/{review_id}.shell-extension.zip"


def apply_extension_state(
    *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, uuid: str, dry_run: bool
) -> dict[str, Any]:
    enabled = _enabled_extensions(runner)
    if uuid in enabled:
        return {"kind": "gnome_extension", "resource": uuid, "status": "already_converged"}
    if dry_run:
        return {"kind": "gnome_extension", "resource": uuid, "status": "would_change", "to": "enabled"}
    enabled.append(uuid)
    _set_enabled_extensions(runner, enabled)
    try:
        _save_receipt(store, state, app_version, {
            "kind": "gnome_extension", "resource": uuid, "installed_by_macubuntu": False,
            "original_enabled": False, "applied_enabled": True, "path": None, "digest": None,
        })
    except Exception:
        _set_enabled_extensions(runner, [value for value in enabled if value != uuid])
        raise
    return {"kind": "gnome_extension", "resource": uuid, "status": "changed", "to": "enabled", "session_restart_required": True}


def apply_gnome_extension(
    *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str,
    uuid: str, version: int, review_id: int, shell_major: str, dry_run: bool
) -> dict[str, Any]:
    receipt = _find_receipt(state, "gnome_extension", uuid)
    enabled = _enabled_extensions(runner)
    known = _extension_known(runner, uuid)
    user_dir = _extension_user_dir(uuid)

    if known and uuid in enabled:
        if receipt and receipt.get("installed_by_macubuntu") and receipt.get("path") and receipt.get("digest"):
            managed_path = Path(receipt["path"])
            if managed_path.exists() and _tree_digest(managed_path) != receipt["digest"]:
                return {"kind": "gnome_extension", "resource": uuid, "status": "kept", "reason": "drift_detected"}
        return {"kind": "gnome_extension", "resource": uuid, "status": "already_converged"}
    if dry_run:
        return {
            "kind": "gnome_extension",
            "resource": uuid,
            "status": "would_install" if not known else "would_change",
            "version": version,
            "review_id": review_id,
        }

    installed_now = False
    if not known:
        if user_dir.exists():
            return {"kind": "gnome_extension", "resource": uuid, "status": "skipped", "reason": "preexisting_unmanaged_path"}
        user_dir.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="macubuntu-extension-") as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "extension.zip"
            url = EGO_REVIEW_DOWNLOAD.format(review_id=review_id)
            _download(url, archive, resource=uuid)
            extract = tmp_path / "extract"
            extract.mkdir()
            _safe_extract(archive, extract, resource=uuid)
            metadata_path = extract / "metadata.json"
            if not metadata_path.exists():
                raise ExternalOperationError("extension_metadata_missing", uuid, "extension archive has no metadata.json")
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                raise ExternalOperationError("extension_metadata_invalid", uuid, str(exc)) from exc
            if metadata.get("uuid") != uuid:
                raise ExternalOperationError("extension_uuid_mismatch", uuid, f"expected {uuid}, got {metadata.get('uuid')}")
            try:
                archive_version = int(metadata.get("version"))
            except (TypeError, ValueError) as exc:
                raise ExternalOperationError("extension_version_missing", uuid, "extension archive has no valid EGO version") from exc
            if archive_version != version:
                raise ExternalOperationError(
                    "extension_version_mismatch",
                    uuid,
                    f"expected EGO version {version}, review {review_id} contains version {archive_version}",
                )
            supported = [str(value).split(".", 1)[0] for value in metadata.get("shell-version", [])]
            if shell_major not in supported:
                raise ExternalOperationError("extension_incompatible", uuid, f"v{version} does not declare GNOME {shell_major}")
            try:
                shutil.copytree(extract, user_dir)
            except OSError as exc:
                if user_dir.exists():
                    shutil.rmtree(user_dir, ignore_errors=True)
                raise ExternalOperationError("extension_install_failed", uuid, str(exc)) from exc
        installed_now = True

    current_enabled = _enabled_extensions(runner)
    original_enabled = uuid in current_enabled
    if not original_enabled:
        current_enabled.append(uuid)
        _set_enabled_extensions(runner, current_enabled)

    try:
        if receipt is None:
            _save_receipt(store, state, app_version, {
                "kind": "gnome_extension", "resource": uuid,
                "installed_by_macubuntu": installed_now,
                "original_enabled": original_enabled,
                "applied_enabled": True,
                "path": str(user_dir) if installed_now else None,
                "digest": _tree_digest(user_dir) if installed_now else None,
                "version": version,
                "review_id": review_id,
                "shell_major": shell_major,
            })
        elif installed_now:
            receipt.update({
                "installed_by_macubuntu": True,
                "path": str(user_dir),
                "digest": _tree_digest(user_dir),
                "version": version,
                "review_id": review_id,
            })
            store.save(state, app_version)
    except Exception:
        # Restore the user-visible state if ownership cannot be persisted.
        restored_enabled = _enabled_extensions(runner)
        if not original_enabled and uuid in restored_enabled:
            restored_enabled.remove(uuid)
            _set_enabled_extensions(runner, restored_enabled)
        if installed_now and user_dir.exists():
            shutil.rmtree(user_dir, ignore_errors=True)
        raise

    return {
        "kind": "gnome_extension", "resource": uuid,
        "status": "installed" if installed_now else "changed",
        "version": version,
        "review_id": review_id,
        "session_restart_required": True,
    }
