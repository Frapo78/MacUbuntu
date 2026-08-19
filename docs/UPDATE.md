# Updating MacUbuntu

MacUbuntu can update its own source checkout from the official GitHub repository.

## Normal use

```bash
./macubuntu update
```

The command fetches the official `main` branch and applies an update only when the local checkout can be fast-forwarded safely.

To check without changing source files:

```bash
./macubuntu update --check
```

Technical diagnostics:

```bash
./macubuntu update --verbose
```

Agent/automation output:

```bash
./macubuntu update --check --json
./macubuntu update --json
```

`--dry-run` behaves like `--check` for the update command.

## Safety rules

Automatic update is intentionally limited to a standard user clone of the official repository. MacUbuntu refuses to auto-update when:

- Git is unavailable;
- the application is not running from a Git checkout;
- the `origin` remote is missing;
- `origin` is not `Frapo78/MacUbuntu` on `github.com`;
- HEAD is detached;
- the current branch is not `main`;
- tracked or untracked local changes are present;
- the local branch contains commits not present upstream;
- local and upstream histories have diverged;
- Git cannot perform a fast-forward-only update.

The updater never uses `git reset --hard`, never deletes local changes and never force-updates a development branch.

## Update algorithm

1. Validate Git and the checkout.
2. Validate the official `origin` remote.
3. Require a clean `main` worktree.
4. Record the current commit.
5. Run `git fetch --quiet origin main`.
6. Compare local HEAD with `refs/remotes/origin/main`.
7. If equal, report `up_to_date`.
8. If the remote is a descendant of local HEAD, report `update_available` in check mode or run `git merge --ff-only refs/remotes/origin/main`.
9. If local history is ahead or divergent, stop without mutation.

After a successful update, the source files on disk are already current. The running process finishes using the code that started it; the next MacUbuntu command automatically loads the new version.

## Machine statuses

The JSON `data.status` field uses stable codes:

- `up_to_date`
- `update_available`
- `updated`
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

Agents should branch on these codes, not on localized text.
