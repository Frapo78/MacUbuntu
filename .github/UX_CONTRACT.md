# Terminal UX contract

MacUbuntu has three presentation modes with different audiences and stability guarantees.

## Default human mode

- Automatically localizes to Italian or English from the system locale.
- Uses short outcome-oriented sentences.
- Hides package internals, GSettings schemas, paths and receipt details.
- Must be understandable by a user who does not know GNOME internals.
- New modules must not print raw implementation identifiers by default.

## Verbose human mode

Enable with `--verbose`.

- Includes technical resource identifiers.
- Includes current/desired values where relevant.
- Includes receipt and state information useful for troubleshooting.
- Keeps the same localized high-level summary before technical detail.

## Agent mode

Enable with `--json`.

- Machine codes and semantic fields are language-independent.
- Agents must not parse human console prose.
- Human translations may change without being treated as a machine-interface breaking change.
- Semantic JSON fields must not be repurposed without an explicit compatibility decision.

Global presentation flags should work both before and after the subcommand, for example `macubuntu --verbose status` and `macubuntu status --verbose`.
