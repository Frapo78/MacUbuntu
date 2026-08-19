from __future__ import annotations

from typing import Any

from . import __version__
from .modules import ALL_MODULES
from .operations import uninstall_operations
from .state import StateStore
from .system import audit_system
from .util import Runner


class Engine:
    def __init__(
        self,
        runner: Runner | None = None,
        store: StateStore | None = None,
    ):
        self.runner = runner or Runner()
        self.store = store or StateStore()

    def audit(self) -> dict[str, Any]:
        facts = audit_system(self.runner)
        facts["modules"] = [m.id for m in ALL_MODULES]
        facts["state_file"] = str(self.store.path)
        return facts

    def plan(self) -> dict[str, Any]:
        audit = self.audit()
        changes: list[dict[str, Any]] = []
        for module in ALL_MODULES:
            changes.extend(module.plan(self.runner))
        return {
            "audit": audit,
            "changes": changes,
            "summary": {
                "install": sum(1 for c in changes if c["action"] == "install"),
                "set": sum(1 for c in changes if c["action"] == "set"),
                "keep": sum(1 for c in changes if c["action"] == "keep"),
                "skip": sum(1 for c in changes if c["action"] == "skip"),
            },
        }

    def apply(self, *, dry_run: bool = False) -> dict[str, Any]:
        audit = self.audit()
        if audit["support"]["level"] == "unsupported":
            return {
                "ok": False,
                "reason": "unsupported_system",
                "audit": audit,
                "results": [],
            }

        state = self.store.load()
        results: list[dict[str, Any]] = []
        for module in ALL_MODULES:
            module_results = module.apply(
                runner=self.runner,
                store=self.store,
                state=state,
                app_version=__version__,
                dry_run=dry_run,
            )
            for item in module_results:
                item["module"] = module.id
            results.extend(module_results)

        return {
            "ok": True,
            "dry_run": dry_run,
            "support": audit["support"],
            "results": results,
        }

    def status(self) -> dict[str, Any]:
        state = self.store.load()
        return {
            "state_file": str(self.store.path),
            "managed": bool(state.get("operations")),
            "operation_count": len(state.get("operations", [])),
            "state": state,
        }

    def uninstall(
        self,
        *,
        force: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        state = self.store.load()
        if not state.get("operations"):
            return {
                "ok": True,
                "dry_run": dry_run,
                "results": [],
                "message": "nothing_managed",
            }

        results = uninstall_operations(
            runner=self.runner,
            store=self.store,
            state=state,
            app_version=__version__,
            force=force,
            dry_run=dry_run,
        )
        return {
            "ok": True,
            "dry_run": dry_run,
            "force": force,
            "results": results,
        }

    def macify(self, *, dry_run: bool = False) -> dict[str, Any]:
        audit = self.audit()
        plan = self.plan()
        if audit["support"]["level"] == "unsupported":
            return {
                "ok": False,
                "audit": audit,
                "plan": plan,
                "apply": None,
            }
        apply_result = self.apply(dry_run=dry_run)
        return {
            "ok": bool(apply_result.get("ok")),
            "audit": audit,
            "plan": plan,
            "apply": apply_result,
        }
