# Credits and upstream acknowledgements

## MacUbuntu

**Idea and implementation / Idea e realizzazione: Francesco Poltero.**

MacUbuntu is an integration and configuration project. The software listed below is created and maintained by its respective owners and contributors. MacUbuntu is grateful to them and does not claim ownership of their work.

This page describes components MacUbuntu may install or manage. Upstream licenses, trademarks, copyright notices and project policies remain authoritative.

## Desktop platform

### GNOME Project

Thank you to the GNOME Project and contributors for GNOME Shell, Nautilus, GNOME Sushi, GNOME Shell Extensions/User Themes, GNOME Tweaks and the GNOME platform.

- GNOME: https://www.gnome.org/
- GNOME Shell: https://gitlab.gnome.org/GNOME/gnome-shell
- Nautilus: https://gitlab.gnome.org/GNOME/nautilus
- Sushi: https://gitlab.gnome.org/GNOME/sushi
- GNOME Shell Extensions: https://gitlab.gnome.org/GNOME/gnome-shell-extensions

### Ubuntu / Canonical and Ubuntu contributors

Thank you to Canonical, Ubuntu maintainers and Debian/Ubuntu package maintainers for Ubuntu GNOME integration, Ubuntu Dock, AppIndicator integration and the package infrastructure used by MacUbuntu.

- Ubuntu: https://ubuntu.com/
- Ubuntu Dock / Dash to Dock lineage: https://github.com/micheleg/dash-to-dock

## Appearance

### Vince Liuice and WhiteSur contributors

MacUbuntu's default deep appearance uses the WhiteSur family from **Vince Liuice (`vinceliuice`) and contributors**.

- WhiteSur GTK Theme: https://github.com/vinceliuice/WhiteSur-gtk-theme — upstream MIT license
- WhiteSur Icon Theme: https://github.com/vinceliuice/WhiteSur-icon-theme — upstream GPL-3.0 license
- WhiteSur Cursors: https://github.com/vinceliuice/WhiteSur-cursors — upstream GPL-3.0 license
- WhiteSur Wallpapers: https://github.com/vinceliuice/WhiteSur-wallpapers — upstream MIT license

MacUbuntu uses isolated `MacUbuntu-*` install names and deliberately does not enable WhiteSur's libadwaita `~/.config/gtk-4.0` overwrite path by default.

### Inter

Thank you to **Rasmus Andersson and Inter contributors** for the Inter typeface. MacUbuntu uses Ubuntu's `fonts-inter` package as a free/open, high-quality system font instead of redistributing proprietary Apple fonts.

- Inter: https://github.com/rsms/inter

## GNOME Shell extensions

### Blur my Shell

Thank you to **aunetx and contributors**.

- https://github.com/aunetx/blur-my-shell
- https://extensions.gnome.org/extension/3193/blur-my-shell/

### Just Perfection

Thank you to **Just Perfection / jrahmatzadeh and contributors**.

- https://gitlab.gnome.org/jrahmatzadeh/just-perfection
- https://extensions.gnome.org/extension/3843/just-perfection/

### Clipboard Indicator

Thank you to **Tudmotu and contributors**.

- https://github.com/Tudmotu/gnome-shell-extension-clipboard-indicator
- https://extensions.gnome.org/extension/779/clipboard-indicator/

Clipboard history can contain sensitive material. MacUbuntu installs/enables the extension but does not weaken its privacy controls.

### GSConnect

Thank you to the **GSConnect contributors** and to the **KDE Connect** ecosystem whose protocol enables device integration.

- GSConnect: https://github.com/GSConnect/gnome-shell-extension-gsconnect
- KDE Connect: https://kdeconnect.kde.org/

MacUbuntu does not install GSConnect when the KDE Connect desktop application is already installed because the upstream projects should not be run as competing implementations on the same desktop.

### X11 Gestures and Touchégg

Thank you to **José Expósito** for Touchégg and GNOME X11 Gestures and to all project contributors.

- Touchégg: https://github.com/JoseExposito/touchegg
- X11 Gestures: https://github.com/JoseExposito/gnome-shell-extension-x11gestures

MacUbuntu uses these only for X11 sessions. Wayland uses the desktop's native gesture path.

## Launcher

### Ulauncher

Thank you to **Oleksandr Gornostal and Ulauncher contributors**.

- https://github.com/Ulauncher/Ulauncher
- https://launchpad.net/~agornostal/+archive/ubuntu/ulauncher

MacUbuntu selects the stable v5 channel rather than a pre-release development line.

## Local sharing

### Warpinator

Thank you to the **Linux Mint team and Warpinator contributors** for a mature open-source LAN file-sharing application.

- https://github.com/linuxmint/warpinator
- https://flathub.org/apps/org.x.Warpinator

MacUbuntu installs the verified Flathub build when needed. Warpinator remains an independent Linux Mint project. MacUbuntu does not auto-enable insecure sharing behavior; users should select a private group code in Warpinator to enable its secure mode.

## Phone integration

### libimobiledevice ecosystem

Thank you to the **libimobiledevice, usbmuxd and ifuse contributors** for open iPhone/iOS device connectivity on Linux.

- https://libimobiledevice.org/
- https://github.com/libimobiledevice/libimobiledevice
- https://github.com/libimobiledevice/usbmuxd
- https://github.com/libimobiledevice/ifuse

MacUbuntu uses Ubuntu-packaged versions when available.

## Desktop management tooling

### Extension Manager

Thank you to **Matthew Jakeman and contributors** for Extension Manager.

- https://github.com/mjakeman/extension-manager

MacUbuntu uses Ubuntu's packaged `gnome-shell-extension-manager` when available.

## Packaging and distribution services

Thank you to Ubuntu/Debian maintainers, Launchpad and Flathub contributors. MacUbuntu may use official Ubuntu repositories, specific upstream-maintained Launchpad PPAs and Flathub as documented in `COMPONENTS.md`.

## Trademark and affiliation notice

Credits are acknowledgement, not endorsement. MacUbuntu is not affiliated with the upstream projects listed here unless explicitly stated by those projects. Apple, macOS and Mac are trademarks of Apple Inc.; Ubuntu is a trademark of Canonical Ltd. All third-party names and marks belong to their respective owners.
