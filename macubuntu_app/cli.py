from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .doctor import run_doctor
from .engine import Engine
from .i18n import Translator, detect_language
from .locking import AppLock, LockBusyError
from .progress import ProgressUI
from .state import StateError
from .updater import update_checkout
from .util import CommandError


def _requested_language(argv: list[str] | None) -> str:
    values = list(sys.argv[1:] if argv is None else argv)
    for index, token in enumerate(values):
        if token.startswith("--lang="):
            return detect_language(token.split("=", 1)[1])
        if token == "--lang" and index + 1 < len(values):
            return detect_language(values[index + 1])
    return detect_language()


def _add_common_options(parser: argparse.ArgumentParser, t: Translator, *, suppress_defaults: bool = False) -> None:
    default_flag: Any = argparse.SUPPRESS if suppress_defaults else False
    default_lang: Any = argparse.SUPPRESS if suppress_defaults else "auto"
    parser.add_argument("--json", action="store_true", default=default_flag, help=t("help_json"))
    parser.add_argument("--verbose", action="store_true", default=default_flag, help=t("help_verbose"))
    parser.add_argument("--lang", choices=["auto", "it", "en"], default=default_lang, help=t("help_lang"))
    parser.add_argument("--dry-run", action="store_true", default=default_flag, help=t("help_dry_run"))


def build_parser(language: str | None = None) -> argparse.ArgumentParser:
    lang = language or detect_language()
    t = Translator(lang)
    parser = argparse.ArgumentParser(prog="macubuntu", description=t("app_description"))
    _add_common_options(parser, t)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    p_audit = sub.add_parser("audit", help=t("help_audit"))
    _add_common_options(p_audit, t, suppress_defaults=True)

    p_doctor = sub.add_parser("doctor", help=t("help_doctor"))
    _add_common_options(p_doctor, t, suppress_defaults=True)

    p_plan = sub.add_parser("plan", help=t("help_plan"))
    _add_common_options(p_plan, t, suppress_defaults=True)

    p_status = sub.add_parser("status", help=t("help_status"))
    _add_common_options(p_status, t, suppress_defaults=True)

    p_apply = sub.add_parser("apply", help=t("help_apply"))
    _add_common_options(p_apply, t, suppress_defaults=True)
    p_apply.add_argument("--yes", action="store_true", help=t("help_yes"))

    p_macify = sub.add_parser("macify", help=t("help_macify"))
    _add_common_options(p_macify, t, suppress_defaults=True)
    p_macify.add_argument("--yes", action="store_true", help=t("help_yes"))

    p_update = sub.add_parser("update", help=t("help_update"))
    _add_common_options(p_update, t, suppress_defaults=True)
    p_update.add_argument("--check", action="store_true", help=t("help_update_check"))

    p_un = sub.add_parser("uninstall", help=t("help_uninstall"))
    _add_common_options(p_un, t, suppress_defaults=True)
    p_un.add_argument("--yes", action="store_true", help=t("help_yes"))
    p_un.add_argument("--force", action="store_true", help=t("help_force"))
    return parser


def _confirm(prompt: str, hint: str) -> bool:
    if not sys.stdin.isatty():
        return False
    answer = input(f"{prompt} {hint} ").strip().lower()
    return answer in {"s", "si", "sì", "y", "yes"}


def _emit_json(command: str, payload: Any, language: str, verbose: bool) -> None:
    print(json.dumps({
        "macubuntu_version": __version__,
        "command": command,
        "interface": {"language": language, "verbose": verbose},
        "data": payload,
    }, indent=2, sort_keys=True))


def _short_gnome_version(value: str | None) -> str:
    if not value:
        return "GNOME ?"
    return value.replace("GNOME Shell ", "GNOME ")


def _print_audit(data: dict[str, Any], t: Translator, verbose: bool) -> None:
    pretty = data["os"].get("pretty_name") or "Ubuntu"
    gnome = _short_gnome_version(data["gnome"].get("shell_version"))
    session = (data["session"].get("type") or "?").upper()
    print(f"✓ {pretty} · {gnome} · {session}")

    level = data["support"]["level"]
    symbol = "✓" if level == "supported" else "!"
    print(f"{symbol} {t(level if level in {'supported', 'experimental', 'unsupported'} else 'experimental')}")

    if verbose:
        print()
        print(f"{t('technical_details')}:")
        print(f"  desktop: {data['session'].get('desktop') or '-'}")
        print(f"  session: {data['session'].get('type') or '-'}")
        print(f"  hardware: {data['hardware'].get('product_name') or '-'}")
        print(f"  support: {level}")
        print(f"  modules: {', '.join(data.get('modules', [])) or '-'}")
        print(f"  state_file: {data['state_file']}")


def _print_doctor(data: dict[str, Any], t: Translator, verbose: bool) -> None:
    status = data.get("status", "blocked")
    symbol = "✓" if status == "healthy" else "!"
    print(f"{symbol} {t(f'doctor_{status}')}")
    summary = data.get("summary", {})
    print(t(
        "doctor_summary",
        passed=summary.get("pass", 0),
        warnings=summary.get("warn", 0),
        failed=summary.get("fail", 0),
    ))

    for item in data.get("checks", []):
        if not verbose and item.get("status") == "pass":
            continue
        item_symbol = "✓" if item.get("status") == "pass" else ("!" if item.get("status") == "warn" else "✗")
        key = f"doctor_{item.get('id')}_{item.get('code')}"
        print(f"  {item_symbol} {t(key)}")
        if item.get("id") == "state" and item.get("data", {}).get("backup_valid"):
            print(f"    {t('doctor_state_backup_available')}")

    if verbose:
        print()
        print(f"{t('technical_details')}:")
        for item in data.get("checks", []):
            print(
                f"  {item.get('status', '?'):4} {item.get('id', '?')}:{item.get('code', '?')} "
                f"{json.dumps(item.get('data', {}), sort_keys=True)}"
            )


def _print_plan(data: dict[str, Any], t: Translator, verbose: bool) -> None:
    s = data["summary"]
    changes = s["install"] + s["set"]
    if changes == 0:
        print(f"✓ {t('plan_nothing')}")
    else:
        print(t("plan_changes", changes=s["set"], packages=s["install"]))
    if s["skip"]:
        print(f"! {t('plan_skip', count=s['skip'])}")

    if verbose:
        print()
        print(f"{t('technical_details')}:")
        print(f"  summary: install={s['install']} set={s['set']} keep={s['keep']} skip={s['skip']}")
        for change in data["changes"]:
            action = change["action"].upper()
            resource = change["resource"]
            line = f"  {action:7} {resource}"
            if action == "SET":
                line += f" | {change.get('current')} -> {change.get('desired')}"
            print(line)


def _mutating_result_count(data: dict[str, Any]) -> int:
    return sum(
        1 for item in data.get("results", [])
        if item.get("status") in {"changed", "installed", "restored", "removed", "cleared"}
    )


def _print_apply(data: dict[str, Any], t: Translator, verbose: bool) -> None:
    if data.get("ok") is False:
        print(f"! {t('unsupported')}")
        return
    count = _mutating_result_count(data)
    if count:
        print(f"✓ {t('apply_done')} {t('apply_changed', count=count)}")
    else:
        print(f"✓ {t('apply_nothing')}")
    if data.get("dry_run"):
        print(t("dry_run"))
    if verbose:
        _print_result_details(data, t)


def _print_uninstall(data: dict[str, Any], t: Translator, verbose: bool) -> None:
    if data.get("message") == "nothing_managed":
        print(f"✓ {t('uninstall_nothing')}")
        return
    kept = any(item.get("status") in {"kept", "skipped"} for item in data.get("results", []))
    print(f"{'!' if kept else '✓'} {t('uninstall_partial') if kept else t('uninstall_done')}")
    if data.get("dry_run"):
        print(t("dry_run"))
    if verbose:
        _print_result_details(data, t)


def _print_result_details(data: dict[str, Any], t: Translator) -> None:
    print()
    print(f"{t('technical_details')}:")
    known = {"changed", "installed", "restored", "removed", "kept", "skipped", "already_converged", "cleared"}
    for item in data.get("results", []):
        resource = item.get("resource", item.get("kind", "operation"))
        status = item.get("status", "unknown")
        localized = t(f"result_{status}") if status in known else status
        print(f"  {localized:20} {resource}")
        if item.get("reason"):
            print(f"    reason: {item['reason']}")
        if "from" in item or "to" in item:
            print(f"    {item.get('from')} -> {item.get('to')}")


def _print_status(data: dict[str, Any], t: Translator, verbose: bool) -> None:
    print(f"{'✓' if data['profile_applied'] else '○'} {t('profile_applied') if data['profile_applied'] else t('profile_not_applied')}")
    print(f"{'✓' if data['converged'] else '!'} {t('converged') if data['converged'] else t('not_converged')}")
    if data["operation_count"]:
        print(t("owns_count", count=data["operation_count"]))
    else:
        print(t("owns_none"))

    if verbose:
        print()
        print(f"{t('technical_details')}:")
        print(f"  state_file: {data['state_file']}")
        print(f"  profile_applied: {str(data['profile_applied']).lower()}")
        print(f"  converged: {str(data['converged']).lower()}")
        print(f"  owned_operations: {data['operation_count']}")
        print(f"  plan_summary: {json.dumps(data.get('plan_summary', {}), sort_keys=True)}")
        for op in data["state"].get("operations", []):
            if op.get("kind") == "gsettings":
                resource = f"{op['schema']}::{op['key']}"
            else:
                resource = ",".join(op.get("requested", []))
            print(f"  receipt: {op.get('kind')} {resource}")


def _print_update(data: dict[str, Any], t: Translator, verbose: bool) -> None:
    status = data.get("status", "unknown")
    message_key = f"update_{status}"
    symbol = "✓" if data.get("ok") else "!"
    print(f"{symbol} {t(message_key)}")
    if status == "updated":
        print(f"  {t('update_next_run')}")

    if verbose:
        print()
        print(f"{t('technical_details')}:")
        for key in (
            "repository", "branch", "expected_branch", "remote_url", "status",
            "check_only", "updated", "previous_commit", "current_commit", "latest_commit",
            "restart_required",
        ):
            if key in data:
                print(f"  {key}: {data[key]}")
        if data.get("changed_files"):
            print("  changed_files:")
            for path in data["changed_files"]:
                print(f"    - {path}")
        if data.get("dirty_paths"):
            print("  dirty_paths:")
            for path in data["dirty_paths"]:
                print(f"    - {path}")
        if data.get("error"):
            print(f"  error: {data['error']}")


def _print_global_error(data: dict[str, Any], t: Translator, verbose: bool) -> None:
    if data.get("status") == "busy":
        print(f"! {t('busy')}")
    elif data.get("status") == "state_error":
        key = f"state_error_{data.get('code', 'state_error')}"
        print(f"! {t(key)}")
    elif data.get("status") == "command_failed":
        print(f"! {t('command_failed')}")
    else:
        print("! MacUbuntu error")
    if verbose:
        print()
        print(f"{t('technical_details')}:")
        for key, value in data.items():
            if key != "ok":
                print(f"  {key}: {value}")


def _run_locked(command: str, operation: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    with AppLock(command=command):
        return operation()


def main(argv: list[str] | None = None) -> int:
    language = _requested_language(argv)
    parser = build_parser(language)
    args = parser.parse_args(argv)
    language = detect_language(args.lang)
    t = Translator(language)
    engine = Engine()
    root = Path(__file__).resolve().parents[1]

    try:
        if args.command == "audit":
            data = engine.audit()
        elif args.command == "doctor":
            data = run_doctor(engine.runner, engine.store, root)
        elif args.command == "plan":
            data = engine.plan()
        elif args.command == "status":
            data = engine.status()
        elif args.command in {"apply", "macify"}:
            preflight = run_doctor(engine.runner, engine.store, root)
            if not preflight["ok"]:
                data = {"ok": False, "status": "preflight_failed", "doctor": preflight}
            else:
                if not args.dry_run and not args.yes:
                    if not _confirm(t("confirm_apply"), t("yes_hint")):
                        print(t("cancelled"), file=sys.stderr)
                        return 2
                progress = None if (args.json or args.dry_run) else ProgressUI(language, verbose=args.verbose)
                operation = (
                    (lambda: engine.macify(dry_run=args.dry_run, progress=progress))
                    if args.command == "macify"
                    else (lambda: engine.apply(dry_run=args.dry_run, progress=progress))
                )
                try:
                    data = operation() if args.dry_run else _run_locked(args.command, operation)
                finally:
                    if progress is not None:
                        progress.close()
                data["doctor"] = preflight
        elif args.command == "update":
            operation = lambda: update_checkout(
                engine.runner,
                root,
                check_only=bool(args.check or args.dry_run),
            )
            data = operation() if (args.check or args.dry_run) else _run_locked("update", operation)
        elif args.command == "uninstall":
            if not args.dry_run and not args.yes:
                if not _confirm(t("confirm_uninstall"), t("yes_hint")):
                    print(t("cancelled"), file=sys.stderr)
                    return 2
            operation = lambda: engine.uninstall(force=args.force, dry_run=args.dry_run)
            data = operation() if args.dry_run else _run_locked("uninstall", operation)
        else:
            raise AssertionError(args.command)
    except LockBusyError as exc:
        data = {
            "ok": False,
            "status": "busy",
            "lock_file": str(exc.path),
            "holder": exc.holder,
        }
    except StateError as exc:
        data = {
            "ok": False,
            "status": "state_error",
            "code": exc.code,
            "path": str(exc.path),
            "error": str(exc),
        }
    except CommandError as exc:
        data = {
            "ok": False,
            "status": "command_failed",
            "command": exc.args_list,
            "returncode": exc.returncode,
            "stdout": exc.stdout[-4000:],
            "stderr": exc.stderr[-4000:],
        }

    if args.json:
        _emit_json(args.command, data, language, args.verbose)
    elif data.get("status") in {"busy", "state_error", "command_failed"}:
        _print_global_error(data, t, args.verbose)
    elif data.get("status") == "preflight_failed":
        _print_doctor(data["doctor"], t, args.verbose)
    else:
        if args.command == "audit":
            _print_audit(data, t, args.verbose)
        elif args.command == "doctor":
            _print_doctor(data, t, args.verbose)
        elif args.command == "plan":
            _print_plan(data, t, args.verbose)
        elif args.command == "status":
            _print_status(data, t, args.verbose)
        elif args.command == "macify":
            if data.get("doctor", {}).get("status") != "healthy":
                _print_doctor(data["doctor"], t, args.verbose)
            _print_audit(data["audit"], t, args.verbose)
            _print_plan(data["plan"], t, args.verbose)
            if data["apply"] is not None:
                _print_apply(data["apply"], t, args.verbose)
        elif args.command == "apply":
            if data.get("doctor", {}).get("status") != "healthy":
                _print_doctor(data["doctor"], t, args.verbose)
            _print_apply(data, t, args.verbose)
        elif args.command == "update":
            _print_update(data, t, args.verbose)
        elif args.command == "uninstall":
            _print_uninstall(data, t, args.verbose)

    if isinstance(data, dict) and data.get("ok") is False:
        return 1
    return 0
