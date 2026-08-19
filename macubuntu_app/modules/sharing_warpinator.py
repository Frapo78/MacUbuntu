from __future__ import annotations

from typing import Any

from ..external import FLATHUB_URL, apply_flatpak_app, apply_flatpak_remote
from ..operations import apply_apt_bundle
from ..state import StateStore
from ..util import Runner, package_installed
from .common import package_change


class SharingWarpinatorModule:
    id = "sharing.warpinator"
    title = "AirDrop-like LAN sharing with Warpinator"
    APP_ID = "org.x.Warpinator"

    def _app_installed(self, runner: Runner) -> bool:
        return runner.exists("flatpak") and runner.run(["flatpak", "--user", "info", self.APP_ID], check=False).returncode == 0

    def _flathub_exists(self, runner: Runner) -> bool:
        if not runner.exists("flatpak"):
            return False
        cp = runner.run(["flatpak", "--user", "remotes", "--columns=name"], check=False)
        return cp.returncode == 0 and "flathub" in (cp.stdout or "").splitlines()

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        return [
            package_change(runner, "flatpak", self.id),
            {"module": self.id, "kind": "flatpak_remote", "resource": "flathub", "action": "keep" if self._flathub_exists(runner) else "install"},
            {"module": self.id, "kind": "flatpak_app", "resource": self.APP_ID, "action": "keep" if self._app_installed(runner) else "install"},
        ]

    def apply(self, *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = [apply_apt_bundle(runner=runner, store=store, state=state, app_version=app_version, requested=["flatpak"], dry_run=dry_run)]
        if dry_run and not package_installed(runner, "flatpak"):
            results.append({"kind": "flatpak_remote", "resource": "flathub", "status": "would_install"})
            results.append({"kind": "flatpak_app", "resource": self.APP_ID, "status": "would_install"})
            return results
        results.append(apply_flatpak_remote(runner=runner, store=store, state=state, app_version=app_version, name="flathub", url=FLATHUB_URL, dry_run=dry_run))
        results.append(apply_flatpak_app(runner=runner, store=store, state=state, app_version=app_version, remote="flathub", app_id=self.APP_ID, dry_run=dry_run))
        return results
