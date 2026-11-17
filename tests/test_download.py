import io
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from autoreply import DownloadError, download


class TestDownload(unittest.TestCase):
    @patch("autoreply.downloads.urllib.request.urlopen")
    def test_downloads_in_chunks_and_reports_progress(self, urlopen):
        response = io.BytesIO(b"downloaded content")
        response.headers = {"Content-Length": "18"}
        urlopen.return_value.__enter__.return_value = response
        progress = []

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "nested" / "file.bin"
            result = download(
                "https://example.com/file.bin",
                str(dest),
                chunk_size=5,
                progress=lambda downloaded, total: progress.append(
                    (downloaded, total)
                ),
                headers={"User-Agent": "test-client"},
            )

            self.assertEqual(dest.read_bytes(), b"downloaded content")
            self.assertEqual(
                result,
                {
                    "path": str(dest),
                    "size": 18,
                    "url": "https://example.com/file.bin",
                },
            )
            self.assertEqual(progress, [(5, 18), (10, 18), (15, 18), (18, 18)])

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.com/file.bin")
        self.assertEqual(request.get_header("User-agent"), "test-client")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 30.0)

    @patch("autoreply.downloads.urllib.request.urlopen")
    def test_downloads_when_content_length_is_unknown(self, urlopen):
        response = io.BytesIO(b"data")
        response.headers = {}
        urlopen.return_value.__enter__.return_value = response
        progress = []

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "file.bin"
            download(
                "https://example.com/file.bin",
                str(dest),
                progress=lambda downloaded, total: progress.append(
                    (downloaded, total)
                ),
            )

            self.assertEqual(dest.read_bytes(), b"data")
            self.assertEqual(progress, [(4, None)])

    @patch("autoreply.downloads.urllib.request.urlopen")
    def test_refuses_to_overwrite_existing_file(self, urlopen):
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "file.bin"
            dest.write_bytes(b"original")

            with self.assertRaises(FileExistsError):
                download("https://example.com/file.bin", str(dest))

            self.assertEqual(dest.read_bytes(), b"original")
            urlopen.assert_not_called()

    @patch("autoreply.downloads.urllib.request.urlopen")
    def test_overwrites_existing_file_when_requested(self, urlopen):
        response = io.BytesIO(b"replacement")
        response.headers = {"Content-Length": "11"}
        urlopen.return_value.__enter__.return_value = response

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "file.bin"
            dest.write_bytes(b"original")

            result = download(
                "https://example.com/file.bin",
                str(dest),
                overwrite=True,
            )

            self.assertEqual(dest.read_bytes(), b"replacement")
            self.assertEqual(result["size"], 11)

    @patch("autoreply.downloads.urllib.request.urlopen")
    def test_translates_http_error(self, urlopen):
        urlopen.side_effect = urllib.error.HTTPError(
            "https://example.com/file.bin", 404, "Not Found", {}, None
        )

        with self.assertRaisesRegex(DownloadError, "HTTP 404"):
            download("https://example.com/file.bin", "unused.bin")

    @patch("autoreply.downloads.urllib.request.urlopen")
    def test_translates_url_error(self, urlopen):
        urlopen.side_effect = urllib.error.URLError("connection failed")

        with self.assertRaisesRegex(DownloadError, "Failed to reach"):
            download("https://example.com/file.bin", "unused.bin")

    @patch("autoreply.downloads.urllib.request.urlopen")
    def test_translates_timeout(self, urlopen):
        urlopen.side_effect = TimeoutError

        with self.assertRaisesRegex(DownloadError, "Timed out downloading"):
            download("https://example.com/file.bin", "unused.bin")

    @patch("autoreply.downloads.urllib.request.urlopen")
    def test_removes_partial_file_if_progress_callback_fails(self, urlopen):
        response = io.BytesIO(b"some content")
        response.headers = {"Content-Length": "12"}
        urlopen.return_value.__enter__.return_value = response

        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "file.bin"

            def fail_progress(downloaded, total):
                raise RuntimeError(f"progress failed: {downloaded}/{total}")

            with self.assertRaisesRegex(RuntimeError, "progress failed"):
                download(
                    "https://example.com/file.bin",
                    str(dest),
                    progress=fail_progress,
                )

            self.assertFalse(dest.exists())
            self.assertEqual(list(Path(temp_dir).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
