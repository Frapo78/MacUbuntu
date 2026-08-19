import io
import unittest
from contextlib import redirect_stdout

from macubuntu_app.util import Runner


class RunnerOutputTests(unittest.TestCase):
    def test_default_capture_keeps_subprocess_output_out_of_terminal(self):
        runner = Runner(verbose=False)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            cp = runner.run(["printf", "technical-output"], capture=None)
        self.assertEqual(cp.stdout, "technical-output")
        self.assertEqual(buffer.getvalue(), "")

    def test_explicit_detection_capture_stays_available_in_verbose_mode(self):
        runner = Runner(verbose=True)
        cp = runner.run(["printf", "probe"], capture=True)
        self.assertEqual(cp.stdout, "probe")


if __name__ == "__main__":
    unittest.main()
