from __future__ import annotations

from typing import Any

from ..operations import apply_apt_bundle, apply_gsetting
from ..state import StateStore
from ..system import gsettings_get
from ..util import Runner, package_installed
from .common import package_available


class CoreGnomeModule:
    id = "core.gnome"
    title = "Core GNOME mac-style workflow"

    settings = [
        ("org.gnome.desktop.wm.preferences", "button-layout", "'close,minimize,maximize:'", "window controls on the left"),
        ("org.gnome.desktop.peripherals.touchpad", "natural-scroll", "true", "natural trackpad scrolling"),
        ("org.gnome.desktop.peripherals.touchpad", "tap-to-click", "true", "tap to click"),
        ("org.gnome.desktop.peripherals.touchpad", "two-finger-scrolling-enabled", "true", "two-finger scrolling"),
        ("org.gnome.desktop.interface", "enable-animations", "true", "desktop animations"),
        ("org.gnome.desktop.interface", "clock-show-date", "true", "show date in top bar"),
        ("org.gnome.desktop.interface", "clock-show-seconds", "false", "hide seconds in top bar"),
        # GNOME persists the enabled-extension list in GSettings, but this
        # master switch can disable every user extension after login.  Keep it
        # explicitly enabled so MacUbuntu-managed extensions survive reboots.
        ("org.gnome.shell", "disable-user-extensions", "false", "keep user extensions enabled across sessions"),
        ("org.gnome.shell.extensions.dash-to-dock", "dock-position", "'BOTTOM'", "bottom dock"),
        ("org.gnome.shell.extensions.dash-to-dock", "extend-height", "false", "floating dock width"),
        ("org.gnome.shell.extensions.dash-to-dock", "always-center-icons", "true", "center dock icons"),
        ("org.gnome.shell.extensions.dash-to-dock", "show-mounts", "false", "hide mounted volumes from dock"),
        ("org.gnome.shell.extensions.dash-to-dock", "show-mounts-network", "false", "hide network mounts from dock"),
        ("org.gnome.shell.extensions.dash-to-dock", "show-trash", "true", "show Trash in dock"),
        ("org.gnome.shell.extensions.dash-to-dock", "running-indicator-style", "'DOTS'", "mac-like running indicators"),
        ("org.gnome.shell.extensions.dash-to-dock", "custom-theme-shrink", "true", "compact dock spacing"),
        ("org.gnome.shell.extensions.dash-to-dock", "dock-fixed", "false", "floating dock instead of a full-width panel"),
        ("org.gnome.shell.extensions.dash-to-dock", "autohide", "true", "hide the dock when not in use"),
        ("org.gnome.shell.extensions.dash-to-dock", "intellihide", "true", "dodge application windows"),
        ("org.gnome.shell.extensions.dash-to-dock", "require-pressure-to-show", "false", "show dock immediately at the screen edge"),
        ("org.gnome.shell.extensions.dash-to-dock", "dash-max-icon-size", "48", "mac-like dock icon size"),
        ("org.gnome.shell.extensions.dash-to-dock", "transparency-mode", "'DYNAMIC'", "dynamic dock translucency"),
        ("org.gnome.shell.extensions.dash-to-dock", "background-opacity", "0.8", "translucent dock background"),
        ("org.gnome.shell.extensions.dash-to-dock", "show-windows-preview", "true", "window previews from dock icons"),
    ]

    def _packages(self, runner: Runner) -> list[str]:
        packages = ["gnome-sushi"]
        if package_available(runner, "gnome-shell-extension-ubuntu-dock"):
            packages.append("gnome-shell-extension-ubuntu-dock")
        return packages

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        for package in self._packages(runner):
            changes.append({
                "module": self.id,
                "kind": "package",
                "resource": package,
                "action": "keep" if package_installed(runner, package) else "install",
            })
        for schema, key, desired, description in self.settings:
            current = gsettings_get(runner, schema, key)
            action = "skip" if current is None else ("keep" if current == desired else "set")
            changes.append({
                "module": self.id,
                "kind": "gsettings",
                "resource": f"{schema}::{key}",
                "description": description,
                "current": current,
                "desired": desired,
                "action": action,
            })
        return changes

    def apply(self, *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool) -> list[dict[str, Any]]:
        results = [apply_apt_bundle(runner=runner, store=store, state=state, app_version=app_version, requested=self._packages(runner), dry_run=dry_run)]
        for schema, key, desired, _ in self.settings:
            results.append(apply_gsetting(runner=runner, store=store, state=state, app_version=app_version, schema=schema, key=key, desired=desired, dry_run=dry_run))
        return results
