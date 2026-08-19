# Fullscreen Spaces and press-and-hold accents

MacUbuntu v0.6 adds two interaction behaviors that are central to making GNOME feel less like a themed Linux desktop and more like a coherent Mac-style environment.

## True fullscreen Spaces

macOS gives a fullscreen application a Space of its own. A normal maximize is different: it does not create a new Space.

MacUbuntu follows that distinction:

1. a window enters **real fullscreen**;
2. `MacUbuntu Fullscreen Spaces` records the source workspace and its position;
3. it creates a fresh workspace even when that application was already the only window on the source workspace;
4. the fullscreen window moves to the fresh workspace and that workspace becomes active;
5. when fullscreen ends, the window returns to its source workspace;
6. if GNOME dynamic-workspace cleanup removed the now-empty source workspace while the app was fullscreen, MacUbuntu recreates a workspace at the remembered position first;
7. the disposable fullscreen workspace is then removed/left to GNOME cleanup once empty.

Maximize events are deliberately ignored.

### Why MacUbuntu owns this extension

During design review MacUbuntu evaluated established/fullscreen-workspace projects including:

- `onsah/fullscreen-to-new-workspace` (`Fullscreen to Empty Workspace`), whose GNOME 46 generation explicitly supports fullscreen and workspace movement;
- `eytans/fullscreen-spaces`, a newer implementation centered on returning windows to their original workspace.

Both were useful references, but their current algorithms can deliberately avoid creating a new workspace when the window is already alone. That is a sensible GNOME optimization, but it is not the Mac-style contract MacUbuntu wants.

MacUbuntu therefore ships its own small extension implementation under the MacUbuntu MIT license, with separate source files for GNOME 42 and GNOME 46. It uses the public Mutter/GNOME Shell workspace/window APIs and is enabled through the same reversible extension-state receipt used by the rest of MacUbuntu.

UUID:

```text
macubuntu-fullscreen-spaces@francescopoltero
```

A newly installed Shell extension may require a GNOME Shell/session restart before the running Shell loads it. Its enabled state is persistent, so the next login loads it automatically.

## Press and hold for accents

MacUbuntu's accent behavior is implemented as an **IBus input engine**, not as a global keyboard hook.

This matters for two reasons:

- IBus is the normal Linux desktop input-method layer and can deliver text into applications under both X11 and Wayland;
- MacUbuntu does not need `xdotool`, `/dev/input` keylogging, kernel remapping or application-specific text injection.

### User behavior

For supported letters:

- tap normally → the original letter is committed when the key is released;
- hold for roughly `420 ms` → a horizontal accent candidate list appears;
- press `1`–`9` to choose a candidate;
- Left/Right (or Up/Down) changes the selected candidate and Enter/Space accepts it;
- mouse candidate selection is supported by IBus;
- Escape closes the chooser and keeps the unaccented base letter;
- typing another normal key closes the chooser, keeps the base letter and continues typing.

Examples include:

```text
a → à á â ä ã å ā æ
e → è é ê ë ē ė ę
i → ì í î ï ī į
o → ò ó ô ö õ ø ō œ
u → ù ú û ü ū
n → ñ ń
c → ç ć č
```

Uppercase variants are generated automatically.

### Why the base letter is delayed

A public project named `press2accent` demonstrated that IBus is a viable architecture for this behavior on GNOME/Wayland. Its current engine commits the base character immediately and later calls `delete_surrounding_text()` if the user chooses an accent. Its own documentation notes that surrounding-text behavior can vary between applications.

MacUbuntu uses a more conservative transaction: for accent-capable letters, the base character is held briefly in memory and committed only on key release. If the long-press threshold wins, the chosen accented character is committed directly. MacUbuntu therefore does not need to delete text it already inserted.

MacUbuntu does **not** install or redistribute `press2accent` code.

## Input-source safety

The IBus engine is named:

```text
macubuntu-accents
```

MacUbuntu appends `('ibus', 'macubuntu-accents')` to GNOME's input-source list. It never removes the user's existing XKB/input sources. The MacUbuntu source is placed first in the MRU list so it becomes the preferred source, while the original keyboard remains selectable through GNOME's ordinary input-source switcher.

Both `sources` and `mru-sources` are ordinary MacUbuntu GSettings operations with original/applied values recorded in receipts. Safe uninstall restores the previous lists before removing the MacUbuntu engine files.

## Persistence

MacUbuntu owns and tracks:

- `~/.local/share/macubuntu/input/macubuntu_accent_engine.py`;
- the IBus component XML under the user's IBus component directory;
- `~/.config/environment.d/50-macubuntu-ibus.conf`;
- a small activation helper;
- `~/.config/autostart/macubuntu-accents.desktop`.

At login the helper publishes the user IBus component path, refreshes the IBus cache if necessary and selects `macubuntu-accents`. Failure to refresh IBus is non-destructive: the original GNOME input source remains present and the feature can become active after the next clean session.

## Reversibility

Neither feature requires a daemon running as root.

- Fullscreen Spaces consists of MacUbuntu-owned user extension files plus a reversible enabled-extension receipt.
- MacUbuntu Accents consists of user files, an optional APT delta for IBus bindings if they were missing, and reversible input-source GSettings receipts.
- Safe uninstall preserves drifted user files/settings rather than assuming ownership solely from a recognizable name.
