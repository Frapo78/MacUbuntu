from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__
from .engine import Engine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="macubuntu",
        description="Reversible mac-style configuration engine for Ubuntu GNOME.",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--dry-run", action="store_true", help="plan mutations without applying them")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("audit", help="inspect OS, GNOME and current support")
    sub.add_parser("plan", help="show exact changes MacUbuntu would make")
    sub.add_parser("status", help="show mutations currently owned by MacUbuntu")

    p_apply = sub.add_parser("apply", help="apply supported modules")
    p_apply.add_argument("--yes", action="store_true", help="confirm mutations non-interactively")

    p_macify = sub.add_parser("macify", help="audit, plan and apply in one autonomous run")
    p_macify.add_argument("--yes", action="store_true", help="confirm mutations non-interactively")

    p_un = sub.add_parser("uninstall", help="restore the recorded pre-MacUbuntu state")
    p_un.add_argument("--yes", action="store_true", help="confirm mutations non-interactively")
    p_un.add_argument(
        "--force",
        action="store_true",
        help="override drift/dependency safety checks where possible",
    )
    return parser


def _confirm(prompt: str) -> bool:
    if not sys.stdin.isatty():
        return False
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def _emit_json(command: str, payload: Any) -> None:
    print(json.dumps({
        "macubuntu_version": __version__,
        "command": command,
        "data": payload,
    }, indent=2, sort_keys=True))


def _print_audit(data: dict[str, Any]) -> None:
    osinfo = data["os"]
    support = data["support"]
    print(f"System: {osinfo.get('pretty_name') or 'unknown'}")
    print(f"Desktop: {data['session'].get('desktop') or 'unknown'} ({data['session'].get('type') or 'unknown'})")
    print(f"GNOME: {data['gnome'].get('shell_version') or 'not detected'}")
    print(f"Hardware: {data['hardware'].get('product_name') or 'unknown'}")
    print(f"Support: {support['level']}")
    print(f"State: {data['state_file']}")


def _print_plan(data: dict[str, Any]) -> None:
    s = data["summary"]
    print(
        "Plan: "
        f"{s['install']} package install(s), "
        f"{s['set']} setting change(s), "
        f"{s['keep']} already converged, "
        f"{s['skip']} unsupported/skipped."
    )
    for change in data["changes"]:
        action = change["action"].upper()
        resource = change["resource"]
        print(f"  {action:7} {resource}")
        if action == "SET":
            print(f"          {change.get('current')} -> {change.get('desired')}")


def _print_results(title: str, data: dict[str, Any]) -> None:
    print(title)
    if data.get("message") == "nothing_managed":
        print("  Nothing is currently managed by MacUbuntu.")
        return
    for item in data.get("results", []):
        resource = item.get("resource", item.get("kind", "operation"))
        print(f"  {item.get('status', 'unknown'):18} {resource}")
        if item.get("reason"):
            print(f"    reason: {item['reason']}")


def _print_status(data: dict[str, Any]) -> None:
    print(f"State file: {data['state_file']}")
    print(f"Managed: {'yes' if data['managed'] else 'no'}")
    print(f"Operations: {data['operation_count']}")
    for op in data["state"].get("operations", []):
        if op.get("kind") == "gsettings":
            resource = f"{op['schema']}::{op['key']}"
        else:
            resource = ",".join(op.get("requested", []))
        print(f"  {op.get('kind')}: {resource}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    engine = Engine()

    if args.command == "audit":
        data = engine.audit()
    elif args.command == "plan":
        data = engine.plan()
    elif args.command == "status":
        data = engine.status()
    elif args.command in {"apply", "macify"}:
        if not args.dry_run and not args.yes:
            if not _confirm("Apply MacUbuntu changes?"):
                print("Cancelled.", file=sys.stderr)
                return 2
        data = (
            engine.macify(dry_run=args.dry_run)
            if args.command == "macify"
            else engine.apply(dry_run=args.dry_run)
        )
    elif args.command == "uninstall":
        if not args.dry_run and not args.yes:
            if not _confirm("Restore the recorded pre-MacUbuntu state?"):
                print("Cancelled.", file=sys.stderr)
                return 2
        data = engine.uninstall(force=args.force, dry_run=args.dry_run)
    else:
        raise AssertionError(args.command)

    if args.json:
        _emit_json(args.command, data)
    else:
        if args.command == "audit":
            _print_audit(data)
        elif args.command == "plan":
            _print_plan(data)
        elif args.command == "status":
            _print_status(data)
        elif args.command == "macify":
            _print_audit(data["audit"])
            _print_plan(data["plan"])
            if data["apply"] is not None:
                _print_results("Apply:", data["apply"])
        elif args.command == "apply":
            _print_results("Apply:", data)
        elif args.command == "uninstall":
            _print_results("Uninstall:", data)

    if isinstance(data, dict) and data.get("ok") is False:
        return 1
    return 0
