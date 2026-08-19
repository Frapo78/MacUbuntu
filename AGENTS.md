# MacUbuntu agent contract

MacUbuntu is designed to be usable by both humans and automation.

## Safe autonomous flow

An AI agent should use this order:

```bash
./macubuntu --json audit
./macubuntu --json plan
./macubuntu --json macify --yes
./macubuntu --json status
```

For removal:

```bash
./macubuntu --json uninstall --yes
```

Use `--force` only when the user explicitly wants MacUbuntu to overwrite post-install configuration drift or accept package-removal conflicts reported by the safe uninstall path.

## Rules for agents

- Never edit the state file manually.
- Treat `support.level=unsupported` as a hard stop.
- Treat `support.level=experimental` as a reason to inspect `plan` before applying.
- Do not run raw `apt remove`, `gsettings reset`, or delete MacUbuntu-managed files to simulate uninstall.
- Prefer `--dry-run` for exploratory actions.
- Preserve receipts: MacUbuntu records each successful mutation immediately.
- If an operation is reported as drifted during uninstall, keep the user's newer value unless the user explicitly asks for `--force`.
- Hardware drivers, GPU configuration and bootloader changes are outside the default MacUbuntu scope.

## JSON stability

The top-level envelope is:

```json
{
  "macubuntu_version": "0.1.0",
  "command": "audit",
  "data": {}
}
```

Fields may be added in minor versions. Existing semantic fields should not be repurposed without a schema/version change.
