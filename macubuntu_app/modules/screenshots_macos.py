from __future__ import annotations

from typing import Any

from ..operations import apply_gsetting
from ..state import StateStore
from ..util import Runner
from .common import setting_change


class ScreenshotsMacOSModule:
    """Configure GNOME Shell's native screenshot UI with macOS-like shortcuts.

    GNOME 42+ ships screenshot and screencast capture directly in GNOME Shell,
    including area/window/full-screen selection and clipboard integration.  We
    reuse that native implementation so the behavior remains solid on both X11
    and Wayland instead of adding a second screenshot daemon.
    """

    id = "screenshots.macos"
    title = "macOS-style screenshots and screen recording"

    settings = [
        (
            "org.gnome.shell.keybindings",
            "screenshot",
            "['<Shift><Super>3', '<Shift>Print']",
            "Command-Shift-3 style full-screen screenshot",
        ),
        (
            "org.gnome.shell.keybindings",
            "show-screenshot-ui",
            "['<Shift><Super>4', '<Shift><Super>5', 'Print']",
            "Command-Shift-4/5 style screenshot and recording palette",
        ),
        (
            "org.gnome.shell.keybindings",
            "screenshot-window",
            "['<Alt>Print']",
            "retain GNOME focused-window capture fallback",
        ),
        (
            "org.gnome.shell.keybindings",
            "show-screen-recording-ui",
            "['<Ctrl><Shift><Alt>R']",
            "retain direct GNOME screencast fallback",
        ),
    ]

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        return [setting_change(runner, self.id, *setting) for setting in self.settings]

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
        for schema, key, desired, _ in self.settings:
            results.append(
                apply_gsetting(
                    runner=runner,
                    store=store,
                    state=state,
                    app_version=app_version,
                    schema=schema,
                    key=key,
                    desired=desired,
                    dry_run=dry_run,
                )
            )
        return results
