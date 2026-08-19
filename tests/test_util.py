import unittest

from macubuntu_app.util import CommandError, Runner


class RunnerTests(unittest.TestCase):
    MISSING = "__macubuntu_definitely_missing_executable__"

    def test_missing_executable_is_returned_as_127_when_not_checked(self):
        cp = Runner().run([self.MISSING], check=False)
        self.assertEqual(cp.returncode, 127)
        self.assertTrue(cp.stderr)

    def test_missing_executable_raises_predictable_command_error(self):
        with self.assertRaises(CommandError) as ctx:
            Runner().run([self.MISSING])
        self.assertEqual(ctx.exception.returncode, 127)
        self.assertEqual(ctx.exception.args_list, [self.MISSING])


if __name__ == "__main__":
    unittest.main()
