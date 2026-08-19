# MacUbuntu agent contract

MacUbuntu is designed to be usable by both humans and automation. Human-readable output is intentionally concise and localized; agents should consume JSON and must not scrape or depend on translated prose.

## Safe autonomous flow

An AI agent should use this order:

```bash
./macubuntu audit --json
./macubuntu plan --json
./macubuntu macify --yes --json
./macubuntu status --json
```

For removal:

```bash
./macubuntu uninstall --yes --json
```

Global presentation options are accepted either before or after the command. `--verbose` is primarily for human diagnostics; it does not change the semantic data returned by `--json`.

Use `--force` only when the user explicitly wants MacUbuntu to overwrite post-install configuration drift or accept package-removal conflicts reported by the safe uninstall path.

## Rules for agents

- Never parse the normal localized console output. Use `--json`.
- Never edit the state file manually.
- Treat `support.level=unsupported` as a hard stop.
- Treat `support.level=experimental` as a reason to inspect `plan` before applying.
- Do not run raw `apt remove`, `gsettings reset`, or delete MacUbuntu-managed files to simulate uninstall.
- Prefer `--dry-run` for exploratory actions.
- Preserve receipts: MacUbuntu records each successful mutation immediately.
- Distinguish profile state from ownership: a system may be fully converged while MacUbuntu owns zero mutations because everything was already configured before MacUbuntu ran.
- If an operation is reported as drifted during uninstall, keep the user's newer value unless the user explicitly asks for `--force`.
- Hardware drivers, GPU configuration and bootloader changes are outside the default MacUbuntu scope.

## JSON stability

The top-level envelope is:

```json
{
  "macubuntu_version": "0.1.0",
  "command": "audit",
  "interface": {
    "language": "en",
    "verbose": false
  },
  "data": {}
}
```

The `interface` object describes presentation choices only. Agent logic should depend on machine fields inside `data`, such as support levels, action/status codes, plan summaries, `profile_applied`, `converged`, and operation receipts.

Fields may be added in minor versions. Existing semantic fields should not be repurposed without a schema/version change.
