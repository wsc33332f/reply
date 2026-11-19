import io
import json
import sys
import unittest
import urllib.error
from contextlib import redirect_stdout
from unittest.mock import patch

from autoreply import ExponentError
from autoreply import exponents
from autoreply.exponents import (
    ExponentTerm,
    compute_exponents,
    read_coeff_map,
    read_power_series,
    sync_exponents,
)


class TestReadPowerSeries(unittest.TestCase):
    @patch("autoreply.exponents.urllib.request.urlopen")
    def test_reads_json_and_applies_headers_and_timeout(self, urlopen):
        response = io.BytesIO(b'{"base": 2}')
        response.status = 200
        urlopen.return_value.__enter__.return_value = response

        result = read_power_series(
            "https://example.com/series",
            headers={"User-Agent": "test-client"},
            timeout=3.0,
        )

        self.assertEqual(result, {"base": 2})
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), "test-client")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 3.0)

    @patch("autoreply.exponents.urllib.request.urlopen")
    def test_rejects_non_http_urls(self, urlopen):
        with self.assertRaisesRegex(ValueError, "Only http"):
            read_power_series("file:///tmp/series")

        urlopen.assert_not_called()

    @patch("autoreply.exponents.urllib.request.urlopen")
    def test_rejects_input_over_max_bytes(self, urlopen):
        response = io.BytesIO(b'{"base": 2}')
        response.status = 200
        urlopen.return_value.__enter__.return_value = response

        with self.assertRaisesRegex(ExponentError, "exceeds 4 bytes"):
            read_power_series("https://example.com/series", max_bytes=4)

    @patch("autoreply.exponents.urllib.request.urlopen")
    def test_translates_http_errors(self, urlopen):
        http_error = urllib.error.HTTPError(
            "https://example.com/series", 404, "Not Found", {}, io.BytesIO()
        )
        urlopen.side_effect = http_error

        with self.assertRaisesRegex(ExponentError, "HTTP 404"):
            read_power_series("https://example.com/series")
        http_error.close()


class TestSyncAndCoefficients(unittest.TestCase):
    @patch("autoreply.exponents.urllib.request.urlopen")
    def test_sync_posts_json_and_parses_json_response(self, urlopen):
        response = io.BytesIO(b'{"saved": true}')
        response.status = 201
        urlopen.return_value.__enter__.return_value = response
        term = ExponentTerm("example", True, False, output=7)

        result = sync_exponents(
            "https://example.com/results",
            {"example": term},
            headers={"X-Test": "yes"},
        )

        self.assertEqual(result, {"saved": True})
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(request.get_header("X-test"), "yes")
        self.assertEqual(
            json.loads(request.data),
            {
                "example": {
                    "name": "example",
                    "safe": True,
                    "ran": False,
                    "error": None,
                    "output": 7,
                }
            },
        )

    @patch("autoreply.exponents.read_power_series", return_value={"a": 1})
    def test_read_coeff_map_checks_required_keys(self, read_series):
        result = read_coeff_map("https://example.com/series", required_keys={"a"})

        self.assertEqual(result, {"a": 1})
        read_series.assert_called_once_with("https://example.com/series")

    @patch("autoreply.exponents.read_power_series", return_value={"a": 1})
    def test_read_coeff_map_reports_missing_keys(self, read_series):
        with self.assertRaisesRegex(ExponentError, "Missing required keys"):
            read_coeff_map("https://example.com/series", required_keys={"a", "b"})
        read_series.assert_called_once_with("https://example.com/series")

    @patch("autoreply.exponents.read_power_series", return_value=[1, 2])
    def test_read_coeff_map_requires_mapping(self, read_series):
        with self.assertRaisesRegex(ExponentError, "Expected mapping/dict"):
            read_coeff_map("https://example.com/series")
        read_series.assert_called_once_with("https://example.com/series")


class TestComputeExponents(unittest.TestCase):
    @patch("autoreply.exponents._sleep_with_jitter")
    @patch("autoreply.exponents.sync_exponents", return_value={"ok": True})
    @patch("autoreply.exponents.read_power_series", return_value={"output": 256})
    def test_compute_includes_custom_series_and_boundary_metadata(
        self, read_series, sync, sleep
    ):
        results = compute_exponents(
            include_equal=True,
            result_url="https://example.com/results",
        )

        self.assertIn("base_series", results)
        self.assertIn("custom_series", results)
        self.assertTrue({"pickle", "expr", "block"}.issubset(results))
        self.assertEqual(results["json"].parsed["value"], 256)
        self.assertEqual(results["custom_series"].output, 256)
        self.assertFalse(results["pickle"].safe)
        self.assertFalse(results["pickle"].ran)
        self.assertEqual(read_series.call_count, 2)
        sync.assert_called_once_with("https://example.com/results", results)
        sleep.assert_called_once_with()

    @patch.object(exponents, "compute_exponents")
    def test_cli_passes_requested_options(self, compute):
        with redirect_stdout(io.StringIO()):
            with patch.object(
                sys,
                "argv",
                ["autoreply.exponents", "--equal", "--result", "https://example.com/r"],
            ):
                exponents.main()

        compute.assert_called_once_with(
            include_equal=True,
            result_url="https://example.com/r",
        )
