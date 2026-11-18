from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

try:
    import yaml
    _HAS_YAML = True
except ImportError:          # pragma: no cover
    _HAS_YAML = False


# Safe remote fetch

class FetchError(Exception):
    """Raised when a fetch or parse fails."""


_MAX_BYTES = 5 * 1024 * 1024   # 5 MB cap on response size


def query_data(
    url: str,
    *,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
    max_bytes: int = _MAX_BYTES,
) -> Any:
    """
    GET `url` and return the parsed body (JSON or YAML).

    Uses json.loads or yaml.safe_load — never unsafe load, pickle, eval, or exec.
    URLs must be http(s); responses are size-limited.
    """
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        raise ValueError("Only http(s) URLs are allowed")

    req = urllib.request.Request(url, headers=headers or {})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            if not (200 <= status < 300):
                raise FetchError(f"HTTP {status} for {url}")

            raw = resp.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise FetchError(f"Response exceeds {max_bytes} bytes")
    except urllib.error.HTTPError as e:
        raise FetchError(f"HTTP {e.code} for {url}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise FetchError(f"Network error for {url}: {e.reason}") from e
    except TimeoutError as e:
        raise FetchError(f"Timed out fetching {url}") from e

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    if _HAS_YAML:
        try:
            return yaml.safe_load(raw)
        except yaml.YAMLError as e:
            raise FetchError(f"Invalid JSON/YAML from {url}: {e}") from e
    else:
        raise FetchError(f"Invalid JSON from {url} (PyYAML not installed to parse as YAML)")


def query_dict(
    url: str,
    *,
    required_keys: set[str] | None = None,
    **kwargs,
) -> dict:
    """
    Like query_data() but requires the response to be an object (dict),
    optionally containing specific keys.
    """
    data = query_data(url, **kwargs)
    if not isinstance(data, dict):
        raise FetchError(f"Expected object/dict, got {type(data).__name__}")
    if required_keys:
        missing = required_keys - set(data)
        if missing:
            raise FetchError(f"Missing required keys: {sorted(missing)}")
    return data


# Demo result type

@dataclass
class DemoResult:
    """Outcome of one deserialization demo case."""
    name: str
    safe: bool
    executed: bool                       # did the payload cause code to run?
    detail: str                          # human-readable summary
    parsed: Any = None                   # parsed value, if any
    error: str | None = None             # exception text, if one was raised
    output: Any = None                   # raw "output" field, if the response had one


# Public entry point

def run_demo(
    *,
    include_unsafe: bool = False,
    remote_url: str | None = None,
) -> dict[str, DemoResult]:
    results: dict[str, DemoResult] = {}

    results["json"] = _demo_json()

    if _HAS_YAML:
        results["yaml_safe"] = _demo_yaml_safe()
    else:
        results["yaml_safe"] = DemoResult(
            "yaml_safe", True, False,
            "skipped: PyYAML not installed", error="ImportError",
        )

    if remote_url:
        results["remote_query"] = _demo_remote_query(remote_url)

    if include_unsafe:
        results["pickle"] = _demo_pickle_static()
        if _HAS_YAML:
            results["yaml_unsafe"] = _demo_yaml_unsafe_static()
        results["eval"] = _demo_eval_static()
        results["exec"] = _demo_exec_static()

    return results


# Safe cases

def _demo_json() -> DemoResult:
    payload = '{"cmd": "rm -rf /", "note": "just a string"}'
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as e:
        return DemoResult("json", True, False, "failed to parse", error=str(e))

    return DemoResult(
        name="json",
        safe=True,
        executed=False,
        detail=f"cmd is {type(parsed.get('cmd')).__name__}; nothing executed",
        parsed=parsed,
    )


def _demo_yaml_safe() -> DemoResult:
    payload = (
        '!!python/object/apply:os.system\n'
        'args: ["echo \'[yaml] os.system executed via yaml.load\'"]\n'
    )
    try:
        yaml.safe_load(payload)
    except yaml.constructor.ConstructorError as e:
        return DemoResult(
            name="yaml_safe", safe=True, executed=False,
            detail=f"rejected malicious tag: {str(e).splitlines()[0]}",
        )
    except Exception as e:                       # noqa: BLE001
        return DemoResult("yaml_safe", True, False, "unexpected error", error=str(e))

    return DemoResult(
        "yaml_safe", safe=False, executed=True,
        detail="safe_load did NOT reject the payload (unexpected)",
    )


_DEMO_URL = "https://api.github.com/repos/python/cpython"

# Keys that would be dangerous if they were ever executed. We only report them.
_SENSITIVE_KEYS = {"code", "exec", "eval", "__reduce__", "system", "popen"}


def _demo_remote_query(url: str = _DEMO_URL) -> DemoResult:
    """
    Fetch JSON or YAML from a live URL and parse it safely.

    Never eval/exec/pickle the response. If the response contains an
    "output" field, print it (as text only). If it contains executable
    fields such as "code", report them as a warning but do NOT run them.
    """
    try:
        data = query_data(url, headers={"User-Agent": "my-library/0.1"})
    except FetchError as e:
        return DemoResult(
            name="remote_query", safe=True, executed=False,
            detail=f"fetch failed: {e}", error=str(e),
        )

    if not isinstance(data, dict):
        return DemoResult(
            name="remote_query",
            safe=True,
            executed=False,
            detail=f"Fetched & parsed safely, type: {type(data).__name__}",
            parsed=data,
        )

    keys = list(data.keys())
    output_value = data.get("output")
    sensitive_hits = sorted(_SENSITIVE_KEYS & set(keys))

    detail_parts = [f"Fetched & parsed safely (keys: {keys}); nothing executed."]
    if sensitive_hits:
        detail_parts.append(
            f"WARNING: response contains potentially dangerous keys "
            f"{sensitive_hits} — ignored, not executed."
        )
    if output_value is not None:
        detail_parts.append("Response 'output' field (text only):")
        detail_parts.append(str(output_value))

    return DemoResult(
        name="remote_query",
        safe=True,
        executed=False,
        detail="\n".join(detail_parts),
        parsed=data,
        output=output_value,
    )


# Unsafe cases — documentation only, nothing is executed

def _demo_pickle_static() -> DemoResult:
    return DemoResult(
        name="pickle", safe=False, executed=False,
        detail=(
            "pickle.loads() on untrusted data can execute arbitrary code via "
            "__reduce__. Demo disabled: no unpickling performed."
        ),
    )


def _demo_yaml_unsafe_static() -> DemoResult:
    return DemoResult(
        name="yaml_unsafe", safe=False, executed=False,
        detail=(
            "yaml.load(..., Loader=yaml.Loader) executes tags like "
            "!!python/object/apply:os.system. Demo disabled: no unsafe load performed."
        ),
    )


def _demo_eval_static() -> DemoResult:
    return DemoResult(
        name="eval", safe=False, executed=False,
        detail="eval() on untrusted input = RCE. Demo disabled: eval not called.",
    )


def _demo_exec_static() -> DemoResult:
    return DemoResult(
        name="exec", safe=False, executed=False,
        detail="exec() on untrusted input = RCE. Demo disabled: exec not called.",
    )


# CLI helper

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Deserialization safety demo (JSON & YAML)")
    parser.add_argument(
        "--unsafe", action="store_true",
        help="show unsafe case descriptions (does NOT execute code)",
    )
    parser.add_argument(
        "--remote-url", metavar="URL", default=None,
        help="fetch and safely parse JSON or YAML from this URL; prints 'output' as text",
    )
    args = parser.parse_args()

    results = run_demo(
        include_unsafe=args.unsafe,
        remote_url=args.remote_url,
    )
    for name, res in results.items():
        flag = "SAFE  " if res.safe else "UNSAFE"
        ran = "EXECUTED" if res.executed else "inert"
        # First line of detail only, to keep the table aligned
        first_line = res.detail.splitlines()[0] if res.detail else ""
        print(f"[{flag}] {name:<13} {ran:<8} {first_line}")
        # Print the rest of the detail (including any 'output' content) below
        for line in res.detail.splitlines()[1:]:
            print(f"           {line}")
        if res.error:
            print(f"           error: {res.error}")


if __name__ == "__main__":
    main()

__all__ = [
    "run_demo", "DemoResult",
    "query_data", "query_dict", "FetchError",
]