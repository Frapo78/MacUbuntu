from __future__ import annotations

from pathlib import Path
from typing import Any

from ..external import apply_apt_repository, apply_managed_text_file, apply_service_state, apt_repository_present
from ..operations import apply_apt_bundle
from ..state import StateStore
from ..util import Runner, package_installed
from .common import package_change, service_change


class SpotlightUlauncherModule:
    id = "spotlight.ulauncher"
    title = "Spotlight-like launcher with Ulauncher"
    PPA = "ppa:agornostal/ulauncher"

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        if package_installed(runner, "ulauncher"):
            changes.append({"module": self.id, "kind": "package", "resource": "ulauncher", "action": "keep"})
        else:
            repo_present = apt_repository_present(self.PPA)
            if not repo_present:
                changes.append(package_change(runner, "software-properties-common", self.id))
            changes.append({"module": self.id, "kind": "apt_repository", "resource": self.PPA, "action": "keep" if repo_present else "install"})
            changes.append({"module": self.id, "kind": "package", "resource": "ulauncher", "action": "install"})
        service = runner.run(["systemctl", "--user", "cat", "ulauncher.service"], check=False)
        if service.returncode == 0:
            changes.append(service_change(runner, self.id, "ulauncher.service", user=True))
        else:
            autostart = Path.home() / ".config" / "autostart" / "macubuntu-ulauncher.desktop"
            changes.append({"module": self.id, "kind": "managed_file", "resource": "Ulauncher autostart", "action": "keep" if autostart.exists() else "install", "path": str(autostart)})
        return changes

    def apply(self, *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        if not package_installed(runner, "ulauncher") and not apt_repository_present(self.PPA):
            results.append(apply_apt_bundle(runner=runner, store=store, state=state, app_version=app_version, requested=["software-properties-common"], dry_run=dry_run))
            results.append(apply_apt_repository(runner=runner, store=store, state=state, app_version=app_version, ppa=self.PPA, dry_run=dry_run))
        results.append(apply_apt_bundle(runner=runner, store=store, state=state, app_version=app_version, requested=["ulauncher"], dry_run=dry_run))
        service = runner.run(["systemctl", "--user", "cat", "ulauncher.service"], check=False)
        if service.returncode == 0:
            results.append(apply_service_state(runner=runner, store=store, state=state, app_version=app_version, unit="ulauncher.service", user=True, dry_run=dry_run))
        else:
            content = """[Desktop Entry]\nType=Application\nName=Ulauncher (MacUbuntu)\nComment=Spotlight-like launcher managed by MacUbuntu\nExec=ulauncher\nTerminal=false\nX-GNOME-Autostart-enabled=true\nOnlyShowIn=GNOME;Unity;\n"""
            results.append(apply_managed_text_file(store=store, state=state, app_version=app_version, resource="ulauncher-autostart", path=Path.home() / ".config" / "autostart" / "macubuntu-ulauncher.desktop", content=content, dry_run=dry_run))
        return results
