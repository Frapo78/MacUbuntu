from __future__ import annotations

import os
from typing import Any

SUPPORTED_LANGUAGES = ("it", "en")

_MESSAGES: dict[str, dict[str, str]] = {
    "it": {
        "supported": "Sistema supportato.",
        "experimental": "Sistema riconosciuto come sperimentale: alcune funzioni potrebbero non essere disponibili.",
        "unsupported": "Sistema non supportato: MacUbuntu non applicherà modifiche.",
        "audit_ok": "Controllo completato.",
        "profile_applied": "Profilo MacUbuntu: applicato",
        "profile_not_applied": "Profilo MacUbuntu: non ancora applicato",
        "converged": "Configurazione: allineata",
        "not_converged": "Configurazione: da completare",
        "owns_none": "Modifiche possedute: nessuna. I componenti già presenti restano dell'utente.",
        "owns_count": "Modifiche possedute da MacUbuntu: {count}",
        "plan_nothing": "Tutto è già configurato correttamente: nessuna modifica necessaria.",
        "plan_changes": "MacUbuntu applicherà {changes} modifica/modifiche e installerà {packages} pacchetto/pacchetti.",
        "plan_keep": "{count} elemento/elementi sono già a posto.",
        "plan_skip": "{count} elemento/elementi non sono disponibili su questo sistema e verranno ignorati.",
        "apply_done": "Configurazione completata.",
        "apply_nothing": "Il sistema era già configurato: nessuna modifica necessaria.",
        "apply_changed": "Modifiche applicate: {count}.",
        "uninstall_nothing": "MacUbuntu non possiede modifiche da rimuovere.",
        "uninstall_done": "Ripristino completato.",
        "uninstall_partial": "Ripristino parziale: alcune modifiche sono state conservate per sicurezza.",
        "cancelled": "Operazione annullata.",
        "confirm_apply": "Applicare la configurazione MacUbuntu?",
        "confirm_uninstall": "Ripristinare lo stato precedente a MacUbuntu?",
        "yes_hint": "[s/N]",
        "state_file": "File di stato",
        "technical_details": "Dettagli tecnici",
        "hardware": "Hardware",
        "support": "Supporto",
        "state": "Stato",
        "dry_run": "Simulazione: nessuna modifica verrà applicata.",
    },
    "en": {
        "supported": "System supported.",
        "experimental": "System recognized as experimental: some features may be unavailable.",
        "unsupported": "Unsupported system: MacUbuntu will not apply changes.",
        "audit_ok": "Check completed.",
        "profile_applied": "MacUbuntu profile: applied",
        "profile_not_applied": "MacUbuntu profile: not applied yet",
        "converged": "Configuration: converged",
        "not_converged": "Configuration: changes needed",
        "owns_none": "Owned changes: none. Pre-existing components remain user-owned.",
        "owns_count": "Changes owned by MacUbuntu: {count}",
        "plan_nothing": "Everything is already configured correctly: no changes are needed.",
        "plan_changes": "MacUbuntu will apply {changes} change(s) and install {packages} package(s).",
        "plan_keep": "{count} item(s) are already configured.",
        "plan_skip": "{count} item(s) are unavailable on this system and will be skipped.",
        "apply_done": "Configuration completed.",
        "apply_nothing": "The system was already configured: no changes were needed.",
        "apply_changed": "Changes applied: {count}.",
        "uninstall_nothing": "MacUbuntu does not own any changes to remove.",
        "uninstall_done": "Restore completed.",
        "uninstall_partial": "Partial restore: some changes were preserved for safety.",
        "cancelled": "Operation cancelled.",
        "confirm_apply": "Apply the MacUbuntu configuration?",
        "confirm_uninstall": "Restore the pre-MacUbuntu state?",
        "yes_hint": "[y/N]",
        "state_file": "State file",
        "technical_details": "Technical details",
        "hardware": "Hardware",
        "support": "Support",
        "state": "State",
        "dry_run": "Simulation: no changes will be applied.",
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
