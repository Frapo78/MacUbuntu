from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..external import apply_pinned_download
from ..operations import apply_gsetting
from ..state import StateStore
from ..util import Runner
from .common import path_change, setting_change


class WallpaperWhiteSurModule:
    id = "appearance.wallpaper"
    title = "WhiteSur desktop and lock-screen wallpaper"

    COMMIT = "5c1d7ca20b8de0a7efe443792c19e49277262e02"
    LIGHT_BLOB = "43c035745ebaf1622317b2ea7537b127447454fc"
    DARK_BLOB = "5d43c022c58b853e873ea43a4c7fc86cc25c5b85"

    @property
    def directory(self) -> Path:
        data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return data_home / "backgrounds" / "MacUbuntu"

    @property
    def light(self) -> Path:
        return self.directory / "WhiteSur-light.jpg"

    @property
    def dark(self) -> Path:
        return self.directory / "WhiteSur-dark.jpg"

    def _uri(self, path: Path) -> str:
        return repr(path.expanduser().resolve().as_uri())

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        changes = [path_change(self.id, "WhiteSur light wallpaper", self.light), path_change(self.id, "WhiteSur dark wallpaper", self.dark)]
        for setting in [
            ("org.gnome.desktop.background", "picture-uri", self._uri(self.light), "WhiteSur desktop wallpaper"),
            ("org.gnome.desktop.background", "picture-uri-dark", self._uri(self.dark), "WhiteSur dark wallpaper"),
            ("org.gnome.desktop.screensaver", "picture-uri", self._uri(self.dark), "WhiteSur lock-screen wallpaper"),
        ]:
            changes.append(setting_change(runner, self.id, *setting))
        return changes

    def apply(self, *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool) -> list[dict[str, Any]]:
        base = "https://raw.githubusercontent.com/vinceliuice/WhiteSur-wallpapers"
        light_result = apply_pinned_download(store=store, state=state, app_version=app_version, resource="whitesur-wallpaper-light", url=f"{base}/{self.COMMIT}/2k/WhiteSur-light.jpg", destination=self.light, expected_git_blob_sha1=self.LIGHT_BLOB, dry_run=dry_run)
        dark_result = apply_pinned_download(store=store, state=state, app_version=app_version, resource="whitesur-wallpaper-dark", url=f"{base}/{self.COMMIT}/2k/WhiteSur-dark.jpg", destination=self.dark, expected_git_blob_sha1=self.DARK_BLOB, dry_run=dry_run)
        results = [light_result, dark_result]
        if any(result.get("status") in {"skipped", "kept"} for result in (light_result, dark_result)):
            results.append({"kind": "gsettings", "resource": "wallpaper-selection", "status": "skipped", "reason": "wallpaper_files_not_managed"})
            return results
        for schema, key, desired in [
            ("org.gnome.desktop.background", "picture-uri", self._uri(self.light)),
            ("org.gnome.desktop.background", "picture-uri-dark", self._uri(self.dark)),
            ("org.gnome.desktop.screensaver", "picture-uri", self._uri(self.dark)),
        ]:
            results.append(apply_gsetting(runner=runner, store=store, state=state, app_version=app_version, schema=schema, key=key, desired=desired, dry_run=dry_run))
        return results
