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

## External component failures

Third-party download/validation/install errors use the same controlled command-failure UX as APT/GSettings failures. In normal mode the user sees a short localized error. `--verbose`/JSON expose the failing resource, synthetic operation code and captured stderr.

Source installers are pinned and constrained to MacUbuntu-owned user destinations. Partial/new destination entries created by a failed source install are cleaned when MacUbuntu can prove they did not exist before the run. No receipt is written until required output exists and has passed validation.

## Flatpak adoption

If MacUbuntu added a Flatpak remote and the user later installs other apps from that remote, uninstall does not delete a now-shared dependency. MacUbuntu relinquishes ownership of the remote and leaves it available.

## Known recovery boundary

A process interruption between an external machine mutation and receipt persistence is still a special recovery case. Issue #12 tracks explicit transaction reconciliation. Until that work lands, MacUbuntu fails closed when receipt integrity is uncertain rather than reconstructing ownership from guesses.
