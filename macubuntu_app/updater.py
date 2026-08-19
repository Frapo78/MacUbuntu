from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import Runner

OFFICIAL_REPOSITORY = "Frapo78/MacUbuntu"
OFFICIAL_BRANCH = "main"


def normalize_github_remote(url: str) -> str | None:
    """Return owner/repo for supported github.com remote URL forms."""
    value = url.strip().rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]

    if value.startswith("git@github.com:"):
        path = value.split(":", 1)[1]
    elif value.startswith("ssh://git@github.com/"):
        path = value[len("ssh://git@github.com/"):]
    elif value.startswith("https://github.com/"):
        path = value[len("https://github.com/"):]
    elif value.startswith("http://github.com/"):
        path = value[len("http://github.com/"):]
    else:
        return None

    parts = [part for part in path.split("/") if part]
    if len(parts) != 2:
        return None
    return f"{parts[0]}/{parts[1]}"


def is_official_remote(url: str) -> bool:
    slug = normalize_github_remote(url)
    return slug is not None and slug.casefold() == OFFICIAL_REPOSITORY.casefold()


def _git(runner: Runner, root: Path, *args: str, check: bool = True):
    return runner.run(["git", "-C", str(root), *args], check=check)


def _text(cp: Any) -> str:
    return (cp.stdout or "").strip()


def _failure(status: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "status": status, **extra}


def update_checkout(
    runner: Runner,
    root: Path,
    *,
    check_only: bool = False,
) -> dict[str, Any]:
    """Check or fast-forward a clean checkout of the official repository.

    The updater deliberately refuses to alter dirty trees, forks, detached HEADs,
    development branches, locally-ahead branches or diverged histories.
    """
    root = root.resolve()

    if not runner.exists("git"):
        return _failure("git_missing", repository=OFFICIAL_REPOSITORY)

    inside = _git(runner, root, "rev-parse", "--is-inside-work-tree", check=False)
    if inside.returncode != 0 or _text(inside) != "true":
        return _failure("not_git_checkout", repository=OFFICIAL_REPOSITORY, root=str(root))

    origin = _git(runner, root, "remote", "get-url", "origin", check=False)
    if origin.returncode != 0:
        return _failure("origin_missing", repository=OFFICIAL_REPOSITORY, root=str(root))
    remote_url = _text(origin)
    if not is_official_remote(remote_url):
        return _failure(
            "unofficial_remote",
            repository=OFFICIAL_REPOSITORY,
            remote_url=remote_url,
        )

    branch_cp = _git(runner, root, "symbolic-ref", "--short", "-q", "HEAD", check=False)
    branch = _text(branch_cp)
    if branch_cp.returncode != 0 or not branch:
        return _failure("detached_head", repository=OFFICIAL_REPOSITORY, remote_url=remote_url)
    if branch != OFFICIAL_BRANCH:
        return _failure(
            "wrong_branch",
            repository=OFFICIAL_REPOSITORY,
            branch=branch,
            expected_branch=OFFICIAL_BRANCH,
            remote_url=remote_url,
        )

    status_cp = _git(runner, root, "status", "--porcelain", "--untracked-files=normal", check=False)
    if status_cp.returncode != 0:
        return _failure("status_failed", repository=OFFICIAL_REPOSITORY, branch=branch)
    dirty_lines = [line for line in (status_cp.stdout or "").splitlines() if line.strip()]
    if dirty_lines:
        return _failure(
            "dirty_worktree",
            repository=OFFICIAL_REPOSITORY,
            branch=branch,
            remote_url=remote_url,
            dirty_paths=dirty_lines,
        )

    before_cp = _git(runner, root, "rev-parse", "HEAD", check=False)
    if before_cp.returncode != 0:
        return _failure("head_unreadable", repository=OFFICIAL_REPOSITORY, branch=branch)
    before = _text(before_cp)

    fetch = _git(runner, root, "fetch", "--quiet", "origin", OFFICIAL_BRANCH, check=False)
    if fetch.returncode != 0:
        return _failure(
            "fetch_failed",
            repository=OFFICIAL_REPOSITORY,
            branch=branch,
            remote_url=remote_url,
            current_commit=before,
            error=(fetch.stderr or "").strip(),
        )

    remote_ref = f"refs/remotes/origin/{OFFICIAL_BRANCH}"
    remote_cp = _git(runner, root, "rev-parse", remote_ref, check=False)
    if remote_cp.returncode != 0:
        return _failure(
            "remote_head_unreadable",
            repository=OFFICIAL_REPOSITORY,
            branch=branch,
            remote_url=remote_url,
            current_commit=before,
        )
    latest = _text(remote_cp)

    base = {
        "repository": OFFICIAL_REPOSITORY,
        "branch": branch,
        "remote_url": remote_url,
        "current_commit": before,
        "latest_commit": latest,
        "check_only": check_only,
    }

    if before == latest:
        return {"ok": True, "status": "up_to_date", **base, "updated": False}

    remote_ahead = _git(runner, root, "merge-base", "--is-ancestor", before, latest, check=False)
    if remote_ahead.returncode == 0:
        if check_only:
            return {"ok": True, "status": "update_available", **base, "updated": False}

        changed_cp = _git(runner, root, "diff", "--name-only", before, latest, check=False)
        changed_files = [line for line in (changed_cp.stdout or "").splitlines() if line.strip()]
        merge = _git(runner, root, "merge", "--ff-only", remote_ref, check=False)
        if merge.returncode != 0:
            return _failure(
                "fast_forward_failed",
                **base,
                error=(merge.stderr or "").strip(),
            )

        after_cp = _git(runner, root, "rev-parse", "HEAD", check=False)
        after = _text(after_cp) if after_cp.returncode == 0 else latest
        return {
            "ok": True,
            "status": "updated",
            **base,
            "updated": True,
            "previous_commit": before,
            "current_commit": after,
            "changed_files": changed_files,
            "restart_required": True,
        }

    local_ahead = _git(runner, root, "merge-base", "--is-ancestor", latest, before, check=False)
    if local_ahead.returncode == 0:
        return _failure("local_ahead", **base)

    return _failure("diverged", **base)
