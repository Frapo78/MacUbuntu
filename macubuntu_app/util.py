from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Sequence


class CommandError(RuntimeError):
    def __init__(self, args: Sequence[str], returncode: int, stdout: str, stderr: str):
        self.args_list = list(args)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(f"command failed ({returncode}): {shlex.join(self.args_list)}")


class Runner:
    """Thin subprocess wrapper, replaceable in tests.

    Missing executables are normalized into return code 127 so `check=False`
    detection code does not crash with FileNotFoundError.
    """

    def run(self, args: Sequence[str], *, check: bool = True, capture: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        command = list(args)
        try:
            cp = subprocess.run(
                command,
                text=True,
                stdout=subprocess.PIPE if capture else None,
                stderr=subprocess.PIPE if capture else None,
                env=env,
            )
        except OSError as exc:
            cp = subprocess.CompletedProcess(
                command,
                127,
                stdout="" if capture else None,
                stderr=str(exc) if capture else None,
            )
        if check and cp.returncode != 0:
            raise CommandError(args, cp.returncode, cp.stdout or "", cp.stderr or "")
        return cp

    def exists(self, command: str) -> bool:
        from shutil import which
        return which(command) is not None


def xdg_state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))


def read_os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
    result: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" not in line or line.startswith("#"):
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
            result[key] = value
    except OSError:
        pass
    return result


def atomic_json_write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def installed_deb_packages(runner: Runner) -> set[str]:
    if not runner.exists("dpkg-query"):
        return set()
    cp = runner.run(["dpkg-query", "-W", "-f=${binary:Package}\\t${db:Status-Abbrev}\\n"], check=False)
    packages: set[str] = set()
    for line in (cp.stdout or "").splitlines():
        try:
            name, status = line.split("\t", 1)
        except ValueError:
            continue
        if status.startswith("ii"):
            packages.add(name)
    return packages


def package_installed(runner: Runner, package: str) -> bool:
    if not runner.exists("dpkg-query"):
        return False
    cp = runner.run(["dpkg-query", "-W", "-f=${db:Status-Abbrev}", package], check=False)
    return cp.returncode == 0 and (cp.stdout or "").startswith("ii")


def apt_base_command() -> list[str]:
    if os.geteuid() == 0:
        return ["apt-get"]
    return ["sudo", "apt-get"]
