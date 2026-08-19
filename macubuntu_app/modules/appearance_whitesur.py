from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..external import apply_extension_state, apply_pinned_installer, apply_pinned_subdir_copy, gnome_extension_enabled, gnome_extension_known
from ..operations import apply_apt_bundle, apply_gsetting
from ..state import StateStore
from ..util import Runner
from .common import package_change, path_change, setting_change


class AppearanceWhiteSurModule:
    id = "appearance.whitesur"
    title = "WhiteSur mac-style appearance"

    GTK_REPO = "vinceliuice/WhiteSur-gtk-theme"
    GTK_COMMIT = "3bd1b21f7a097c2a4cd88d58ed94385463455692"
    ICON_REPO = "vinceliuice/WhiteSur-icon-theme"
    ICON_COMMIT = "bab5833b5cae200bccb786a2d3d6afa2201e7806"
    CURSOR_REPO = "vinceliuice/WhiteSur-cursors"
    CURSOR_COMMIT = "e190baf618ed95ee217d2fd45589bd309b37672b"

    dependencies = ["sassc", "libglib2.0-dev-bin", "libxml2-utils", "gnome-shell-extensions"]

    @property
    def data_home(self) -> Path:
        return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    @property
    def themes_dir(self) -> Path:
        return self.data_home / "themes"

    @property
    def icons_dir(self) -> Path:
        return self.data_home / "icons"

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        changes = [package_change(runner, package, self.id) for package in self.dependencies]
        changes.extend([
            path_change(self.id, "WhiteSur GTK", self.themes_dir / "MacUbuntu-WhiteSur-Dark-solid"),
            path_change(self.id, "WhiteSur icons", self.icons_dir / "MacUbuntu-WhiteSur"),
            path_change(self.id, "WhiteSur cursors", self.icons_dir / "MacUbuntu-WhiteSur-cursors"),
        ])
        settings = [
            ("org.gnome.desktop.interface", "gtk-theme", "'MacUbuntu-WhiteSur-Dark-solid'", "WhiteSur application theme"),
            ("org.gnome.desktop.interface", "icon-theme", "'MacUbuntu-WhiteSur'", "WhiteSur icon theme"),
            ("org.gnome.desktop.interface", "cursor-theme", "'MacUbuntu-WhiteSur-cursors'", "WhiteSur cursor theme"),
            ("org.gnome.desktop.interface", "color-scheme", "'prefer-dark'", "dark appearance"),
            ("org.gnome.shell.extensions.user-theme", "name", "'MacUbuntu-WhiteSur-Dark-solid'", "WhiteSur shell theme"),
        ]
        changes.extend(setting_change(runner, self.id, *setting) for setting in settings)
        user_theme_uuid = "user-theme@gnome-shell-extensions.gcampax.github.com"
        if not gnome_extension_known(runner, user_theme_uuid):
            extension_action = "install" if package_change(runner, "gnome-shell-extensions", self.id)["action"] == "install" else "skip"
        else:
            extension_action = "keep" if gnome_extension_enabled(runner, user_theme_uuid) else "set"
        changes.append({"module": self.id, "kind": "gnome_extension", "resource": "User Themes", "uuid": user_theme_uuid, "action": extension_action})
        return changes

    def apply(self, *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        results.append(apply_apt_bundle(runner=runner, store=store, state=state, app_version=app_version, requested=self.dependencies, dry_run=dry_run))
        gtk_result = apply_pinned_installer(
            runner=runner, store=store, state=state, app_version=app_version,
            resource="whitesur-gtk", repository=self.GTK_REPO, commit=self.GTK_COMMIT,
            destination=self.themes_dir, owned_prefix="MacUbuntu-WhiteSur",
            command=["bash", "{root}/install.sh", "-d", "{dest}", "-n", "MacUbuntu-WhiteSur", "-o", "solid", "-c", "dark", "-c", "light"],
            required_paths=["MacUbuntu-WhiteSur-Dark-solid", "MacUbuntu-WhiteSur-Light-solid"], dry_run=dry_run,
        )
        results.append(gtk_result)
        icon_result = apply_pinned_installer(
            runner=runner, store=store, state=state, app_version=app_version,
            resource="whitesur-icons", repository=self.ICON_REPO, commit=self.ICON_COMMIT,
            destination=self.icons_dir, owned_prefix="MacUbuntu-WhiteSur",
            command=["bash", "{root}/install.sh", "-d", "{dest}", "-n", "MacUbuntu-WhiteSur"],
            required_paths=["MacUbuntu-WhiteSur"], dry_run=dry_run,
        )
        results.append(icon_result)
        cursor_result = apply_pinned_subdir_copy(
            store=store, state=state, app_version=app_version,
            resource="whitesur-cursors", repository=self.CURSOR_REPO, commit=self.CURSOR_COMMIT,
            subdir="dist", destination=self.icons_dir / "MacUbuntu-WhiteSur-cursors", dry_run=dry_run,
        )
        results.append(cursor_result)
        if any(result.get("status") in {"skipped", "kept"} for result in (gtk_result, icon_result, cursor_result)):
            results.append({"kind": "appearance", "resource": "WhiteSur activation", "status": "skipped", "reason": "theme_assets_not_managed"})
            return results

        results.append(apply_extension_state(
            runner=runner, store=store, state=state, app_version=app_version,
            uuid="user-theme@gnome-shell-extensions.gcampax.github.com", dry_run=dry_run,
        ))
        for schema, key, desired in [
            ("org.gnome.desktop.interface", "gtk-theme", "'MacUbuntu-WhiteSur-Dark-solid'"),
            ("org.gnome.desktop.interface", "icon-theme", "'MacUbuntu-WhiteSur'"),
            ("org.gnome.desktop.interface", "cursor-theme", "'MacUbuntu-WhiteSur-cursors'"),
            ("org.gnome.desktop.interface", "color-scheme", "'prefer-dark'"),
            ("org.gnome.shell.extensions.user-theme", "name", "'MacUbuntu-WhiteSur-Dark-solid'"),
        ]:
            results.append(apply_gsetting(runner=runner, store=store, state=state, app_version=app_version, schema=schema, key=key, desired=desired, dry_run=dry_run))
        return results
