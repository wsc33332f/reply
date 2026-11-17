import subprocess
import unittest
from unittest.mock import patch

from autoreply import CommandError, command, command_args


class TestCommand(unittest.TestCase):
    @patch("autoreply.commands.subprocess.run")
    def test_returns_captured_output(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = "host-user\n"
        run.return_value.stderr = ""

        result = command("whoami")

        self.assertEqual(
            result,
            {"returncode": 0, "stdout": "host-user", "stderr": ""},
        )
        run.assert_called_once_with(
            "whoami",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30.0,
            cwd=None,
            env=None,
        )

    @patch("autoreply.commands.subprocess.run")
    def test_raises_command_error_on_nonzero_exit(self, run):
        run.return_value.returncode = 7
        run.return_value.stdout = "partial output\n"
        run.return_value.stderr = "command failed\n"

        with self.assertRaises(CommandError) as raised:
            command("whoami")

        self.assertEqual(raised.exception.command, "whoami")
        self.assertEqual(raised.exception.returncode, 7)
        self.assertEqual(raised.exception.stdout, "partial output")
        self.assertEqual(raised.exception.stderr, "command failed")

    @patch("autoreply.commands.subprocess.run")
    def test_check_false_returns_nonzero_result(self, run):
        run.return_value.returncode = 7
        run.return_value.stdout = ""
        run.return_value.stderr = "command failed"

        result = command("whoami", check=False)

        self.assertEqual(
            result,
            {"returncode": 7, "stdout": "", "stderr": "command failed"},
        )

    @patch("autoreply.commands.subprocess.run")
    def test_timeout_raises_command_error(self, run):
        run.side_effect = subprocess.TimeoutExpired("whoami", timeout=2.5)

        with self.assertRaises(CommandError) as raised:
            command("whoami", timeout=2.5)

        self.assertEqual(raised.exception.command, "whoami")
        self.assertEqual(raised.exception.returncode, -1)
        self.assertEqual(raised.exception.stdout, "")
        self.assertEqual(raised.exception.stderr, "Timed out after 2.5s")


class TestCommandArgs(unittest.TestCase):
    @patch("autoreply.commands.subprocess.run")
    def test_runs_argument_list_without_a_shell(self, run):
        run.return_value.returncode = 0
        run.return_value.stdout = "host-user\n"
        run.return_value.stderr = ""

        result = command_args(["whoami"])

        self.assertEqual(
            result,
            {"returncode": 0, "stdout": "host-user", "stderr": ""},
        )
        run.assert_called_once_with(
            ["whoami"],
            capture_output=True,
            text=True,
            timeout=30.0,
            cwd=None,
        )

    @patch("autoreply.commands.subprocess.run")
    def test_check_false_returns_nonzero_result(self, run):
        run.return_value.returncode = 2
        run.return_value.stdout = ""
        run.return_value.stderr = "not found\n"

        result = command_args(["missing-command"], check=False)

        self.assertEqual(
            result,
            {"returncode": 2, "stdout": "", "stderr": "not found"},
        )


if __name__ == "__main__":
    unittest.main()
