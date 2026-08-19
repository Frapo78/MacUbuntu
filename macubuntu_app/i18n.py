from __future__ import annotations

import os
from typing import Any

SUPPORTED_LANGUAGES = ("it", "en")

_MESSAGES: dict[str, dict[str, str]] = {
    "it": {
        "app_description": "Trasforma Ubuntu GNOME in un ambiente in stile Mac, in modo reversibile.",
        "help_json": "output JSON stabile per agenti e automazioni",
        "help_verbose": "mostra dettagli tecnici, risorse e valori",
        "help_lang": "lingua dell'interfaccia (auto, it, en)",
        "help_dry_run": "simula le modifiche senza applicarle",
        "help_audit": "controlla sistema, desktop e compatibilità",
        "help_plan": "mostra in sintesi cosa cambierebbe",
        "help_status": "mostra profilo, allineamento e modifiche gestite",
        "help_apply": "applica i moduli supportati",
        "help_macify": "controlla e configura automaticamente in un solo passaggio",
        "help_update": "controlla e installa aggiornamenti dal repository ufficiale",
        "help_update_check": "controlla soltanto se è disponibile un aggiornamento",
        "help_uninstall": "ripristina ciò che MacUbuntu ha modificato",
        "help_yes": "conferma automaticamente l'operazione",
        "help_force": "forza il ripristino anche se alcune impostazioni sono cambiate dopo",
        "supported": "Sistema supportato.",
        "experimental": "Sistema sperimentale: alcune funzioni potrebbero non essere disponibili.",
        "unsupported": "Sistema non supportato: MacUbuntu non applicherà modifiche.",
        "profile_applied": "Profilo MacUbuntu: applicato",
        "profile_not_applied": "Profilo MacUbuntu: non ancora applicato",
        "converged": "Configurazione: allineata",
        "not_converged": "Configurazione: da completare",
        "owns_none": "Modifiche gestite: nessuna. I componenti già presenti restano dell'utente.",
        "owns_count": "Modifiche gestite da MacUbuntu: {count}",
        "plan_nothing": "Tutto è già configurato correttamente: nessuna modifica necessaria.",
        "plan_changes": "Modifiche alle impostazioni: {changes} · Pacchetti da installare: {packages}",
        "plan_skip": "Elementi non disponibili: {count}. Verranno ignorati.",
        "apply_done": "Configurazione completata.",
        "apply_nothing": "Il sistema era già configurato: nessuna modifica necessaria.",
        "apply_changed": "Operazioni eseguite: {count}.",
        "update_up_to_date": "MacUbuntu è già aggiornato.",
        "update_available": "È disponibile un aggiornamento di MacUbuntu.",
        "update_updated": "MacUbuntu è stato aggiornato correttamente.",
        "update_next_run": "Il prossimo comando userà automaticamente la nuova versione.",
        "update_git_missing": "Aggiornamento automatico non disponibile: Git non è installato.",
        "update_not_git_checkout": "Aggiornamento automatico non disponibile: questa copia non è un clone Git.",
        "update_origin_missing": "Aggiornamento automatico non disponibile: manca il remote Git 'origin'.",
        "update_unofficial_remote": "Aggiornamento bloccato: questa copia non punta al repository ufficiale MacUbuntu.",
        "update_detached_head": "Aggiornamento bloccato: il repository è in modalità detached HEAD.",
        "update_wrong_branch": "Aggiornamento bloccato: passa alla branch principale 'main' prima di aggiornare.",
        "update_dirty_worktree": "Aggiornamento bloccato: ci sono modifiche locali non salvate nel repository.",
        "update_status_failed": "Impossibile verificare lo stato locale del repository.",
        "update_head_unreadable": "Impossibile leggere la versione locale del repository.",
        "update_fetch_failed": "Non riesco a scaricare le informazioni di aggiornamento da GitHub.",
        "update_remote_head_unreadable": "Non riesco a leggere l'ultima versione disponibile.",
        "update_local_ahead": "Aggiornamento automatico bloccato: la copia locale contiene commit non presenti sul repository ufficiale.",
        "update_diverged": "Aggiornamento automatico bloccato: la cronologia locale e quella ufficiale sono divergenti.",
        "update_fast_forward_failed": "L'aggiornamento è stato scaricato ma non è stato possibile applicarlo in sicurezza.",
        "uninstall_nothing": "MacUbuntu non gestisce modifiche da rimuovere.",
        "uninstall_done": "Ripristino completato.",
        "uninstall_partial": "Ripristino parziale: alcune modifiche sono state conservate per sicurezza.",
        "cancelled": "Operazione annullata.",
        "confirm_apply": "Applicare la configurazione MacUbuntu?",
        "confirm_uninstall": "Ripristinare lo stato precedente a MacUbuntu?",
        "yes_hint": "[s/N]",
        "technical_details": "Dettagli tecnici",
        "dry_run": "Simulazione: nessuna modifica verrà applicata.",
        "result_changed": "modificato",
        "result_installed": "installato",
        "result_restored": "ripristinato",
        "result_removed": "rimosso",
        "result_kept": "conservato",
        "result_skipped": "ignorato",
        "result_already_converged": "già a posto",
        "result_cleared": "profilo rimosso",
    },
    "en": {
        "app_description": "Turn Ubuntu GNOME into a Mac-style environment, reversibly.",
        "help_json": "stable JSON output for agents and automation",
        "help_verbose": "show technical details, resources and values",
        "help_lang": "interface language (auto, it, en)",
        "help_dry_run": "simulate changes without applying them",
        "help_audit": "check system, desktop and compatibility",
        "help_plan": "summarize what would change",
        "help_status": "show profile, convergence and managed changes",
        "help_apply": "apply supported modules",
        "help_macify": "check and configure automatically in one step",
        "help_update": "check and install updates from the official repository",
        "help_update_check": "only check whether an update is available",
        "help_uninstall": "restore what MacUbuntu changed",
        "help_yes": "confirm the operation automatically",
        "help_force": "force restore even if some settings changed later",
        "supported": "System supported.",
        "experimental": "Experimental system: some features may be unavailable.",
        "unsupported": "Unsupported system: MacUbuntu will not apply changes.",
        "profile_applied": "MacUbuntu profile: applied",
        "profile_not_applied": "MacUbuntu profile: not applied yet",
        "converged": "Configuration: converged",
        "not_converged": "Configuration: changes needed",
        "owns_none": "Managed changes: none. Pre-existing components remain user-owned.",
        "owns_count": "Changes managed by MacUbuntu: {count}",
        "plan_nothing": "Everything is already configured correctly: no changes are needed.",
        "plan_changes": "Setting changes: {changes} · Packages to install: {packages}",
        "plan_skip": "Unavailable items: {count}. They will be skipped.",
        "apply_done": "Configuration completed.",
        "apply_nothing": "The system was already configured: no changes were needed.",
        "apply_changed": "Operations completed: {count}.",
        "update_up_to_date": "MacUbuntu is already up to date.",
        "update_available": "A MacUbuntu update is available.",
        "update_updated": "MacUbuntu was updated successfully.",
        "update_next_run": "The next command will automatically use the new version.",
        "update_git_missing": "Automatic update is unavailable because Git is not installed.",
        "update_not_git_checkout": "Automatic update is unavailable because this copy is not a Git clone.",
        "update_origin_missing": "Automatic update is unavailable because the Git 'origin' remote is missing.",
        "update_unofficial_remote": "Update blocked: this copy does not point to the official MacUbuntu repository.",
        "update_detached_head": "Update blocked: the repository is in detached HEAD mode.",
        "update_wrong_branch": "Update blocked: switch to the main branch before updating.",
        "update_dirty_worktree": "Update blocked: the repository contains uncommitted local changes.",
        "update_status_failed": "Unable to inspect the local repository state.",
        "update_head_unreadable": "Unable to read the local repository version.",
        "update_fetch_failed": "Unable to download update information from GitHub.",
        "update_remote_head_unreadable": "Unable to read the latest available version.",
        "update_local_ahead": "Automatic update blocked: the local copy contains commits that are not in the official repository.",
        "update_diverged": "Automatic update blocked: local and official histories have diverged.",
        "update_fast_forward_failed": "The update was downloaded but could not be applied safely.",
        "uninstall_nothing": "MacUbuntu does not manage any changes to remove.",
        "uninstall_done": "Restore completed.",
        "uninstall_partial": "Partial restore: some changes were preserved for safety.",
        "cancelled": "Operation cancelled.",
        "confirm_apply": "Apply the MacUbuntu configuration?",
        "confirm_uninstall": "Restore the pre-MacUbuntu state?",
        "yes_hint": "[y/N]",
        "technical_details": "Technical details",
        "dry_run": "Simulation: no changes will be applied.",
        "result_changed": "changed",
        "result_installed": "installed",
        "result_restored": "restored",
        "result_removed": "removed",
        "result_kept": "kept",
        "result_skipped": "skipped",
        "result_already_converged": "already configured",
        "result_cleared": "profile removed",
    },
}


def detect_language(explicit: str | None = None) -> str:
    if explicit and explicit != "auto":
        if explicit not in SUPPORTED_LANGUAGES:
            raise ValueError(f"unsupported language: {explicit}")
        return explicit

    env = os.environ.get("MACUBUNTU_LANG")
    if env:
        lang = env.split(".", 1)[0].split("_", 1)[0].lower()
        if lang in SUPPORTED_LANGUAGES:
            return lang

    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name, "")
        lang = value.split(".", 1)[0].split("_", 1)[0].lower()
        if lang in SUPPORTED_LANGUAGES:
            return lang
    return "en"


class Translator:
    def __init__(self, language: str):
        self.language = language

    def __call__(self, key: str, **values: Any) -> str:
        text = _MESSAGES[self.language].get(key, _MESSAGES["en"].get(key, key))
        return text.format(**values)
