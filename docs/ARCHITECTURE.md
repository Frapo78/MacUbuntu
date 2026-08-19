# Architecture

MacUbuntu is a transaction-oriented configuration engine, not a monolithic shell script.

## Layers

```text
macubuntu
└── macubuntu_app
    ├── cli.py          command line and human/JSON presentation
    ├── doctor.py       local safety preflight
    ├── engine.py       module orchestration
    ├── system.py       feature detection and audit
    ├── operations.py   core reversible GSettings/APT mutations
    ├── external.py     safe third-party/repository/file/extension operations
    ├── state.py        receipt persistence and validation
    ├── locking.py      exclusive mutation lock
    ├── updater.py      safe official-repository self-update
    ├── util.py         subprocess and platform helpers
    └── modules/        independently plannable/applicable capabilities
```

## Transaction model

A module declares desired state. Every successful mutation that MacUbuntu owns appends or updates a receipt immediately. Existing resources are not claimed merely because they match the desired profile.

State normally lives at `~/.local/state/macubuntu/state.json`; the last valid previous state is retained as `state.json.bak` before replacement.

### Receipt kinds

The v0.4 engine understands:

- `gsettings` — original/applied GVariant values with drift-safe restore;
- `apt_bundle` — actual dpkg package delta introduced by the transaction;
- `owned_paths` — MacUbuntu-created files/directories plus content-tree digest and upstream provenance;
- `gnome_extension` — whether MacUbuntu installed extension files, original enable state, pinned version and tree digest;
- `apt_repository` — repository/PPA added by MacUbuntu;
- `flatpak_app` — user Flatpak installed by MacUbuntu;
- `flatpak_remote` — user remote added by MacUbuntu, with adoption protection if the user later relies on it;
- `service` — original active/enabled state for a service MacUbuntu changed.

## Third-party source boundary

Source-based integrations are constrained more tightly than ordinary shell scripts:

- HTTPS source allowlist;
- pinned commits/version tags;
- bounded download/archive sizes;
- ZIP traversal and symlink rejection;
- extension metadata UUID/GNOME-version verification;
- MacUbuntu-specific user destinations;
- unexpected installer output under a managed destination triggers cleanup/failure;
- no receipt is written for a failed/incomplete install.

Source installers are never used for GPU, bootloader, firmware or disk changes.

## Quiet subprocess model

Normal mode captures subprocess stdout/stderr so `apt`, Flatpak and upstream installers do not overwhelm beginners. The entrypoint enables streaming when `--verbose` is present. Detection commands that need parsed stdout explicitly request captured output.

## Module contract

A module exposes a stable `id`, `plan(runner)` and `apply(runner, store, state, app_version, dry_run)`. Modules feature-detect schemas, packages, session type and GNOME major instead of assuming a particular image.

The v0.4 default catalog includes core GNOME, desktop tools, typography, WhiteSur appearance/wallpaper, Shell enhancements, X11 gestures, Ulauncher, Warpinator and phone integration.

## Scope boundaries

The default transformation path does not modify bootloader configuration, kernel command line, GPU driver selection, firmware or disk partitions. Those are hardware-support concerns and must never be hidden inside a desktop customization run.
