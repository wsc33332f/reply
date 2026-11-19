import subprocess
import sys
import unittest
from importlib import import_module
from unittest.mock import patch

from autoreply import MultiError, multi, multi_args

multi_module = import_module("autoreply.multi")


class TestMulti(unittest.TestCase):
    def test_importing_package_does_not_preload_exponents(self):
        result = subprocess.run(
            [
                sys.executable,
                "-W",
                "error",
                "-c",
                "import sys, autoreply; "
                "assert 'autoreply.exponents' not in sys.modules; "
                "assert 'autoreply.devide' not in sys.modules",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    @patch.object(multi_module, "_x1")
    def test_multi_returns_captured_output(self, execute):
        execute.return_value = {
            "code": 0,
            "out": "/workspaces/reply",
            "err": "",
        }

        result = multi("pwd")

        self.assertEqual(
            result,
            {"code": 0, "out": "/workspaces/reply", "err": ""},
        )
        execute.assert_called_once_with(
            "pwd", _p1=True, _p2=30.0, _p3=None, _p4=None
        )

    @patch.object(multi_module, "_x1")
    def test_multi_args_passes_argument_list(self, execute):
        execute.return_value = {
            "code": 0,
            "out": "codespace",
            "err": "",
        }

        result = multi_args(["whoami"])

        self.assertEqual(
            result,
            {"code": 0, "out": "codespace", "err": ""},
        )
        execute.assert_called_once_with(
            ["whoami"], _p1=False, _p2=30.0, _p3=None, _p4=None
        )

    @patch.object(multi_module, "_x1")
    def test_multi_raises_error_on_failure(self, execute):
        execute.return_value = {
            "code": 7,
            "out": "",
            "err": "failed",
        }

        with self.assertRaises(MultiError) as raised:
            multi("bad-command")

        self.assertEqual(raised.exception.status_code, 7)
        self.assertEqual(raised.exception.err_buffer, "failed")


if __name__ == "__main__":
    unittest.main()