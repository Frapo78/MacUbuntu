# Resilience and diagnostics

MacUbuntu treats reversibility as a correctness requirement.

## Doctor

`./macubuntu doctor` is local and read-only. It checks Ubuntu/GNOME support, graphical session, GSettings, APT/dpkg tooling, privilege capability, managed-state integrity, free space and whether the local checkout is suitable for self-update. `apply` and `macify` use the same preflight.

Use `./macubuntu doctor --verbose` for technical evidence and `./macubuntu doctor --json` for agents.

## Mutation lock

Real `apply`, `macify`, `uninstall` and `update` runs acquire the XDG-state lock `~/.local/state/macubuntu/macubuntu.lock`. Read-only audit/doctor/plan/status/update-check operations do not.

## State durability

`state.json` must contain valid JSON, a supported schema, a list of operation objects and a valid profile object. Corrupt state is never silently overwritten.

Before replacing a valid state, MacUbuntu copies it to `state.json.bak`. The backup is not automatically restored because machine mutations may have happened after it was created; recovery requires reconciliation rather than guessing.

### Transaction interruption journal

Every real `apply`, `macify` and `uninstall` now writes an `in_progress` transaction marker to `state.json` before the first module or receipt mutation. The marker contains a random run ID, operation name, MacUbuntu version, start time and the number of owned operation receipts at the start of the run. Successful completion atomically moves that record to `last_transaction` with `status: committed`, completion time and the final receipt count.

If the process, host or desktop session dies before commit, the active marker remains durable. `StateStore.health()` then reports `transaction_interrupted` and `doctor` blocks further mutation instead of assuming that the backup, current receipts or machine state are authoritative. `status --json` also exposes `recovery_required` plus the transaction evidence already stored in state.

This journal deliberately records no usernames, arbitrary home paths, environment variables, tokens, network identifiers or command output. It is ownership/recovery metadata only.

The transaction marker is detection evidence, not an automatic rollback instruction. MacUbuntu still does not silently restore `state.json.bak`, purge packages, reset GSettings or overwrite user drift after an interrupted run.

## External component failures

Third-party download/validation/install errors use the same controlled command-failure UX as APT/GSettings failures. In normal mode the user sees a short localized error. `--verbose`/JSON expose the failing resource, synthetic operation code and captured stderr.

Source installers are pinned and constrained to MacUbuntu-owned user destinations. Partial/new destination entries created by a failed source install are cleaned when MacUbuntu can prove they did not exist before the run. No receipt is written until required output exists and has passed validation.

## Flatpak adoption

If MacUbuntu added a Flatpak remote and the user later installs other apps from that remote, uninstall does not delete a now-shared dependency. MacUbuntu relinquishes ownership of the remote and leaves it available.

## Remaining recovery boundary

Issue #12 still tracks the next reconciliation layer: inspect actual machine state, current receipts and the valid backup, classify each interrupted resource as applied/partial/not-applied, and offer explicit safe recovery choices. Until that layer lands, an interrupted transaction fails closed and requires deliberate reconciliation rather than reconstruction from guesses.
