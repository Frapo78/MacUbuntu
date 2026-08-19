from __future__ import annotations

import sys
from typing import Any, TextIO


_PHRASES: dict[str, dict[str, str]] = {
    "it": {
        "core.gnome": "Mettiamo ordine: anche il Finder approverebbe.",
        "desktop.tools": "Prepariamo gli attrezzi del mestiere.",
        "typography": "Mettiamo in riga anche le lettere.",
        "appearance.whitesur": "Vestiamo GNOME da Mac, senza mele morsicate vere.",
        "wallpaper.whitesur": "Un po' di panorama da Cupertino... quasi.",
        "shell.enhancements": "Lucidiamo la Shell senza farla scivolare.",
        "gestures.x11": "Tre dita, grandi ambizioni.",
        "spotlight.ulauncher": "Accendiamo il nostro piccolo Spotlight.",
        "sharing.warpinator": "Prepariamo il teletrasporto sulla rete locale.",
        "phone.integration": "Facciamo presentazioni ufficiali con il telefono.",
        "fallback": "MacUbuntu sta sistemando i dettagli.",
        "complete": "Fatto: Ubuntu ora parla molto più fluentemente Mac.",
    },
    "en": {
        "core.gnome": "Tidying things up. Finder would probably approve.",
        "desktop.tools": "Getting the desktop toolbox ready.",
        "typography": "Even the letters are getting in line.",
        "appearance.whitesur": "Dressing GNOME like a Mac, minus the actual Apple.",
        "wallpaper.whitesur": "Adding a little Cupertino scenery... almost.",
        "shell.enhancements": "Polishing the Shell without making it slippery.",
        "gestures.x11": "Three fingers, big ambitions.",
        "spotlight.ulauncher": "Switching on our tiny Spotlight.",
        "sharing.warpinator": "Preparing local-network teleportation.",
        "phone.integration": "Making proper introductions with your phone.",
        "fallback": "MacUbuntu is tuning the little details.",
        "complete": "Done: Ubuntu now speaks much more fluent Mac.",
    },
}


class ProgressUI:
    """Small dependency-free progress renderer for human one-shot runs.

    JSON output never instantiates this class. In a normal interactive terminal
    the same line is refreshed between modules. Verbose and non-TTY runs print
    one stable line per module so subprocess output and logs remain readable.
    """

    def __init__(
        self,
        language: str,
        *,
        verbose: bool = False,
        stream: TextIO | None = None,
        force_tty: bool | None = None,
        width: int = 26,
    ):
        self.language = language if language in _PHRASES else "en"
        self.verbose = verbose
        self.stream = stream or sys.stdout
        self.width = max(10, int(width))
        detected_tty = bool(getattr(self.stream, "isatty", lambda: False)())
        self.tty = detected_tty if force_tty is None else bool(force_tty)
        self._line_open = False

    def _phrase(self, module: str) -> str:
        messages = _PHRASES[self.language]
        return messages.get(module, messages["fallback"])

    def _bar(self, completed: int, total: int) -> str:
        total = max(1, total)
        completed = max(0, min(completed, total))
        filled = round(self.width * completed / total)
        return "█" * filled + "░" * (self.width - filled)

    def _line(self, completed: int, total: int, phrase: str) -> str:
        percent = round(100 * max(0, min(completed, total)) / max(1, total))
        return f"[{self._bar(completed, total)}] {percent:3d}%  {phrase}"

    def __call__(self, event: dict[str, Any]) -> None:
        phase = event.get("event")
        index = int(event.get("index", 0))
        total = int(event.get("total", 1))
        module = str(event.get("module", "fallback"))

        if phase == "start":
            # index is 1-based: before the module runs, show the amount already done.
            line = self._line(max(0, index - 1), total, self._phrase(module))
            if self.tty and not self.verbose:
                print("\r" + line, end="", file=self.stream, flush=True)
                self._line_open = True
            else:
                print(line, file=self.stream, flush=True)
            return

        if phase == "finish":
            if index >= total:
                line = self._line(total, total, _PHRASES[self.language]["complete"])
                if self.tty and not self.verbose:
                    print("\r" + line, file=self.stream, flush=True)
                    self._line_open = False
                else:
                    print(line, file=self.stream, flush=True)

    def close(self) -> None:
        if self._line_open:
            print(file=self.stream, flush=True)
            self._line_open = False
