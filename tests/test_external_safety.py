import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from macubuntu_app.external import (
    ExternalOperationError,
    _safe_extract,
    _validate_download_url,
    apply_managed_text_file,
    apply_pinned_download,
    uninstall_external_operation,
)
from macubuntu_app.state import StateStore, default_state
from macubuntu_app.util import Runner


class ExternalSafetyTests(unittest.TestCase):
    @staticmethod
    def _symlink_info(name: str) -> zipfile.ZipInfo:
        info = zipfile.ZipInfo(name)
        info.create_system = 3
        info.external_attr = 0o120777 << 16
        return info

    def test_download_source_allowlist_rejects_http_and_unknown_hosts(self):
        with self.assertRaises(ExternalOperationError):
            _validate_download_url("http://github.com/example/example.zip")
        with self.assertRaises(ExternalOperationError):
            _validate_download_url("https://example.invalid/example.zip")
        _validate_download_url("https://github.com/example/example/archive/deadbeef.zip")
        _validate_download_url("https://raw.githubusercontent.com/example/example/deadbeef/file")

    def test_zip_slip_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../escape", "bad")
            with self.assertRaises(ExternalOperationError):
                _safe_extract(archive, root / "out", resource="test")

    def test_internal_relative_symlink_is_preserved(self):
        """Models the relative SVG symlinks used by the pinned WhiteSur source."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "safe-symlink.zip"
            prefix = "WhiteSur-gtk-theme-test/src/assets/gtk/scalable"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(f"{prefix}/checkbox-mixed-symbolic.svg", "safe-svg")
                zf.writestr(
                    self._symlink_info(f"{prefix}/radio-mixed-symbolic.svg"),
                    "checkbox-mixed-symbolic.svg",
                )
            out = root / "out"
            _safe_extract(archive, out, resource="whitesur-gtk")
            link = out / prefix / "radio-mixed-symbolic.svg"
            self.assertTrue(link.is_symlink())
            self.assertEqual(link.read_text(encoding="utf-8"), "safe-svg")

    def test_symlink_target_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "escape-symlink.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(self._symlink_info("root/link"), "../../outside")
            with self.assertRaises(ExternalOperationError):
                _safe_extract(archive, root / "out", resource="test")

    def test_absolute_symlink_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "absolute-symlink.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(self._symlink_info("root/link"), "/etc/passwd")
            with self.assertRaises(ExternalOperationError):
                _safe_extract(archive, root / "out", resource="test")

    def test_member_below_archive_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "symlink-parent.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("root/inside/placeholder", "ok")
                zf.writestr(self._symlink_info("root/linkdir"), "inside")
                zf.writestr("root/linkdir/payload", "must-not-write-through-link")
            with self.assertRaises(ExternalOperationError):
                _safe_extract(archive, root / "out", resource="test")

    def test_special_archive_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            archive = root / "special.zip"
            fifo = zipfile.ZipInfo("root/fifo")
            fifo.create_system = 3
            fifo.external_attr = 0o010644 << 16
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr(fifo, "")
            with self.assertRaises(ExternalOperationError):
                _safe_extract(archive, root / "out", resource="test")

    def test_managed_file_never_overwrites_preexisting_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "existing.desktop"
            path.write_text("user-data", encoding="utf-8")
            store = StateStore(root / "state.json")
            state = default_state()
            result = apply_managed_text_file(store=store, state=state, app_version="test", resource="managed-test", path=path, content="macubuntu", dry_run=False)
            self.assertEqual(result["status"], "skipped")
            self.assertEqual(path.read_text(encoding="utf-8"), "user-data")
            self.assertEqual(state["operations"], [])

    def test_pinned_download_checks_git_blob_integrity_and_is_reversible(self):
        payload = b"MacUbuntu-test-payload"
        git_sha = hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); destination = root / "wallpaper.jpg"; store = StateStore(root / "state.json"); state = default_state()
            def fake_download(url, target, *, resource): target.write_bytes(payload)
            with patch("macubuntu_app.external_assets._download", fake_download):
                result = apply_pinned_download(store=store, state=state, app_version="test", resource="wallpaper", url="https://raw.githubusercontent.com/example/repo/deadbeef/file.jpg", destination=destination, expected_git_blob_sha1=git_sha, dry_run=False)
            self.assertEqual(result["status"], "installed")
            self.assertTrue(destination.exists())
            self.assertEqual(len(state["operations"]), 1)
            removed = uninstall_external_operation(op=state["operations"][0], runner=Runner(), store=store, state=state, app_version="test", force=False, dry_run=False)
            self.assertEqual(removed["status"], "removed")
            self.assertFalse(destination.exists())

    def test_managed_file_repair_updates_receipt_instead_of_duplicating_it(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); path = root / "managed.desktop"; store = StateStore(root / "state.json"); state = default_state()
            first = apply_managed_text_file(store=store, state=state, app_version="test", resource="managed-test", path=path, content="macubuntu", dry_run=False)
            self.assertEqual(first["status"], "installed")
            self.assertEqual(len(state["operations"]), 1)
            path.unlink()
            second = apply_managed_text_file(store=store, state=state, app_version="test", resource="managed-test", path=path, content="macubuntu", dry_run=False)
            self.assertEqual(second["status"], "installed")
            self.assertEqual(len(state["operations"]), 1)

    def test_pinned_download_reports_drift_instead_of_overwriting(self):
        payload = b"MacUbuntu-test-payload"
        git_sha = hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); destination = root / "wallpaper.jpg"; store = StateStore(root / "state.json"); state = default_state()
            def fake_download(url, target, *, resource): target.write_bytes(payload)
            with patch("macubuntu_app.external_assets._download", fake_download):
                apply_pinned_download(store=store, state=state, app_version="test", resource="wallpaper", url="https://raw.githubusercontent.com/example/repo/deadbeef/file.jpg", destination=destination, expected_git_blob_sha1=git_sha, dry_run=False)
            destination.write_bytes(b"user-edited")
            with patch("macubuntu_app.external_assets._download", fake_download):
                result = apply_pinned_download(store=store, state=state, app_version="test", resource="wallpaper", url="https://raw.githubusercontent.com/example/repo/deadbeef/file.jpg", destination=destination, expected_git_blob_sha1=git_sha, dry_run=False)
            self.assertEqual(result["status"], "kept")
            self.assertEqual(result["reason"], "drift_detected")
            self.assertEqual(destination.read_bytes(), b"user-edited")

    def test_pinned_download_removes_partial_file_on_integrity_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); destination = root / "bad.jpg"; store = StateStore(root / "state.json"); state = default_state()
            def fake_download(url, target, *, resource): target.write_bytes(b"wrong")
            with patch("macubuntu_app.external_assets._download", fake_download):
                with self.assertRaises(ExternalOperationError):
                    apply_pinned_download(store=store, state=state, app_version="test", resource="wallpaper", url="https://raw.githubusercontent.com/example/repo/deadbeef/file.jpg", destination=destination, expected_git_blob_sha1="0" * 40, dry_run=False)
            self.assertFalse(destination.exists())
            self.assertEqual(state["operations"], [])


if __name__ == "__main__":
    unittest.main()
