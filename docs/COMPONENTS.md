# Managed component catalog

This file is the reviewed component allowlist for the v0.4 deep-macify profile. External sources are intentionally explicit so a MacUbuntu release can be reproduced and audited.

## Selection rules

A component belongs in the default one-shot only when it has a clearly identifiable upstream, an established user base or distro integration, compatibility with the supported Ubuntu/GNOME targets, a non-destructive install path and a reversible ownership model MacUbuntu can enforce.

MacUbuntu does not automatically install abandoned global-menu hacks, boot themes, GDM replacements, proprietary Apple fonts, GRUB themes, GPU tweaks, kernel modules or random theme packs from aggregators.

## Pinned source components

### WhiteSur GTK

- Upstream: `vinceliuice/WhiteSur-gtk-theme`
- Pin: `3bd1b21f7a097c2a4cd88d58ed94385463455692` (reviewed 2026-07-07 upstream release commit)
- Install scope: user data directory only
- MacUbuntu name prefix: `MacUbuntu-WhiteSur`
- Dependency packages: `sassc`, `libglib2.0-dev-bin`, `libxml2-utils`, `gnome-shell-extensions`
- Safety: custom destination/name; exact expected output checked; unexpected destination writes abort and are cleaned; no GDM tweak; no Firefox rewrite; no libadwaita overwrite path.

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

### WhiteSur wallpapers

- Upstream: `vinceliuice/WhiteSur-wallpapers`
- Pin: `5c1d7ca20b8de0a7efe443792c19e49277262e02`
- Files: `2k/WhiteSur-light.jpg`, `2k/WhiteSur-dark.jpg`
- Integrity: the downloaded bytes are verified against the pinned Git blob SHA before installation.

## GNOME extension compatibility pins

Extension ZIPs are downloaded from `extensions.gnome.org`. For the core Shell-enhancement set MacUbuntu pins both the EGO version and the exact official review artifact ID, then validates `metadata.json`, UUID, EGO version and declared GNOME major before copying anything to the user extension directory.

| Extension | UUID | GNOME 42 | GNOME 46 |
|---|---|---:|---:|
| Blur my Shell | `blur-my-shell@aunetx` | EGO v47 / review 42627 | EGO v72 / review 69740 |
| Just Perfection | `just-perfection-desktop@just-perfection` | EGO v26 / review 43626 | EGO v36 / review 68110 |
| Clipboard Indicator | `clipboard-indicator@tudmotu.com` | EGO v47 / review 43380 | EGO v71 / review 70694 |
| X11 Gestures | `x11gestures@joseexposito.github.io` | EGO v17 | EGO v25 |
| GSConnect | `gsconnect@andyholmes.github.io` | EGO v68 | EGO v72 |

Unsupported GNOME majors are skipped; MacUbuntu does not guess a compatible extension build.

## Ubuntu and upstream package sources

### Ubuntu repositories

MacUbuntu can use these distro packages when available:

- `gnome-sushi`
- `gnome-tweaks`
- `gnome-shell-extension-manager`
- `gnome-shell-extensions`
- `gnome-shell-extension-ubuntu-dock`
- `fonts-inter`
- `flatpak`
- `software-properties-common` (only when MacUbuntu must add a reviewed PPA)
- `libimobiledevice-utils`
- `ifuse`
- `usbmuxd`
- `gvfs-backends`
- WhiteSur build dependencies listed above

APT ownership is based on the actual dpkg delta around each MacUbuntu transaction, not just the requested package name.

### Touchégg stable PPA

- Source: `ppa:touchegg/stable`
- Reviewed stable version for Ubuntu 22.04/24.04: Touchégg `2.0.18`
- Purpose: Touchégg 2.x for X11 Gestures
- MacUbuntu behavior: use a pre-existing compatible 2.x installation; if a legacy pre-existing Touchégg package is detected, skip rather than silently replace it; add the stable PPA only when MacUbuntu needs to install the modern daemon.

### Ulauncher stable PPA

- Source: `ppa:agornostal/ulauncher`
- Reviewed stable version for Ubuntu 22.04/24.04: Ulauncher `5.15.15`
- Purpose: stable Ulauncher v5 series; v6 development/pre-release is not selected by v0.4
- MacUbuntu behavior: if Ulauncher already exists, leave its package source alone; otherwise add the official PPA and install the stable package.

## Flatpak

### Warpinator

- Project: Linux Mint `warpinator`
- Reviewed Flathub version: `2.0.3`
- App ID: `org.x.Warpinator`
- Remote: Flathub (`https://flathub.org/repo/flathub.flatpakrepo`)
- Scope: user Flatpak installation
- Security posture: the upstream project supports encrypted LAN connections and a secure mode based on a private group code; MacUbuntu installs the app but does not invent or store that secret for the user.
- Ownership: MacUbuntu removes the app only when it installed it. A Flathub remote added by MacUbuntu is removed only while unused; if the user later installs other Flathub apps, MacUbuntu relinquishes ownership and leaves the remote intact.

### LocalSend — reviewed but not enabled

LocalSend was evaluated because it is popular and cross-platform, but MacUbuntu v0.4 deliberately does **not** install it. As of the v0.4 review, the current stable 1.17.0 line is listed by the upstream security advisory as affected by an unpatched critical unauthenticated local-network MitM vulnerability (GHSA-424h-5f6m-x63f). It may be reconsidered after an upstream stable release explicitly fixes the issue.

## Runtime download security

Third-party runtime downloads are HTTPS-only and limited to the reviewed hosts needed by this release (`github.com`, `codeload.github.com`, `raw.githubusercontent.com`, `extensions.gnome.org`). ZIP extraction rejects traversal paths, escaping/absolute symlinks and special files. Relative symlinks are preserved only when their lexical target remains inside the extraction root and no archive member writes through them. Archive size/member limits remain enforced, with component-specific overrides bounded by a hard global ceiling.

A failed or incomplete third-party installer must not receive a receipt. Where an installer creates new entries under a MacUbuntu-owned destination, unexpected new names trigger cleanup and a controlled failure.

## Deliberately deferred

The following can be valuable but are not in the default v0.4 deep profile because their safe merge/uninstall semantics need more work:

- WhiteSur Firefox profile rewrites;
- WhiteSur libadwaita `~/.config/gtk-4.0` overwrite mode;
- GDM/login-screen replacement;
- GRUB themes;
- global-menu hacks;
- forced Super+Space reassignment when it conflicts with GNOME input-source switching;
- proprietary SF Pro/SF Mono redistribution;
- hardware-driver, GPU, kernel, firmware or bootloader changes.

These are deferred rather than silently applied because “deeper” is not useful if it makes the machine harder to restore.
