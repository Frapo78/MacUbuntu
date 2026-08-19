import io
import time
import unittest

from macubuntu_app.progress import ProgressUI


class ProgressUITests(unittest.TestCase):
    def test_italian_non_tty_progress_and_success_are_log_friendly(self):
        stream = io.StringIO()
        progress = ProgressUI("it", stream=stream, force_tty=False, width=10)
        progress({"event": "start", "index": 4, "total": 10, "module": "appearance.mactahoe"})
        progress({"event": "finish", "index": 10, "total": 10, "module": "phone.integration"})
        progress({"event": "complete", "index": 10, "total": 10, "module": "complete"})
        output = stream.getvalue()
        self.assertIn("30%", output)
        self.assertIn("Tahoe", output)
        self.assertIn("100%", output)
        self.assertIn("Goditi il tuo nuovo MacUbuntu!", output)

    def test_english_progress_is_localized(self):
        stream = io.StringIO()
        progress = ProgressUI("en", stream=stream, force_tty=False, width=10)
        progress({"event": "start", "index": 6, "total": 10, "module": "shell.enhancements"})
        progress({"event": "complete", "index": 10, "total": 10, "module": "complete"})
        output = stream.getvalue()
        self.assertIn("50%", output)
        self.assertIn("Polishing the Shell", output)
        self.assertIn("Enjoy your new MacUbuntu!", output)

    def test_tty_progress_animates_without_faking_percent(self):
        stream = io.StringIO()
        progress = ProgressUI(
            "it",
            stream=stream,
            force_tty=True,
            width=10,
            interval=0.01,
        )
        progress({"event": "start", "index": 4, "total": 10, "module": "appearance.mactahoe"})
        time.sleep(0.05)
        progress({"event": "error", "index": 4, "total": 10, "module": "appearance.mactahoe"})
        output = stream.getvalue()
        self.assertGreaterEqual(output.count("\r"), 2)
        self.assertIn("30%", output)
        self.assertIn("▓", output)
        self.assertNotIn("31%", output)

    def test_tty_error_terminates_open_progress_line(self):
        stream = io.StringIO()
        progress = ProgressUI("en", stream=stream, force_tty=True, width=10, interval=0.01)
        progress({"event": "start", "index": 1, "total": 10, "module": "core.gnome"})
        time.sleep(0.02)
        progress({"event": "error", "index": 1, "total": 10, "module": "core.gnome"})
        self.assertTrue(stream.getvalue().endswith("\n"))


if __name__ == "__main__":
    unittest.main()
