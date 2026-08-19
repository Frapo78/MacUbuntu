import tempfile
import unittest
from pathlib import Path

from macubuntu_app.locking import AppLock, LockBusyError


class LockingTests(unittest.TestCase):
    def test_second_mutation_is_rejected_while_lock_is_held(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "macubuntu.lock"
            with AppLock(command="apply", path=path):
                with self.assertRaises(LockBusyError) as ctx:
                    with AppLock(command="uninstall", path=path):
                        pass
                self.assertEqual(ctx.exception.holder.get("command"), "apply")
                self.assertIsInstance(ctx.exception.holder.get("pid"), int)

    def test_lock_can_be_acquired_again_after_release(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "macubuntu.lock"
            with AppLock(command="apply", path=path):
                pass
            with AppLock(command="update", path=path):
                pass


if __name__ == "__main__":
    unittest.main()
