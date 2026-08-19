from __future__ import annotations

from typing import Any

from ..operations import apply_apt_bundle, apply_gsetting
from ..state import StateStore
from ..system import gsettings_get
from ..util import Runner, package_installed


class CoreGnomeModule:
    id = "core.gnome"
    title = "Core GNOME mac-style workflow"

    packages = ["gnome-sushi"]

    settings = [
        ("org.gnome.desktop.wm.preferences", "button-layout", "'close,minimize,maximize:'", "window controls on the left"),
        ("org.gnome.desktop.peripherals.touchpad", "natural-scroll", "true", "natural trackpad scrolling"),
        ("org.gnome.desktop.peripherals.touchpad", "tap-to-click", "true", "tap to click"),
        ("org.gnome.desktop.peripherals.touchpad", "two-finger-scrolling-enabled", "true", "two-finger scrolling"),
        ("org.gnome.desktop.interface", "enable-animations", "true", "desktop animations"),
        ("org.gnome.desktop.interface", "clock-show-date", "true", "show date in top bar"),
        ("org.gnome.desktop.interface", "clock-show-seconds", "false", "hide seconds in top bar"),
        ("org.gnome.shell.extensions.dash-to-dock", "dock-position", "'BOTTOM'", "bottom dock"),
        ("org.gnome.shell.extensions.dash-to-dock", "extend-height", "false", "floating dock width"),
        ("org.gnome.shell.extensions.dash-to-dock", "always-center-icons", "true", "center dock icons"),
        ("org.gnome.shell.extensions.dash-to-dock", "show-mounts", "false", "hide mounted volumes from dock"),
        ("org.gnome.shell.extensions.dash-to-dock", "show-mounts-network", "false", "hide network mounts from dock"),
        ("org.gnome.shell.extensions.dash-to-dock", "show-trash", "true", "show Trash in dock"),
        ("org.gnome.shell.extensions.dash-to-dock", "running-indicator-style", "'DOTS'", "mac-like running indicators"),
        ("org.gnome.shell.extensions.dash-to-dock", "custom-theme-shrink", "true", "compact dock spacing"),
    ]

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        for package in self.packages:
            changes.append({"module": self.id, "kind": "package", "resource": package, "action": "keep" if package_installed(runner, package) else "install"})

        for schema, key, desired, description in self.settings:
            current = gsettings_get(runner, schema, key)
            if current is None:
                action = "skip"
            elif current == desired:
                action = "keep"
            else:
                action = "set"
            changes.append({"module": self.id, "kind": "gsettings", "resource": f"{schema}::{key}", "description": description, "current": current, "desired": desired, "action": action})
        return changes

    def apply(self, *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        results.append(apply_apt_bundle(runner=runner, store=store, state=state, app_version=app_version, requested=self.packages, dry_run=dry_run))
        for schema, key, desired, _ in self.settings:
            results.append(apply_gsetting(runner=runner, store=store, state=state, app_version=app_version, schema=schema, key=key, desired=desired, dry_run=dry_run))
        return results
