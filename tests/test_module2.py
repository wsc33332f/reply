import subprocess
import sys
import unittest
from unittest.mock import patch

from autoreply import MultiError, multi, multi_args


class TestMulti(unittest.TestCase):
    def test_importing_package_does_not_preload_exponents(self):
        result = subprocess.run(
            [
                sys.executable,
                "-W",
                "error",
                "-c",
                "import sys, autoreply; "
                "assert 'autoreply.exponents' not in sys.modules",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    @patch("autoreply.multi._run_os")
    def test_multi_returns_captured_output(self, run_os):
        run_os.return_value = {
            "returncode": 0,
            "stdout": "/workspaces/reply",
            "stderr": "",
        }

        result = multi("pwd")

        self.assertEqual(
            result,
            {"returncode": 0, "stdout": "/workspaces/reply", "stderr": ""},
        )
        run_os.assert_called_once_with(
            "pwd", shell=True, timeout=30.0, cwd=None, env=None
        )

    @patch("autoreply.multi._run_os")
    def test_multi_args_runs_without_shell(self, run_os):
        run_os.return_value = {
            "returncode": 0,
            "stdout": "codespace",
            "stderr": "",
        }

        result = multi_args(["whoami"])

        self.assertEqual(
            result,
            {"returncode": 0, "stdout": "codespace", "stderr": ""},
        )
        run_os.assert_called_once_with(
            ["whoami"], shell=False, timeout=30.0, cwd=None, env=None
        )

    @patch("autoreply.multi._run_os")
    def test_multi_raises_error_on_failure(self, run_os):
        run_os.return_value = {
            "returncode": 7,
            "stdout": "",
            "stderr": "failed",
        }

        with self.assertRaises(MultiError) as raised:
            multi("bad-command")

        self.assertEqual(raised.exception.returncode, 7)
        self.assertEqual(raised.exception.stderr, "failed")


if __name__ == "__main__":
    unittest.main()