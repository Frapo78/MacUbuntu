# MacUbuntu agent contract

MacUbuntu is designed to be usable by both humans and automation. Human-readable output is intentionally concise and localized; agents should consume JSON and must not scrape or depend on translated prose.

## Safe autonomous flow

An AI agent should normally use this order:

```bash
./macubuntu update --check --json
./macubuntu audit --json
./macubuntu plan --json
./macubuntu macify --yes --json
./macubuntu status --json
```

If `update --check --json` returns `data.status=update_available`, an agent may run:

```bash
./macubuntu update --json
```

only when the user is operating a normal official checkout and no local-development intent is present. After `data.status=updated`, start a new MacUbuntu process before continuing so the newly downloaded code is loaded.

For removal:

```bash
./macubuntu uninstall --yes --json
```

Global presentation options are accepted either before or after the command. `--verbose` is primarily for human diagnostics; it does not change the semantic data returned by `--json`.

Use `--force` only when the user explicitly wants MacUbuntu to overwrite post-install configuration drift or accept package-removal conflicts reported by the safe uninstall path.

## Update statuses

Agent logic for self-update must branch on `data.status`, not translated text. Safe success states are:

- `up_to_date`
- `update_available`
- `updated`

Blocked/error states include:

- `git_missing`
- `not_git_checkout`
- `origin_missing`
- `unofficial_remote`
- `detached_head`
- `wrong_branch`
- `dirty_worktree`
- `status_failed`
- `head_unreadable`
- `fetch_failed`
- `remote_head_unreadable`
- `local_ahead`
- `diverged`
- `fast_forward_failed`

Do not work around a blocked update with `git reset --hard`, forced checkout, local-file deletion, branch rewriting or remote replacement. Surface the blocker to the user or operate on the existing installed version.

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
  "macubuntu_version": "0.2.0",
  "command": "audit",
  "interface": {
    "language": "en",
    "verbose": false
  },
  "data": {}
}
```

The `interface` object describes presentation choices only. Agent logic should depend on machine fields inside `data`, such as support levels, action/status codes, plan summaries, `profile_applied`, `converged`, update status and operation receipts.

Fields may be added in minor versions. Existing semantic fields should not be repurposed without a schema/version change.
