from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .util import Runner, package_installed, read_os_release


def _cmd_version(runner: Runner, args: list[str]) -> str | None:
    if not runner.exists(args[0]):
        return None
    cp = runner.run(args, check=False)
    text = ((cp.stdout or "") + "\n" + (cp.stderr or "")).strip()
    return text.splitlines()[0] if text else None


def _gsettings_base(schema_dir: str | Path | None = None) -> list[str]:
    command = ["gsettings"]
    if schema_dir is not None:
        command.extend(["--schemadir", str(schema_dir)])
    return command


def gsettings_schema_exists(runner: Runner, schema: str, schema_dir: str | Path | None = None) -> bool:
    if not runner.exists("gsettings"):
        return False
    cp = runner.run(_gsettings_base(schema_dir) + ["list-schemas"], check=False)
    return schema in (cp.stdout or "").splitlines()


def gsettings_key_exists(runner: Runner, schema: str, key: str, schema_dir: str | Path | None = None) -> bool:
    if not gsettings_schema_exists(runner, schema, schema_dir):
        return False
    cp = runner.run(_gsettings_base(schema_dir) + ["list-keys", schema], check=False)
    return key in (cp.stdout or "").splitlines()


def gsettings_get(runner: Runner, schema: str, key: str, schema_dir: str | Path | None = None) -> str | None:
    if not gsettings_key_exists(runner, schema, key, schema_dir):
        return None
    cp = runner.run(_gsettings_base(schema_dir) + ["get", schema, key], check=False)
    if cp.returncode != 0:
        return None
    return (cp.stdout or "").strip()


def gsettings_set(runner: Runner, schema: str, key: str, value: str, schema_dir: str | Path | None = None) -> None:
    runner.run(_gsettings_base(schema_dir) + ["set", schema, key, value])


def audit_system(runner: Runner) -> dict[str, Any]:
    osr = read_os_release()
    product_name = None
    try:
        product_name = Path("/sys/devices/virtual/dmi/id/product_name").read_text(encoding="utf-8").strip()
    except OSError:
        pass

    facts: dict[str, Any] = {
        "os": {"id": osr.get("ID"), "version_id": osr.get("VERSION_ID"), "pretty_name": osr.get("PRETTY_NAME")},
        "session": {"type": os.environ.get("XDG_SESSION_TYPE"), "desktop": os.environ.get("XDG_CURRENT_DESKTOP")},
        "hardware": {"product_name": product_name},
        "gnome": {"shell_version": _cmd_version(runner, ["gnome-shell", "--version"]), "gsettings_available": runner.exists("gsettings")},
        "packages": {"gnome-sushi": package_installed(runner, "gnome-sushi")},
    }

    ubuntu = osr.get("ID") == "ubuntu"
    version = osr.get("VERSION_ID")
    supported_version = version in {"22.04", "24.04"}
    gnomeish = "GNOME" in (os.environ.get("XDG_CURRENT_DESKTOP") or "").upper()
    if ubuntu and supported_version and gnomeish:
        level = "supported"
    elif ubuntu and gnomeish:
        level = "experimental"
    else:
        level = "unsupported"
    facts["support"] = {"level": level, "ubuntu": ubuntu, "target_version": supported_version, "gnome_session": gnomeish}
    return facts
