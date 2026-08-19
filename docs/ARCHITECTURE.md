# Architecture

MacUbuntu is a transaction-oriented configuration engine, not a monolithic shell script.

## Layers

```text
macubuntu
└── macubuntu_app
    ├── cli.py          command line and human/JSON presentation
    ├── doctor.py       local readiness and integrity diagnostics
    ├── engine.py       orchestration
    ├── system.py       feature detection and audit
    ├── operations.py   reversible mutations
    ├── locking.py      exclusive mutation lock
    ├── state.py        validated receipt persistence + backup
    ├── updater.py      safe official-repository self-update
    ├── util.py         subprocess and platform helpers
    └── modules
        └── core_gnome.py
```

## Safety before mutation

`apply` and `macify` run a local doctor preflight before changing the system. Blocking readiness failures prevent mutation. The doctor checks core desktop/package capabilities, state integrity and resource availability without network access.

Commands that mutate MacUbuntu state or its own source checkout use a non-blocking exclusive lock under the XDG state directory. This prevents concurrent `apply`, `macify`, `uninstall`, or `update` processes from racing on the same receipts or checkout.

See [`RESILIENCE.md`](RESILIENCE.md).

## Transaction model

A module declares desired state. Operations perform the mutation and immediately append or update a receipt in the state store.

The state file normally lives at:

```text
~/.local/state/macubuntu/state.json
```

Before being trusted, state must contain valid JSON, a supported schema, a valid profile object and an operation list made of objects. A corrupt or structurally invalid state file is never silently replaced.

Before replacing an existing valid state file, MacUbuntu keeps the previous known-good state at:

```text
~/.local/state/macubuntu/state.json.bak
```

The backup is diagnostic/recovery evidence, not permission to guess at rollback. Automatic backup restoration requires future transaction reconciliation because machine mutations may have occurred after the backup was written.

### GSettings receipt

A managed GNOME key records:

- schema;
- key;
- original GVariant text;
- last value applied by MacUbuntu.

Uninstall restores the original value only when the current value still equals MacUbuntu's last applied value. A different current value is drift and is protected unless `--force` is requested.

### APT bundle receipt

Before installing a requested package bundle, MacUbuntu snapshots the installed dpkg package set. After the successful installation it records the package delta. This allows uninstall to know which packages were introduced by that transaction rather than merely which package names a module knows about.

Before purge, MacUbuntu simulates the operation. If APT would remove packages outside the recorded delta, safe uninstall keeps the bundle and reports a dependency conflict. Forced uninstall may override this check.

## Idempotence

`plan` compares desired and current state. `apply` only mutates values that differ and only installs missing packages. Existing receipts are updated rather than duplicated.

A successful `apply` records profile application even when every requested setting/package was already converged. Profile state and operation ownership remain separate concepts.

## Module contract

A module should expose:

- a stable `id`;
- `plan(runner)`;
- `apply(runner, store, state, app_version, dry_run)`.

Modules should feature-detect schemas, keys, session type and package availability instead of assuming a particular Ubuntu image.

No module may enter the default one-shot `macify` flow until every resource type it mutates has defined detection, receipt, drift and uninstall semantics.

## Scope boundaries

The default transformation path must not modify:

- bootloader configuration;
- kernel command line;
- GPU driver selection;
- firmware;
- disk partitions.

Those are separate hardware-support concerns and should never be hidden inside a desktop customization module.

## Future receipt kinds

The same model will be extended for:

- managed files/directories;
- GNOME extensions;
- third-party APT repositories/keys;
- user/system services;
- upstream source installs;
- desktop launchers;
- keyboard shortcut sets.

Each new kind must define detection, apply, drift semantics and uninstall before it is enabled in the one-shot `macify` flow.
