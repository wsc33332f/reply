from pathlib import Path
from tempfile import TemporaryDirectory

from autoreply import DownloadError, download


def show_progress(downloaded: int, total: int | None) -> None:
    if total:
        print(f"{downloaded}/{total} bytes ({downloaded * 100 // total}%)")
    else:
        print(f"{downloaded} bytes")


def main() -> None:
    with TemporaryDirectory(prefix="autoreply-example-") as temp_dir:
        directory = Path(temp_dir)
        try:
            basic = download(
                "https://example.com/file.zip",
                str(directory / "file.zip"),
            )
            print(basic)

            replacement = download(
                "https://example.com/file.zip",
                str(directory / "file.zip"),
                overwrite=True,
            )
            print(replacement)

            download(
                "https://example.com/big.iso",
                str(directory / "big.iso"),
                progress=show_progress,
            )
            download(
                "https://example.com/api/data",
                str(directory / "data.json"),
                headers={"User-Agent": "my-library/0.1"},
            )
        except (DownloadError, FileExistsError) as exc:
            raise RuntimeError(f"Download failed: {exc}") from exc


if __name__ == "__main__":
    main()