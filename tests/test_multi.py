import os
import tempfile
import unittest

from autoreply import MultiError, multi, multi_args


class TestMultiProcess(unittest.TestCase):
    def test_multi_success_and_ctx_vars(self):
        res = multi(
            "printf '%s' \"$GREETING_VAL\"",
            ctx_vars={"GREETING_VAL": "hello-from-ctx"},
        )
        self.assertEqual(res["code"], 0)
        self.assertEqual(res["out"], "hello-from-ctx")
        self.assertEqual(res["err"], "")

    def test_multi_work_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            res = multi("pwd", work_dir=tmpdir)
            self.assertEqual(res["code"], 0)
            self.assertEqual(os.path.realpath(res["out"]), os.path.realpath(tmpdir))

    def test_multi_args_success(self):
        res = multi_args(["echo", "arg-test"])
        self.assertEqual(res["code"], 0)
        self.assertEqual(res["out"], "arg-test")

    def test_strict_raises_multi_error_on_nonzero_exit(self):
        with self.assertRaises(MultiError) as ctx:
            multi("echo boom >&2; exit 7", strict=True)
        self.assertEqual(ctx.exception.status_code, 7)
        self.assertIn("boom", ctx.exception.err_buffer)

    def test_non_strict_returns_nonzero_code(self):
        res = multi("exit 3", strict=False)
        self.assertEqual(res["code"], 3)

    def test_timeout_kills_process_and_raises(self):
        with self.assertRaises(MultiError) as ctx:
            multi("sleep 5", limit_sec=0.1)
        self.assertEqual(ctx.exception.status_code, -1)
        self.assertIn("limit", ctx.exception.err_buffer)

    def test_missing_binary_raises_nonzero_multi_error(self):
        with self.assertRaises(MultiError) as ctx:
            multi_args(["definitely_nonexistent_binary_xyz_123"])
        self.assertEqual(ctx.exception.status_code, 127)


if __name__ == "__main__":
    unittest.main(verbosity=2)