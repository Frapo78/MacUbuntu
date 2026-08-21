# Ubuntu package

MacUbuntu now includes a Debian packaging foundation for supported Ubuntu LTS releases.

## Build

Install the build dependency and build a binary package from a clean checkout:

```bash
sudo apt-get install debhelper
DPKG_DEB_COMPRESSOR_TYPE=gzip dpkg-buildpackage -us -uc -b
```

The resulting `macubuntu_0.6.0-1_all.deb` installs the shared transaction engine under `/usr/lib/macubuntu`, exposes `macubuntu` and `macubuntu-gui` in `/usr/bin`, and installs the desktop launcher, AppStream metadata, scalable icon, architecture notes and third-party credits in standard system locations.

## Runtime dependencies

The package declares Python 3, PyGObject, GTK 4 and libadwaita introspection data as dependencies. It recommends Git because the source-checkout updater uses Git. A future repository/PPA release channel must teach `macubuntu update` to use the package manager rather than mutating packaged files.

## Ownership boundary

Installing or removing the `.deb` owns only application files installed by dpkg. It does not itself apply the mac-style transformation and it does not delete MacUbuntu state or receipts. `macubuntu uninstall` remains the operation that reverses MacUbuntu-owned desktop changes. Package removal therefore cannot silently reset GSettings, purge transformation dependencies or override user drift.

The application continues to use the same CLI/JSON engine for GUI and terminal actions. Packaging does not add GPU-driver, firmware, kernel, disk, bootloader or partition changes.

## Credits and licenses

Idea and implementation / Idea e realizzazione: **Francesco Poltero**.

`docs/CREDITS.md` and `docs/COMPONENTS.md` are installed with the package. External projects managed by MacUbuntu retain their upstream licenses; the package does not relicense or vendor proprietary Apple operating-system files or fonts.
