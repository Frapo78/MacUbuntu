# MacUbuntu

**Deep, reversible mac-style transformation for Ubuntu GNOME.**

**Idea and implementation / Idea e realizzazione: Francesco Poltero.**

MacUbuntu is an independent open-source project that turns a supported Ubuntu GNOME installation into a cohesive Mac-inspired desktop while keeping Ubuntu underneath. It audits the machine, plans changes, installs compatible components, records ownership receipts, detects drift, persists the intended desktop behavior across sessions, updates itself safely and can undo what it actually changed.

> Status: **alpha / v0.5 Tahoe-polish foundation**. Ownership and safe uninstall remain more important than visual tricks. Hardware drivers, GPU configuration, firmware, bootloader and disk partitioning remain outside the default transformation path.

## One command

```bash
git clone https://github.com/Frapo78/MacUbuntu.git
cd MacUbuntu
./macubuntu
```

The commandless launch is the beginner-friendly one-shot. It performs doctor/preflight checks, asks for confirmation, obtains sudo authorization up front only when the plan needs administrative work, then applies the supported modules.

During long work the normal terminal UI shows a **live animated progress bar**. Percentages move only when a real module completes; a spinner and moving pulse keep the bar visibly alive while downloads, APT or upstream installers are still working. On success MacUbuntu finishes with a localized greeting such as:

```text
🍏 Goditi il tuo nuovo MacUbuntu!
```

For unattended AI/automation use:

```bash
./macubuntu macify --yes --json
```

For technical terminal output:

```bash
./macubuntu macify --yes --verbose
```

`--verbose` keeps stable step lines while streaming technical subprocess output. `--json` never mixes prompts, progress animation or playful prose into the machine-readable result.

## What the v0.5 one-shot manages

| Capability | Component / project | MacUbuntu behavior |
|---|---|---|
| Core desktop | GNOME + Ubuntu Dock | left-side window controls, Mac-like trackpad behavior, bottom floating Dock, previews and reversible GSettings |
| Current window/Shell look | MacTahoe GTK | pinned upstream Tahoe-inspired GTK/Shell theme under `MacUbuntu-*` names, including rounded maximized-window styling; no libadwaita overwrite hack |
| Icons | WhiteSur icon theme | mature pinned upstream icon layer under MacUbuntu-specific names |
| Cursor | WhiteSur cursors | pinned upstream cursor layer under a MacUbuntu-specific name |
| Title bar | MacTahoe + GNOME WM preferences | Tahoe-style chrome, left traffic-light controls, Inter Semi-Bold title text and Mac-like titlebar mouse actions |
| Wallpapers | WhiteSur + Monterey + MacTahoe | six pinned open-source mac-inspired day/dark wallpapers with Git-blob verification; Tahoe day/night is the default pair |
| Typography | Inter | Ubuntu `fonts-inter`; open alternative instead of redistributing proprietary Apple fonts |
| Quick Look-like preview | GNOME Sushi | installs only when missing |
| Shell polish | Blur my Shell | GNOME-version-pinned extension with exact official EGO review artifact |
| Shell controls | Just Perfection | GNOME-version-pinned extension with exact official EGO review artifact |
| Clipboard | Clipboard Indicator | GNOME-version-pinned extension |
| X11 gestures | Touchégg + X11 Gestures | Touchégg system service plus persistent GNOME extension on X11 |
| Spotlight-like launcher | Ulauncher | stable v5 channel; persistent user service when available, otherwise a MacUbuntu-owned GNOME autostart entry |
| AirDrop-like LAN sharing | Warpinator | verified user Flatpak from Flathub; installed for on-demand use rather than forcibly opened at every login |
| Android continuity | GSConnect | persistent GNOME extension; skipped when KDE Connect desktop is already installed |
| iPhone USB integration | libimobiledevice / ifuse / usbmuxd / GVfs | Ubuntu packages when available |
| Desktop tooling | GNOME Tweaks + Extension Manager | installed for on-demand configuration, not auto-opened every session |

See [docs/COMPONENTS.md](docs/COMPONENTS.md) for exact pins and [docs/CREDITS.md](docs/CREDITS.md) for upstream acknowledgements.

## Persistence across reboot

MacUbuntu distinguishes **persistent functionality** from **interactive applications**:

- GSettings, themes, icons, cursors, wallpaper choices, Dock settings and title-bar preferences are stored by GNOME and persist across login/reboot;
- MacUbuntu explicitly keeps GNOME user extensions enabled and records the enabled extension set through reversible receipts;
- Touchégg is managed as an enabled+active system service;
- Ulauncher is managed through its user service when available, otherwise through `~/.config/autostart/macubuntu-ulauncher.desktop`;
- interactive programs such as Warpinator, GNOME Tweaks and Extension Manager remain installed and available, but are **not** pointlessly opened at every login;
- safe uninstall restores or removes only the persistence state MacUbuntu actually introduced.

## Wallpaper policy

MacUbuntu does **not** redistribute proprietary Apple wallpaper files. The default collection uses pinned assets from the open-source WhiteSur and MacTahoe projects to provide recognizable Big Sur/Monterey/Tahoe-inspired choices while keeping the repository redistributable and auditable.

Files are installed under:

```text
~/.local/share/backgrounds/MacUbuntu/
```

The v0.5 collection contains WhiteSur light/dark, Monterey light/dark and MacTahoe day/night. Each download is verified against its pinned upstream Git blob before MacUbuntu accepts ownership.

## Safety model

MacUbuntu follows a few non-negotiable rules:

- **audit before mutation**;
- **idempotence** — rerunning converges instead of duplicating work;
- **ownership** — pre-existing packages/files/extensions stay user-owned;
- **receipts** — a component is removed only when MacUbuntu has evidence that it installed or changed it;
- **drift protection** — user changes made after MacUbuntu are preserved by safe uninstall;
- **pinned external sources** — external source and GNOME extension artifacts are selected by MacUbuntu releases rather than arbitrary `latest` state;
- **archive safety** — downloads are source-allowlisted, path-checked and size/member-limited;
- **no proprietary Apple asset redistribution**;
- **no hidden hardware surgery** — GPU/driver/firmware/boot/disk operations are not part of the normal path;
- **quiet by default** — technical command output is opt-in with `--verbose`;
- **machine interface** — agents use `--json` and stable codes rather than scraping translated prose.

The resilience model is documented in [docs/RESILIENCE.md](docs/RESILIENCE.md).

## Reversibility

Managed state normally lives at:

```text
~/.local/state/macubuntu/state.json
```

MacUbuntu records reversible GSettings changes, APT package deltas, repositories it added, user Flatpak apps/remotes it added, GNOME extensions it installed/enabled, service state, generated files and MacUbuntu-owned paths downloaded from pinned upstream sources.

A v0.4 installation upgrading to v0.5 can migrate from the WhiteSur GTK selection to MacTahoe without erasing the original pre-MacUbuntu GSettings receipt: the existing receipt retains the true original value while its current MacUbuntu-applied value is updated. Legacy MacUbuntu-owned WhiteSur assets remain tracked until safe uninstall rather than being silently orphaned.

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

## Self-update

```bash
./macubuntu update
```

The updater accepts only a clean checkout of the official `Frapo78/MacUbuntu` `main` branch and uses a fast-forward update. It does not use `git reset --hard` and does not discard local work.

## AI agents

Read [AGENTS.md](AGENTS.md). Agents should use `doctor --json`, `plan --json`, `macify --yes --json`, `status --json` and `uninstall --yes --json`, and must never bypass receipts with raw package removal, direct GSettings resets or forced Git operations.

## Development

```bash
python3 -m compileall -q macubuntu_app
python3 -m unittest discover -s tests -v
```

CI validates the supported Ubuntu LTS matrix before changes are merged.

## Credits and independence

MacUbuntu exists because of the work of GNOME, Ubuntu/Canonical and many independent open-source maintainers. MacUbuntu installs or configures their software; it does not claim ownership or authorship of those projects. Please read [docs/CREDITS.md](docs/CREDITS.md).

MacUbuntu is an independent community project conceived and implemented by **Francesco Poltero**. It is not affiliated with, endorsed by or sponsored by Apple Inc., Canonical Ltd. or the third-party projects it integrates. macOS, Mac and related Apple marks belong to Apple Inc.; Ubuntu is a trademark of Canonical Ltd.

MacUbuntu does not distribute Apple proprietary operating-system assets, proprietary Apple fonts or proprietary Apple wallpaper files.

## License

MacUbuntu's own source code is released under the [MIT License](LICENSE). Components installed or managed by MacUbuntu remain under their respective upstream licenses.
