# Managed component catalog

This file is the reviewed component allowlist for the **v0.6 interaction profile**. External sources are intentionally explicit so a MacUbuntu release can be reproduced and audited.

## Selection rules

A component belongs in the default one-shot only when it has a clearly identifiable upstream, compatibility with the supported Ubuntu/GNOME targets, a non-destructive install path and a reversible ownership model MacUbuntu can enforce.

MacUbuntu does not automatically install abandoned global-menu hacks, boot themes, GDM replacements, proprietary Apple fonts/wallpapers, GRUB themes, GPU tweaks, kernel modules or random theme packs from aggregators.

## MacUbuntu-owned interaction components

### MacUbuntu Fullscreen Spaces

- Code owner: MacUbuntu project.
- Idea and implementation context: Francesco Poltero / MacUbuntu contributors.
- License: MacUbuntu MIT license.
- UUID: `macubuntu-fullscreen-spaces@francescopoltero`.
- GNOME targets: separate bundled implementation for GNOME 42 and GNOME 46.
- Install scope: user GNOME extension directory only.
- Behavior: **every real fullscreen transition creates a new dedicated workspace**, even if the application was already alone; normal maximize is ignored; unfullscreen returns the window to the source Space.
- Dynamic-workspace protection: if GNOME removes an empty source workspace while the app is fullscreen, the extension recreates a workspace at the remembered position before returning the window.
- Persistence: enabled through MacUbuntu's normal GNOME-extension receipt; a Shell/session restart may be required immediately after first install.

During research MacUbuntu reviewed `onsah/fullscreen-to-new-workspace` and `eytans/fullscreen-spaces`. They are not installed by v0.6 because both current algorithms can avoid a new Space when the app is already alone, which does not satisfy MacUbuntu's stricter fullscreen contract.

### MacUbuntu Accents

- Code owner: MacUbuntu project.
- Idea and implementation: Francesco Poltero / MacUbuntu contributors.
- License: MacUbuntu MIT license.
- Engine name: `macubuntu-accents`.
- Framework: IBus through Ubuntu packages `ibus`, `python3-gi` and `gir1.2-ibus-1.0` when available.
- Hold threshold: default approximately `420 ms`.
- Supported base letters: `a c e i n o s u y z` plus uppercase variants.
- Safety: no `/dev/input` capture, no `xdotool`, no global key injection and no deletion of previously committed text for accent replacement.
- Source safety: existing GNOME input sources are preserved. MacUbuntu appends its IBus source and records `sources` / `mru-sources` through reversible GSettings receipts.
- Persistence: MacUbuntu-owned environment + activation helper + GNOME autostart entry re-publish the component path and reactivate the engine at login.

The public project `dresnite/press2accent` was reviewed as design research because it demonstrated the IBus approach on modern GNOME. MacUbuntu v0.6 does **not** install or redistribute its code; MacUbuntu's engine uses a different delayed-commit design that avoids `delete_surrounding_text()` replacement.

## Pinned appearance components

### MacTahoe GTK / GNOME Shell

- Upstream: `vinceliuice/MacTahoe-gtk-theme`
- Pin: `ae82d8ea6a7eba42b9bf375ec602538c34fdabab` (2026-05-24 reviewed upstream commit)
- Install scope: user theme directory only
- MacUbuntu name prefix: `MacUbuntu-MacTahoe`
- Selected variants: light + dark, solid
- Selected title-bar option: upstream `--round` support for rounded maximized-window styling
- Dependency packages: `sassc`, `libglib2.0-dev-bin`, `libxml2-utils`, `gnome-shell-extensions`
- Safety: custom destination/name; expected outputs checked; no GDM tweak, Firefox rewrite or libadwaita `~/.config/gtk-4.0` overwrite path.

MacUbuntu also sets reversible GNOME window-manager preferences for left-side controls, Inter Semi-Bold title text and predictable double/middle/right-click title-bar actions.

### WhiteSur GTK — legacy managed asset / compatibility path

WhiteSur GTK was the v0.4 default. Existing MacUbuntu-owned WhiteSur GTK assets and receipts remain understood so upgrades and uninstall do not orphan them.

- Upstream: `vinceliuice/WhiteSur-gtk-theme`
- Previous v0.4 pin: `3bd1b21f7a097c2a4cd88d58ed94385463455692`
- Previous MacUbuntu name prefix: `MacUbuntu-WhiteSur`

### WhiteSur icons

- Upstream: `vinceliuice/WhiteSur-icon-theme`
- Pin: `bab5833b5cae200bccb786a2d3d6afa2201e7806`
- Install scope: user icon directory
- MacUbuntu name prefix: `MacUbuntu-WhiteSur`
- Archive note: the reviewed source contains 27,864 ZIP entries, so this component has an explicit 30,000-member extraction ceiling while the normal ceiling remains 20,000. All other archive checks remain active.

### WhiteSur cursors

- Upstream: `vinceliuice/WhiteSur-cursors`
- Pin: `e190baf618ed95ee217d2fd45589bd309b37672b`
- Install scope: `~/.local/share/icons/MacUbuntu-WhiteSur-cursors` (or XDG equivalent)
- MacUbuntu copies only the pinned upstream `dist` tree.

## Wallpaper collection

MacUbuntu does **not** redistribute Apple-owned macOS wallpaper files. It installs six pinned open-source mac-inspired assets under `~/.local/share/backgrounds/MacUbuntu/` and verifies every file against its upstream Git blob SHA.

### WhiteSur / Big Sur-inspired

Upstream: `vinceliuice/WhiteSur-wallpapers` @ `5c1d7ca20b8de0a7efe443792c19e49277262e02`

- `2k/WhiteSur-light.jpg` — blob `43c035745ebaf1622317b2ea7537b127447454fc`
- `2k/WhiteSur-dark.jpg` — blob `5d43c022c58b853e873ea43a4c7fc86cc25c5b85`

### Monterey-inspired

- `2k/Monterey-light.jpg` — blob `4b1aed36dfe3d10fab72caf573a9ec4a1fe2d3c2`
- `2k/Monterey-dark.jpg` — blob `bdfc4cbdca810ae1c8d9dd9cf40b961d30bbf60c`

### Tahoe-inspired — default pair

Upstream: `vinceliuice/MacTahoe-gtk-theme` @ `ae82d8ea6a7eba42b9bf375ec602538c34fdabab`

- `wallpaper/MacTahoe-day.jpeg` — blob `fb4a50aa1eddb93d2e3d901e6bf001e89fec84bd`
- `wallpaper/MacTahoe-night.jpeg` — blob `c516afb27d3d7c2713a0ab4468941631d75e0415`

## GNOME extension compatibility pins

Third-party extension ZIPs are downloaded from `extensions.gnome.org`. MacUbuntu pins both EGO version and exact official review artifact ID, then validates metadata, UUID, version and declared GNOME major.

| Extension | UUID | GNOME 42 | GNOME 46 |
|---|---|---:|---:|
| Blur my Shell | `blur-my-shell@aunetx` | EGO v47 / review 42627 | EGO v72 / review 69740 |
| Just Perfection | `just-perfection-desktop@just-perfection` | EGO v26 / review 43626 | EGO v36 / review 68110 |
| Clipboard Indicator | `clipboard-indicator@tudmotu.com` | EGO v47 / review 43380 | EGO v71 / review 70694 |
| X11 Gestures | `x11gestures@joseexposito.github.io` | EGO v17 / review 41094 | EGO v25 / review 63139 |
| GSConnect | `gsconnect@andyholmes.github.io` | EGO v68 / review 66552 | EGO v72 / review 70399 |

MacUbuntu Fullscreen Spaces is not downloaded from EGO: it is MacUbuntu-owned source bundled with the application and selected explicitly for GNOME 42 or 46.

## Ubuntu and upstream package sources

### Ubuntu repositories

MacUbuntu can use these distro packages when available:

- `gnome-sushi`
- `gnome-tweaks`
- `gnome-shell-extension-manager`
- `gnome-shell-extensions`
- `gnome-shell-extension-ubuntu-dock`
- `fonts-inter`
- `ibus`, `python3-gi`, `gir1.2-ibus-1.0`
- `flatpak`
- `software-properties-common`
- `libimobiledevice-utils`
- `ifuse`
- `usbmuxd`
- `gvfs-backends`
- MacTahoe build dependencies listed above

APT ownership is based on the actual dpkg delta around each MacUbuntu transaction, not just requested package names.

### Touchégg stable PPA

- Source: `ppa:touchegg/stable`
- Reviewed stable version for Ubuntu 22.04/24.04: Touchégg `2.0.18`
- Persistence: MacUbuntu manages `touchegg.service` as enabled+active, recording its previous service state for uninstall.

### Ulauncher stable PPA

- Source: `ppa:agornostal/ulauncher`
- Reviewed stable version: Ulauncher `5.15.15`
- Persistence: MacUbuntu enables the user service when available; otherwise it creates a reversible GNOME autostart file.

## Flatpak

### Warpinator

- Project: Linux Mint `warpinator`
- Reviewed Flathub version: `2.0.3`
- App ID: `org.x.Warpinator`
- Remote: Flathub (`https://flathub.org/repo/flathub.flatpakrepo`)
- Scope: user Flatpak installation
- Security posture: upstream supports encrypted LAN connections and a private group code; MacUbuntu does not invent or store that secret.
- Startup policy: installed for on-demand use, not auto-opened at login.

### LocalSend — reviewed but not enabled

LocalSend was evaluated but remains excluded until its stable security posture meets the default-profile bar.

## Persistence contract

MacUbuntu persists what must persist, not every GUI process:

- GNOME GSettings selections persist normally and remain receipt-managed;
- GNOME user extensions stay enabled through the persistent enabled list and master enable switch;
- MacUbuntu Fullscreen Spaces is a persistent user Shell extension;
- MacUbuntu Accents uses user-session autostart plus reversible input-source settings;
- Touchégg is enabled as a system service;
- Ulauncher uses a user service or GNOME autostart;
- interactive apps remain installed without opening on every login.

## Runtime download security

Third-party runtime downloads are HTTPS-only and limited to reviewed hosts (`github.com`, `codeload.github.com`, `raw.githubusercontent.com`, `extensions.gnome.org`). ZIP extraction rejects traversal paths, escaping/absolute symlinks and special files. Relative symlinks are preserved only when their target remains inside the extraction root. Archive limits remain enforced.

## Deliberately deferred

The default profile still avoids operations whose merge/uninstall semantics or cost are not strong enough:

- MacTahoe/WhiteSur Firefox profile rewrites;
- libadwaita `~/.config/gtk-4.0` overwrite mode;
- GDM/login-screen replacement;
- GRUB themes;
- global-menu hacks;
- shader-only rounded-window extensions as a default dependency;
- forced Super+Space reassignment when it conflicts with GNOME input-source switching;
- proprietary SF Pro/SF Mono redistribution;
- proprietary Apple wallpaper redistribution;
- hardware-driver, GPU, kernel, firmware or bootloader changes.

“Deeper” is useful only while MacUbuntu remains stable, understandable and reversible.
