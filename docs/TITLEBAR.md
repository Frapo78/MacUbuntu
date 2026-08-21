# macOS-style title bars

MacUbuntu aims to make window chrome feel coherent rather than merely moving GNOME buttons to the left.

## What MacUbuntu configures

The default appearance module uses the pinned **MacTahoe GTK/Shell theme** and explicitly selects its normal macOS-style window-control variant. MacTahoe supplies the familiar red, yellow and green traffic-light artwork, backdrop states, hover/active states and restore artwork for maximized windows.

MacUbuntu also configures GNOME/Mutter with:

- window controls on the left in `close,minimize,maximize` order;
- the MacTahoe rounded-window option;
- `titlebar-uses-system-font=false` so the configured title-bar font is actually honored;
- `Inter Semi-Bold 11` as the free/open mac-inspired title font;
- double-click to toggle maximize;
- no middle-click title-bar action.

MacUbuntu does not redistribute Apple fonts or other proprietary Apple UI assets.

## GTK 3

GTK 3 and classic client-side decorations use the installed `MacUbuntu-MacTahoe-*` theme directly. The traffic lights, spacing, headerbar dimensions, rounded corners and active/backdrop states come from the pinned MacTahoe source.

## GTK 4 and libadwaita

Many current GNOME applications use GTK 4/libadwaita and can otherwise keep Adwaita-looking headerbars even when the GTK 3 theme is mac-styled.

MacTahoe upstream offers a `--libadwaita` installation mode, but that mode replaces files and directories directly under `~/.config/gtk-4.0`. MacUbuntu deliberately does **not** call that destructive path.

Instead, on a clean profile MacUbuntu creates only two receipt-owned bridge files:

- `~/.config/gtk-4.0/gtk.css`
- `~/.config/gtk-4.0/gtk-dark.css`

Each file contains only an absolute `@import` pointing at the already installed, pinned MacTahoe GTK 4 stylesheet. Assets referenced by that stylesheet continue to resolve inside the managed theme directory; MacUbuntu does not copy or delete unrelated user assets.

If either GTK 4 CSS file already exists and is not owned by a MacUbuntu receipt, the complete GTK 4/libadwaita bridge is skipped with `preexisting_unmanaged_gtk4_css`. Existing user CSS is never overwritten merely to make the desktop more mac-like.

The two bridge files are tracked as ordinary `owned_paths`, so a safe uninstall removes only MacUbuntu-owned files and keeps drifted or user-owned files.

## Limits

Toolkits and applications ultimately control their own client-side decorations. GTK 3, GTK 4 and libadwaita receive the deepest default integration. Applications with completely custom chrome, some Electron/Qt applications, browsers using their own titlebar mode, and server-side decorated legacy windows can still differ from macOS.

MacUbuntu treats those as app-specific integration work rather than globally patching application binaries or overwriting arbitrary configuration.
