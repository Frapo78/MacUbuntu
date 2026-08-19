from __future__ import annotations

from typing import Any

from ..operations import apply_apt_bundle, apply_gsetting
from ..state import StateStore
from ..util import Runner
from .common import package_available, package_change, setting_change


class TypographyModule:
    id = "appearance.typography"
    title = "Mac-like typography using the open Inter family"
    packages = ["fonts-inter"]
    settings = [
        ("org.gnome.desktop.interface", "font-name", "'Inter 11'", "Inter interface font"),
        ("org.gnome.desktop.interface", "document-font-name", "'Inter 11'", "Inter document font"),
    ]

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        if not package_available(runner, "fonts-inter"):
            return [{"module": self.id, "kind": "package", "resource": "fonts-inter", "action": "skip", "reason": "package_unavailable"}]
        changes = [package_change(runner, package, self.id) for package in self.packages]
        changes.extend(setting_change(runner, self.id, *setting) for setting in self.settings)
        return changes

    def apply(self, *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool) -> list[dict[str, Any]]:
        if not package_available(runner, "fonts-inter"):
            return [{"kind": "package", "resource": "fonts-inter", "status": "skipped", "reason": "package_unavailable"}]
        results: list[dict[str, Any]] = [apply_apt_bundle(runner=runner, store=store, state=state, app_version=app_version, requested=self.packages, dry_run=dry_run)]
        for schema, key, desired, _ in self.settings:
            results.append(apply_gsetting(runner=runner, store=store, state=state, app_version=app_version, schema=schema, key=key, desired=desired, dry_run=dry_run))
        return results
