# MacUbuntu

**Turn Ubuntu GNOME into a mac-style desktop with one reversible tool.**

MacUbuntu is an open-source configuration engine for people who want the workflow, interaction model and visual conventions of a modern Mac while keeping Ubuntu underneath.

The project is deliberately more than a theme installer. Its goal is to provide one main application that can:

- audit the machine and desktop session;
- explain what is supported and what would change;
- install only the packages that are missing;
- configure GNOME in a mac-style, module by module;
- keep a receipt of every managed mutation;
- detect configuration drift;
- update itself safely from the official GitHub repository;
- report its state in concise human-readable or stable JSON form;
- undo only what MacUbuntu actually changed.

> **Status: alpha / v0.2 foundation.** The reversible core and safe self-update path are usable now. Appearance, gestures, launcher, sharing and device-integration modules are being moved into the same transaction model instead of being shipped as unrelated shell scripts.

## Quick start

```bash
git clone https://github.com/Frapo78/MacUbuntu.git
cd MacUbuntu
./macubuntu audit
./macubuntu plan
./macubuntu apply --yes
```

Or run the complete safe transformation flow in one command:

```bash
./macubuntu macify --yes
```

This performs audit → plan → apply. It still refuses an unsupported system and every mutation is recorded for uninstall.

To see the current MacUbuntu profile, whether the system is converged and what MacUbuntu actually owns:

```bash
./macubuntu status
```

To update MacUbuntu itself from the official repository:

```bash
./macubuntu update
```

Check for an update without applying it:

```bash
./macubuntu update --check
```

The updater only performs a clean fast-forward of the official `main` branch. It refuses dirty worktrees, forks, development branches, locally-ahead histories and divergence rather than overwriting user work. See [`docs/UPDATE.md`](docs/UPDATE.md).

To restore the recorded pre-MacUbuntu state:

```bash
./macubuntu uninstall --yes
```

If a managed setting was manually changed after MacUbuntu applied it, uninstall protects that newer user choice and reports drift. A deliberate full restore can be requested with:

```bash
./macubuntu uninstall --yes --force
```

## Human interface

The default terminal interface is intentionally short and understandable without Linux/GNOME knowledge. It automatically selects Italian or English from the system locale, with an explicit override when desired:

```bash
./macubuntu status --lang it
./macubuntu status --lang en
```

Technical identifiers, GSettings schemas, before/after values, state paths, Git commits and individual operation results are hidden from normal output. Show them explicitly with:

```bash
./macubuntu status --verbose
./macubuntu plan --verbose
./macubuntu update --verbose
./macubuntu macify --yes --verbose
```

Presentation options can be written before or after the command. For example, both forms are valid:

```bash
./macubuntu --verbose status
./macubuntu status --verbose
```

The normal interface and the machine interface are deliberately separate: scripts and AI agents should use `--json`, not parse translated console text.

## One-command use

Once the repository is cloned, the main entry point is always `./macubuntu`. No Python virtual environment or third-party Python package is required for the current core.

For an unattended run by an automation or AI agent:

```bash
./macubuntu update --check --json
./macubuntu audit --json
./macubuntu plan --json
./macubuntu macify --yes --json
./macubuntu status --json
```

The JSON interface uses stable machine-oriented status/action fields. Human translations do not change those codes.

## Commands

| Command | Purpose |
|---|---|
| `audit` | Inspect OS, GNOME, session, hardware identifier, packages and current settings |
| `plan` | Summarize what MacUbuntu would change; use `--verbose` for exact resources |
| `apply` | Apply supported mac-style modules |
| `macify` | Audit, plan and apply in one autonomous run |
| `status` | Show profile state, convergence and operations actually owned by MacUbuntu |
| `update` | Safely check/apply a fast-forward update from the official GitHub repository |
| `uninstall` | Restore recorded settings and safely remove packages installed by MacUbuntu |

Global options:

```text
--lang auto|it|en  interface language; auto follows the system locale
--verbose          show technical resources, values and receipts
--json             stable machine-readable output for agents/automation
--dry-run          execute detection and planning without mutations
--version          show the MacUbuntu version
```

`update` additionally supports:

```text
--check            fetch update metadata and report availability without changing source files
```

For `update`, `--dry-run` is equivalent to `--check`.

## Safe self-update

`./macubuntu update` is intentionally conservative. It validates that the program is running from a Git checkout whose `origin` points to `Frapo78/MacUbuntu`, requires a clean `main` branch, fetches `origin/main`, and only applies the update when Git proves that a fast-forward is possible.

It never uses `git reset --hard`, never silently discards local files and never force-updates forks or development branches. After a successful update the files on disk are current; the next invocation automatically runs the newly downloaded code.

## Profile state vs ownership

MacUbuntu deliberately separates two concepts:

- **profile applied / converged** — whether the machine currently matches the MacUbuntu profile;
- **owned operations** — changes that MacUbuntu itself performed and therefore may reverse.

A machine can be fully converged with zero owned operations. This happens when the desired packages and settings already existed before MacUbuntu ran. MacUbuntu does not claim ownership of those pre-existing choices and will not remove them during uninstall.

## What v0.2 configures

The first module, `core.gnome`, intentionally uses Ubuntu/GNOME components before adding external projects. It currently manages:

- GNOME Sushi for Space-bar file previews, similar to Quick Look;
- bottom-centered Ubuntu/Dash-to-Dock behavior where that schema is available;
- mac-style window control placement on the left;
- natural scrolling, tap-to-click and two-finger trackpad scrolling;
- GNOME animations and a compact mac-like clock behavior.

All settings are feature-detected. A missing GNOME schema or key is skipped rather than treated as a reason to damage or downgrade the desktop.

## Reversibility model

MacUbuntu stores state under the XDG state directory, normally:

```text
~/.local/state/macubuntu/
└── state.json
```

Every mutation is recorded with enough information to reverse it. A GNOME setting receipt contains its original and applied values. For package installation, MacUbuntu snapshots the dpkg package set before and after the transaction and records the packages actually introduced by that transaction.

During uninstall, operations are replayed in reverse. MacUbuntu refuses to silently overwrite a setting that has drifted after installation unless `--force` is explicitly supplied. Package removal is simulated first; if removing a MacUbuntu-installed bundle would now remove unrelated packages, the safe uninstall reports the conflict instead of proceeding blindly.

This receipt model is the foundation for upcoming theme files, GNOME extensions, repositories and user services.

## Planned modules

The roadmap is organized around user-visible Mac capabilities rather than random tweaks:

- `appearance.whitesur` — GTK/Shell theme, icons and cursor with upstream-aware uninstall;
- `gestures.x11` — Touchégg + GNOME X11 Gestures with session detection;
- `gestures.wayland` — native/desktop-supported gesture path where available;
- `finder.nautilus` — Finder-like Nautilus behavior, previews and services;
- `spotlight.launcher` — fast global app/file/action launcher;
- `spaces.workspaces` — Mission Control/Spaces conventions;
- `keyboard.macos` — mac-oriented shortcuts and modifier conventions;
- `sharing.local` — AirDrop-like LAN sharing using open protocols;
- `phone.integration` — phone notifications, file transfer and clipboard where supported;
- `desktop.polish` — fonts, panel, dock and visual consistency;
- `power.portable` — conservative laptop power tuning, kept separate from graphics drivers.

Hardware driver changes, bootloader changes and GPU troubleshooting are outside the default MacUbuntu transformation path.

## Supported systems

The initial target is **Ubuntu GNOME 22.04 and 24.04**. Other Ubuntu/GNOME combinations are detected as experimental rather than rejected outright.

The architecture is intentionally module-based so support for newer Ubuntu/GNOME releases can be added without rewriting the application.

## For AI agents

Read [`AGENTS.md`](AGENTS.md). The short version is:

1. optionally run `./macubuntu update --check --json` and inspect `data.status`;
2. run `./macubuntu audit --json`;
3. run `./macubuntu plan --json`;
4. inspect the plan and support level;
5. run `./macubuntu macify --yes --json` only when appropriate;
6. never edit `state.json` manually;
7. use `status` and `uninstall` rather than guessing what was changed;
8. never parse the localized human output when JSON is available.

## Design principles

1. **Audit before mutation.**
2. **Idempotence.** Running `apply` again should converge, not duplicate work.
3. **Ownership.** Never uninstall a package merely because MacUbuntu knows about it; remove it only if MacUbuntu installed it.
4. **Rollback receipts.** Record the previous state immediately after each successful mutation.
5. **Feature detection.** Check schemas, packages and session capabilities instead of assuming them.
6. **No opaque mega-script.** A one-command UX may orchestrate many modules, but each module remains independently diagnosable.
7. **Human-first terminal UX.** Normal output is concise and localized; internals are opt-in with `--verbose`.
8. **Agent-friendly output.** Important decisions are available as structured, language-independent JSON.
9. **Safe self-update.** Updating the application must never require destructive Git operations.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the internal model.

## Development

The core intentionally uses the Python standard library only. Run the current test suite with:

```bash
python3 -m unittest discover -s tests -v
```

## Upstream projects

MacUbuntu integrates or plans to integrate upstream open-source projects rather than redistributing Apple software. Relevant projects include GNOME, Ubuntu, WhiteSur, Touchégg and GNOME X11 Gestures. Their own licenses and trademarks remain theirs.

## Trademark notice

MacUbuntu is an independent community project and is not affiliated with, endorsed by or sponsored by Apple Inc. or Canonical Ltd. macOS, Mac and related Apple marks belong to Apple Inc. Ubuntu is a trademark of Canonical Ltd.

MacUbuntu does not ship proprietary Apple operating-system files.

## License

MacUbuntu's own source code is released under the [MIT License](LICENSE). Third-party components installed by modules remain under their respective licenses.
