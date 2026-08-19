from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Iterable

from .external_core import (
    MAX_ARCHIVE_MEMBERS, ExternalOperationError, _download, _find_receipt, _git_blob_sha1,
    _record_owned_paths, _remove_created_entries, _safe_extract, _tree_digest,
)
from .state import StateStore
from .util import Runner

def apply_pinned_installer(
    *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str,
    resource: str, repository: str, commit: str, destination: Path,
    command: list[str], owned_prefix: str, dry_run: bool, required_paths: Iterable[str] = (),
    archive_max_members: int = MAX_ARCHIVE_MEMBERS,
) -> dict[str, Any]:
    receipt = _find_receipt(state, "owned_paths", resource)
    if receipt:
        entries = receipt.get("paths", [])
        paths = [Path(entry["path"]) for entry in entries]
        if paths and all(path.exists() for path in paths):
            drifted = [
                str(path) for path, entry in zip(paths, entries)
                if _tree_digest(path) != entry.get("digest")
            ]
            if drifted:
                return {"kind": "owned_paths", "resource": resource, "status": "kept", "reason": "drift_detected", "paths": drifted}
            return {"kind": "owned_paths", "resource": resource, "status": "already_converged"}
    destination = destination.expanduser()
    preexisting = sorted(path for path in destination.glob(f"{owned_prefix}*") if path.exists()) if destination.exists() else []
    if preexisting and receipt is None:
        return {"kind": "owned_paths", "resource": resource, "status": "skipped", "reason": "preexisting_unmanaged_path", "paths": [str(p) for p in preexisting]}
    if dry_run:
        return {"kind": "owned_paths", "resource": resource, "status": "would_install", "source": f"{repository}@{commit}"}

    destination.mkdir(parents=True, exist_ok=True)
    before = {path.name for path in destination.iterdir()}
    try:
        with tempfile.TemporaryDirectory(prefix="macubuntu-source-") as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "source.zip"
            extract = tmp_path / "extract"
            extract.mkdir()
            _download(f"https://github.com/{repository}/archive/{commit}.zip", archive, resource=resource)
            _safe_extract(archive, extract, resource=resource, max_members=archive_max_members)
            roots = [item for item in extract.iterdir() if item.is_dir()]
            if len(roots) != 1:
                raise ExternalOperationError("source_layout_invalid", resource, f"unexpected source archive layout for {repository}")
            root = roots[0]
            expanded = [value.replace("{root}", str(root)).replace("{dest}", str(destination)) for value in command]
            runner.run(expanded, capture=None)

        all_created = sorted(path for path in destination.iterdir() if path.name not in before)
        unexpected = [path for path in all_created if not path.name.startswith(owned_prefix)]
        if unexpected:
            raise ExternalOperationError(
                "installer_wrote_unexpected_paths", resource,
                "installer created unexpected paths: " + ", ".join(path.name for path in unexpected),
            )
        created = [path for path in all_created if path.name.startswith(owned_prefix)]
        if not created:
            raise ExternalOperationError("installer_no_output", resource, "installer created no managed paths")
        missing_required = [name for name in required_paths if not (destination / name).exists()]
        if missing_required:
            raise ExternalOperationError(
                "installer_output_incomplete", resource,
                "required paths missing: " + ", ".join(missing_required),
            )
    except Exception:
        _remove_created_entries(destination, before)
        raise

    try:
        _record_owned_paths(
            store=store, state=state, app_version=app_version, resource=resource, paths=created,
            source={"repository": repository, "commit": commit},
        )
    except Exception:
        _remove_created_entries(destination, before)
        raise
    return {"kind": "owned_paths", "resource": resource, "status": "installed", "paths": [str(p) for p in created]}

def apply_pinned_download(
    *, store: StateStore, state: dict[str, Any], app_version: str,
    resource: str, url: str, destination: Path, expected_git_blob_sha1: str, dry_run: bool
) -> dict[str, Any]:
    receipt = _find_receipt(state, "owned_paths", resource)
    if receipt and destination.exists():
        expected_digest = receipt.get("paths", [{}])[0].get("digest")
        if expected_digest and _tree_digest(destination) == expected_digest:
            return {"kind": "owned_paths", "resource": resource, "status": "already_converged"}
        return {"kind": "owned_paths", "resource": resource, "status": "kept", "reason": "drift_detected"}
    if destination.exists() and receipt is None:
        return {"kind": "owned_paths", "resource": resource, "status": "skipped", "reason": "preexisting_unmanaged_path"}
    if dry_run:
        return {"kind": "owned_paths", "resource": resource, "status": "would_install", "url": url}

    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + ".macubuntu-download")
    try:
        _download(url, temp, resource=resource)
        actual = _git_blob_sha1(temp)
        if actual != expected_git_blob_sha1:
            raise ExternalOperationError(
                "download_integrity_mismatch", resource,
                f"expected git blob {expected_git_blob_sha1}, got {actual}",
            )
        os.replace(temp, destination)
    except Exception:
        temp.unlink(missing_ok=True)
        raise

    try:
        _record_owned_paths(
            store=store, state=state, app_version=app_version, resource=resource, paths=[destination],
            source={"url": url, "git_blob_sha1": expected_git_blob_sha1},
        )
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return {"kind": "owned_paths", "resource": resource, "status": "installed", "path": str(destination)}

def apply_pinned_subdir_copy(
    *, store: StateStore, state: dict[str, Any], app_version: str,
    resource: str, repository: str, commit: str, subdir: str,
    destination: Path, dry_run: bool, archive_max_members: int = MAX_ARCHIVE_MEMBERS,
) -> dict[str, Any]:
    receipt = _find_receipt(state, "owned_paths", resource)
    if receipt and destination.exists():
        expected = receipt.get("paths", [{}])[0].get("digest")
        if expected and _tree_digest(destination) != expected:
            return {"kind": "owned_paths", "resource": resource, "status": "kept", "reason": "drift_detected"}
        return {"kind": "owned_paths", "resource": resource, "status": "already_converged"}
    if destination.exists() and receipt is None:
        return {"kind": "owned_paths", "resource": resource, "status": "skipped", "reason": "preexisting_unmanaged_path"}
    if dry_run:
        return {"kind": "owned_paths", "resource": resource, "status": "would_install", "source": f"{repository}@{commit}"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="macubuntu-source-") as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "source.zip"
            extract = tmp_path / "extract"
            extract.mkdir()
            _download(f"https://github.com/{repository}/archive/{commit}.zip", archive, resource=resource)
            _safe_extract(archive, extract, resource=resource, max_members=archive_max_members)
            roots = [item for item in extract.iterdir() if item.is_dir()]
            if len(roots) != 1:
                raise ExternalOperationError("source_layout_invalid", resource, f"unexpected source archive layout for {repository}")
            source = roots[0] / subdir
            if not source.is_dir():
                raise ExternalOperationError("source_subdir_missing", resource, f"missing source subdirectory {subdir}")
            shutil.copytree(source, destination)
    except Exception:
        if destination.exists():
            shutil.rmtree(destination, ignore_errors=True)
        raise
    try:
        _record_owned_paths(
            store=store, state=state, app_version=app_version, resource=resource, paths=[destination],
            source={"repository": repository, "commit": commit, "subdir": subdir},
        )
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return {"kind": "owned_paths", "resource": resource, "status": "installed", "paths": [str(destination)]}

def apply_managed_text_file(
    *, store: StateStore, state: dict[str, Any], app_version: str,
    resource: str, path: Path, content: str, mode: int = 0o644, dry_run: bool
) -> dict[str, Any]:
    receipt = _find_receipt(state, "owned_paths", resource)
    if path.exists():
        if receipt and _tree_digest(path) == receipt.get("paths", [{}])[0].get("digest"):
            return {"kind": "owned_paths", "resource": resource, "status": "already_converged"}
        if receipt is None:
            return {"kind": "owned_paths", "resource": resource, "status": "skipped", "reason": "preexisting_unmanaged_path"}
        if path.read_text(encoding="utf-8", errors="replace") == content:
            return {"kind": "owned_paths", "resource": resource, "status": "already_converged"}
        return {"kind": "owned_paths", "resource": resource, "status": "kept", "reason": "drift_detected"}
    if dry_run:
        return {"kind": "owned_paths", "resource": resource, "status": "would_install", "path": str(path)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)
    try:
        _record_owned_paths(
            store=store, state=state, app_version=app_version, resource=resource,
            paths=[path], source={"type": "generated", "app": "MacUbuntu"},
        )
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {"kind": "owned_paths", "resource": resource, "status": "installed", "path": str(path)}