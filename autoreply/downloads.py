import os
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Callable


class DownloadError(Exception):
    """Raised when a download fails."""


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
            downloaded = 0
            try:
                with os.fdopen(fd, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress:
                            progress(downloaded, total)

                os.replace(tmp_name, dest_path)  # atomic on same filesystem
            except BaseException:
                # Clean up the partial file on any failure
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
                raise

    except urllib.error.HTTPError as e:
        raise DownloadError(f"HTTP {e.code} for {url}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise DownloadError(f"Failed to reach {url}: {e.reason}") from e
    except TimeoutError as e:
        raise DownloadError(f"Timed out downloading {url}") from e

    return {"path": str(dest_path), "size": downloaded, "url": url}

__all__ = ["download", "DownloadError"]