from pathlib import Path
from tempfile import TemporaryDirectory

from autoreply import download


def show_progress(downloaded: int, total: int | None) -> None:
    if total:
        print(f"Downloaded {downloaded}/{total} bytes")
    else:
        print(f"Downloaded {downloaded} bytes")


def main() -> None:
    url = "https://example.com/"
    with TemporaryDirectory(prefix="autoreply-download-") as temp_dir:
        destination = Path(temp_dir) / "example.html"
        result = download(url, str(destination), progress=show_progress)

        if destination.stat().st_size != result["size"]:
            raise RuntimeError("Downloaded file size does not match the result")
        print(f"Download succeeded: {result}")


if __name__ == "__main__":
    main()
