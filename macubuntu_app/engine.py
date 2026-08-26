from __future__ import annotations

from typing import Any, Callable

from . import __version__
from .modules import ALL_MODULES
from .operations import uninstall_operations
from .state import StateStore, now_iso, privacy_safe_state
from .system import audit_system
from .util import Runner

ProgressCallback = Callable[[dict[str, Any]], None]


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

    def apply(
        self,
        *,
        dry_run: bool = False,
        progress: ProgressCallback | None = None,
        _transaction_operation: str = "apply",
    ) -> dict[str, Any]:
        audit = self.audit()
        if audit["support"]["level"] == "unsupported":
            return {
                "ok": False,
                "reason": "unsupported_system",
                "audit": audit,
                "results": [],
            }

        state = self.store.load()
        if not dry_run:
            self.store.begin_transaction(state, __version__, _transaction_operation)

        results: list[dict[str, Any]] = []
        total = len(ALL_MODULES)
        for index, module in enumerate(ALL_MODULES, start=1):
            event = {
                "event": "start",
                "index": index,
                "total": total,
                "module": module.id,
                "title": module.title,
            }
            if progress:
                progress(event)
            try:
                module_results = module.apply(
                    runner=self.runner,
                    store=self.store,
                    state=state,
                    app_version=__version__,
                    dry_run=dry_run,
                )
            except Exception:
                if progress:
                    progress({**event, "event": "error"})
                raise
            for item in module_results:
                item["module"] = module.id
            results.extend(module_results)
            if progress:
                progress({**event, "event": "finish"})

        if not dry_run:
            profile = state.setdefault("profile", {})
            if not profile.get("applied_at"):
                profile["applied_at"] = now_iso()
            profile["applied"] = True
            profile["last_apply_at"] = now_iso()
            profile["version"] = __version__
            self.store.commit_transaction(state, __version__)

        if progress:
            progress({
                "event": "complete",
                "index": total,
                "total": total,
                "module": "complete",
                "title": "MacUbuntu complete",
            })

        return {
            "ok": True,
            "dry_run": dry_run,
            "support": audit["support"],
            "results": results,
        }

    def status(self) -> dict[str, Any]:
        state = self.store.load()
        plan = self.plan()
        summary = plan["summary"]
        owned_operations = len(state.get("operations", []))
        return {
            "state_file": str(self.store.path),
            "profile_applied": bool(state.get("profile", {}).get("applied")),
            "converged": summary["install"] == 0 and summary["set"] == 0,
            "managed": bool(owned_operations),
            "operation_count": owned_operations,
            "plan_summary": summary,
            "recovery_required": bool(state.get("transaction")),
            "state": privacy_safe_state(state),
        }

    def uninstall(
        self,
        *,
        force: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        state = self.store.load()
        profile_applied = bool(state.get("profile", {}).get("applied"))
        if not state.get("operations") and not profile_applied:
            return {
                "ok": True,
                "dry_run": dry_run,
                "results": [],
                "message": "nothing_managed",
            }

        if not dry_run:
            self.store.begin_transaction(state, __version__, "uninstall")

        results: list[dict[str, Any]] = []
        if state.get("operations"):
            results.extend(
                uninstall_operations(
                    runner=self.runner,
                    store=self.store,
                    state=state,
                    app_version=__version__,
                    force=force,
                    dry_run=dry_run,
                )
            )

        blockers = any(item.get("status") in {"kept", "skipped"} for item in results)
        remaining_operations = bool(state.get("operations"))

        if profile_applied:
            if dry_run:
                results.append({
                    "kind": "profile",
                    "resource": "default",
                    "status": "would_clear" if not blockers and not remaining_operations else "would_keep",
                    "reason": None if not blockers and not remaining_operations else "owned_operations_remain",
                })
            elif not remaining_operations:
                profile = state.setdefault("profile", {})
                profile["applied"] = False
                profile["last_uninstall_at"] = now_iso()
                results.append({
                    "kind": "profile",
                    "resource": "default",
                    "status": "cleared",
                })

        if not dry_run:
            self.store.commit_transaction(state, __version__)
            self.store.remove_if_empty(state)

        return {
            "ok": True,
            "dry_run": dry_run,
            "force": force,
            "results": results,
        }

    def macify(
        self,
        *,
        dry_run: bool = False,
        progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        audit = self.audit()
        plan = self.plan()
        if audit["support"]["level"] == "unsupported":
            return {
                "ok": False,
                "audit": audit,
                "plan": plan,
                "apply": None,
            }
        apply_result = self.apply(
            dry_run=dry_run,
            progress=progress,
            _transaction_operation="macify",
        )
        return {
            "ok": bool(apply_result.get("ok")),
            "audit": audit,
            "plan": plan,
            "apply": apply_result,
        }
