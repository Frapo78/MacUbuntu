import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def test_help(self):
        cp = subprocess.run([str(ROOT / "macubuntu"), "--help"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(cp.returncode, 0)
        self.assertIn("macify", cp.stdout)
        self.assertIn("uninstall", cp.stdout)

    def test_version(self):
        cp = subprocess.run([str(ROOT / "macubuntu"), "--version"], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(cp.returncode, 0)
        self.assertIn("0.1.0", cp.stdout)


if __name__ == "__main__":
    unittest.main()
