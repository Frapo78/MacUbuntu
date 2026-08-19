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

    # Version numbers and review IDs are both pinned. The review ID identifies
    # the exact archive approved by extensions.gnome.org, avoiding mutable or
    # deprecated download URL formats while preserving reproducibility.
    EXTENSIONS = {
        "blur-my-shell@aunetx": {
            "name": "Blur my Shell",
            "42": {"version": 47, "review_id": 42627},
            "46": {"version": 72, "review_id": 69740},
        },
        "just-perfection-desktop@just-perfection": {
            "name": "Just Perfection",
            "42": {"version": 26, "review_id": 43626},
            "46": {"version": 36, "review_id": 68110},
        },
        "clipboard-indicator@tudmotu.com": {
            "name": "Clipboard Indicator",
            "42": {"version": 47, "review_id": 43380},
            "46": {"version": 71, "review_id": 70694},
        },
    }

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        major = shell_major(runner)
        changes: list[dict[str, Any]] = [setting_change(runner, self.id, "org.gnome.shell", "disable-user-extensions", "false", "allow user GNOME Shell extensions")]
        for uuid, info in self.EXTENSIONS.items():
            pin = info.get(major or "")
            if pin is None:
                action = "skip"
                version = None
            else:
                version = int(pin["version"])
                if not gnome_extension_known(runner, uuid):
                    action = "install"
                else:
                    action = "keep" if gnome_extension_enabled(runner, uuid) else "set"
            changes.append({
                "module": self.id,
                "kind": "gnome_extension",
                "resource": info["name"],
                "uuid": uuid,
                "version": version,
                "action": action,
                "reason": None if pin is not None else "unsupported_gnome_version",
            })
        return changes

    def apply(self, *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool) -> list[dict[str, Any]]:
        major = shell_major(runner)
        results: list[dict[str, Any]] = [apply_gsetting(runner=runner, store=store, state=state, app_version=app_version, schema="org.gnome.shell", key="disable-user-extensions", desired="false", dry_run=dry_run)]
        for uuid, info in self.EXTENSIONS.items():
            pin = info.get(major or "")
            if pin is None:
                results.append({"kind": "gnome_extension", "resource": uuid, "status": "skipped", "reason": "unsupported_gnome_version"})
                continue
            results.append(apply_gnome_extension(
                runner=runner,
                store=store,
                state=state,
                app_version=app_version,
                uuid=uuid,
                version=int(pin["version"]),
                review_id=int(pin["review_id"]),
                shell_major=str(major),
                dry_run=dry_run,
            ))
        return results
