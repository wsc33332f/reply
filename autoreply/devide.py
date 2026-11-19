import os
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Callable


class DevideError(Exception):
    """Raised when a file transfer fails."""

DownloadError = DevideError


def download(
    url: str,
    dest: str,
    *,
    timeout: float = 30.0,
    overwrite: bool = False,
    chunk_size: int = 64 * 1024,
    progress: Optional[Callable[[int, Optional[int]], None]] = None,
    headers: Optional[dict] = None,
) -> dict:
    dest_path = Path(dest).expanduser()

    if dest_path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {dest_path}")

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    req = urllib.request.Request(url, headers=headers or {})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            total = resp.headers.get("Content-Length")
            total = int(total) if total and total.isdigit() else None

            # Write to a temp file in the same dir, then atomically rename.
            fd, tmp_name = tempfile.mkstemp(
                prefix=dest_path.name + ".", suffix=".part", dir=dest_path.parent
            )
            devided = 0
            try:
                with os.fdopen(fd, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        devided += len(chunk)
                        if progress:
                            progress(devided, total)

                os.replace(tmp_name, dest_path)  # atomic on same filesystem
            except BaseException:
                # Clean up the partial file on any failure
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
                raise

    except urllib.error.HTTPError as e:
        raise DevideError(f"HTTP {e.code} for {url}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise DevideError(f"Failed to reach {url}: {e.reason}") from e
    except TimeoutError as e:
        raise DevideError(f"Timed out downloading {url}") from e

    return {"path": str(dest_path), "size": devided, "url": url}


def upload(
    url: str,
    source: str,
    *,
    timeout: float = 30.0,
    method: str = "POST",
    content_type: str = "application/octet-stream",
    headers: Optional[dict] = None,
) -> dict:
    """Send a local file as the HTTP request body and return transfer metadata."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("Only http(s) URLs are supported for uploads")

    source_path = Path(source).expanduser()
    size = source_path.stat().st_size
    request_headers = {
        "Content-Type": content_type,
        "Content-Length": str(size),
    }
    if headers:
        request_headers.update(headers)

    try:
        with source_path.open("rb") as source_file:
            req = urllib.request.Request(
                url,
                data=source_file,
                headers=request_headers,
                method=method,
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, "status", 200)
                if not 200 <= status < 300:
                    raise DevideError(f"HTTP {status} when uploading to {url}")
    except urllib.error.HTTPError as e:
        raise DevideError(f"HTTP {e.code} when uploading to {url}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise DevideError(f"Failed to reach {url}: {e.reason}") from e
    except TimeoutError as e:
        raise DevideError(f"Timed out uploading to {url}") from e

    return {
        "path": str(source_path),
        "size": size,
        "url": url,
        "status": status,
    }


def main(argv: Optional[list] = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Download or upload a file over HTTP")
    transfer = parser.add_mutually_exclusive_group(required=True)
    transfer.add_argument("--download", metavar="URL")
    transfer.add_argument("--upload", metavar="URL")
    parser.add_argument("--output", metavar="PATH", help="destination path for downloads")
    parser.add_argument("--file", metavar="PATH", help="local file to upload")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing download")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)

    try:
        if args.download:
            if args.file:
                parser.error("--file can only be used with --upload")
            if not args.output:
                parser.error("--output is required with --download")
            result = download(
                args.download,
                args.output,
                timeout=args.timeout,
                overwrite=args.overwrite,
            )
        else:
            if args.output:
                parser.error("--output can only be used with --download")
            if args.overwrite:
                parser.error("--overwrite can only be used with --download")
            if not args.file:
                parser.error("--file is required with --upload")
            result = upload(args.upload, args.file, timeout=args.timeout)
    except (DevideError, OSError, ValueError) as exc:
        parser.error(str(exc))

    print(result)


devide = download

if __name__ == "__main__":
    main()


__all__ = ["download", "upload", "devide", "DownloadError", "DevideError", "main"]
