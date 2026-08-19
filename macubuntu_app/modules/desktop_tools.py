from __future__ import annotations

from typing import Any

from ..operations import apply_apt_bundle
from ..state import StateStore
from ..util import Runner, package_installed
from .common import package_available


class DesktopToolsModule:
    id = "desktop.tools"
    title = "GNOME customization and extension management tools"
    CANDIDATES = ["gnome-tweaks", "gnome-shell-extension-manager"]

    def _available(self, runner: Runner) -> list[str]:
        return [package for package in self.CANDIDATES if package_available(runner, package)]

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        for package in self.CANDIDATES:
            if not package_available(runner, package):
                action = "skip"
                reason = "package_unavailable"
            else:
                action = "keep" if package_installed(runner, package) else "install"
                reason = None
            changes.append({"module": self.id, "kind": "package", "resource": package, "action": action, "reason": reason})
        return changes

    def apply(self, *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool) -> list[dict[str, Any]]:
        available = self._available(runner)
        results: list[dict[str, Any]] = []
        if available:
            results.append(apply_apt_bundle(runner=runner, store=store, state=state, app_version=app_version, requested=available, dry_run=dry_run))
        for package in self.CANDIDATES:
            if package not in available:
                results.append({"kind": "package", "resource": package, "status": "skipped", "reason": "package_unavailable"})
        return results
