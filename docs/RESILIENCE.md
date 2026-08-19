# Resilience and diagnostics

MacUbuntu treats reversibility as a correctness requirement. Before adding more modules, the core protects three things: **readiness**, **exclusive ownership of mutations**, and **receipt durability**.

## Doctor

Run:

```bash
./macubuntu doctor
```

The normal interface reports only the overall result and actionable warnings/errors. Technical evidence is opt-in:

```bash
./macubuntu doctor --verbose
```

Agents should use:

```bash
./macubuntu doctor --json
```

Doctor is local and read-only. It does not contact GitHub or modify the system. It checks:

- Ubuntu/GNOME support level;
- graphical session type;
- GSettings availability and basic responsiveness;
- APT/dpkg tooling;
- root/sudo capability for privileged package operations;
- MacUbuntu state-file integrity;
- free disk space;
- whether the checkout is suitable for automatic update.

Repository/update problems are warnings because a tarball or development checkout can still configure the desktop. Missing core desktop/package capabilities and invalid state are blocking failures.

`apply` and `macify` automatically run the same doctor preflight. A blocking doctor result prevents mutation.

## Mutation lock

Commands that can change either managed state or MacUbuntu's own checkout acquire:

```text
~/.local/state/macubuntu/macubuntu.lock
```

The lock is non-blocking. If another MacUbuntu process already owns it, the second process exits safely instead of racing.

The following commands are locked when they are not dry-runs/check-only operations:

- `apply`;
- `macify`;
- `uninstall`;
- `update`.

Read-only commands such as `audit`, `doctor`, `plan`, `status`, and `update --check` do not acquire the mutation lock.

## State validation

The managed state normally lives at:

```text
~/.local/state/macubuntu/state.json
```

Before MacUbuntu trusts it, the file must:

- contain valid JSON;
- use a supported state schema version;
- contain an operation list made of objects;
- contain a valid profile object when present.

A corrupted or structurally invalid state file is never silently replaced. Mutating commands stop and report a state error.

## Last-known-good backup

Before replacing an existing valid state file, MacUbuntu copies it to:

```text
~/.local/state/macubuntu/state.json.bak
```

The backup is therefore the state immediately before the latest successful state write. `doctor` checks whether a backup exists and whether it is itself valid when the primary state is broken.

The backup is not automatically restored yet. Automatic recovery would need explicit rules for reconciling the backup with mutations that may already have happened on the machine. Until that transaction recovery model exists, MacUbuntu prefers to stop rather than guess.

After a complete clean uninstall, both the empty state file and its stale backup are removed.

## Agent behavior

Agents must treat these machine codes as stable decisions:

- doctor `status=healthy`: no warnings or failures;
- doctor `status=degraded`: warnings exist, but no blocking failure;
- doctor `status=blocked`: one or more blocking failures;
- command `status=busy`: another MacUbuntu mutation is running;
- command `status=state_error`: managed-state integrity prevented the operation.

Never work around these safeguards with direct file deletion, `git reset --hard`, raw GSettings resets, or manual package removal.
