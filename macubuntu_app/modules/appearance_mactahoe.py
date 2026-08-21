from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..external import (
    apply_extension_state,
    apply_managed_text_file,
    apply_pinned_installer,
    apply_pinned_subdir_copy,
    gnome_extension_enabled,
    gnome_extension_known,
)
from ..operations import apply_apt_bundle, apply_gsetting
from ..state import StateStore
from ..util import Runner
from .common import package_change, path_change, setting_change


class AppearanceMacTahoeModule:
    """Current macOS-inspired GTK/Shell appearance with conservative assets."""

    id = "appearance.mactahoe"
    title = "MacTahoe mac-style appearance and title bars"

    GTK_REPO = "vinceliuice/MacTahoe-gtk-theme"
    GTK_COMMIT = "ae82d8ea6a7eba42b9bf375ec602538c34fdabab"

    ICON_REPO = "vinceliuice/WhiteSur-icon-theme"
    ICON_COMMIT = "bab5833b5cae200bccb786a2d3d6afa2201e7806"
    CURSOR_REPO = "vinceliuice/WhiteSur-cursors"
    CURSOR_COMMIT = "e190baf618ed95ee217d2fd45589bd309b37672b"
    ICON_ARCHIVE_MAX_MEMBERS = 30000

    GTK4_LIGHT_RESOURCE = "mactahoe-gtk4-user-css"
    GTK4_DARK_RESOURCE = "mactahoe-gtk4-user-dark-css"

    dependencies = ["sassc", "libglib2.0-dev-bin", "libxml2-utils", "gnome-shell-extensions"]

    @property
    def data_home(self) -> Path:
        return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    @property
    def config_home(self) -> Path:
        return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    @property
    def themes_dir(self) -> Path:
        return self.data_home / "themes"

    @property
    def icons_dir(self) -> Path:
        return self.data_home / "icons"

    @property
    def gtk4_config_dir(self) -> Path:
        return self.config_home / "gtk-4.0"

    @property
    def gtk4_css(self) -> Path:
        return self.gtk4_config_dir / "gtk.css"

    @property
    def gtk4_dark_css(self) -> Path:
        return self.gtk4_config_dir / "gtk-dark.css"

    @property
    def settings(self) -> list[tuple[str, str, str, str]]:
        return [
            (
                "org.gnome.desktop.interface",
                "gtk-theme",
                "'MacUbuntu-MacTahoe-Dark-solid'",
                "Tahoe-style application and title-bar theme",
            ),
            (
                "org.gnome.desktop.interface",
                "icon-theme",
                "'MacUbuntu-WhiteSur'",
                "mac-style icon theme",
            ),
            (
                "org.gnome.desktop.interface",
                "cursor-theme",
                "'MacUbuntu-WhiteSur-cursors'",
                "mac-style cursor theme",
            ),
            (
                "org.gnome.desktop.interface",
                "color-scheme",
                "'prefer-dark'",
                "dark appearance",
            ),
            (
                "org.gnome.shell.extensions.user-theme",
                "name",
                "'MacUbuntu-MacTahoe-Dark-solid'",
                "Tahoe-style GNOME Shell theme",
            ),
            (
                "org.gnome.desktop.wm.preferences",
                "titlebar-uses-system-font",
                "false",
                "use the MacUbuntu title-bar font instead of GNOME's system-font default",
            ),
            (
                "org.gnome.desktop.wm.preferences",
                "titlebar-font",
                "'Inter Semi-Bold 11'",
                "clean mac-like title-bar typography",
            ),
            (
                "org.gnome.desktop.wm.preferences",
                "action-double-click-titlebar",
                "'toggle-maximize'",
                "mac-like title-bar double-click behavior",
            ),
            (
                "org.gnome.desktop.wm.preferences",
                "action-middle-click-titlebar",
                "'none'",
                "avoid non-mac middle-click title-bar actions",
            ),
            (
                "org.gnome.desktop.wm.preferences",
                "action-right-click-titlebar",
                "'menu'",
                "keep the window menu available from the title bar",
            ),
        ]

    def _gtk4_import_css(self, *, dark: bool) -> str:
        variant = "Dark" if dark else "Light"
        source = (
            self.themes_dir
            / f"MacUbuntu-MacTahoe-{variant}-solid"
            / "gtk-4.0"
            / "gtk.css"
        ).expanduser().resolve()
        return (
            "/* Managed by MacUbuntu. Do not edit: safe MacTahoe GTK4/libadwaita bridge. */\n"
            f'@import url("{source.as_uri()}");\n'
        )

    @staticmethod
    def _receipt_owns_path(state: dict[str, Any], resource: str, path: Path) -> bool:
        wanted = str(path)
        for op in state.get("operations", []):
            if op.get("kind") != "owned_paths" or op.get("resource") != resource:
                continue
            return any(entry.get("path") == wanted for entry in op.get("paths", []))
        return False

    def _unmanaged_gtk4_css(self, state: dict[str, Any]) -> list[str]:
        unmanaged: list[str] = []
        for resource, path in (
            (self.GTK4_LIGHT_RESOURCE, self.gtk4_css),
            (self.GTK4_DARK_RESOURCE, self.gtk4_dark_css),
        ):
            if path.exists() and not self._receipt_owns_path(state, resource, path):
                unmanaged.append(str(path))
        return unmanaged

    def _apply_gtk4_bridge(
        self, *, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool
    ) -> list[dict[str, Any]]:
        unmanaged = self._unmanaged_gtk4_css(state)
        if unmanaged:
            return [{
                "kind": "appearance",
                "resource": "MacTahoe GTK4/libadwaita titlebar bridge",
                "status": "skipped",
                "reason": "preexisting_unmanaged_gtk4_css",
                "paths": unmanaged,
            }]
        return [
            apply_managed_text_file(
                store=store,
                state=state,
                app_version=app_version,
                resource=self.GTK4_LIGHT_RESOURCE,
                path=self.gtk4_css,
                content=self._gtk4_import_css(dark=False),
                mode=0o644,
                dry_run=dry_run,
            ),
            apply_managed_text_file(
                store=store,
                state=state,
                app_version=app_version,
                resource=self.GTK4_DARK_RESOURCE,
                path=self.gtk4_dark_css,
                content=self._gtk4_import_css(dark=True),
                mode=0o644,
                dry_run=dry_run,
            ),
        ]

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        changes = [package_change(runner, package, self.id) for package in self.dependencies]
        changes.extend([
            path_change(self.id, "MacTahoe GTK", self.themes_dir / "MacUbuntu-MacTahoe-Dark-solid"),
            path_change(self.id, "WhiteSur icons", self.icons_dir / "MacUbuntu-WhiteSur"),
            path_change(self.id, "WhiteSur cursors", self.icons_dir / "MacUbuntu-WhiteSur-cursors"),
            path_change(self.id, "MacTahoe GTK4/libadwaita light bridge", self.gtk4_css),
            path_change(self.id, "MacTahoe GTK4/libadwaita dark bridge", self.gtk4_dark_css),
        ])
        changes.extend(setting_change(runner, self.id, *setting) for setting in self.settings)

        user_theme_uuid = "user-theme@gnome-shell-extensions.gcampax.github.com"
        if not gnome_extension_known(runner, user_theme_uuid):
            extension_action = (
                "install"
                if package_change(runner, "gnome-shell-extensions", self.id)["action"] == "install"
                else "skip"
            )
        else:
            extension_action = "keep" if gnome_extension_enabled(runner, user_theme_uuid) else "set"
        changes.append({
            "module": self.id,
            "kind": "gnome_extension",
            "resource": "User Themes",
            "uuid": user_theme_uuid,
            "action": extension_action,
        })
        return changes

    def apply(
        self,
        *,
        runner: Runner,
        store: StateStore,
        state: dict[str, Any],
        app_version: str,
        dry_run: bool,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        results.append(apply_apt_bundle(
            runner=runner,
            store=store,
            state=state,
            app_version=app_version,
            requested=self.dependencies,
            dry_run=dry_run,
        ))

        gtk_result = apply_pinned_installer(
            runner=runner,
            store=store,
            state=state,
            app_version=app_version,
            resource="mactahoe-gtk",
            repository=self.GTK_REPO,
            commit=self.GTK_COMMIT,
            destination=self.themes_dir,
            owned_prefix="MacUbuntu-MacTahoe",
            command=[
                "bash",
                "{root}/install.sh",
                "-d",
                "{dest}",
                "-n",
                "MacUbuntu-MacTahoe",
                "-o",
                "solid",
                "-c",
                "dark",
                "-c",
                "light",
                "-a",
                "normal",
                "--round",
            ],
            required_paths=[
                "MacUbuntu-MacTahoe-Dark-solid",
                "MacUbuntu-MacTahoe-Light-solid",
            ],
            dry_run=dry_run,
        )
        results.append(gtk_result)

        icon_result = apply_pinned_installer(
            runner=runner,
            store=store,
            state=state,
            app_version=app_version,
            resource="whitesur-icons",
            repository=self.ICON_REPO,
            commit=self.ICON_COMMIT,
            destination=self.icons_dir,
            owned_prefix="MacUbuntu-WhiteSur",
            command=[
                "bash", "{root}/install.sh", "-d", "{dest}", "-n", "MacUbuntu-WhiteSur",
            ],
            required_paths=["MacUbuntu-WhiteSur"],
            dry_run=dry_run,
            archive_max_members=self.ICON_ARCHIVE_MAX_MEMBERS,
        )
        results.append(icon_result)

        cursor_result = apply_pinned_subdir_copy(
            store=store,
            state=state,
            app_version=app_version,
            resource="whitesur-cursors",
            repository=self.CURSOR_REPO,
            commit=self.CURSOR_COMMIT,
            subdir="dist",
            destination=self.icons_dir / "MacUbuntu-WhiteSur-cursors",
            dry_run=dry_run,
        )
        results.append(cursor_result)

        if any(result.get("status") in {"skipped", "kept"} for result in (gtk_result, icon_result, cursor_result)):
            results.append({
                "kind": "appearance",
                "resource": "MacTahoe activation",
                "status": "skipped",
                "reason": "theme_assets_not_managed",
            })
            return results

        results.extend(self._apply_gtk4_bridge(
            store=store, state=state, app_version=app_version, dry_run=dry_run,
        ))

        results.append(apply_extension_state(
            runner=runner,
            store=store,
            state=state,
            app_version=app_version,
            uuid="user-theme@gnome-shell-extensions.gcampax.github.com",
            dry_run=dry_run,
        ))

        for schema, key, desired, _ in self.settings:
            results.append(apply_gsetting(
                runner=runner,
                store=store,
                state=state,
                app_version=app_version,
                schema=schema,
                key=key,
                desired=desired,
                dry_run=dry_run,
            ))
        return results
