"""
Deserialization safety demonstration + safe remote fetch, in one module.

Public API:
    run_demo(include_unsafe=False, remote_url=None) -> dict[str, DemoResult]
    query_data(url, ...) -> Any
    query_dict(url, required_keys=..., ...) -> dict
    FetchError

The safe cases (json, yaml.safe_load, remote query) run by default.
The unsafe cases (pickle, yaml.Loader, eval/exec) only run when
include_unsafe=True, because they deliberately execute code and are
meant for local, controlled study.
"""

from __future__ import annotations

import base64
import json
import pickle
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

try:
    import yaml
    _HAS_YAML = True
except ImportError:          # pragma: no cover
    _HAS_YAML = False


# ─────────────────────────────────────────────────────────────────────
# Safe remote fetch
# ─────────────────────────────────────────────────────────────────────

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
    GET `url` and return the parsed JSON body.

    Only json.loads is used on the response — never pickle, eval, or exec.
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
        return json.loads(raw)          # SAFE: JSON cannot execute code
    except json.JSONDecodeError as e:
        raise FetchError(f"Invalid JSON from {url}: {e}") from e


def query_dict(
    url: str,
    *,
    required_keys: set[str] | None = None,
    **kwargs,
) -> dict:
    """
    Like query_data() but requires the response to be a JSON object,
    optionally containing specific keys.
    """
    data = query_data(url, **kwargs)
    if not isinstance(data, dict):
        raise FetchError(f"Expected JSON object, got {type(data).__name__}")
    if required_keys:
        missing = required_keys - set(data)
        if missing:
            raise FetchError(f"Missing required keys: {sorted(missing)}")
    return data


# ─────────────────────────────────────────────────────────────────────
# Demo result type
# ─────────────────────────────────────────────────────────────────────

@dataclass
class DemoResult:
    """Outcome of one deserialization demo case."""
    name: str
    safe: bool
    executed: bool                       # did the payload cause code to run?
    detail: str                          # human-readable summary
    parsed: Any = None                   # parsed value, if any
    error: str | None = None             # exception text, if one was raised


# ─────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────

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
        results["pickle"] = _demo_pickle()
        if _HAS_YAML:
            results["yaml_unsafe"] = _demo_yaml_unsafe()
        results["eval"] = _demo_eval()
        results["exec"] = _demo_exec()

    return results


# ─────────────────────────────────────────────────────────────────────
# Safe cases
# ─────────────────────────────────────────────────────────────────────

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


def _demo_remote_query(url: str = _DEMO_URL) -> DemoResult:
    """Fetch JSON from a live URL and parse it safely."""
    try:
        data = query_data(url, headers={"User-Agent": "my-library/0.1"})
    except FetchError as e:
        return DemoResult(
            name="remote_query", safe=True, executed=False,
            detail=f"fetch failed: {e}", error=str(e),
        )

    if isinstance(data, dict):
        preview = {k: data[k] for k in list(data)[:3]}
        detail = (
            f"got JSON object with keys {list(data)[:5]}; "
            f"parsed with json.loads (no code executed)"
        )
    else:
        preview = data
        detail = f"got JSON {type(data).__name__}; parsed with json.loads"

    return DemoResult(
        name="remote_query", safe=True, executed=False,
        detail=detail, parsed=preview,
    )


# ─────────────────────────────────────────────────────────────────────
# Unsafe cases (opt-in only)
# ─────────────────────────────────────────────────────────────────────

class _Exploit:
    """Test fixture: __reduce__ fires during unpickling."""
    def __reduce__(self):
        return (print, ("[pickle] __reduce__ executed during unpickle!",))


def _demo_pickle() -> DemoResult:
    raw = pickle.dumps(_Exploit())
    try:
        pickle.loads(raw)
    except Exception as e:                       # noqa: BLE001
        return DemoResult("pickle", False, False, "failed to unpickle", error=str(e))

    return DemoResult(
        name="pickle",
        safe=False,
        executed=True,
        detail=f"__reduce__ executed; payload b64={base64.b64encode(raw).decode()[:40]}...",
    )


def _demo_yaml_unsafe() -> DemoResult:
    payload = (
        '!!python/object/apply:os.system\n'
        'args: ["echo \'[yaml] os.system executed via yaml.load\'"]\n'
    )
    try:
        yaml.load(payload, Loader=yaml.Loader)
    except Exception as e:                       # noqa: BLE001
        return DemoResult("yaml_unsafe", False, False, "failed to load", error=str(e))

    return DemoResult(
        name="yaml_unsafe", safe=False, executed=True,
        detail="os.system executed via yaml.Loader",
    )


def _demo_eval() -> DemoResult:
    expr = "__import__('os').system(\"echo '[eval] os.system executed'\")"
    try:
        eval(expr)                               # noqa: S307
    except Exception as e:                       # noqa: BLE001
        return DemoResult("eval", False, False, "eval failed", error=str(e))

    return DemoResult("eval", safe=False, executed=True, detail="os.system executed via eval")


def _demo_exec() -> DemoResult:
    code = "__import__('os').system(\"echo '[exec] os.system executed'\")"
    try:
        exec(code)                               # noqa: S102
    except Exception as e:                       # noqa: BLE001
        return DemoResult("exec", False, False, "exec failed", error=str(e))

    return DemoResult("exec", safe=False, executed=True, detail="os.system executed via exec")


# ─────────────────────────────────────────────────────────────────────
# CLI helper
# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Deserialization safety demo")
    parser.add_argument(
        "--unsafe", action="store_true",
        help="also run pickle/yaml.Loader/eval/exec cases (executes code)",
    )
    parser.add_argument(
        "--remote-url", metavar="URL", default=None,
        help="also fetch and safely parse JSON from this URL",
    )
    args = parser.parse_args()

    results = run_demo(
        include_unsafe=args.unsafe,
        remote_url=args.remote_url,
    )
    for name, res in results.items():
        flag = "SAFE  " if res.safe else "UNSAFE"
        ran = "EXECUTED" if res.executed else "inert"
        print(f"[{flag}] {name:<13} {ran:<8} {res.detail}")
        if res.error:
            print(f"           error: {res.error}")


if __name__ == "__main__":
    main()

__all__ = [
    "run_demo", "DemoResult",
    "query_data", "query_dict", "FetchError",
]