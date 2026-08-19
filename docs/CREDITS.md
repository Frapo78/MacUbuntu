# Credits and upstream acknowledgements

## MacUbuntu

**Idea and implementation / Idea e realizzazione: Francesco Poltero.**

MacUbuntu is an integration and configuration project. The software and creative assets listed below are created and maintained by their respective owners and contributors. MacUbuntu is grateful to them and does not claim ownership of their work.

MacUbuntu-owned components, including **MacUbuntu Fullscreen Spaces** and **MacUbuntu Accents**, are part of the MacUbuntu project and are released under MacUbuntu's MIT license.

## Desktop platform

### GNOME Project

Thank you to the GNOME Project and contributors for GNOME Shell, Mutter, Nautilus, GNOME Sushi, GNOME Shell Extensions/User Themes, GNOME Tweaks and the GNOME platform. MacUbuntu Fullscreen Spaces relies on GNOME Shell/Mutter's public window and workspace APIs.

- GNOME: https://www.gnome.org/
- GNOME Shell: https://gitlab.gnome.org/GNOME/gnome-shell
- Mutter: https://gitlab.gnome.org/GNOME/mutter
- Nautilus: https://gitlab.gnome.org/GNOME/nautilus
- Sushi: https://gitlab.gnome.org/GNOME/sushi
- GNOME Shell Extensions: https://gitlab.gnome.org/GNOME/gnome-shell-extensions

### IBus Project

Thank you to the **IBus project and contributors** for the Linux input-method framework used by MacUbuntu Accents. IBus provides the application-facing input-method path that lets MacUbuntu implement accent candidates without global key injection.

- IBus: https://github.com/ibus/ibus

The MacUbuntu accent engine itself is original MacUbuntu code; IBus remains an independent upstream project.

### Ubuntu / Canonical and Ubuntu contributors

Thank you to Canonical, Ubuntu maintainers and Debian/Ubuntu package maintainers for Ubuntu GNOME integration, Ubuntu Dock, AppIndicator integration, IBus packages and the package infrastructure used by MacUbuntu.

- Ubuntu: https://ubuntu.com/
- Ubuntu Dock / Dash to Dock lineage: https://github.com/micheleg/dash-to-dock

## Interaction research acknowledgements

### Fullscreen-workspace projects

While designing the stricter Mac-style fullscreen contract, MacUbuntu reviewed these open-source projects:

- **Fullscreen to Empty Workspace** by onsah and contributors: https://github.com/onsah/fullscreen-to-new-workspace
- **Fullscreen Spaces** by Eytan S. and contributors: https://github.com/eytans/fullscreen-spaces

They helped validate GNOME/Mutter workspace approaches. MacUbuntu v0.6 does **not** install or redistribute their extension code: MacUbuntu Fullscreen Spaces is a separate implementation because MacUbuntu requires a new Space even when the fullscreen app was already alone.

### press2accent research reference

Thank you to **dresnite / press2accent contributors** for publicly demonstrating a modern IBus-based press-and-hold accent approach on GNOME/Wayland:

- https://github.com/dresnite/press2accent

MacUbuntu does **not** install or redistribute press2accent. MacUbuntu Accents is separate MIT-licensed MacUbuntu code and deliberately uses delayed base-character commit rather than surrounding-text deletion/replacement.

## Appearance

### Vince Liuice and MacTahoe / WhiteSur contributors

A major part of MacUbuntu's visual transformation is possible thanks to **Vince Liuice (`vinceliuice`) and contributors**.

- MacTahoe GTK Theme: https://github.com/vinceliuice/MacTahoe-gtk-theme — upstream MIT license
- WhiteSur GTK Theme: https://github.com/vinceliuice/WhiteSur-gtk-theme — upstream MIT license; legacy v0.4 managed appearance
- WhiteSur Icon Theme: https://github.com/vinceliuice/WhiteSur-icon-theme — upstream GPL-3.0 license
- WhiteSur Cursors: https://github.com/vinceliuice/WhiteSur-cursors — upstream GPL-3.0 license
- WhiteSur Wallpapers: https://github.com/vinceliuice/WhiteSur-wallpapers — upstream MIT license

Thank you also for the open-source mac-inspired wallpaper artwork distributed with the WhiteSur and MacTahoe projects. MacUbuntu uses pinned WhiteSur/Monterey-inspired assets and MacTahoe day/night assets instead of redistributing proprietary Apple wallpaper files.

MacUbuntu uses isolated `MacUbuntu-*` install names and deliberately does not enable the upstream libadwaita `~/.config/gtk-4.0` overwrite path, GDM replacement or Firefox rewrite by default.

### Inter

Thank you to **Rasmus Andersson and Inter contributors** for the Inter typeface. MacUbuntu uses Ubuntu's `fonts-inter` package instead of redistributing proprietary Apple fonts.

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

Thank you to the **GSConnect contributors** and the **KDE Connect** ecosystem.

- GSConnect: https://github.com/GSConnect/gnome-shell-extension-gsconnect
- KDE Connect: https://kdeconnect.kde.org/

MacUbuntu does not install GSConnect when KDE Connect desktop is already installed.

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

MacUbuntu selects the stable v5 channel and manages launcher persistence only when needed.

## Local sharing

### Warpinator

Thank you to the **Linux Mint team and Warpinator contributors**.

- https://github.com/linuxmint/warpinator
- https://flathub.org/apps/org.x.Warpinator

MacUbuntu installs the verified Flathub build when needed and does not force the interactive app open on every login.

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

## Packaging and distribution services

Thank you to Ubuntu/Debian maintainers, Launchpad and Flathub contributors. MacUbuntu may use official Ubuntu repositories, reviewed upstream PPAs and Flathub as documented in `COMPONENTS.md`.

## Trademark and affiliation notice

Credits are acknowledgement, not endorsement. MacUbuntu is not affiliated with the upstream projects listed here unless explicitly stated by those projects. Apple, macOS and Mac are trademarks of Apple Inc.; Ubuntu is a trademark of Canonical Ltd. All third-party names and marks belong to their respective owners.

MacUbuntu does not redistribute proprietary Apple operating-system assets, fonts or wallpaper files.
