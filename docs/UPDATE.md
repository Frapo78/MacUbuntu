# Updating MacUbuntu

MacUbuntu supports two installation sources with different ownership rules: a source checkout from the official GitHub repository and a Debian package installed under `/usr/lib/macubuntu`.

## Source checkout

For a normal Git checkout:

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

## Debian package installs

A `.deb` installation is owned by `dpkg`. MacUbuntu must never use Git to rewrite files below `/usr/lib/macubuntu`, because doing so would make the package database disagree with the files actually installed on disk and would break clean package upgrades/removal.

When the updater detects that it is running from `/usr/lib/macubuntu`, it stops before invoking Git. JSON output keeps the existing `not_git_checkout` status for compatibility and adds:

- `data.installation.kind = "deb_package"`;
- `data.installation.package = "macubuntu"`;
- `data.installation.package_version` when `dpkg-query` can read it;
- `data.update_method = "package_manager"`.

Until MacUbuntu publishes a supported APT/PPA repository, packaged installations should be upgraded by installing a newer trusted MacUbuntu `.deb` with the Ubuntu package manager. The application does not silently replace its own package-owned files.

The package-detection guard is path-first: even if `dpkg-query` is missing or its database is temporarily unavailable, code running from `/usr/lib/macubuntu` is still treated as package-owned and the Git updater remains disabled.

## Safety rules

Automatic Git update is intentionally limited to a standard user clone of the official repository. MacUbuntu refuses to auto-update when:

- the running copy is a Debian package installation;
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

The updater never uses `git reset --hard`, never deletes local changes, never force-updates a development branch and never mutates `dpkg`-owned payload files.

## Update algorithm

1. Resolve the running installation root.
2. If the root is inside `/usr/lib/macubuntu`, classify it as `deb_package`, optionally query the installed package version, and stop before any Git command.
3. Otherwise classify the copy as a source checkout.
4. Validate Git and the checkout.
5. Validate the official `origin` remote.
6. Require a clean `main` worktree.
7. Record the current commit.
8. Run `git fetch --quiet origin main`.
9. Compare local HEAD with `refs/remotes/origin/main`.
10. If equal, report `up_to_date`.
11. If the remote is a descendant of local HEAD, report `update_available` in check mode or run `git merge --ff-only refs/remotes/origin/main`.
12. If local history is ahead or divergent, stop without mutation.

After a successful source-checkout update, the source files on disk are already current. The running process finishes using the code that started it; the next MacUbuntu command automatically loads the new version.

## Machine statuses

The JSON `data.status` field keeps these stable codes:

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

Agents should branch on these codes and, for `not_git_checkout`, inspect `data.installation.kind` before deciding what action to recommend.
