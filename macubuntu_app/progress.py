from __future__ import annotations

import sys
import threading
from typing import Any, TextIO


_PHRASES: dict[str, dict[str, str]] = {
    "it": {
        "core.gnome": "Mettiamo ordine: anche il Finder approverebbe.",
        "desktop.tools": "Prepariamo gli attrezzi del mestiere.",
        "screenshots.macos": "Prepariamo le scorciatoie da paparazzo digitale.",
        "typography": "Mettiamo in riga anche le lettere.",
        "appearance.mactahoe": "Vestiamo GNOME in stile Tahoe: sartoria digitale.",
        "appearance.whitesur": "Vestiamo GNOME da Mac, senza mele morsicate vere.",
        "appearance.wallpapers": "Appendiamo qualche panorama da Mac alla parete.",
        "wallpaper.whitesur": "Un po' di panorama da Cupertino... quasi.",
        "shell.enhancements": "Lucidiamo la Shell senza farla scivolare.",
        "spaces.fullscreen": "Prepariamo uno Space tutto suo per il vero fullscreen.",
        "gestures.x11": "Tre dita, grandi ambizioni.",
        "spotlight.ulauncher": "Accendiamo il nostro piccolo Spotlight.",
        "keyboard.press-hold-accents": "Teniamo premute le vocali: stanno arrivando gli accenti.",
        "sharing.warpinator": "Prepariamo il teletrasporto sulla rete locale.",
        "phone.integration": "Facciamo presentazioni ufficiali con il telefono.",
        "fallback": "MacUbuntu sta sistemando i dettagli.",
        "complete": "Fatto: Ubuntu ora parla molto più fluentemente Mac.",
        "enjoy": "🍏 Goditi il tuo nuovo MacUbuntu!",
    },
    "en": {
        "core.gnome": "Tidying things up. Finder would probably approve.",
        "desktop.tools": "Getting the desktop toolbox ready.",
        "screenshots.macos": "Getting the digital paparazzi shortcuts ready.",
        "typography": "Even the letters are getting in line.",
        "appearance.mactahoe": "Dressing GNOME Tahoe-style. Digital tailoring time.",
        "appearance.whitesur": "Dressing GNOME like a Mac, minus the actual Apple.",
        "appearance.wallpapers": "Hanging some Mac-like scenery on the wall.",
        "wallpaper.whitesur": "Adding a little Cupertino scenery... almost.",
        "shell.enhancements": "Polishing the Shell without making it slippery.",
        "spaces.fullscreen": "Giving real fullscreen apps a Space of their own.",
        "gestures.x11": "Three fingers, big ambitions.",
        "spotlight.ulauncher": "Switching on our tiny Spotlight.",
        "keyboard.press-hold-accents": "Hold that vowel. The accents are on their way.",
        "sharing.warpinator": "Preparing local-network teleportation.",
        "phone.integration": "Making proper introductions with your phone.",
        "fallback": "MacUbuntu is tuning the little details.",
        "complete": "Done: Ubuntu now speaks much more fluent Mac.",
        "enjoy": "🍏 Enjoy your new MacUbuntu!",
    },
}

_SPINNER = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


class ProgressUI:
    """Dependency-free progress renderer for human one-shot runs.

    Percentages are based only on completed MacUbuntu modules.  While a long
    module is running, normal interactive mode animates a spinner and a pulse
    in the unfinished portion of the bar.  This communicates liveness without
    fabricating percentage progress.  Verbose/non-TTY modes remain stable and
    log-friendly, and JSON never instantiates this renderer.
    """

    def __init__(
        self,
        language: str,
        *,
        verbose: bool = False,
        stream: TextIO | None = None,
        force_tty: bool | None = None,
        width: int = 26,
        interval: float = 0.12,
    ):
        self.language = language if language in _PHRASES else "en"
        self.verbose = verbose
        self.stream = stream or sys.stdout
        self.width = max(10, int(width))
        self.interval = max(0.05, float(interval))
        detected_tty = bool(getattr(self.stream, "isatty", lambda: False)())
        self.tty = detected_tty if force_tty is None else bool(force_tty)
        self._line_open = False
        self._worker: threading.Thread | None = None
        self._worker_stop: threading.Event | None = None
        self._write_lock = threading.Lock()

    def _phrase(self, module: str) -> str:
        messages = _PHRASES[self.language]
        return messages.get(module, messages["fallback"])

    def _bar(self, completed: int, total: int, *, pulse_frame: int | None = None) -> str:
        total = max(1, total)
        completed = max(0, min(completed, total))
        filled = round(self.width * completed / total)
        cells = ["█"] * filled + ["░"] * (self.width - filled)
        if pulse_frame is not None and filled < self.width:
            remaining = self.width - filled
            pulse = filled + (pulse_frame % remaining)
            cells[pulse] = "▓"
        return "".join(cells)

    def _line(
        self,
        completed: int,
        total: int,
        phrase: str,
        *,
        frame: int | None = None,
    ) -> str:
        percent = round(100 * max(0, min(completed, total)) / max(1, total))
        spinner = f" {_SPINNER[frame % len(_SPINNER)]}" if frame is not None else ""
        return f"[{self._bar(completed, total, pulse_frame=frame)}] {percent:3d}%{spinner}  {phrase}"

    def _write_tty(self, text: str, *, end: str = "") -> None:
        with self._write_lock:
            print("\r" + text, end=end, file=self.stream, flush=True)

    def _stop_animation(self) -> None:
        stop = self._worker_stop
        worker = self._worker
        self._worker_stop = None
        self._worker = None
        if stop is not None:
            stop.set()
        if worker is not None and worker.is_alive() and worker is not threading.current_thread():
            worker.join(timeout=max(0.5, self.interval * 4))

    def _start_animation(self, completed: int, total: int, phrase: str) -> None:
        self._stop_animation()
        stop = threading.Event()
        self._worker_stop = stop

        def animate() -> None:
            frame = 0
            while not stop.is_set():
                self._write_tty(self._line(completed, total, phrase, frame=frame))
                self._line_open = True
                frame += 1
                stop.wait(self.interval)

        worker = threading.Thread(
            target=animate,
            name="macubuntu-progress",
            daemon=True,
        )
        self._worker = worker
        worker.start()

    def __call__(self, event: dict[str, Any]) -> None:
        phase = event.get("event")
        index = int(event.get("index", 0))
        total = int(event.get("total", 1))
        module = str(event.get("module", "fallback"))

        if phase == "start":
            completed = max(0, index - 1)
            phrase = self._phrase(module)
            if self.tty and not self.verbose:
                self._start_animation(completed, total, phrase)
            else:
                print(self._line(completed, total, phrase), file=self.stream, flush=True)
            return

        if phase == "finish":
            if self.tty and not self.verbose:
                self._stop_animation()
                self._write_tty(self._line(index, total, self._phrase(module)))
                self._line_open = True
            return

        if phase == "error":
            self._stop_animation()
            if self._line_open:
                with self._write_lock:
                    print(file=self.stream, flush=True)
                self._line_open = False
            return

        if phase == "complete":
            self._stop_animation()
            complete = _PHRASES[self.language]["complete"]
            enjoy = _PHRASES[self.language]["enjoy"]
            if self.tty and not self.verbose:
                self._write_tty(self._line(total, total, complete), end="\n")
            else:
                print(self._line(total, total, complete), file=self.stream, flush=True)
            print(enjoy, file=self.stream, flush=True)
            self._line_open = False

    def close(self) -> None:
        self._stop_animation()
        if self._line_open:
            with self._write_lock:
                print(file=self.stream, flush=True)
            self._line_open = False
