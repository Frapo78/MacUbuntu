# MacUbuntu

**Deep, reversible mac-style transformation for Ubuntu GNOME.**

**Idea and implementation / Idea e realizzazione: Francesco Poltero.**

MacUbuntu is an independent open-source project that turns a supported Ubuntu GNOME installation into a cohesive Mac-inspired desktop while keeping Ubuntu underneath. It is not a theme dump and it is not a destructive setup script: MacUbuntu audits the machine, plans changes, installs compatible components, records ownership receipts, detects drift, updates itself safely and can undo what it actually changed.

> Status: **alpha / v0.4 deep-macify foundation**. The project is intentionally conservative about ownership and uninstall. Hardware drivers, GPU configuration, firmware, bootloader and disk partitioning remain outside the default transformation path.

## One command

Clone MacUbuntu once:

```bash
git clone https://github.com/Frapo78/MacUbuntu.git
cd MacUbuntu
```

Then run:

```bash
./macubuntu
```

A bare launch is the beginner-friendly one-shot entry point. It performs the same flow as `macify`, shows a short plan and asks before changing the machine.

For unattended use by an AI agent or automation:

```bash
./macubuntu macify --yes --json
```

For technical terminal output:

```bash
./macubuntu macify --yes --verbose
```

Normal mode deliberately hides APT, Flatpak and upstream-installer noise. `--verbose` streams technical subprocess output; failures still retain diagnostic stdout/stderr for JSON and troubleshooting.

## What the v0.4 one-shot manages

MacUbuntu chooses established upstream projects and Ubuntu packages, pins external source/extension versions where practical and skips unsupported/conflicting components rather than forcing them.

| Capability | Component / project | MacUbuntu behavior |
|---|---|---|
| Core desktop | GNOME + Ubuntu Dock | Dock, window controls, trackpad, previews, animations and mac-like dock behavior through reversible GSettings |
| Quick Look-like preview | GNOME Sushi | Installs only when missing |
| Theme | WhiteSur GTK | Pinned upstream source, installed under MacUbuntu-specific user paths; no libadwaita overwrite hack |
| Icons | WhiteSur icon theme | Pinned upstream source under MacUbuntu-specific names |
| Cursor | WhiteSur cursors | Pinned upstream source under a MacUbuntu-specific name |
| Wallpaper | WhiteSur wallpapers | Pinned 2K light/dark files with Git-blob integrity verification |
| Typography | Inter | Ubuntu `fonts-inter`; open alternative rather than redistributing Apple fonts |
| Shell polish | Blur my Shell | GNOME-version-pinned extension |
| Shell controls | Just Perfection | GNOME-version-pinned extension, enabled without fragile opinionated key overrides |
| Clipboard | Clipboard Indicator | GNOME-version-pinned extension |
| X11 gestures | Touchégg + X11 Gestures | Only on X11; stable Touchégg PPA when required; legacy pre-existing Touchégg is not silently replaced |
| Spotlight-like launcher | Ulauncher | Stable official PPA when needed; reversible user service when available, otherwise a MacUbuntu-owned autostart file |
| AirDrop-like LAN sharing | Warpinator (Linux Mint) | Verified user Flatpak from Flathub; encrypted LAN sharing; user must choose a private group code for secure mode |
| Android continuity | GSConnect | GNOME-version-pinned extension; skipped when KDE Connect desktop is installed |
| iPhone USB integration | libimobiledevice / ifuse / usbmuxd / GVfs | Ubuntu packages only, when available |
| Desktop tooling | GNOME Tweaks + Extension Manager | Ubuntu packages when available |

See [docs/COMPONENTS.md](docs/COMPONENTS.md) for exact pins, selection rationale and safety notes, and [docs/CREDITS.md](docs/CREDITS.md) for upstream acknowledgements.

## Safety model

MacUbuntu follows a few non-negotiable rules:

- **audit before mutation**;
- **idempotence** — rerunning converges instead of duplicating work;
- **ownership** — pre-existing packages/files/extensions stay user-owned;
- **receipts** — a component is removed only when MacUbuntu has evidence that it installed or changed it;
- **drift protection** — user changes made after MacUbuntu are preserved by safe uninstall;
- **pinned external sources** — source archives and GNOME extension versions are selected by MacUbuntu releases instead of tracking arbitrary upstream `master`/`latest` state;
- **archive safety** — downloaded ZIPs are path-checked, size-limited and symlink entries are rejected;
- **source allowlist** — runtime source downloads are restricted to the expected HTTPS upstream hosts;
- **no hidden hardware surgery** — GPU/driver/firmware/boot/disk operations are not part of the normal macification path;
- **quiet by default** — technical command output is opt-in with `--verbose`;
- **machine interface** — AI agents use `--json` and stable codes rather than scraping translated prose.

The resilience model is documented in [docs/RESILIENCE.md](docs/RESILIENCE.md).

## Reversibility

Managed state normally lives at:

```text
~/.local/state/macubuntu/state.json
```

MacUbuntu records reversible GSettings changes, APT package deltas, third-party repositories it added, user Flatpak apps/remotes it added, GNOME extensions it installed/enabled, service state, generated files and MacUbuntu-owned directories/files downloaded from pinned upstream sources.

Examples of ownership behavior:

- if Sushi was already installed, MacUbuntu does not claim it and uninstall leaves it alone;
- if a GNOME extension was already present but disabled, MacUbuntu can record only the enable/disable transition without claiming the extension files;
- if Flathub already existed, MacUbuntu never claims the remote;
- if MacUbuntu added Flathub and the user later installs other Flatpak apps from it, uninstall relinquishes the remote instead of breaking those apps;
- source-installed themes use names beginning with `MacUbuntu-` so existing WhiteSur installations are not overwritten;
- if a managed file/directory drifts after install, safe uninstall preserves it unless the user explicitly requests a force path where supported.

## Commands

```text
./macubuntu                         one-shot interactive macification
./macubuntu audit                   inspect system and compatibility
./macubuntu doctor                  safety/readiness checks
./macubuntu plan                    show what would change
./macubuntu apply                   apply the configured modules
./macubuntu macify                  audit → plan → apply
./macubuntu status                  show convergence and owned operations
./macubuntu update                  safe self-update from the official repository
./macubuntu update --check          check without changing the checkout
./macubuntu uninstall               restore MacUbuntu-owned changes
```

Common presentation options:

```text
--lang auto|it|en
--verbose
--json
--dry-run
```

Mutating commands require confirmation unless `--yes` is supplied.

## Self-update

```bash
./macubuntu update
```

The updater accepts only a clean checkout of the official `Frapo78/MacUbuntu` `main` branch and uses a fast-forward update. It does not use `git reset --hard` and does not discard local work.

## AI agents

Read [AGENTS.md](AGENTS.md). Agents should use `doctor --json`, `plan --json`, `macify --yes --json`, `status --json` and `uninstall --yes --json`, and must never bypass receipts with raw package removal, direct GSettings resets or forced Git operations.

## Development

The core uses the Python standard library. Run tests with:

```bash
python3 -m compileall -q macubuntu_app
python3 -m unittest discover -s tests -v
```

CI currently validates the supported Ubuntu LTS matrix before changes are merged.

## Credits and independence

MacUbuntu exists because of the work of GNOME, Ubuntu/Canonical and many independent open-source maintainers. MacUbuntu installs or configures their software; it does not claim ownership or authorship of those projects. Please read [docs/CREDITS.md](docs/CREDITS.md).

MacUbuntu is an independent community project conceived and implemented by **Francesco Poltero**. It is not affiliated with, endorsed by or sponsored by Apple Inc., Canonical Ltd. or the third-party projects it integrates. macOS, Mac and related Apple marks belong to Apple Inc.; Ubuntu is a trademark of Canonical Ltd.

MacUbuntu does not distribute Apple proprietary operating-system assets or proprietary Apple fonts.

## License

MacUbuntu's own source code is released under the [MIT License](LICENSE). Components installed or managed by MacUbuntu remain under their respective upstream licenses.
