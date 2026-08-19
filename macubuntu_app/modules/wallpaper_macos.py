from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ..external import apply_pinned_download
from ..operations import apply_gsetting
from ..state import StateStore
from ..util import Runner
from .common import path_change, setting_change


class WallpaperMacCollectionModule:
    """Install a small, pinned, redistributable mac-inspired wallpaper set.

    MacUbuntu deliberately does not redistribute Apple-owned macOS wallpaper
    files.  The collection comes from the open-source WhiteSur and MacTahoe
    projects and gives users Big Sur/Monterey/Tahoe-inspired choices while
    preserving the project's clean licensing model.
    """

    id = "appearance.wallpapers"
    title = "Mac-inspired Big Sur, Monterey and Tahoe wallpapers"

    WHITESUR_COMMIT = "5c1d7ca20b8de0a7efe443792c19e49277262e02"
    MACTAHOE_COMMIT = "ae82d8ea6a7eba42b9bf375ec602538c34fdabab"

    WALLPAPERS = {
        "WhiteSur-light.jpg": {
            "url": f"https://raw.githubusercontent.com/vinceliuice/WhiteSur-wallpapers/{WHITESUR_COMMIT}/2k/WhiteSur-light.jpg",
            "blob": "43c035745ebaf1622317b2ea7537b127447454fc",
            "resource": "whitesur-wallpaper-light",
        },
        "WhiteSur-dark.jpg": {
            "url": f"https://raw.githubusercontent.com/vinceliuice/WhiteSur-wallpapers/{WHITESUR_COMMIT}/2k/WhiteSur-dark.jpg",
            "blob": "5d43c022c58b853e873ea43a4c7fc86cc25c5b85",
            "resource": "whitesur-wallpaper-dark",
        },
        "Monterey-light.jpg": {
            "url": f"https://raw.githubusercontent.com/vinceliuice/WhiteSur-wallpapers/{WHITESUR_COMMIT}/2k/Monterey-light.jpg",
            "blob": "4b1aed36dfe3d10fab72caf573a9ec4a1fe2d3c2",
            "resource": "monterey-wallpaper-light",
        },
        "Monterey-dark.jpg": {
            "url": f"https://raw.githubusercontent.com/vinceliuice/WhiteSur-wallpapers/{WHITESUR_COMMIT}/2k/Monterey-dark.jpg",
            "blob": "bdfc4cbdca810ae1c8d9dd9cf40b961d30bbf60c",
            "resource": "monterey-wallpaper-dark",
        },
        "MacTahoe-day.jpeg": {
            "url": f"https://raw.githubusercontent.com/vinceliuice/MacTahoe-gtk-theme/{MACTAHOE_COMMIT}/wallpaper/MacTahoe-day.jpeg",
            "blob": "fb4a50aa1eddb93d2e3d901e6bf001e89fec84bd",
            "resource": "mactahoe-wallpaper-day",
        },
        "MacTahoe-night.jpeg": {
            "url": f"https://raw.githubusercontent.com/vinceliuice/MacTahoe-gtk-theme/{MACTAHOE_COMMIT}/wallpaper/MacTahoe-night.jpeg",
            "blob": "c516afb27d3d7c2713a0ab4468941631d75e0415",
            "resource": "mactahoe-wallpaper-night",
        },
    }

    @property
    def directory(self) -> Path:
        data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return data_home / "backgrounds" / "MacUbuntu"

    @property
    def day(self) -> Path:
        return self.directory / "MacTahoe-day.jpeg"

    @property
    def night(self) -> Path:
        return self.directory / "MacTahoe-night.jpeg"

    def _uri(self, path: Path) -> str:
        return repr(path.expanduser().resolve().as_uri())

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        for filename in self.WALLPAPERS:
            changes.append(path_change(
                self.id,
                f"MacUbuntu wallpaper {filename}",
                self.directory / filename,
            ))

        settings = [
            (
                "org.gnome.desktop.background",
                "picture-uri",
                self._uri(self.day),
                "Tahoe-inspired light desktop wallpaper",
            ),
            (
                "org.gnome.desktop.background",
                "picture-uri-dark",
                self._uri(self.night),
                "Tahoe-inspired dark desktop wallpaper",
            ),
            (
                "org.gnome.desktop.background",
                "picture-options",
                "'zoom'",
                "mac-like fill behavior",
            ),
            (
                "org.gnome.desktop.screensaver",
                "picture-uri",
                self._uri(self.night),
                "Tahoe-inspired lock-screen wallpaper",
            ),
        ]
        changes.extend(setting_change(runner, self.id, *setting) for setting in settings)
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
        asset_results: list[dict[str, Any]] = []

        for filename, spec in self.WALLPAPERS.items():
            result = apply_pinned_download(
                store=store,
                state=state,
                app_version=app_version,
                resource=str(spec["resource"]),
                url=str(spec["url"]),
                destination=self.directory / filename,
                expected_git_blob_sha1=str(spec["blob"]),
                dry_run=dry_run,
            )
            results.append(result)
            asset_results.append(result)

        # A user-modified managed wallpaper is preserved rather than silently
        # selected over.  Other collection files may still install normally.
        if any(
            result.get("status") in {"skipped", "kept"}
            and result.get("resource") in {"mactahoe-wallpaper-day", "mactahoe-wallpaper-night"}
            for result in asset_results
        ):
            results.append({
                "kind": "gsettings",
                "resource": "wallpaper-selection",
                "status": "skipped",
                "reason": "default_wallpaper_files_not_managed",
            })
            return results

        for schema, key, desired in [
            ("org.gnome.desktop.background", "picture-uri", self._uri(self.day)),
            ("org.gnome.desktop.background", "picture-uri-dark", self._uri(self.night)),
            ("org.gnome.desktop.background", "picture-options", "'zoom'"),
            ("org.gnome.desktop.screensaver", "picture-uri", self._uri(self.night)),
        ]:
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
