from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..external import apply_extension_state, apply_managed_text_file
from ..state import StateStore
from ..util import Runner
from .common import path_change, shell_major


class FullscreenSpacesModule:
    """Give every true fullscreen window its own GNOME workspace.

    Existing third-party extensions were useful design references but commonly
    optimize away the new workspace when the app is already alone. MacUbuntu's
    own minimal extension deliberately does not: every fullscreen transition
    creates a fresh Space and remembers where the window came from. If GNOME's
    dynamic-workspace cleanup removes the empty origin, it is recreated at the
    original position when fullscreen ends.
    """

    id = "spaces.fullscreen"
    title = "macOS-style fullscreen Spaces"

    UUID = "macubuntu-fullscreen-spaces@francescopoltero"
    SUPPORTED_MAJORS = {"42", "46"}

    @property
    def data_home(self) -> Path:
        return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    @property
    def extension_dir(self) -> Path:
        return self.data_home / "gnome-shell" / "extensions" / self.UUID

    @property
    def extension_file(self) -> Path:
        return self.extension_dir / "extension.js"

    @property
    def metadata_file(self) -> Path:
        return self.extension_dir / "metadata.json"

    @property
    def assets_dir(self) -> Path:
        return Path(__file__).resolve().parents[1] / "assets"

    def _source_file(self, major: str) -> Path:
        return self.assets_dir / f"fullscreen_spaces_gnome{major}.js"

    def _metadata(self, major: str) -> str:
        return json.dumps(
            {
                "uuid": self.UUID,
                "name": "MacUbuntu Fullscreen Spaces",
                "description": "Give every true fullscreen application a dedicated workspace and return it afterwards.",
                "shell-version": [major],
                "version": 1,
            },
            indent=2,
            sort_keys=True,
        ) + "\n"

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        major = shell_major(runner)
        if major not in self.SUPPORTED_MAJORS:
            return [{
                "module": self.id,
                "kind": "gnome_extension",
                "resource": self.UUID,
                "action": "skip",
                "reason": "unsupported_gnome_version",
            }]
        return [
            path_change(self.id, "MacUbuntu Fullscreen Spaces code", self.extension_file),
            path_change(self.id, "MacUbuntu Fullscreen Spaces metadata", self.metadata_file),
            {
                "module": self.id,
                "kind": "gnome_extension",
                "resource": self.UUID,
                "action": "set",
                "desired": "enabled",
                "behavior": "every_fullscreen_gets_dedicated_workspace",
            },
        ]

    def apply(
        self,
        *,
        runner: Runner,
        store: StateStore,
        state: dict[str, Any],
        app_version: str,
        dry_run: bool,
    ) -> list[dict[str, Any]]:
        major = shell_major(runner)
        if major not in self.SUPPORTED_MAJORS:
            return [{
                "kind": "gnome_extension",
                "resource": self.UUID,
                "status": "skipped",
                "reason": "unsupported_gnome_version",
            }]

        try:
            source = self._source_file(str(major)).read_text(encoding="utf-8")
        except OSError as exc:
            return [{
                "kind": "gnome_extension",
                "resource": self.UUID,
                "status": "skipped",
                "reason": "bundled_extension_missing",
                "error": str(exc),
            }]

        asset_results = [
            apply_managed_text_file(
                store=store,
                state=state,
                app_version=app_version,
                resource="macubuntu-fullscreen-spaces-code",
                path=self.extension_file,
                content=source,
                dry_run=dry_run,
            ),
            apply_managed_text_file(
                store=store,
                state=state,
                app_version=app_version,
                resource="macubuntu-fullscreen-spaces-metadata",
                path=self.metadata_file,
                content=self._metadata(str(major)),
                dry_run=dry_run,
            ),
        ]
        results: list[dict[str, Any]] = list(asset_results)
        if any(result.get("status") in {"skipped", "kept"} for result in asset_results):
            results.append({
                "kind": "gnome_extension",
                "resource": self.UUID,
                "status": "skipped",
                "reason": "unmanaged_or_drifted_extension_files",
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
        return results
