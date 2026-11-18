# autoreply

This just serve for studying, We are not responsible if you use it for illegal purposes

`autoreply` is a small Python package for studying basic library design and
common Python tasks:

- arithmetic helpers
- shell and argument-list command execution
- HTTP file downloads
- JSON and YAML deserialization
- opt-in unsafe deserialization and dynamic code-execution demonstrations

## Requirements

- Python 3.9 or newer
- PyYAML is optional and enables YAML examples

Install the package from the repository root:

```bash
python -m pip install .
```

Optional YAML support:

```bash
python -m pip install PyYAML
```

## Public API

The package exports these helpers:

```python
import autoreply

autoreply.add(2, 3)
autoreply.subtract(7, 4)
autoreply.command(...)
autoreply.command_args([...])
autoreply.download(...)
autoreply.query_data(...)
autoreply.query_dict(...)
autoreply.run_demo(...)
```

The package also exports `CommandError`, `DownloadError`, `FetchError`, and
`DemoResult`.

## Math helpers

```python
import autoreply

print(autoreply.add(2, 3))       # 5
print(autoreply.subtract(7, 4))  # 3
```

## Running commands

Use `command()` for a trusted shell command string:

```python
result = autoreply.command("whoami")
print(result["stdout"])
print(result["returncode"])
print(result["stderr"])
```

Use `command_args()` for an argument list without invoking a shell:

```python
result = autoreply.command_args(["whoami"])
print(result["stdout"])
```

Both functions return:

```python
{
    "returncode": 0,
    "stdout": "...",
    "stderr": "...",
}
```

By default, a nonzero exit code raises `autoreply.CommandError`. Use
`check=False` to receive the result instead. Commands support `timeout` and
`cwd`; `command()` also supports an environment override.

```python
result = autoreply.command(
    "whoami",
    timeout=10,
    cwd="/tmp",
    env={"EXAMPLE": "value"},
)
```

`command()` uses a shell and therefore accepts shell syntax. Only pass trusted
command strings. Prefer `command_args()` for untrusted arguments.

## Downloading files

```python
info = autoreply.download(
    "https://example.com/archive.zip",
    "downloads/archive.zip",
)

print(info)
# {"path": "downloads/archive.zip", "size": 12345, "url": "..."}
```

An existing destination is not overwritten by default:

```python
autoreply.download(
    "https://example.com/archive.zip",
    "downloads/archive.zip",
    overwrite=True,
    timeout=60,
    headers={"User-Agent": "my-library/0.1"},
)
```

Track progress with a callback:

```python
def show_progress(downloaded, total):
    if total is None:
        print(f"{downloaded} bytes downloaded")
    else:
        print(f"{downloaded}/{total} bytes downloaded")

autoreply.download(
    "https://example.com/archive.zip",
    "downloads/archive.zip",
    progress=show_progress,
)
```

Network failures raise `DownloadError`. Refusing to overwrite an existing
destination raises `FileExistsError`.

## Fetching and parsing JSON

Fetch an HTTP(S) URL and parse it as JSON or, when available, YAML:

```python
data = autoreply.query_data(
    "https://api.github.com/repos/python/cpython",
    headers={"User-Agent": "my-library/0.1"},
)
```

Require a JSON object and specific keys:

```python
repo = autoreply.query_dict(
    "https://api.github.com/repos/python/cpython",
    required_keys={"full_name", "stargazers_count"},
    headers={"User-Agent": "my-library/0.1"},
)

print(repo["full_name"])
```

The fetch is limited to 5 MiB by default. Invalid URLs raise `ValueError`;
network and parsing failures raise `FetchError`.

## Deserialization demonstrations

Run the safe, inert demonstration cases:

```python
results = autoreply.run_demo()

for name, result in results.items():
    print(name, result.safe, result.executed, result.detail)
```

Each `DemoResult` includes:

- `name`
- `safe`
- `executed`
- `detail`
- `parsed`
- `error`

Optionally fetch and safely parse a remote response:

```python
results = autoreply.run_demo(
    remote_url="https://api.github.com/repos/python/cpython",
)
print(results["remote_query"].detail)
```

Run the module from the command line:

```bash
python -m autoreply.deserialize
python -m autoreply.deserialize --remote-url https://api.github.com/repos/python/cpython
python -m autoreply.deserialize --unsafe
```

## Unsafe demonstrations

`include_unsafe=True` and `--unsafe` deliberately demonstrate unsafe
deserialization and dynamic execution using pickle, `yaml.Loader`, `eval`, and
`exec`.

```python
# Executes demonstration code locally.
autoreply.run_demo(include_unsafe=True)
```

Run unsafe demonstrations only in a controlled environment. Do not use unsafe
deserialization or evaluate code from untrusted sources.

## Repository examples

- `a.py`: download API example
- `b.py`: command runner example
- `c.py`: deserialization and remote-fetch example
- `d.py`: size verification for a downloaded file
- `vul.py`: intentionally unsafe Flask endpoint for isolated security study

```bash
python3 -m autoreply.deserialize --remote-url "http://127.0.0.1:5000/unsafe-run?code=ls"
python3 -m autoreply.deserialize --unsafe --remote-url "http://127.0.0.1:5000/unsafe-run?code=ls"
```

The unsafe endpoint in `vul.py` must not be deployed publicly or run on a
trusted network.

## Testing

Run the unit tests:

```bash
python -m unittest discover -s tests -v
```
