# autoreply


`autoreply` is a small Python package for studying basic library design and
common Python tasks:

- arithmetic helpers

## Requirements

- Python 3.9 or newer


Install the package from the repository root:

```bash
python -m pip install .
```


## Public API

The package exports these helpers:

```python
import autoreply

autoreply.add(2, 3)
autoreply.subtract(7, 4)

```


```python
import autoreply

print(autoreply.add(2, 3))       # 5
print(autoreply.subtract(7, 4))  # 3
```

## File transfer CLI

Download a URL to a local path:

```bash
python3 -m autoreply.devide --download https://example.com/file.bin --output file.bin
```

Upload a local file to a URL:

```bash
python3 -m autoreply.devide --upload https://example.com/upload --file file.bin
```

Downloads refuse to overwrite an existing file unless `--overwrite` is given.
Uploads send the file as the raw request body using HTTP POST.


Run the unit tests:

```bash
python -m unittest discover -s tests -v
```
