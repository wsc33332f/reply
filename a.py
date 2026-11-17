import my_library

# Basic
info = my_library.download("https://example.com/file.zip", "downloads/file.zip")
print(info)  # {'path': 'downloads/file.zip', 'size': 12345, 'url': '...'}

# Overwrite if it exists
my_library.download("https://example.com/file.zip", "file.zip", overwrite=True)

# With progress
def show(done, total):
    if total:
        print(f"{done}/{total} ({done*100//total}%)")
    else:
        print(f"{done} bytes")

my_library.download("https://example.com/big.iso", "big.iso", progress=show)

# Custom headers
my_library.download(
    "https://example.com/api/data",
    "data.json",
    headers={"User-Agent": "my-library/0.1"},
)