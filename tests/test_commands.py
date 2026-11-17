import unittest
from subprocess import PIPE
from unittest.mock import patch

from autoreply import call


class TestCall(unittest.TestCase):
    @patch("autoreply.commands.subprocess.run")
    def test_whoami_returns_command_output(self, run):
        run.return_value.stdout = "host-user\n"

        self.assertEqual(call("whoami"), "host-user")
        run.assert_called_once_with(
            ["whoami"],
            check=True,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
        )

    @patch("autoreply.commands.subprocess.run")
    def test_rejects_other_commands(self, run):
        with self.assertRaises(ValueError):
            call("whoami; echo unsafe")

        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
