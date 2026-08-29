# Pending-mutation recovery probes

MacUbuntu persists a `pending_mutation` record before selected machine mutations so an interrupted run can be inspected without guessing whether the mutation reached the system.

The recovery inspector now has privacy-reviewed read-only probes for these pending kinds:

- `gsettings_set` / `gsettings_restore`: compare SHA-256 fingerprints of the current value with the recorded before/target fingerprints;
- `apt_install` / `apt_purge`: compare only the package names recorded in the mutation intent with current dpkg state;
- `apt_repository_add`: check whether the recorded PPA is currently present;
- `flatpak_remote_add`: check user-scope Flatpak remote presence when Flatpak is available;
- `flatpak_app_install`: check user-scope Flatpak application presence when Flatpak is available;
- `service_enable_start`: inspect the recorded system/user unit with read-only `systemctl cat`, `is-enabled` and `is-active` probes.

Each probe classifies the pending boundary as `applied`, `original`, `partial`, `drifted` or `unverifiable` where that distinction is meaningful. Probe failure never triggers mutation.

## Privacy contract

Known-safe public resource identities such as a PPA, Flatpak remote/app ID or systemd unit may appear in recovery JSON only after their mutation kind has a dedicated probe. Raw mutation evidence is never echoed. Invalid or unknown mutation kinds remain redacted, so arbitrary paths, commands, environment values and future private fields do not leak into diagnostics.

## Safety boundary

These probes improve evidence only. `inspect_recovery()` still returns `automatic_mutation: false` and `decision: manual_review` for interrupted transactions. MacUbuntu does not restore the backup, reset GSettings, uninstall packages, remove repositories, alter Flatpak state or change services merely because a probe produced a classification.

Issue #12 remains open until pre-mutation evidence also covers owned-path/source-install and GNOME-extension mutation boundaries and a dedicated recovery command can prove each proposed reconciliation action safe against current machine state, receipts, backup state and user drift.
