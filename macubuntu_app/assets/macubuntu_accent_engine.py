#!/usr/bin/env python3
"""MacUbuntu press-and-hold accent input engine.

This file is part of MacUbuntu and is released under MacUbuntu's MIT license.
It intentionally uses IBus rather than global key injection so text insertion
works through the desktop input-method stack on both X11 and Wayland.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys

ENGINE_NAME = "macubuntu-accents"
ENGINE_PATH = "/org/freedesktop/IBus/MacUbuntuAccents/Engine"
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


def variants_for(character: str) -> tuple[str, ...]:
    if len(character) != 1:
        return ()
    variants = ACCENTS.get(character.lower(), ())
    if character.isupper():
        return tuple(value.upper() for value in variants)
    return variants


def _load_ibus():
    import gi

    gi.require_version("IBus", "1.0")
    from gi.repository import GLib, IBus

    return GLib, IBus


def run_engine() -> int:
    GLib, IBus = _load_ibus()

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
                    # Hardware auto-repeat must never create repeated base letters.
                    return True
                self._commit_base_and_clear()

            if has_blocking_modifier(state):
                return False

            character = key_character(keyval)
            variants = variants_for(character)
            if not variants:
                return False

            # Delay only accent-capable letters until key release. Typical taps
            # therefore feel immediate, while a hold can open candidates without
            # inserting then deleting a base character.
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
            self._commit_base_and_clear()

        def do_reset(self):
            self._commit_base_and_clear()

        def _on_release(self, keyval, keycode):
            if self._pending is None or not self._same_key(keyval, keycode):
                return False
            if self._lookup_visible:
                # Keep the chooser visible after the user releases the held key.
                return True
            self._commit_base_and_clear()
            return True

        def _same_key(self, keyval, keycode):
            return (
                self._pending is not None
                and self._pending["keyval"] == keyval
                and self._pending["keycode"] == keycode
            )

        def _show_lookup(self):
            self._timer = 0
            if self._pending is None:
                return GLib.SOURCE_REMOVE
            variants = self._pending["variants"]
            table = IBus.LookupTable.new(
                page_size=min(9, len(variants)),
                cursor_pos=0,
                cursor_visible=True,
                round=True,
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

            # Normal typing closes the chooser and keeps the unaccented base.
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
        def __init__(self, bus):
            self._connection = bus.get_connection()
            self._counter = 0
            super().__init__(connection=self._connection, object_path=IBus.PATH_FACTORY)

        def do_create_engine(self, engine_name):
            if engine_name != ENGINE_NAME:
                return None
            self._counter += 1
            return AccentEngine(
                self._connection,
                f"{ENGINE_PATH}/{self._counter}",
            )

    IBus.init()
    loop = GLib.MainLoop()
    bus = IBus.Bus()
    factory = AccentFactory(bus)
    bus.request_name("org.freedesktop.IBus.MacUbuntuAccents", 0)

    def stop(*_args):
        loop.quit()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    loop.run()
    factory.destroy()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="MacUbuntu press-and-hold accent engine")
    parser.add_argument("--ibus", action="store_true", help="run as an IBus engine")
    parser.add_argument("--self-test", action="store_true", help="test accent tables without IBus")
    args = parser.parse_args()

    if args.self_test:
        assert variants_for("e")[0] == "è"
        assert "É" in variants_for("E")
        assert variants_for("q") == ()
        print("macubuntu-accent-engine: ok")
        return 0
    if args.ibus:
        return run_engine()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
