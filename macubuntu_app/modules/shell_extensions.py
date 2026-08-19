from __future__ import annotations

from typing import Any

from ..external import apply_gnome_extension, gnome_extension_enabled, gnome_extension_known
from ..operations import apply_gsetting
from ..state import StateStore
from ..util import Runner
from .common import setting_change, shell_major


class ShellExtensionsModule:
    id = "shell.enhancements"
    title = "Mac-style GNOME Shell enhancements"

    EXTENSIONS = {
        "blur-my-shell@aunetx": {"name": "Blur my Shell", "42": 47, "46": 72},
        "just-perfection-desktop@just-perfection": {"name": "Just Perfection", "42": 26, "46": 36},
        "clipboard-indicator@tudmotu.com": {"name": "Clipboard Indicator", "42": 47, "46": 71},
    }

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        major = shell_major(runner)
        changes: list[dict[str, Any]] = [setting_change(runner, self.id, "org.gnome.shell", "disable-user-extensions", "false", "allow user GNOME Shell extensions")]
        for uuid, info in self.EXTENSIONS.items():
            version = info.get(major or "")
            if version is None:
                action = "skip"
            elif not gnome_extension_known(runner, uuid):
                action = "install"
            else:
                action = "keep" if gnome_extension_enabled(runner, uuid) else "set"
            changes.append({"module": self.id, "kind": "gnome_extension", "resource": info["name"], "uuid": uuid, "version": version, "action": action, "reason": None if version is not None else "unsupported_gnome_version"})
        return changes

    def apply(self, *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool) -> list[dict[str, Any]]:
        major = shell_major(runner)
        results: list[dict[str, Any]] = [apply_gsetting(runner=runner, store=store, state=state, app_version=app_version, schema="org.gnome.shell", key="disable-user-extensions", desired="false", dry_run=dry_run)]
        for uuid, info in self.EXTENSIONS.items():
            version = info.get(major or "")
            if version is None:
                results.append({"kind": "gnome_extension", "resource": uuid, "status": "skipped", "reason": "unsupported_gnome_version"})
                continue
            results.append(apply_gnome_extension(runner=runner, store=store, state=state, app_version=app_version, uuid=uuid, version=int(version), shell_major=str(major), dry_run=dry_run))
        return results
