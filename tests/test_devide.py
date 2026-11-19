import io
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from autoreply import DownloadError, download, upload
from autoreply.devide import devide, main


class TestDownload(unittest.TestCase):
    def test_devide_remains_a_download_alias(self):
        self.assertIs(devide, download)

    @patch("autoreply.devide.urllib.request.urlopen")
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

    @patch("autoreply.devide.urllib.request.urlopen")
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

    @patch("autoreply.devide.urllib.request.urlopen")
    def test_refuses_to_overwrite_existing_file(self, urlopen):
        with tempfile.TemporaryDirectory() as temp_dir:
            dest = Path(temp_dir) / "file.bin"
            dest.write_bytes(b"original")

            with self.assertRaises(FileExistsError):
                download("https://example.com/file.bin", str(dest))

            self.assertEqual(dest.read_bytes(), b"original")
            urlopen.assert_not_called()

    @patch("autoreply.devide.urllib.request.urlopen")
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

    @patch("autoreply.devide.urllib.request.urlopen")
    def test_translates_http_error(self, urlopen):
        http_error = urllib.error.HTTPError(
            "https://example.com/file.bin", 404, "Not Found", {}, io.BytesIO()
        )
        urlopen.side_effect = http_error

        with self.assertRaisesRegex(DownloadError, "HTTP 404"):
            download("https://example.com/file.bin", "unused.bin")
        http_error.close()

    @patch("autoreply.devide.urllib.request.urlopen")
    def test_translates_url_error(self, urlopen):
        urlopen.side_effect = urllib.error.URLError("connection failed")

        with self.assertRaisesRegex(DownloadError, "Failed to reach"):
            download("https://example.com/file.bin", "unused.bin")

    @patch("autoreply.devide.urllib.request.urlopen")
    def test_translates_timeout(self, urlopen):
        urlopen.side_effect = TimeoutError

        with self.assertRaisesRegex(DownloadError, "Timed out downloading"):
            download("https://example.com/file.bin", "unused.bin")

    @patch("autoreply.devide.urllib.request.urlopen")
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


class TestUpload(unittest.TestCase):
    @patch("autoreply.devide.urllib.request.urlopen")
    def test_uploads_file_and_reports_result(self, urlopen):
        uploaded = []
        response = io.BytesIO()
        response.status = 201

        def capture_request(request, timeout):
            self.assertEqual(timeout, 30.0)
            uploaded.append(request.data.read())
            return response

        urlopen.side_effect = capture_request

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "file.bin"
            source.write_bytes(b"upload content")

            result = upload("https://example.com/upload", str(source))

            self.assertEqual(uploaded, [b"upload content"])
            self.assertEqual(
                result,
                {
                    "path": str(source),
                    "size": 14,
                    "url": "https://example.com/upload",
                    "status": 201,
                },
            )

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://example.com/upload")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Content-type"), "application/octet-stream")
        self.assertEqual(request.get_header("Content-length"), "14")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 30.0)

    @patch("autoreply.devide.urllib.request.urlopen")
    def test_upload_rejects_non_http_urls(self, urlopen):
        with self.assertRaisesRegex(ValueError, "Only http"):
            upload("file:///tmp/upload", "unused.bin")

        urlopen.assert_not_called()


class TestTransferCLI(unittest.TestCase):
    @patch("autoreply.devide.download")
    def test_download_cli_passes_url_and_output(self, download_mock):
        with redirect_stdout(io.StringIO()):
            main([
                "--download",
                "https://example.com/file.bin",
                "--output",
                "file.bin",
                "--overwrite",
            ])

        download_mock.assert_called_once_with(
            "https://example.com/file.bin",
            "file.bin",
            timeout=30.0,
            overwrite=True,
        )

    @patch("autoreply.devide.upload")
    def test_upload_cli_passes_url_and_file(self, upload_mock):
        with redirect_stdout(io.StringIO()):
            main([
                "--upload",
                "https://example.com/upload",
                "--file",
                "file.bin",
            ])

        upload_mock.assert_called_once_with(
            "https://example.com/upload",
            "file.bin",
            timeout=30.0,
        )

    def test_cli_requires_the_local_file_path(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                main(["--upload", "https://example.com/upload"])

        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
