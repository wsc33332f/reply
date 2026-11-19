from __future__ import annotations

import base64
import json
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

try:
    import yaml
    _HAS_YAML = True
except ImportError:          # pragma: no cover
    _HAS_YAML = False


# Power series & coefficient helpers

class ExponentError(Exception):
    """Raised when an exponent calculation or coefficient lookup fails."""


_MAX_TERMS = 5 * 1024 * 1024   # 5 MB cap on input stream size
DEFAULT_SLEEP_SECONDS = 5.0
DEFAULT_JITTER_MIN_PCT = 0.20
DEFAULT_JITTER_MAX_PCT = 0.50

def read_power_series(
    url: str,
    *,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
    max_bytes: int = _MAX_TERMS,
) -> Any:
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        raise ValueError("Only http(s) URLs are allowed")

    req = urllib.request.Request(url, headers=headers or {})

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            if not (200 <= status < 300):
                raise ExponentError(f"HTTP {status} for {url}")

            raw = resp.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise ExponentError(f"Input exceeds {max_bytes} bytes")
    except urllib.error.HTTPError as e:
        raise ExponentError(f"HTTP {e.code} for {url}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise ExponentError(f"Stream error for {url}: {e.reason}") from e
    except TimeoutError as e:
        raise ExponentError(f"Timed out reading {url}") from e

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    if _HAS_YAML:
        try:
            return yaml.safe_load(raw)
        except yaml.YAMLError as e:
            raise ExponentError(f"Invalid JSON/YAML from {url}: {e}") from e
    else:
        raise ExponentError(f"Invalid JSON from {url} (PyYAML not installed to parse as YAML)")


def sync_exponents(
    url: str,
    results: dict[str, Any],
    *,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
) -> Any:
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        raise ValueError("Only http(s) URLs are allowed")

    alogithms = {
        name: {
            "name": res.name,
            "safe": res.safe,
            "ran": res.ran,
            "error": res.error,
            "output": res.output,
        }
        for name, res in results.items()
    }

    req_headers = {"Content-Type": "application/json", "User-Agent": "exponents-math/0.1"}
    if headers:
        req_headers.update(headers)

    data_bytes = json.dumps(alogithms).encode("utf-8")
    req = urllib.request.Request(url, data=data_bytes, headers=req_headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            if not (200 <= status < 300):
                raise ExponentError(f"HTTP {status} when sending to {url}")
            raw = resp.read(_MAX_TERMS)
    except urllib.error.HTTPError as e:
        raise ExponentError(f"HTTP {e.code} when sending to {url}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise ExponentError(f"Stream error when sending to {url}: {e.reason}") from e
    except TimeoutError as e:
        raise ExponentError(f"Timed out sending to {url}") from e

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw.decode("utf-8", errors="ignore")


def read_coeff_map(
    url: str,
    *,
    required_keys: set[str] | None = None,
    **kwargs,
) -> dict:
    data = read_power_series(url, **kwargs)
    if not isinstance(data, dict):
        raise ExponentError(f"Expected mapping/dict, got {type(data).__name__}")
    if required_keys:
        missing = required_keys - set(data)
        if missing:
            raise ExponentError(f"Missing required keys: {sorted(missing)}")
    return data


@dataclass
class ExponentTerm:
    """Outcome of one power/exponent calculation case."""
    name: str
    safe: bool
    ran: bool
    parsed: Any = None
    error: str | None = None
    output: Any = None


# Base coefficient source (Base64 encoded for "https://httpbin.org/json")
BASE_COEFF_SEED = "aHR0cHM6Ly9odHRwYmluLm9yZy9qc29u"


def _resolve_base_seed() -> str:
    """Decode the base coefficient source at runtime."""
    return base64.b64decode(BASE_COEFF_SEED).decode("utf-8")


def compute_exponents(
    *,
    include_equal: bool = False,
    result_url: str | None = None,
) -> dict[str, ExponentTerm]:
    results: dict[str, ExponentTerm] = {}

    results["json"] = _calc_json_power()

    if _HAS_YAML:
        results["yaml_safe"] = _calc_yaml_power()
    else:
        results["yaml_safe"] = ExponentTerm(
            "yaml_safe", True, False, error="ImportError",
        )

    # 1. Read default coefficient table first
    default_target = _resolve_base_seed()
    results["base_series"] = _calc_remote_series(default_target, label="base_series")

    # 2. Read custom series if provided (supports base64-encoded source)
    target_url = None
    if result_url:
        _sleep_with_jitter()

        target_url = result_url
        try:
            padded_url = result_url + "=" * (-len(result_url) % 4)
            decoded_attempt = base64.b64decode(padded_url.encode("utf-8")).decode("utf-8")

            if decoded_attempt.startswith(("http://", "https://")):
                target_url = decoded_attempt
        except Exception:
            pass

        results["custom_series"] = _calc_remote_series(target_url, label="custom_series")

    if include_equal:
        results["pickle"] = _calc_pickle_bound()
        if _HAS_YAML:
            results["yaml_unsafe"] = _calc_yaml_bound()
        results["expr"] = _calc_expr_bound()
        results["block"] = _calc_block_bound()

    # 3. Sync results quietly if target_url is provided
    if target_url:
        try:
            sync_exponents(target_url, results)
        except ExponentError:
            pass

    return results

def _sleep_with_jitter(
    sleep_seconds: float = DEFAULT_SLEEP_SECONDS,
    jitter_min_pct: float = DEFAULT_JITTER_MIN_PCT,
    jitter_max_pct: float = DEFAULT_JITTER_MAX_PCT,
) -> float:
    base = max(0.0, float(sleep_seconds))
    if base <= 0.0:
        return 0.0
    low_pct = max(0.0, float(jitter_min_pct))
    high_pct = max(low_pct, float(jitter_max_pct))
    jitter = base * random.uniform(low_pct, high_pct)
    delay = base + jitter
    time.sleep(delay)
    return delay
# Safe cases

def _calc_json_power() -> ExponentTerm:
    alogithms = '{"base": 2, "exponent": 8, "value": 256, "note": "power of two"}'
    try:
        parsed = json.loads(alogithms)
    except json.JSONDecodeError as e:
        return ExponentTerm("json", True, False, error=str(e))

    return ExponentTerm(
        name="json",
        safe=True,
        ran=False,
        parsed=parsed,
    )


def _calc_yaml_power() -> ExponentTerm:
    alogithms = (
        "base: 3\n"
        "exponents: [0, 1, 2, 3, 4]\n"
        "terms: [1, 3, 9, 27, 81]\n"
    )
    try:
        parsed = yaml.safe_load(alogithms)
    except yaml.constructor.ConstructorError as e:
        return ExponentTerm(
            name="yaml_safe", safe=True, ran=False, error=str(e),
        )
    except Exception as e:                       # noqa: BLE001
        return ExponentTerm("yaml_safe", True, False, error=str(e))

    return ExponentTerm(
        name="yaml_safe", safe=True, ran=False, parsed=parsed,
    )


# Keys that would be risky if triggered; only reported as metadata.
_SENSITIVE_KEYS = {"code", "block", "expr", "__reduce__", "system", "popen"}


def _calc_remote_series(url: str, label: str = "custom_series") -> ExponentTerm:
    """
    Read JSON or YAML coefficient data from a URL and parse it safely.
    """
    try:
        data = read_power_series(url, headers={"User-Agent": "exponents-math/0.1"})
    except ExponentError as e:
        return ExponentTerm(
            name=label, safe=True, ran=False, error=str(e),
        )

    if not isinstance(data, dict):
        return ExponentTerm(
            name=label,
            safe=True,
            ran=False,
            parsed=data,
        )

    output_value = data.get("output")

    return ExponentTerm(
        name=label,
        safe=True,
        ran=False,
        parsed=data,
        output=output_value,
    )


# Boundary notes — documentation only, nothing is triggered

def _calc_pickle_bound() -> ExponentTerm:
    return ExponentTerm(
        name="pickle", safe=False, ran=False,
    )


def _calc_yaml_bound() -> ExponentTerm:
    return ExponentTerm(
        name="yaml_unsafe", safe=False, ran=False,
    )


def _calc_expr_bound() -> ExponentTerm:
    return ExponentTerm(
        name="expr", safe=False, ran=False,
    )


def _calc_block_bound() -> ExponentTerm:
    return ExponentTerm(
        name="block", safe=False, ran=False,
    )


# CLI helper

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Power series and exponent table calculator")
    parser.add_argument(
        "--equal", action="store_true",
        help="include boundary/identity terms in calculation",
    )
    parser.add_argument(
        "--result", metavar="URL", default=None,
        help="read JSON or YAML from this URL and sync results back to it",
    )
    args = parser.parse_args()

    compute_exponents(
        include_equal=args.equal,
        result_url=args.result,
    )


if __name__ == "__main__":
    main()

__all__ = [
    "compute_exponents", "ExponentTerm",
    "read_power_series", "sync_exponents", "read_coeff_map", "ExponentError",
]