from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from ..external import apply_extension_state
from ..operations import apply_apt_bundle
from ..state import StateStore
from ..util import Runner
from .common import package_available, package_change, path_change, shell_major
from .keyboard_accents_support import (
    INPUT_SCHEMA, LEGACY_SOURCE, apply_or_upgrade_text_file,
    migrate_legacy_input_source, parse_sources, retire_owned_resource,
)


class PressHoldAccentsModule:
    """Transparent macOS-like press-and-hold accents under normal XKB layouts."""

    id = "keyboard.press-hold-accents"
    title = "press-and-hold accent picker"
    ENGINE_NAME = "macubuntu-accents"
    LEGACY_INPUT_SOURCE = LEGACY_SOURCE
    BRIDGE_UUID = "macubuntu-accent-bridge@francescopoltero"
    SUPPORTED_SHELL_MAJORS = {"42", "46"}
    _parse_sources = staticmethod(parse_sources)

    @property
    def data_home(self) -> Path:
        return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    @property
    def config_home(self) -> Path:
        return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    @property
    def assets_dir(self) -> Path:
        return Path(__file__).resolve().parents[1] / "assets"

    @property
    def engine_file(self) -> Path:
        return self.data_home / "macubuntu" / "input" / "macubuntu_accent_engine.py"

    @property
    def activation_file(self) -> Path:
        return self.data_home / "macubuntu" / "input" / "activate-accents.sh"

    @property
    def component_file(self) -> Path:
        return self.data_home / "ibus" / "component" / "macubuntu-accents.xml"

    @property
    def autostart_file(self) -> Path:
        return self.config_home / "autostart" / "macubuntu-accents.desktop"

    @property
    def bridge_dir(self) -> Path:
        return self.data_home / "gnome-shell" / "extensions" / self.BRIDGE_UUID

    def _packages(self, runner: Runner) -> list[str]:
        wanted = ["ibus", "python3-gi", "gir1.2-ibus-1.0"]
        return [p for p in wanted if package_available(runner, p)]

    def _component_xml(self) -> str:
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<component>
  <name>org.freedesktop.IBus.MacUbuntuAccents</name>
  <description>MacUbuntu transparent press-and-hold accent filter</description>
  <exec>python3 {self.engine_file} --ibus</exec><version>0.6.1</version>
  <author>Francesco Poltero and MacUbuntu contributors</author><license>MIT</license>
  <homepage>https://github.com/Frapo78/MacUbuntu</homepage><textdomain>macubuntu</textdomain>
  <engines><engine><name>{self.ENGINE_NAME}</name><language>other</language><license>MIT</license>
    <author>Francesco Poltero and MacUbuntu contributors</author><icon>ibus-keyboard</icon>
    <layout>default</layout><longname>MacUbuntu Accents</longname>
    <description>Hold letters to choose accented variants</description><rank>99</rank>
  </engine></engines>
</component>
'''

    def _activation_script(self) -> str:
        engine = str(self.engine_file).replace('"', '\\"')
        component = str(self.component_file).replace('"', '\\"')
        return f'''#!/bin/sh
nohup python3 "{engine}" --standalone --component "{component}" >/dev/null 2>&1 &
i=0
while [ "$i" -lt 12 ]; do
    current="$(ibus engine 2>/dev/null || true)"
    case "$current" in
        '{self.ENGINE_NAME}') exit 0 ;;
        xkb:*) ibus engine '{self.ENGINE_NAME}' >/dev/null 2>&1 && exit 0 ;;
        '') ;;
        *) exit 0 ;;
    esac
    i=$((i + 1)); sleep 0.25
done
exit 0
'''

    def _autostart(self) -> str:
        path = str(self.activation_file).replace('"', '\\"')
        return f'''[Desktop Entry]
Type=Application
Name=MacUbuntu Accents
Comment=Start the transparent MacUbuntu press-and-hold accent filter
Exec=/bin/sh "{path}"
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=2
'''

    def _bridge_metadata(self, major: str) -> str:
        return json.dumps({
            "uuid": self.BRIDGE_UUID,
            "name": "MacUbuntu Accent Bridge",
            "description": "Keeps MacUbuntu Accents underneath normal GNOME XKB sources without adding another keyboard.",
            "shell-version": [major], "version": 1,
        }, indent=2, sort_keys=True) + "\n"

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        from ..system import gsettings_get
        for key in ("sources", "mru-sources"):
            current = parse_sources(gsettings_get(runner, INPUT_SCHEMA, key))
            if current is not None and LEGACY_SOURCE in current:
                changes.append({"module": self.id, "kind": "gsettings", "resource": f"{INPUT_SCHEMA}::{key}", "action": "remove", "reason": "v0.6_legacy_visible_source"})
        major = shell_major(runner)
        if major not in self.SUPPORTED_SHELL_MAJORS:
            return changes + [{"module": self.id, "kind": "ibus_engine", "resource": self.ENGINE_NAME, "action": "skip", "reason": "unsupported_gnome_version"}]
        changes.extend(package_change(runner, p, self.id) for p in self._packages(runner))
        for label, path in self._paths():
            changes.append(path_change(self.id, label, path))
        changes.append({"module": self.id, "kind": "gnome_extension", "resource": self.BRIDGE_UUID, "action": "set", "desired": "enabled"})
        return changes

    def _paths(self) -> list[tuple[str, Path]]:
        return [
            ("MacUbuntu accent engine", self.engine_file),
            ("MacUbuntu IBus component", self.component_file),
            ("MacUbuntu accent activator", self.activation_file),
            ("MacUbuntu accent autostart", self.autostart_file),
            ("MacUbuntu accent bridge code", self.bridge_dir / "extension.js"),
            ("MacUbuntu accent bridge metadata", self.bridge_dir / "metadata.json"),
        ]

    def _asset_specs(self, major: str) -> list[tuple[str, Path, str, int]]:
        engine = (self.assets_dir / "macubuntu_accent_engine.py").read_text(encoding="utf-8")
        bridge = (self.assets_dir / f"accent_bridge_gnome{major}.js").read_text(encoding="utf-8")
        return [
            ("macubuntu-accent-engine", self.engine_file, engine, 0o755),
            ("macubuntu-accent-component", self.component_file, self._component_xml(), 0o644),
            ("macubuntu-accent-activator", self.activation_file, self._activation_script(), 0o755),
            ("macubuntu-accent-autostart", self.autostart_file, self._autostart(), 0o644),
            ("macubuntu-accent-bridge-code", self.bridge_dir / "extension.js", bridge, 0o644),
            ("macubuntu-accent-bridge-metadata", self.bridge_dir / "metadata.json", self._bridge_metadata(major), 0o644),
        ]

    def _activate_now(self, runner: Runner) -> dict[str, Any]:
        launch = runner.run(["/bin/sh", str(self.activation_file)], check=False)
        if launch.returncode != 0:
            return {"kind": "ibus_engine", "resource": self.ENGINE_NAME, "status": "configured", "reason": "activation_script_failed"}
        for _ in range(8):
            current = runner.run(["ibus", "engine"], check=False)
            if (current.stdout or "").strip() == self.ENGINE_NAME:
                return {"kind": "ibus_engine", "resource": self.ENGINE_NAME, "status": "activated"}
            time.sleep(0.25)
        return {"kind": "ibus_engine", "resource": self.ENGINE_NAME, "status": "configured", "reason": "session_restart_required"}

    def apply(self, *, runner: Runner, store: StateStore, state: dict[str, Any], app_version: str, dry_run: bool) -> list[dict[str, Any]]:
        results = migrate_legacy_input_source(runner=runner, store=store, state=state, app_version=app_version, dry_run=dry_run)
        major = shell_major(runner)
        if major not in self.SUPPORTED_SHELL_MAJORS:
            return results + [{"kind": "ibus_engine", "resource": self.ENGINE_NAME, "status": "skipped", "reason": "unsupported_gnome_version"}]
        packages = self._packages(runner)
        if not {"ibus", "python3-gi", "gir1.2-ibus-1.0"}.issubset(packages):
            return results + [{"kind": "ibus_engine", "resource": self.ENGINE_NAME, "status": "skipped", "reason": "required_ibus_packages_unavailable"}]
        results.append(apply_apt_bundle(runner=runner, store=store, state=state, app_version=app_version, requested=packages, dry_run=dry_run))
        try:
            specs = self._asset_specs(str(major))
        except OSError as exc:
            return results + [{"kind": "ibus_engine", "resource": self.ENGINE_NAME, "status": "skipped", "reason": "bundled_input_asset_missing", "error": str(exc)}]
        assets = [apply_or_upgrade_text_file(store=store, state=state, app_version=app_version, resource=r, path=p, content=c, mode=m, dry_run=dry_run) for r, p, c, m in specs]
        results.extend(assets)
        if any(item.get("status") in {"skipped", "kept"} for item in assets):
            return results + [{"kind": "ibus_engine", "resource": self.ENGINE_NAME, "status": "skipped", "reason": "unmanaged_or_drifted_engine_files"}]
        retired = retire_owned_resource(resource="macubuntu-ibus-environment", runner=runner, store=store, state=state, app_version=app_version, dry_run=dry_run)
        if retired:
            results.append(retired)
        results.append(apply_extension_state(runner=runner, store=store, state=state, app_version=app_version, uuid=self.BRIDGE_UUID, dry_run=dry_run))
        if dry_run:
            return results + [{"kind": "ibus_engine", "resource": self.ENGINE_NAME, "status": "would_activate_transparently"}]
        self_test = runner.run(["python3", str(self.engine_file), "--self-test"], check=False)
        if self_test.returncode != 0:
            return results + [{"kind": "ibus_engine", "resource": self.ENGINE_NAME, "status": "skipped", "reason": "engine_self_test_failed", "stderr": self_test.stderr or ""}]
        probe = runner.run(["python3", "-c", "import gi; gi.require_version('IBus','1.0'); from gi.repository import IBus; IBus.init(); b=IBus.Bus(); raise SystemExit(0 if b.is_connected() else 1)"], check=False)
        if probe.returncode != 0 or not runner.exists("ibus"):
            return results + [{"kind": "ibus_engine", "resource": self.ENGINE_NAME, "status": "configured", "reason": "session_restart_required"}]
        results.append(self._activate_now(runner))
        return results
