from __future__ import annotations

import ast
import hashlib
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Iterable

from .state import StateStore, now_iso
from .system import gsettings_get, gsettings_set
from .util import CommandError, Runner

EGO_DOWNLOAD = "https://extensions.gnome.org/download-extension/{uuid}.shell-extension.zip?version_tag={version}"
FLATHUB_URL = "https://flathub.org/repo/flathub.flatpakrepo"
ALLOWED_DOWNLOAD_HOSTS = {"github.com", "codeload.github.com", "raw.githubusercontent.com", "extensions.gnome.org"}
MAX_ARCHIVE_UNCOMPRESSED = 512 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 20000

class ExternalOperationError(CommandError):
    """Controlled third-party failure using the normal command-error UX."""

    def __init__(self, code: str, resource: str, detail: str):
        self.code = code
        self.resource = resource
        self.detail = detail
        super().__init__(["external-component", resource, code], 1, "", detail)


def _find_receipt(state: dict[str, Any], kind: str, resource: str) -> dict[str, Any] | None:
    for op in state.get("operations", []):
        if op.get("kind") == kind and op.get("resource") == resource:
            return op
    return None


def _save_receipt(store: StateStore, state: dict[str, Any], app_version: str, receipt: dict[str, Any]) -> None:
    """Insert or update one receipt identified by kind/resource.

    External resources use a single ownership record per resource. Updating an
    existing record avoids duplicate uninstall work after a repaired/reapplied
    component. The caller still owns rollback if the state write fails.
    """
    existing = _find_receipt(state, str(receipt.get("kind")), str(receipt.get("resource")))
    if existing is None:
        receipt.setdefault("created_at", now_iso())
        state.setdefault("operations", []).append(receipt)
    else:
        created_at = existing.get("created_at")
        existing.clear()
        existing.update(receipt)
        if created_at:
            existing["created_at"] = created_at
        else:
            existing.setdefault("created_at", now_iso())
        existing["updated_at"] = now_iso()
    store.save(state, app_version)


def _sudo() -> list[str]:
    return [] if os.geteuid() == 0 else ["sudo"]


def _validate_download_url(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ALLOWED_DOWNLOAD_HOSTS:
        raise ExternalOperationError("download_source_not_allowed", url, f"download source is not allowed: {url}")


def _download(url: str, target: Path, *, resource: str) -> None:
    _validate_download_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": "MacUbuntu"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            final_url = response.geturl()
            _validate_download_url(final_url)
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_ARCHIVE_UNCOMPRESSED:
                raise ExternalOperationError("download_too_large", resource, f"download exceeds safety limit: {length} bytes")
            with target.open("wb") as out:
                copied = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > MAX_ARCHIVE_UNCOMPRESSED:
                        raise ExternalOperationError("download_too_large", resource, "download exceeds safety limit")
                    out.write(chunk)
    except ExternalOperationError:
        raise
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError) as exc:
        raise ExternalOperationError("download_failed", resource, str(exc)) from exc


def _safe_extract(zip_path: Path, destination: Path, *, resource: str) -> None:
    """Extract a ZIP without allowing archive paths or symlinks to escape.

    GitHub source archives can legitimately preserve relative Unix symlinks.
    Python's ZipFile.extractall() does not recreate those links faithfully, so
    MacUbuntu validates every member first and performs extraction itself.

    Allowed symlinks must use a relative target whose lexical destination stays
    inside the extraction root. Archive members may never be written through a
    symlink directory, and special files such as devices/FIFOs/sockets are
    rejected outright.
    """
    destination = destination.resolve()

    def inside(candidate: Path) -> bool:
        try:
            candidate.relative_to(destination)
            return True
        except ValueError:
            return False

    def lexical(path: Path) -> Path:
        return Path(os.path.normpath(str(path)))

    try:
        with zipfile.ZipFile(zip_path) as archive:
            members = archive.infolist()
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise ExternalOperationError("archive_too_many_files", resource, f"archive has {len(members)} entries")
            total = sum(member.file_size for member in members)
            if total > MAX_ARCHIVE_UNCOMPRESSED:
                raise ExternalOperationError("archive_too_large", resource, f"archive expands to {total} bytes")

            validated: list[tuple[zipfile.ZipInfo, Path, int, str | None]] = []
            seen: set[Path] = set()
            symlink_paths: set[Path] = set()

            for member in members:
                if not member.filename or "\x00" in member.filename:
                    raise ExternalOperationError("unsafe_archive", resource, "archive contains an invalid path")

                relative = Path(member.filename)
                if relative.is_absolute() or any(part == ".." for part in relative.parts):
                    raise ExternalOperationError("unsafe_archive", resource, f"unsafe archive path: {member.filename}")
                relative = Path(os.path.normpath(str(relative)))
                if str(relative) in {"", "."}:
                    raise ExternalOperationError("unsafe_archive", resource, f"unsafe archive path: {member.filename}")
                if relative in seen:
                    raise ExternalOperationError("unsafe_archive", resource, f"duplicate archive path: {member.filename}")
                seen.add(relative)

                target = lexical(destination / relative)
                if not inside(target):
                    raise ExternalOperationError("unsafe_archive", resource, f"unsafe archive path: {member.filename}")

                unix_mode = (member.external_attr >> 16) & 0xFFFF
                file_type = unix_mode & 0o170000
                is_symlink = file_type == 0o120000
                is_directory = member.is_dir() or file_type == 0o040000
                is_regular = file_type in {0, 0o100000}

                if not (is_symlink or is_directory or is_regular):
                    raise ExternalOperationError("unsafe_archive", resource, f"special archive member rejected: {member.filename}")

                link_target: str | None = None
                if is_symlink:
                    if member.is_dir():
                        raise ExternalOperationError("unsafe_archive", resource, f"invalid archive symlink: {member.filename}")
                    try:
                        link_target = archive.read(member).decode("utf-8")
                    except UnicodeDecodeError as exc:
                        raise ExternalOperationError("unsafe_archive", resource, f"invalid symlink target encoding: {member.filename}") from exc
                    if not link_target or "\x00" in link_target:
                        raise ExternalOperationError("unsafe_archive", resource, f"invalid archive symlink target: {member.filename}")
                    link_path = Path(link_target)
                    if link_path.is_absolute():
                        raise ExternalOperationError("unsafe_archive", resource, f"absolute archive symlink rejected: {member.filename}")
                    resolved_target = lexical(target.parent / link_path)
                    if not inside(resolved_target):
                        raise ExternalOperationError("unsafe_archive", resource, f"escaping archive symlink rejected: {member.filename}")
                    symlink_paths.add(relative)

                validated.append((member, relative, unix_mode, link_target))

            # A regular member below an archive-created symlink directory could
            # otherwise write outside the extraction root after that link exists.
            for member, relative, _, _ in validated:
                for parent in relative.parents:
                    if parent == Path("."):
                        break
                    if parent in symlink_paths:
                        raise ExternalOperationError(
                            "unsafe_archive",
                            resource,
                            f"archive path traverses symlink: {member.filename}",
                        )

            destination.mkdir(parents=True, exist_ok=True)

            # Directories and regular files are materialized first. Symlinks are
            # created last, so no normal file write can traverse a new link.
            for member, relative, unix_mode, link_target in validated:
                if link_target is not None:
                    continue
                target = destination / relative
                current = destination
                for part in relative.parts[:-1]:
                    current = current / part
                    if current.is_symlink():
                        raise ExternalOperationError("unsafe_archive", resource, f"archive path traverses existing symlink: {member.filename}")

                file_type = unix_mode & 0o170000
                if member.is_dir() or file_type == 0o040000:
                    if target.is_symlink():
                        raise ExternalOperationError("unsafe_archive", resource, f"archive directory replaces symlink: {member.filename}")
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                target.parent.mkdir(parents=True, exist_ok=True)
                if target.is_symlink():
                    raise ExternalOperationError("unsafe_archive", resource, f"archive file replaces symlink: {member.filename}")
                with archive.open(member, "r") as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
                permissions = unix_mode & 0o777
                if permissions:
                    target.chmod(permissions)

            for member, relative, _, link_target in validated:
                if link_target is None:
                    continue
                target = destination / relative
                current = destination
                for part in relative.parts[:-1]:
                    current = current / part
                    if current.is_symlink():
                        raise ExternalOperationError("unsafe_archive", resource, f"archive symlink parent is a symlink: {member.filename}")
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists() or target.is_symlink():
                    raise ExternalOperationError("unsafe_archive", resource, f"archive symlink replaces existing path: {member.filename}")
                os.symlink(link_target, target)
    except ExternalOperationError:
        raise
    except (zipfile.BadZipFile, OSError) as exc:
        raise ExternalOperationError("archive_invalid", resource, str(exc)) from exc


def _remove_created_entries(destination: Path, before: set[str]) -> None:
    if not destination.exists():
        return
    for path in destination.iterdir():
        if path.name in before:
            continue
        try:
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
        except OSError:
            pass


def _tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.exists() and not path.is_symlink():
        return "missing"
    if path.is_symlink():
        digest.update(b"L\0")
        digest.update(os.readlink(path).encode())
        return digest.hexdigest()
    if path.is_file():
        digest.update(b"F\0")
        digest.update(path.read_bytes())
        return digest.hexdigest()
    root = path.resolve()
    for item in sorted(path.rglob("*"), key=lambda p: str(p.relative_to(path))):
        rel = str(item.relative_to(path)).encode()
        digest.update(rel)
        digest.update(b"\0")
        if item.is_symlink():
            digest.update(b"L\0")
            digest.update(os.readlink(item).encode())
        elif item.is_file():
            digest.update(b"F\0")
            with item.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        elif item.is_dir():
            digest.update(b"D\0")
        try:
            resolved = item.resolve()
            if root not in resolved.parents and resolved != root and not item.is_symlink():
                raise RuntimeError(f"managed path escapes root: {item}")
        except OSError:
            pass
    return digest.hexdigest()


def _record_owned_paths(
    *, store: StateStore, state: dict[str, Any], app_version: str, resource: str, paths: Iterable[Path], source: dict[str, Any]
) -> dict[str, Any]:
    entries = [{"path": str(path), "digest": _tree_digest(path)} for path in paths]
    receipt = {"kind": "owned_paths", "resource": resource, "paths": entries, "source": source}
    _save_receipt(store, state, app_version, receipt)
    return receipt


def apt_repository_present(ppa: str) -> bool:
    if not ppa.startswith("ppa:") or "/" not in ppa[4:]:
        return False
    owner, archive = ppa[4:].split("/", 1)
    marker = f"ppa.launchpadcontent.net/{owner}/{archive}/ubuntu"
    candidates = [Path("/etc/apt/sources.list")]
    sources = Path("/etc/apt/sources.list.d")
    if sources.exists():
        candidates.extend(sources.glob("*.list"))
        candidates.extend(sources.glob("*.sources"))
    for path in candidates:
        try:
            if marker in path.read_text(encoding="utf-8", errors="ignore"):
                return True
        except OSError:
            continue
    return False

def _flatpak_remote_exists(runner: Runner, name: str) -> bool:
    cp = runner.run(["flatpak", "--user", "remotes", "--columns=name"], check=False)
    return cp.returncode == 0 and name in (cp.stdout or "").splitlines()


def _flatpak_app_installed(runner: Runner, app_id: str) -> bool:
    return runner.run(["flatpak", "--user", "info", app_id], check=False).returncode == 0

def _enabled_extensions(runner: Runner) -> list[str]:
    raw = gsettings_get(runner, "org.gnome.shell", "enabled-extensions")
    if not raw:
        return []
    try:
        parsed = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []
    return [str(value) for value in parsed] if isinstance(parsed, list) else []


def _set_enabled_extensions(runner: Runner, values: list[str]) -> None:
    encoded = "[" + ", ".join(repr(value) for value in values) + "]"
    gsettings_set(runner, "org.gnome.shell", "enabled-extensions", encoded)


def _extension_user_dir(uuid: str) -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return data_home / "gnome-shell" / "extensions" / uuid


def _extension_known(runner: Runner, uuid: str) -> bool:
    if runner.exists("gnome-extensions"):
        cp = runner.run(["gnome-extensions", "info", uuid], check=False)
        if cp.returncode == 0:
            return True
    return _extension_user_dir(uuid).exists()

def _git_blob_sha1(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()
