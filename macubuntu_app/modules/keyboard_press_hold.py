from __future__ import annotations

import ast
import os
import time
from pathlib import Path
from typing import Any

from ..external import apply_managed_text_file, apply_pinned_subdir_copy
from ..operations import apply_apt_bundle, apply_gsetting
from ..state import StateStore
from ..system import gsettings_get
from ..util import Runner
from .common import package_available, package_change, path_change


class PressHoldAccentsModule:
    """Add a macOS-like press-and-hold accent picker through IBus.

    The implementation is pinned to press2accent's IBus engine. IBus is the
    desktop input-method layer, so this avoids X11-only key injection and works
    with Wayland applications. The user's original GNOME input sources are
    preserved and remain available as an immediate fallback.
    """

    id = "keyboard.press-hold-accents"
    title = "press-and-hold accent picker"

    REPOSITORY = "dresnite/press2accent"
    COMMIT = "5a1c3a5da3c2129c304f17d9bf70451d221206ec"
    ENGINE_NAME = "press2accent"
    INPUT_SOURCE = ("ibus", ENGINE_NAME)

    @property
    def data_home(self) -> Path:
        return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    @property
    def config_home(self) -> Path:
        return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    @property
    def engine_dir(self) -> Path:
        return self.data_home / "macubuntu" / "press2accent" / "ibus"

    @property
    def component_dir(self) -> Path:
        return self.data_home / "ibus" / "component"

    @property
    def component_file(self) -> Path:
        return self.component_dir / "macubuntu-press2accent.xml"

    @property
    def environment_file(self) -> Path:
        return self.config_home / "environment.d" / "50-macubuntu-ibus.conf"

    def _packages(self, runner: Runner) -> list[str]:
        wanted = ["ibus", "python3-gi", "gir1.2-ibus-1.0"]
        return [package for package in wanted if package_available(runner, package)]

    @staticmethod
    def _parse_sources(raw: str | None) -> list[tuple[str, str]] | None:
        if raw is None:
            return None
        try:
            parsed = ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return None
        if not isinstance(parsed, list):
            return None
        result: list[tuple[str, str]] = []
        for item in parsed:
            if not isinstance(item, tuple) or len(item) != 2:
                return None
            result.append((str(item[0]), str(item[1])))
        return result

    def _desired_sources(self, runner: Runner) -> tuple[str | None, str | None]:
        raw_sources = gsettings_get(runner, "org.gnome.desktop.input-sources", "sources")
        sources = self._parse_sources(raw_sources)
        if sources is None:
            return None, None
        if self.INPUT_SOURCE not in sources:
            sources.append(self.INPUT_SOURCE)

        raw_mru = gsettings_get(runner, "org.gnome.desktop.input-sources", "mru-sources")
        mru = self._parse_sources(raw_mru)
        if mru is None:
            mru = list(sources)
        mru = [self.INPUT_SOURCE] + [source for source in mru if source != self.INPUT_SOURCE]
        return repr(sources), repr(mru)

    def _component_xml(self) -> str:
        engine = self.engine_dir / "engine.py"
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<component>
  <name>org.freedesktop.IBus.MacUbuntuPress2Accent</name>
  <description>MacUbuntu press-and-hold accent input method</description>
  <exec>python3 {engine} --ibus</exec>
  <version>0.6.0</version>
  <author>press2accent contributors; integrated by MacUbuntu</author>
  <license>MIT</license>
  <homepage>https://github.com/dresnite/press2accent</homepage>
  <textdomain>press2accent</textdomain>
  <engines>
    <engine>
      <name>{self.ENGINE_NAME}</name>
      <language>en</language>
      <license>MIT</license>
      <author>press2accent contributors</author>
      <icon>ibus-keyboard</icon>
      <layout>default</layout>
      <longname>MacUbuntu Accents</longname>
      <description>Hold letters to choose accented variants</description>
      <rank>99</rank>
    </engine>
  </engines>
</component>
'''

    def _component_path_value(self) -> str:
        values = [str(self.component_dir)]
        existing = os.environ.get("IBUS_COMPONENT_PATH", "")
        for value in existing.split(":"):
            value = value.strip()
            if value and value not in values:
                values.append(value)
        if "/usr/share/ibus/component" not in values:
            values.append("/usr/share/ibus/component")
        return ":".join(values)

    def plan(self, runner: Runner) -> list[dict[str, Any]]:
        packages = self._packages(runner)
        changes = [package_change(runner, package, self.id) for package in packages]
        changes.extend([
            path_change(self.id, "press2accent IBus engine", self.engine_dir),
            path_change(self.id, "MacUbuntu IBus component", self.component_file),
            path_change(self.id, "MacUbuntu IBus environment", self.environment_file),
        ])
        desired_sources, desired_mru = self._desired_sources(runner)
        if desired_sources is None:
            changes.append({
                "module": self.id,
                "kind": "gsettings",
                "resource": "org.gnome.desktop.input-sources::sources",
                "action": "skip",
                "reason": "input_sources_unreadable",
            })
        else:
            current_sources = gsettings_get(runner, "org.gnome.desktop.input-sources", "sources")
            current_mru = gsettings_get(runner, "org.gnome.desktop.input-sources", "mru-sources")
            changes.append({
                "module": self.id,
                "kind": "gsettings",
                "resource": "org.gnome.desktop.input-sources::sources",
                "action": "keep" if current_sources == desired_sources else "set",
                "current": current_sources,
                "desired": desired_sources,
            })
            changes.append({
                "module": self.id,
                "kind": "gsettings",
                "resource": "org.gnome.desktop.input-sources::mru-sources",
                "action": "keep" if current_mru == desired_mru else "set",
                "current": current_mru,
                "desired": desired_mru,
            })
        return changes

    def _refresh_ibus_session(self, runner: Runner) -> dict[str, Any]:
        component_path = self._component_path_value()
        env = os.environ.copy()
        env["IBUS_COMPONENT_PATH"] = component_path

        if runner.exists("systemctl"):
            runner.run(
                ["systemctl", "--user", "set-environment", f"IBUS_COMPONENT_PATH={component_path}"],
                check=False,
                env=env,
            )
        if runner.exists("dbus-update-activation-environment"):
            runner.run(
                ["dbus-update-activation-environment", "--systemd", f"IBUS_COMPONENT_PATH={component_path}"],
                check=False,
                env=env,
            )

        write_cache = runner.run(["ibus", "write-cache"], check=False, env=env)
        restart = runner.run(["ibus", "restart"], check=False, env=env)
        if write_cache.returncode != 0 or restart.returncode != 0:
            return {
                "kind": "ibus_engine",
                "resource": self.ENGINE_NAME,
                "status": "configured",
                "reason": "session_restart_required",
            }

        for _ in range(6):
            engines = runner.run(["ibus", "list-engine"], check=False, env=env)
            if self.ENGINE_NAME in (engines.stdout or "").split():
                activate = runner.run(["ibus", "engine", self.ENGINE_NAME], check=False, env=env)
                if activate.returncode == 0:
                    return {
                        "kind": "ibus_engine",
                        "resource": self.ENGINE_NAME,
                        "status": "activated",
                    }
                break
            time.sleep(0.35)
        return {
            "kind": "ibus_engine",
            "resource": self.ENGINE_NAME,
            "status": "configured",
            "reason": "session_restart_required",
        }

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
        packages = self._packages(runner)
        if not {"ibus", "python3-gi", "gir1.2-ibus-1.0"}.issubset(set(packages)):
            results.append({
                "kind": "ibus_engine",
                "resource": self.ENGINE_NAME,
                "status": "skipped",
                "reason": "required_ibus_packages_unavailable",
            })
            return results

        results.append(apply_apt_bundle(
            runner=runner,
            store=store,
            state=state,
            app_version=app_version,
            requested=packages,
            dry_run=dry_run,
        ))

        source_result = apply_pinned_subdir_copy(
            store=store,
            state=state,
            app_version=app_version,
            resource="press2accent-ibus-source",
            repository=self.REPOSITORY,
            commit=self.COMMIT,
            subdir="ibus",
            destination=self.engine_dir,
            dry_run=dry_run,
        )
        results.append(source_result)
        if source_result.get("status") in {"skipped", "kept"}:
            results.append({
                "kind": "ibus_engine",
                "resource": self.ENGINE_NAME,
                "status": "skipped",
                "reason": "unmanaged_or_drifted_engine_path",
            })
            return results

        component_path = self._component_path_value()
        results.append(apply_managed_text_file(
            store=store,
            state=state,
            app_version=app_version,
            resource="press2accent-component",
            path=self.component_file,
            content=self._component_xml(),
            dry_run=dry_run,
        ))
        results.append(apply_managed_text_file(
            store=store,
            state=state,
            app_version=app_version,
            resource="press2accent-environment",
            path=self.environment_file,
            content=f"IBUS_COMPONENT_PATH={component_path}\n",
            dry_run=dry_run,
        ))

        desired_sources, desired_mru = self._desired_sources(runner)
        if desired_sources is None or desired_mru is None:
            results.append({
                "kind": "gsettings",
                "resource": "org.gnome.desktop.input-sources::sources",
                "status": "skipped",
                "reason": "input_sources_unreadable",
            })
            return results

        results.append(apply_gsetting(
            runner=runner,
            store=store,
            state=state,
            app_version=app_version,
            schema="org.gnome.desktop.input-sources",
            key="sources",
            desired=desired_sources,
            dry_run=dry_run,
        ))
        results.append(apply_gsetting(
            runner=runner,
            store=store,
            state=state,
            app_version=app_version,
            schema="org.gnome.desktop.input-sources",
            key="mru-sources",
            desired=desired_mru,
            dry_run=dry_run,
        ))

        if dry_run:
            results.append({
                "kind": "ibus_engine",
                "resource": self.ENGINE_NAME,
                "status": "would_activate",
            })
            return results

        probe = runner.run(
            ["python3", "-c", "import gi; gi.require_version('IBus','1.0'); from gi.repository import IBus"],
            check=False,
        )
        if probe.returncode != 0 or not runner.exists("ibus"):
            results.append({
                "kind": "ibus_engine",
                "resource": self.ENGINE_NAME,
                "status": "configured",
                "reason": "session_restart_required",
            })
            return results

        results.append(self._refresh_ibus_session(runner))
        return results
