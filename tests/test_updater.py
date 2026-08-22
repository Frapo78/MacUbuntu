import unittest
from pathlib import Path

from macubuntu_app.updater import (
    detect_installation_source,
    is_official_remote,
    normalize_github_remote,
    update_checkout,
)


class CP:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeGitRunner:
    def __init__(self, *, remote="https://github.com/Frapo78/MacUbuntu.git", dirty=False, local="aaa", latest="bbb", package_version="0.6.2"):
        self.remote = remote
        self.dirty = dirty
        self.local = local
        self.latest = latest
        self.package_version = package_version
        self.commands = []

    def exists(self, command):
        return command in {"git", "dpkg-query"}

    def run(self, args, check=True, capture=True, env=None):
        self.commands.append(list(args))
        if args and args[0] == "dpkg-query":
            return CP(stdout="ii \t" + self.package_version)
        cmd = list(args[3:])  # git -C ROOT ...
        if cmd == ["rev-parse", "--is-inside-work-tree"]:
            return CP(stdout="true\n")
        if cmd == ["remote", "get-url", "origin"]:
            return CP(stdout=self.remote + "\n")
        if cmd == ["symbolic-ref", "--short", "-q", "HEAD"]:
            return CP(stdout="main\n")
        if cmd == ["status", "--porcelain", "--untracked-files=normal"]:
            return CP(stdout=" M README.md\n" if self.dirty else "")
        if cmd == ["rev-parse", "HEAD"]:
            return CP(stdout=self.local + "\n")
        if cmd == ["fetch", "--quiet", "origin", "main"]:
            return CP()
        if cmd == ["rev-parse", "refs/remotes/origin/main"]:
            return CP(stdout=self.latest + "\n")
        if cmd == ["merge-base", "--is-ancestor", self.local, self.latest]:
            return CP(returncode=0)
        if cmd == ["diff", "--name-only", self.local, self.latest]:
            return CP(stdout="macubuntu_app/cli.py\nREADME.md\n")
        if cmd == ["merge", "--ff-only", "refs/remotes/origin/main"]:
            self.local = self.latest
            return CP(stdout="Updating\n")
        if cmd == ["merge-base", "--is-ancestor", self.latest, self.local]:
            return CP(returncode=1)
        return CP(returncode=1, stderr=f"unexpected command: {cmd}")


class UpdaterTests(unittest.TestCase):
    def test_remote_normalization(self):
        self.assertEqual(normalize_github_remote("https://github.com/Frapo78/MacUbuntu.git"), "Frapo78/MacUbuntu")
        self.assertEqual(normalize_github_remote("git@github.com:Frapo78/MacUbuntu.git"), "Frapo78/MacUbuntu")
        self.assertTrue(is_official_remote("ssh://git@github.com/Frapo78/MacUbuntu.git"))
        self.assertFalse(is_official_remote("https://github.com/example/MacUbuntu.git"))

    def test_dirty_checkout_is_never_updated(self):
        runner = FakeGitRunner(dirty=True)
        result = update_checkout(runner, Path("/tmp/macubuntu"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "dirty_worktree")
        self.assertFalse(any("fetch" in command for command in runner.commands))

    def test_unofficial_remote_is_rejected(self):
        runner = FakeGitRunner(remote="https://github.com/example/MacUbuntu.git")
        result = update_checkout(runner, Path("/tmp/macubuntu"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "unofficial_remote")

    def test_check_reports_update_without_merging(self):
        runner = FakeGitRunner(local="aaa", latest="bbb")
        result = update_checkout(runner, Path("/tmp/macubuntu"), check_only=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "update_available")
        self.assertEqual(runner.local, "aaa")

    def test_update_fast_forwards_clean_official_main(self):
        runner = FakeGitRunner(local="aaa", latest="bbb")
        result = update_checkout(runner, Path("/tmp/macubuntu"), check_only=False)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "updated")
        self.assertEqual(result["current_commit"], "bbb")
        self.assertTrue(result["restart_required"])
        self.assertIn("README.md", result["changed_files"])
        self.assertEqual(result["installation"]["kind"], "checkout")

    def test_up_to_date_is_noop(self):
        runner = FakeGitRunner(local="aaa", latest="aaa")
        result = update_checkout(runner, Path("/tmp/macubuntu"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "up_to_date")
        self.assertFalse(result["updated"])

    def test_debian_install_is_classified_with_package_version(self):
        runner = FakeGitRunner(package_version="0.6.2")
        source = detect_installation_source(runner, Path("/usr/lib/macubuntu"))
        self.assertEqual(source["kind"], "deb_package")
        self.assertTrue(source["installed"])
        self.assertEqual(source["package_version"], "0.6.2")

    def test_debian_install_never_invokes_git(self):
        runner = FakeGitRunner()
        result = update_checkout(runner, Path("/usr/lib/macubuntu"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "not_git_checkout")
        self.assertEqual(result["installation"]["kind"], "deb_package")
        self.assertEqual(result["update_method"], "package_manager")
        self.assertFalse(any(command and command[0] == "git" for command in runner.commands))


if __name__ == "__main__":
    unittest.main()
