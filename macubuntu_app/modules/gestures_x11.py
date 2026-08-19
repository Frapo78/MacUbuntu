from __future__ import annotations

from typing import Any

from ..external import apply_apt_repository, apply_gnome_extension, apply_service_state, apt_repository_present, gnome_extension_enabled, gnome_extension_known
from ..operations import apply_apt_bundle
from ..state import StateStore
from ..util import Runner, package_installed
from .common import package_change, package_version, service_change, session_type, shell_major


class GesturesX11Module:
    id = "gestures.x11"
    title = "Mac-style multi-touch gestures on X11"
    PPA = "ppa:touchegg/stable"
    UUID = "x11gestures@joseexposito.github.io"
    VERSIONS = {"42": 17, "46": 25}

    def _legacy_conflict(self, runner: Runner) -> bool:
        version = package_version(runner, "touchegg")
        return bool(version and not version.startswith("2."))

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        if session_type() != "x11":
            return [{"module": self.id, "kind": "session", "resource": "X11 gestures", "action": "skip", "reason": "wayland_or_unknown_session"}]
        major = shell_major(runner)
        version = self.VERSIONS.get(major or "")
        if version is None:
            return [{"module": self.id, "kind": "gnome_extension", "resource": "X11 Gestures", "action": "skip", "reason": "unsupported_gnome_version"}]
        if self._legacy_conflict(runner):
            return [{"module": self.id, "kind": "package", "resource": "touchegg", "action": "skip", "reason": "legacy_touchegg_preinstalled"}]
        changes: list[dict[str, Any]] = []
        touchegg_present = package_installed(runner, "touchegg")
        if not touchegg_present:
            repo_present = apt_repository_present(self.PPA)
            if not repo_present:
                changes.append(package_change(runner, "software-properties-common", self.id))
            changes.append({"module": self.id, "kind": "apt_repository", "resource": self.PPA, "action": "keep" if repo_present else "install"})
        changes.append(package_change(runner, "touchegg", self.id))
        if touchegg_present:
            changes.append(service_change(runner, self.id, "touchegg.service", user=False))
        else:
            changes.append({"module": self.id, "kind": "service", "resource": "system:touchegg.service", "action": "set", "reason": "after_package_install"})
        if not gnome_extension_known(runner, self.UUID):
            extension_action = "install"
        else:
            extension_action = "keep" if gnome_extension_enabled(runner, self.UUID) else "set"
        changes.append({"module": self.id, "kind": "gnome_extension", "resource": "X11 Gestures", "uuid": self.UUID, "version": version, "action": extension_action})
        return changes

    def apply(self, *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool) -> list[dict[str, Any]]:
        if session_type() != "x11":
            return [{"kind": "session", "resource": "X11 gestures", "status": "skipped", "reason": "wayland_or_unknown_session"}]
        major = shell_major(runner)
        version = self.VERSIONS.get(major or "")
        if version is None:
            return [{"kind": "gnome_extension", "resource": self.UUID, "status": "skipped", "reason": "unsupported_gnome_version"}]
        if self._legacy_conflict(runner):
            return [{"kind": "package", "resource": "touchegg", "status": "skipped", "reason": "legacy_touchegg_preinstalled"}]

        results: list[dict[str, Any]] = []
        if not package_installed(runner, "touchegg") and not apt_repository_present(self.PPA):
            results.append(apply_apt_bundle(runner=runner, store=store, state=state, app_version=app_version, requested=["software-properties-common"], dry_run=dry_run))
            results.append(apply_apt_repository(runner=runner, store=store, state=state, app_version=app_version, ppa=self.PPA, dry_run=dry_run))
        results.append(apply_apt_bundle(runner=runner, store=store, state=state, app_version=app_version, requested=["touchegg"], dry_run=dry_run))
        results.append(apply_service_state(runner=runner, store=store, state=state, app_version=app_version, unit="touchegg.service", user=False, dry_run=dry_run))
        results.append(apply_gnome_extension(runner=runner, store=store, state=state, app_version=app_version, uuid=self.UUID, version=version, shell_major=str(major), dry_run=dry_run))
        return results
