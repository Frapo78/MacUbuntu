import io
import unittest

from macubuntu_app.progress import ProgressUI


class ProgressUITests(unittest.TestCase):
    def test_italian_non_tty_progress_is_log_friendly(self):
        stream = io.StringIO()
        progress = ProgressUI("it", stream=stream, force_tty=False, width=10)
        progress({"event": "start", "index": 4, "total": 10, "module": "appearance.whitesur"})
        progress({"event": "finish", "index": 10, "total": 10, "module": "phone.integration"})
        output = stream.getvalue()
        self.assertIn("30%", output)
        self.assertIn("Vestiamo GNOME da Mac", output)
        self.assertIn("100%", output)
        self.assertIn("Ubuntu ora parla molto più fluentemente Mac", output)

    def test_english_progress_is_localized(self):
        stream = io.StringIO()
        progress = ProgressUI("en", stream=stream, force_tty=False, width=10)
        progress({"event": "start", "index": 6, "total": 10, "module": "shell.enhancements"})
        output = stream.getvalue()
        self.assertIn("50%", output)
        self.assertIn("Polishing the Shell", output)

    def test_tty_error_terminates_open_progress_line(self):
        stream = io.StringIO()
        progress = ProgressUI("en", stream=stream, force_tty=True, width=10)
        progress({"event": "start", "index": 1, "total": 10, "module": "core.gnome"})
        progress({"event": "error", "index": 1, "total": 10, "module": "core.gnome"})
        self.assertTrue(stream.getvalue().endswith("\n"))


if __name__ == "__main__":
    unittest.main()
