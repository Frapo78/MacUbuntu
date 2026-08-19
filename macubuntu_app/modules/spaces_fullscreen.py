from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..external import (
    apply_extension_state,
    apply_pinned_subdir_copy,
    gnome_extension_enabled,
    gnome_extension_known,
)
from ..operations import apply_gsetting
from ..state import StateStore
from ..util import Runner
from .common import path_change, setting_change, shell_major


class FullscreenSpacesModule:
    """Move true fullscreen windows into an empty GNOME workspace.

    macOS models fullscreen applications as their own Space. GNOME does not do
    that natively, so MacUbuntu uses a pinned, version-appropriate release of
    Fullscreen to Empty Workspace and explicitly disables its optional
    maximize behavior: maximization stays on the current desktop; fullscreen
    gets a dedicated workspace and returns when fullscreen ends.
    """

    id = "spaces.fullscreen"
    title = "macOS-style fullscreen Spaces"

    UUID = "fullscreen-to-empty-workspace@aiono.dev"
    REPOSITORY = "onsah/fullscreen-to-new-workspace"
    SETTINGS_SCHEMA = "org.gnome.shell.extensions.fullscreen-to-empty-workspace"
    PINS = {
        # v14: last upstream generation declaring GNOME 42 support.
        "42": "a36f4a879f1bba1f7a0d3cc03af1f699238b73ef",
        # GNOME 46 port, explicitly tested upstream on Fedora 40 / GNOME 46.
        "46": "26014b6f8d569891381ab2ebc75c74a51d2454df",
    }

    @property
    def extension_dir(self) -> Path:
        data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return data_home / "gnome-shell" / "extensions" / self.UUID

    @property
    def schema_dir(self) -> Path:
        return self.extension_dir / "schemas"

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        major = shell_major(runner)
        pin = self.PINS.get(major or "")
        changes: list[dict[str, Any]] = [
            setting_change(
                runner,
                self.id,
                "org.gnome.mutter",
                "dynamic-workspaces",
                "true",
                "dynamic workspaces for disposable fullscreen Spaces",
            )
        ]
        if pin is None:
            changes.append({
                "module": self.id,
                "kind": "gnome_extension",
                "resource": self.UUID,
                "action": "skip",
                "reason": "unsupported_gnome_version",
            })
            return changes

        changes.append(path_change(self.id, "Fullscreen to Empty Workspace", self.extension_dir))
        known = gnome_extension_known(runner, self.UUID)
        changes.append({
            "module": self.id,
            "kind": "gnome_extension",
            "resource": self.UUID,
            "action": "keep" if known and gnome_extension_enabled(runner, self.UUID) else "set" if known else "install",
            "source": f"{self.REPOSITORY}@{pin}",
        })
        if self.schema_dir.exists():
            changes.append(setting_change(
                runner,
                self.id,
                self.SETTINGS_SCHEMA,
                "move-window-when-maximized",
                "false",
                "only real fullscreen windows receive a dedicated Space",
                schema_dir=self.schema_dir,
            ))
        else:
            changes.append({
                "module": self.id,
                "kind": "gsettings",
                "resource": f"{self.SETTINGS_SCHEMA}::move-window-when-maximized",
                "action": "set",
                "desired": "false",
                "reason": "schema_available_after_extension_install",
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
        results.append(apply_gsetting(
            runner=runner,
            store=store,
            state=state,
            app_version=app_version,
            schema="org.gnome.mutter",
            key="dynamic-workspaces",
            desired="true",
            dry_run=dry_run,
        ))

        major = shell_major(runner)
        pin = self.PINS.get(major or "")
        if pin is None:
            results.append({
                "kind": "gnome_extension",
                "resource": self.UUID,
                "status": "skipped",
                "reason": "unsupported_gnome_version",
            })
            return results

        source_result = apply_pinned_subdir_copy(
            store=store,
            state=state,
            app_version=app_version,
            resource="fullscreen-spaces-extension",
            repository=self.REPOSITORY,
            commit=pin,
            subdir="src",
            destination=self.extension_dir,
            dry_run=dry_run,
        )
        results.append(source_result)

        if source_result.get("status") in {"skipped", "kept"} and not gnome_extension_known(runner, self.UUID):
            results.append({
                "kind": "gnome_extension",
                "resource": self.UUID,
                "status": "skipped",
                "reason": "unmanaged_or_drifted_extension_path",
            })
            return results

        results.append(apply_extension_state(
            runner=runner,
            store=store,
            state=state,
            app_version=app_version,
            uuid=self.UUID,
            dry_run=dry_run,
        ))

        if not dry_run and not (self.schema_dir / "gschemas.compiled").exists():
            results.append({
                "kind": "gsettings",
                "resource": f"{self.SETTINGS_SCHEMA}::move-window-when-maximized",
                "status": "skipped",
                "reason": "extension_schema_missing",
            })
            return results

        results.append(apply_gsetting(
            runner=runner,
            store=store,
            state=state,
            app_version=app_version,
            schema=self.SETTINGS_SCHEMA,
            key="move-window-when-maximized",
            desired="false",
            dry_run=dry_run,
            schema_dir=self.schema_dir,
        ))
        return results
