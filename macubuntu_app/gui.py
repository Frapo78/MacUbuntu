from __future__ import annotations

import locale
import threading
from typing import Any

from .gui_model import CliGateway, summarize_payload


def _lang() -> str:
    value = (locale.getlocale()[0] or "").lower()
    return "it" if value.startswith("it") else "en"


COPY = {
    "it": {
        "title": "MacUbuntu",
        "subtitle": "Trasforma Ubuntu in modo profondo, controllabile e reversibile.",
        "audit": "Controlla il sistema",
        "doctor": "Diagnostica",
        "plan": "Anteprima modifiche",
        "apply": "Applica MacUbuntu",
        "status": "Stato",
        "update": "Aggiorna",
        "uninstall": "Disinstalla",
        "confirm_apply": "Applicare le modifiche pianificate?",
        "confirm_uninstall": "Disinstallare solo ciò che MacUbuntu possiede?",
        "working": "Operazione in corso…",
        "ready": "Pronto.",
        "about": "Idea e realizzazione: Francesco Poltero",
    },
    "en": {
        "title": "MacUbuntu",
        "subtitle": "Transform Ubuntu deeply while keeping it controlled and reversible.",
        "audit": "Check system",
        "doctor": "Doctor",
        "plan": "Preview changes",
        "apply": "Apply MacUbuntu",
        "status": "Status",
        "update": "Update",
        "uninstall": "Uninstall",
        "confirm_apply": "Apply the planned changes?",
        "confirm_uninstall": "Uninstall only resources owned by MacUbuntu?",
        "working": "Working…",
        "ready": "Ready.",
        "about": "Idea and implementation: Francesco Poltero",
    },
}


def main() -> int:
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw, GLib, Gtk
    except (ImportError, ValueError) as exc:
        raise SystemExit(
            "MacUbuntu GUI requires GTK 4, libadwaita and PyGObject "
            "(Ubuntu packages: python3-gi gir1.2-gtk-4.0 gir1.2-adw-1)."
        ) from exc

    language = _lang()
    text = COPY[language]
    gateway = CliGateway()

    class MacUbuntuWindow(Adw.ApplicationWindow):
        def __init__(self, app: Adw.Application) -> None:
            super().__init__(application=app, title=text["title"])
            self.set_default_size(760, 560)

            toolbar = Adw.ToolbarView()
            header = Adw.HeaderBar()
            toolbar.add_top_bar(header)

            page = Adw.PreferencesPage()
            hero = Adw.PreferencesGroup(title=text["title"], description=text["subtitle"])
            page.add(hero)

            actions = Adw.PreferencesGroup(title=text["ready"])
            page.add(actions)
            self.status_row = Adw.ActionRow(title=text["ready"])
            actions.add(self.status_row)

            for command, label in (
                ("audit", text["audit"]),
                ("doctor", text["doctor"]),
                ("plan", text["plan"]),
                ("status", text["status"]),
                ("apply", text["apply"]),
                ("update", text["update"]),
                ("uninstall", text["uninstall"]),
            ):
                row = Adw.ActionRow(title=label)
                button = Gtk.Button(label=label, valign=Gtk.Align.CENTER)
                button.connect("clicked", self._clicked, command)
                row.add_suffix(button)
                row.set_activatable_widget(button)
                actions.add(row)

            credits = Adw.PreferencesGroup()
            credits.add(Adw.ActionRow(title=text["about"]))
            page.add(credits)
            toolbar.set_content(page)
            self.set_content(toolbar)

        def _clicked(self, _button: Gtk.Button, command: str) -> None:
            if command in {"apply", "uninstall"}:
                self._confirm(command)
            else:
                self._run(command, confirmed=(command == "update"))

        def _confirm(self, command: str) -> None:
            body = text["confirm_apply"] if command == "apply" else text["confirm_uninstall"]
            dialog = Adw.MessageDialog.new(self, text[command], body)
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("confirm", text[command])
            dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE if command == "uninstall" else Adw.ResponseAppearance.SUGGESTED)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")
            dialog.connect("response", lambda _d, response: self._run(command, confirmed=True) if response == "confirm" else None)
            dialog.present()

        def _run(self, command: str, *, confirmed: bool = False) -> None:
            self.status_row.set_title(text["working"])

            def worker() -> None:
                try:
                    result = gateway.run(command, language=language, confirmed=confirmed)
                    summary = summarize_payload(command, result.payload)
                    rendered = f"{command}: {summary['status']}"
                    if result.stderr and not result.ok:
                        rendered += f" — {result.stderr.splitlines()[-1]}"
                except Exception as exc:  # UI boundary: show failure, do not mutate around it.
                    rendered = f"{command}: error — {exc}"
                GLib.idle_add(self.status_row.set_title, rendered)

            threading.Thread(target=worker, daemon=True).start()

    class MacUbuntuApplication(Adw.Application):
        def __init__(self) -> None:
            super().__init__(application_id="io.github.Frapo78.MacUbuntu")

        def do_activate(self) -> None:
            window = self.props.active_window
            if window is None:
                window = MacUbuntuWindow(self)
            window.present()

    app = MacUbuntuApplication()
    return int(app.run(None))


if __name__ == "__main__":
    raise SystemExit(main())
