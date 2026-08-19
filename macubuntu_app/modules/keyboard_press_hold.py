from __future__ import annotations

import ast
import os
import time
from pathlib import Path
from typing import Any

from ..external import apply_managed_text_file
from ..operations import apply_apt_bundle, apply_gsetting
from ..state import StateStore
from ..system import gsettings_get
from ..util import Runner
from .common import package_available, package_change, path_change


class PressHoldAccentsModule:
    """Add a macOS-like press-and-hold accent picker through IBus.

    MacUbuntu owns the small IBus engine installed by this module. IBus is the
    desktop input-method layer, so the feature works without X11-only key
    injection and has a viable path on both X11 and Wayland. Existing GNOME
    input sources are preserved as immediate fallbacks and are restored by the
    normal GSettings receipts on uninstall.
    """

    id = "keyboard.press-hold-accents"
    title = "press-and-hold accent picker"

    ENGINE_NAME = "macubuntu-accents"
    INPUT_SOURCE = ("ibus", ENGINE_NAME)

    @property
    def data_home(self) -> Path:
        return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    @property
    def config_home(self) -> Path:
        return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    @property
    def source_engine_file(self) -> Path:
        return Path(__file__).resolve().parents[1] / "assets" / "macubuntu_accent_engine.py"

    @property
    def engine_file(self) -> Path:
        return self.data_home / "macubuntu" / "input" / "macubuntu_accent_engine.py"

    @property
    def component_dir(self) -> Path:
        return self.data_home / "ibus" / "component"

    @property
    def component_file(self) -> Path:
        return self.component_dir / "macubuntu-accents.xml"

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

    @classmethod
    def _merge_source_lists(
        cls,
        sources: list[tuple[str, str]],
        mru: list[tuple[str, str]] | None,
    ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        merged_sources = list(sources)
        if cls.INPUT_SOURCE not in merged_sources:
            merged_sources.append(cls.INPUT_SOURCE)
        merged_mru = list(mru) if mru is not None else list(merged_sources)
        merged_mru = [cls.INPUT_SOURCE] + [source for source in merged_mru if source != cls.INPUT_SOURCE]
        # Keep every configured source reachable even if GNOME's MRU list was
        # incomplete before MacUbuntu touched it.
        for source in merged_sources:
            if source not in merged_mru:
                merged_mru.append(source)
        return merged_sources, merged_mru

    def _desired_sources(self, runner: Runner) -> tuple[str | None, str | None]:
        raw_sources = gsettings_get(runner, "org.gnome.desktop.input-sources", "sources")
        sources = self._parse_sources(raw_sources)
        if sources is None:
            return None, None
        raw_mru = gsettings_get(runner, "org.gnome.desktop.input-sources", "mru-sources")
        mru = self._parse_sources(raw_mru)
        sources, mru = self._merge_source_lists(sources, mru)
        return repr(sources), repr(mru)

    def _component_xml(self) -> str:
        engine = self.engine_file
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<component>
  <name>org.freedesktop.IBus.MacUbuntuAccents</name>
  <description>MacUbuntu press-and-hold accent input method</description>
  <exec>python3 {engine} --ibus</exec>
  <version>0.6.0</version>
  <author>Francesco Poltero and MacUbuntu contributors</author>
  <license>MIT</license>
  <homepage>https://github.com/Frapo78/MacUbuntu</homepage>
  <textdomain>macubuntu</textdomain>
  <engines>
    <engine>
      <name>{self.ENGINE_NAME}</name>
      <language>en</language>
      <license>MIT</license>
      <author>Francesco Poltero and MacUbuntu contributors</author>
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
            path_change(self.id, "MacUbuntu accent engine", self.engine_file),
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
        required = {"ibus", "python3-gi", "gir1.2-ibus-1.0"}
        if not required.issubset(set(packages)):
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

        try:
            engine_content = self.source_engine_file.read_text(encoding="utf-8")
        except OSError as exc:
            results.append({
                "kind": "ibus_engine",
                "resource": self.ENGINE_NAME,
                "status": "skipped",
                "reason": "bundled_engine_missing",
                "error": str(exc),
            })
            return results

        asset_results = [
            apply_managed_text_file(
                store=store,
                state=state,
                app_version=app_version,
                resource="macubuntu-accent-engine",
                path=self.engine_file,
                content=engine_content,
                mode=0o755,
                dry_run=dry_run,
            ),
            apply_managed_text_file(
                store=store,
                state=state,
                app_version=app_version,
                resource="macubuntu-accent-component",
                path=self.component_file,
                content=self._component_xml(),
                dry_run=dry_run,
            ),
            apply_managed_text_file(
                store=store,
                state=state,
                app_version=app_version,
                resource="macubuntu-ibus-environment",
                path=self.environment_file,
                content=f"IBUS_COMPONENT_PATH={self._component_path_value()}\n",
                dry_run=dry_run,
            ),
        ]
        results.extend(asset_results)
        if any(result.get("status") in {"skipped", "kept"} for result in asset_results):
            results.append({
                "kind": "ibus_engine",
                "resource": self.ENGINE_NAME,
                "status": "skipped",
                "reason": "unmanaged_or_drifted_engine_files",
            })
            return results

        if not dry_run:
            self_test = runner.run(["python3", str(self.engine_file), "--self-test"], check=False)
            if self_test.returncode != 0:
                results.append({
                    "kind": "ibus_engine",
                    "resource": self.ENGINE_NAME,
                    "status": "skipped",
                    "reason": "engine_self_test_failed",
                    "stderr": self_test.stderr or "",
                })
                return results

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
