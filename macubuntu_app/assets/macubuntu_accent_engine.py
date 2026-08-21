#!/usr/bin/env python3
"""MacUbuntu transparent press-and-hold accent input engine.

The engine is an IBus filter: GNOME keeps the user's real XKB input source
(e.g. Italian) while this engine replaces IBus's xkb passthrough underneath.
It can be launched by IBus (``--ibus``) or as a user-session component
(``--standalone``), where it registers itself with the live IBus bus.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import signal
from pathlib import Path

ENGINE_NAME = "macubuntu-accents"
ENGINE_PATH = "/org/freedesktop/IBus/MacUbuntuAccents/Engine"
SERVICE_NAME = "org.freedesktop.IBus.MacUbuntuAccents"
HOLD_DELAY_MS = max(180, int(os.environ.get("MACUBUNTU_ACCENT_HOLD_MS", "420")))

ACCENTS = {
    "a": ("à", "á", "â", "ä", "ã", "å", "ā", "æ"),
    "c": ("ç", "ć", "č"),
    "e": ("è", "é", "ê", "ë", "ē", "ė", "ę"),
    "i": ("ì", "í", "î", "ï", "ī", "į"),
    "n": ("ñ", "ń"),
    "o": ("ò", "ó", "ô", "ö", "õ", "ø", "ō", "œ"),
    "s": ("ß", "ś", "š"),
    "u": ("ù", "ú", "û", "ü", "ū"),
    "y": ("ý", "ÿ"),
    "z": ("ž", "ź", "ż"),
}

_INSTANCE_LOCK = None


def variants_for(character: str) -> tuple[str, ...]:
    if len(character) != 1:
        return ()
    variants = ACCENTS.get(character.lower(), ())
    return tuple(value.upper() for value in variants) if character.isupper() else variants


def _load_ibus():
    import gi

    gi.require_version("IBus", "1.0")
    from gi.repository import GLib, IBus

    return GLib, IBus


def _acquire_standalone_lock() -> bool:
    """Allow one persistent standalone engine per user session."""
    global _INSTANCE_LOCK
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
    lock_path = runtime / f"macubuntu-accents-{os.getuid()}.lock"
    try:
        handle = lock_path.open("a+", encoding="utf-8")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError):
        return False
    _INSTANCE_LOCK = handle
    return True


def run_engine(*, standalone: bool, component_path: str | None) -> int:
    GLib, IBus = _load_ibus()
    IBus.init()
    bus = IBus.Bus()
    if not bus.is_connected():
        return 2

    release_mask = IBus.ModifierType.RELEASE_MASK
    blocking_mask = (
        IBus.ModifierType.CONTROL_MASK
        | IBus.ModifierType.MOD1_MASK
        | IBus.ModifierType.SUPER_MASK
        | IBus.ModifierType.HYPER_MASK
        | IBus.ModifierType.META_MASK
    )

    def is_release(state: int) -> bool:
        return bool(state & release_mask)

    def has_blocking_modifier(state: int) -> bool:
        return bool(state & blocking_mask)

    def key_character(keyval: int) -> str:
        value = IBus.keyval_to_unicode(keyval)
        if isinstance(value, str):
            return value if len(value) == 1 and value.isprintable() else ""
        return chr(value) if value else ""

    def numeric_index(keyval: int) -> int:
        if IBus.KEY_1 <= keyval <= IBus.KEY_9:
            return keyval - IBus.KEY_1
        if IBus.KEY_KP_1 <= keyval <= IBus.KEY_KP_9:
            return keyval - IBus.KEY_KP_1
        return -1

    class AccentEngine(IBus.Engine):
        def __init__(self, connection, object_path):
            super().__init__(connection=connection, object_path=object_path)
            self._pending = None
            self._timer = 0
            self._lookup = None
            self._lookup_visible = False

        def do_process_key_event(self, keyval, keycode, state):
            if is_release(state):
                return self._on_release(keyval, keycode)

            if self._lookup_visible:
                handled = self._handle_lookup_key(keyval, keycode)
                if handled is not None:
                    return handled

            if self._pending is not None:
                if self._same_key(keyval, keycode):
                    # Swallow auto-repeat for the held accent-capable letter.
                    return True
                self._commit_base_and_clear()

            if has_blocking_modifier(state):
                return False

            character = key_character(keyval)
            variants = variants_for(character)
            if not variants:
                return False

            # Delay only letters that actually have accent candidates. A tap is
            # committed on key release; a hold opens the candidate strip.
            self._pending = {
                "character": character,
                "variants": variants,
                "keyval": keyval,
                "keycode": keycode,
            }
            self._timer = GLib.timeout_add(HOLD_DELAY_MS, self._show_lookup)
            return True

        def do_candidate_clicked(self, index, _button, _state):
            if self._lookup_visible:
                self._select(index)

        def do_focus_out(self):
            # A delayed key must never leak into a newly focused application.
            self._clear_pending()

        def do_reset(self):
            self._clear_pending()

        def _on_release(self, keyval, keycode):
            if self._pending is None or not self._same_key(keyval, keycode):
                return False
            if self._lookup_visible:
                # macOS keeps the chooser open after releasing the held letter.
                return True
            self._commit_base_and_clear()
            return True

        def _same_key(self, keyval, keycode):
            if self._pending is None:
                return False
            pending_code = self._pending["keycode"]
            if pending_code and keycode:
                return pending_code == keycode
            return self._pending["keyval"] == keyval

        def _show_lookup(self):
            self._timer = 0
            if self._pending is None:
                return GLib.SOURCE_REMOVE
            variants = self._pending["variants"]
            table = IBus.LookupTable.new(
                page_size=min(9, len(variants)), cursor_pos=0, cursor_visible=True, round=True
            )
            table.set_orientation(IBus.Orientation.HORIZONTAL)
            for index, variant in enumerate(variants[:9]):
                table.append_candidate(IBus.Text.new_from_string(variant))
                table.append_label(IBus.Text.new_from_string(str(index + 1)))
            self._lookup = table
            self.update_lookup_table(table, True)
            self.show_lookup_table()
            self._lookup_visible = True
            return GLib.SOURCE_REMOVE

        def _handle_lookup_key(self, keyval, keycode):
            if self._same_key(keyval, keycode):
                return True
            index = numeric_index(keyval)
            if index >= 0:
                self._select(index)
                return True
            if keyval == IBus.KEY_Escape:
                self._commit_base_and_clear()
                return True
            if keyval in (IBus.KEY_Left, IBus.KEY_Up):
                if self._lookup is not None:
                    self._lookup.cursor_up()
                    self.update_lookup_table(self._lookup, True)
                return True
            if keyval in (IBus.KEY_Right, IBus.KEY_Down):
                if self._lookup is not None:
                    self._lookup.cursor_down()
                    self.update_lookup_table(self._lookup, True)
                return True
            if keyval in (IBus.KEY_Return, IBus.KEY_KP_Enter, IBus.KEY_space):
                if self._lookup is not None:
                    self._select(self._lookup.get_cursor_pos())
                return True
            self._commit_base_and_clear()
            return None

        def _select(self, index: int):
            if self._pending is None:
                return
            variants = self._pending["variants"]
            if 0 <= index < len(variants):
                selected = variants[index]
                self._clear_pending()
                self.commit_text(IBus.Text.new_from_string(selected))

        def _commit_base_and_clear(self):
            if self._pending is None:
                self._clear_lookup()
                return
            character = self._pending["character"]
            self._clear_pending()
            self.commit_text(IBus.Text.new_from_string(character))

        def _clear_lookup(self):
            if self._lookup_visible:
                self.hide_lookup_table()
            self._lookup_visible = False
            self._lookup = None

        def _clear_pending(self):
            if self._timer:
                GLib.source_remove(self._timer)
            self._timer = 0
            self._clear_lookup()
            self._pending = None

    class AccentFactory(IBus.Factory):
        def __init__(self, ibus_bus):
            self._connection = ibus_bus.get_connection()
            self._counter = 0
            super().__init__(connection=self._connection, object_path=IBus.PATH_FACTORY)

        def do_create_engine(self, engine_name):
            if engine_name != ENGINE_NAME:
                return None
            self._counter += 1
            return AccentEngine(self._connection, f"{ENGINE_PATH}/{self._counter}")

    if standalone and not _acquire_standalone_lock():
        return 0

    factory = AccentFactory(bus)
    component = None
    if standalone:
        if not component_path:
            return 3
        component_file = Path(component_path).expanduser()
        if not component_file.is_file():
            return 4
        component = IBus.Component.new_from_file(str(component_file))
        if component is None or not bus.register_component(component):
            return 5
    else:
        # IBus itself launched us from a component descriptor.
        bus.request_name(SERVICE_NAME, 0)

    loop = GLib.MainLoop()
    bus.connect("disconnected", lambda *_args: loop.quit())

    def stop(*_args):
        loop.quit()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        loop.run()
    finally:
        factory.destroy()
        # Keep a reference until shutdown: the live registration belongs to
        # this component process/connection.
        component = None
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="MacUbuntu press-and-hold accent engine")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--ibus", action="store_true", help="run when launched by IBus")
    modes.add_argument("--standalone", action="store_true", help="register with the live IBus bus and stay resident")
    parser.add_argument("--component", help="component XML path for --standalone")
    parser.add_argument("--self-test", action="store_true", help="test accent tables without loading IBus")
    args = parser.parse_args()

    if args.self_test:
        assert variants_for("e")[0] == "è"
        assert "É" in variants_for("E")
        assert variants_for("q") == ()
        print("macubuntu-accent-engine: ok")
        return 0
    if args.standalone:
        if not args.component:
            parser.error("--standalone requires --component")
        return run_engine(standalone=True, component_path=args.component)
    if args.ibus:
        return run_engine(standalone=False, component_path=None)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
