# Screenshots and screencasts

MacUbuntu uses **GNOME Shell's native screenshot and screencast interface** instead of installing a second screenshot daemon.

This keeps capture integrated with the desktop, works across X11 and Wayland, and remains reversible through ordinary GSettings receipts.

## Mac-style shortcuts

MacUbuntu treats `Super` as the Command-like modifier for the desktop workflow:

| Mac-style action | MacUbuntu shortcut | GNOME action |
|---|---|---|
| Capture the whole screen | `Super` + `Shift` + `3` | immediate full-screen screenshot |
| Select an area/window | `Super` + `Shift` + `4` | open GNOME's screenshot palette |
| Screenshot / recording palette | `Super` + `Shift` + `5` | open GNOME's screenshot palette |

Inside GNOME's palette, `S` selects an area, `C` the screen, `W` a window and `V` toggles screenshot/screencast mode.

MacUbuntu also keeps GNOME's familiar fallback bindings where available:

- `Print` — screenshot palette;
- `Shift` + `Print` — full screen;
- `Alt` + `Print` — focused window;
- `Ctrl` + `Shift` + `Alt` + `R` — direct screencast UI.

GNOME automatically saves screenshots under the user's Pictures/Screenshots directory and also places the captured image in the clipboard. Screencasts are saved under Videos/Screencasts.

## Why not install another screenshot application by default?

GNOME 42 and later integrate screenshots and screencasts directly into GNOME Shell. MacUbuntu therefore prefers the native implementation because it is already part of the supported desktop and behaves consistently on both X11 and Wayland.

Third-party screenshot applications may still be installed by the user, but MacUbuntu does not replace the native capture path or launch a persistent tray process just to imitate macOS shortcuts.

## Reversibility

Every shortcut change is made through MacUbuntu's normal GSettings operation receipts. Safe uninstall restores the user's previous bindings unless they were changed manually after MacUbuntu applied them, in which case drift protection preserves the newer user choice.

## Upstream references

- GNOME Help — Screenshots and screencasts: https://help.gnome.org/gnome-help/screen-shot-record.html
- GNOME Help — Keyboard shortcuts: https://help.gnome.org/gnome-help/keyboard-shortcuts-set.html
- GNOME Shell screenshot API documentation: https://gnome.pages.gitlab.gnome.org/gnome-shell/shell/class.Screenshot.html
