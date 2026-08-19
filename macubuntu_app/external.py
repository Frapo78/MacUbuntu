from __future__ import annotations

from .external_core import (
    ALLOWED_DOWNLOAD_HOSTS, EGO_DOWNLOAD, FLATHUB_URL, MAX_ARCHIVE_MEMBERS,
    MAX_ARCHIVE_UNCOMPRESSED, ExternalOperationError, _download, _safe_extract,
    _validate_download_url, apt_repository_present, _extension_known, _enabled_extensions,
)
from .external_packages import (
    apply_apt_repository, apply_flatpak_app, apply_flatpak_remote, apply_service_state,
)
from .external_gnome import apply_extension_state, apply_gnome_extension
from .external_assets import (
    apply_managed_text_file, apply_pinned_download, apply_pinned_installer,
    apply_pinned_subdir_copy,
)
from .external_uninstall import uninstall_external_operation
from .util import Runner


def gnome_extension_known(runner: Runner, uuid: str) -> bool:
    return _extension_known(runner, uuid)


def gnome_extension_enabled(runner: Runner, uuid: str) -> bool:
    return uuid in _enabled_extensions(runner)


__all__ = [
    "ALLOWED_DOWNLOAD_HOSTS", "EGO_DOWNLOAD", "FLATHUB_URL", "MAX_ARCHIVE_MEMBERS",
    "MAX_ARCHIVE_UNCOMPRESSED", "ExternalOperationError", "_download", "_safe_extract",
    "_validate_download_url", "apt_repository_present", "apply_apt_repository",
    "apply_extension_state", "apply_flatpak_app", "apply_flatpak_remote",
    "apply_gnome_extension", "apply_managed_text_file", "apply_pinned_download",
    "apply_pinned_installer", "apply_pinned_subdir_copy", "apply_service_state",
    "gnome_extension_enabled", "gnome_extension_known", "uninstall_external_operation",
]
