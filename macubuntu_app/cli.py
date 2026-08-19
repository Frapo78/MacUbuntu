from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__
from .engine import Engine
from .i18n import Translator, detect_language


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


def main(argv: list[str] | None = None) -> int:
    language = _requested_language(argv)
    parser = build_parser(language)
    args = parser.parse_args(argv)
    language = detect_language(args.lang)
    t = Translator(language)
    engine = Engine()

    if args.command == "audit":
        data = engine.audit()
    elif args.command == "plan":
        data = engine.plan()
    elif args.command == "status":
        data = engine.status()
    elif args.command in {"apply", "macify"}:
        if not args.dry_run and not args.yes:
            if not _confirm(t("confirm_apply"), t("yes_hint")):
                print(t("cancelled"), file=sys.stderr)
                return 2
        data = engine.macify(dry_run=args.dry_run) if args.command == "macify" else engine.apply(dry_run=args.dry_run)
    elif args.command == "uninstall":
        if not args.dry_run and not args.yes:
            if not _confirm(t("confirm_uninstall"), t("yes_hint")):
                print(t("cancelled"), file=sys.stderr)
                return 2
        data = engine.uninstall(force=args.force, dry_run=args.dry_run)
    else:
        raise AssertionError(args.command)

    if args.json:
        _emit_json(args.command, data, language, args.verbose)
    else:
        if args.command == "audit":
            _print_audit(data, t, args.verbose)
        elif args.command == "plan":
            _print_plan(data, t, args.verbose)
        elif args.command == "status":
            _print_status(data, t, args.verbose)
        elif args.command == "macify":
            _print_audit(data["audit"], t, args.verbose)
            _print_plan(data["plan"], t, args.verbose)
            if data["apply"] is not None:
                _print_apply(data["apply"], t, args.verbose)
        elif args.command == "apply":
            _print_apply(data, t, args.verbose)
        elif args.command == "uninstall":
            _print_uninstall(data, t, args.verbose)

    if isinstance(data, dict) and data.get("ok") is False:
        return 1
    return 0
