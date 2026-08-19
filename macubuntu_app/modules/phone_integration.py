from __future__ import annotations

from typing import Any

from ..external import apply_gnome_extension, gnome_extension_enabled, gnome_extension_known
from ..operations import apply_apt_bundle
from ..state import StateStore
from ..util import Runner, package_installed
from .common import package_available, package_change, shell_major


class PhoneIntegrationModule:
    id = "phone.integration"
    title = "Phone integration for iPhone and Android"
    GS_UUID = "gsconnect@andyholmes.github.io"
    GS_PINS = {
        "42": {"version": 68, "review_id": 66552},
        "46": {"version": 72, "review_id": 70399},
    }
    IPHONE_PACKAGES = ["libimobiledevice-utils", "ifuse", "usbmuxd", "gvfs-backends"]

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        for package in self.IPHONE_PACKAGES:
            if package_available(runner, package):
                changes.append(package_change(runner, package, self.id))
            else:
                changes.append({"module": self.id, "kind": "package", "resource": package, "action": "skip", "reason": "package_unavailable"})
        major = shell_major(runner)
        pin = self.GS_PINS.get(major or "")
        if package_installed(runner, "kdeconnect"):
            changes.append({"module": self.id, "kind": "gnome_extension", "resource": "GSConnect", "action": "skip", "reason": "kdeconnect_conflict"})
        elif pin is None:
            changes.append({"module": self.id, "kind": "gnome_extension", "resource": "GSConnect", "action": "skip", "reason": "unsupported_gnome_version"})
        else:
            if not gnome_extension_known(runner, self.GS_UUID):
                action = "install"
            else:
                action = "keep" if gnome_extension_enabled(runner, self.GS_UUID) else "set"
            changes.append({
                "module": self.id,
                "kind": "gnome_extension",
                "resource": "GSConnect",
                "uuid": self.GS_UUID,
                "version": int(pin["version"]),
                "review_id": int(pin["review_id"]),
                "action": action,
            })
        return changes

    def apply(self, *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        available = [package for package in self.IPHONE_PACKAGES if package_available(runner, package)]
        if available:
            results.append(apply_apt_bundle(runner=runner, store=store, state=state, app_version=app_version, requested=available, dry_run=dry_run))
        for package in self.IPHONE_PACKAGES:
            if package not in available:
                results.append({"kind": "package", "resource": package, "status": "skipped", "reason": "package_unavailable"})
        if package_installed(runner, "kdeconnect"):
            results.append({"kind": "gnome_extension", "resource": self.GS_UUID, "status": "skipped", "reason": "kdeconnect_conflict"})
            return results
        major = shell_major(runner)
        pin = self.GS_PINS.get(major or "")
        if pin is None:
            results.append({"kind": "gnome_extension", "resource": self.GS_UUID, "status": "skipped", "reason": "unsupported_gnome_version"})
            return results
        results.append(apply_gnome_extension(
            runner=runner,
            store=store,
            state=state,
            app_version=app_version,
            uuid=self.GS_UUID,
            version=int(pin["version"]),
            review_id=int(pin["review_id"]),
            shell_major=str(major),
            dry_run=dry_run,
        ))
        return results
