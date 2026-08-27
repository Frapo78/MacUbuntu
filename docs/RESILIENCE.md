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

Every real `apply`, `macify` and `uninstall` writes an `in_progress` transaction marker to `state.json` before the first module or receipt mutation. The marker contains a random run ID, operation name, MacUbuntu version, start time and the number of owned operation receipts at the start of the run. Successful completion atomically moves that record to `last_transaction` with `status: committed`, completion time and the final receipt count.

The core GSettings and APT mutation paths add a second durability boundary inside the transaction. Immediately before changing the machine they persist one `pending_mutation` record containing a separate random mutation ID, mutation kind, preparation time and the minimum evidence required to identify the pre-mutation state. The record is cleared only after the corresponding ownership receipt/state update has been persisted. A transaction cannot be committed while a pending mutation remains.

For GSettings, potentially sensitive setting values are never copied verbatim into mutation-intent evidence. MacUbuntu stores SHA-256 fingerprints of the before/target values, which are sufficient for a read-only comparison without recording wallpaper paths or other arbitrary values a setting may contain. APT intent evidence contains only package names that were absent or present immediately before the requested install/purge.

If the process, host or desktop session dies before commit, the active marker remains durable. If it dies after a mutation was prepared but before the receipt boundary completes, `pending_mutation` remains durable as explicit evidence that the machine may have changed. `StateStore.health()` then reports `transaction_interrupted` and `doctor` blocks further mutation instead of assuming that the backup, current receipts or machine state are authoritative.

Health and `status --json` expose only a privacy-safe pending-mutation summary (ID, kind, status and preparation time). The internal evidence object is deliberately redacted from these general JSON views. Recovery code may inspect the local state directly only through privacy-reviewed probes.

The transaction marker is detection evidence, not an automatic rollback instruction. MacUbuntu still does not silently restore `state.json.bak`, purge packages, reset GSettings or overwrite user drift after an interrupted run.

### Read-only recovery evidence

When an interrupted transaction exists, `doctor --json` adds a read-only recovery inspection report while preserving the stable top-level recovery status `transaction_interrupted`.

The inspector compares the transaction baseline receipt count with the current state and the valid backup when one exists. Receipts created after the transaction baseline are probed against the real machine for conservative, privacy-reviewed operation kinds:

- GSettings receipts are classified as still applied, restored to the original value, drifted, or unverifiable;
- APT bundle receipts are classified from the presence of the packages MacUbuntu actually added, including partial installation/removal states;
- MacUbuntu-owned file/directory receipts are verified by their recorded tree digests and reported only as aggregate matching/missing/drifted counts; local filesystem paths are never echoed into recovery JSON;
- APT repository receipts are checked for the exact MacUbuntu-added PPA;
- user Flatpak remotes and apps are checked read-only for presence/absence;
- GNOME extension receipts combine enabled-state evidence with the digest of MacUbuntu-owned extension files when MacUbuntu installed them; the managed filesystem path is not exposed;
- system and user service receipts compare the current enabled/active state with both the applied state and the recorded original state using read-only `systemctl` probes that do not require privilege escalation;
- receipt kinds without a dedicated privacy-reviewed probe are reported only by kind and index as `unverifiable`. Arbitrary receipt fields such as local paths or command data are not echoed into the recovery report.

The same inspector now consumes durable `pending_mutation` intent for the core GSettings/APT crash boundary. GSettings set/restore intent is compared by hashing the current setting value and matching it against the stored before/target fingerprints. APT install/purge intent is classified from the current presence of only the package names recorded in the pre-mutation evidence. Pending mutations are reported as `applied`, `original`, `partial`, `drifted` or `unverifiable` as appropriate. Raw fingerprint evidence and arbitrary pending fields are never echoed into recovery JSON; unknown pending kinds remain fail-closed and privacy-redacted.

The report exposes a `classification` such as `receipts_consistent`, `inconsistent` or `no_receipted_mutations`, receipt/backup counts, a dedicated privacy-safe `pending_mutation` result and per-receipt evidence. It deliberately sets `automatic_mutation: false` and `decision: manual_review` for every interrupted transaction. Even when the core pending mutation is provably applied or not applied, MacUbuntu does not yet rewrite ownership state automatically because earlier external mutations in the same transaction may still lack equivalent pre-mutation evidence.

The persisted pending-mutation journal and read-only probes close the former ambiguity for the core GSettings/APT boundary: recovery can now tell whether the prepared core mutation reached the machine, did not happen, partially completed, drifted or cannot be verified. External resource families still need the same pre-mutation journaling before a general `recover` command can be safe.

## External component failures

Third-party download/validation/install errors use the same controlled command-failure UX as APT/GSettings failures. In normal mode the user sees a short localized error. `--verbose`/JSON expose the failing resource, synthetic operation code and captured stderr.

Source installers are pinned and constrained to MacUbuntu-owned user destinations. Partial/new destination entries created by a failed source install are cleaned when MacUbuntu can prove they did not exist before the run. No receipt is written until required output exists and has passed validation.

## Flatpak adoption

If MacUbuntu added a Flatpak remote and the user later installs other apps from that remote, uninstall does not delete a now-shared dependency. MacUbuntu relinquishes ownership of the remote and leaves it available.

## Remaining recovery boundary

Issue #12 still tracks the mutating reconciliation layer. Before a general recovery command is enabled, the pre-mutation journal must be extended to the external mutation families (owned paths/source installs, GNOME extensions, APT repositories, Flatpak and services), and those durable intents must receive the same privacy-reviewed read-only classification against the real machine. Until those proofs exist, an interrupted transaction remains blocked and MacUbuntu will not reconstruct ownership, restore the backup or roll back from guesses.
