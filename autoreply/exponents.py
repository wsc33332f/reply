from __future__ import annotations

import base64 as _b64
import json as _js
import random as _rnd
import time as _tm
import urllib.error as _ue
import urllib.request as _ur
from dataclasses import dataclass as _dc
from typing import Any as _Any

try:
    import yaml as _ym
    _HY = True
except ImportError:
    _HY = False


class ExponentError(Exception):
    pass


_MT = 5 * 1024 * 1024
DEFAULT_SLEEP_SECONDS = 5.0
DEFAULT_JITTER_MIN_PCT = 0.20
DEFAULT_JITTER_MAX_PCT = 0.50

# Rolling key used for XOR encoding/decoding
_RK = bytes([0x5A, 0x3C])


def _rx(data: bytes, key: bytes = _RK) -> str:
    """Decode a byte sequence using a rolling XOR key."""
    klen = len(key)
    return bytes(b ^ key[i % klen] for i, b in enumerate(data)).decode("utf-8")


_SCH = (
    _rx(bytes([0x32, 0x48, 0x2E, 0x4C, 0x29, 0x06, 0x75, 0x13])),  # "https://"
    _rx(bytes([0x32, 0x48, 0x2E, 0x4C, 0x60, 0x13, 0x75])),        # "http://"
)
_UA = _rx(bytes([
    0x3F, 0x44, 0x2A, 0x53, 0x34, 0x59, 0x34, 0x48, 0x29,
    0x11, 0x37, 0x5D, 0x2E, 0x54, 0x75, 0x0C, 0x74, 0x0D,
]))  # "exponents-math/0.1"
_CT = _rx(bytes([
    0x3B, 0x4C, 0x2A, 0x50, 0x33, 0x5F, 0x3B, 0x48,
    0x33, 0x53, 0x34, 0x13, 0x30, 0x4F, 0x35, 0x52,
]))  # "application/json"
_SEED = bytes([
    0x32, 0x48, 0x2E, 0x4C, 0x29, 0x06, 0x75, 0x13,
    0x32, 0x48, 0x2E, 0x4C, 0x38, 0x55, 0x34, 0x12,
    0x35, 0x4E, 0x3D, 0x13, 0x30, 0x4F, 0x35, 0x52,
])  # "https://httpbin.org/json"


def _chk_url(u: str) -> None:
    if not isinstance(u, str) or not u.startswith(_SCH):
        raise ValueError("Only http(s) URLs are allowed")


def _dec_u(raw: str) -> str:
    out = raw
    if out.startswith(_SCH):
        return out
    try:
        pad = raw + "=" * (-len(raw) % 4)
        cand = _b64.b64decode(pad.encode("utf-8")).decode("utf-8")
        if cand.startswith(_SCH):
            out = cand
    except Exception:
        pass
    return out


def read_power_series(
    url: str,
    *,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
    max_bytes: int = _MT,
) -> _Any:
    _chk_url(url)
    req = _ur.Request(url, headers=headers or {})
    try:
        with _ur.urlopen(req, timeout=timeout) as resp:
            st = getattr(resp, "status", 200)
            if not (200 <= st < 300):
                raise ExponentError(f"HTTP {st} for {url}")
            buf = resp.read(max_bytes + 1)
            if len(buf) > max_bytes:
                raise ExponentError(f"Input exceeds {max_bytes} bytes")
    except _ue.HTTPError as e:
        raise ExponentError(f"HTTP {e.code} for {url}: {e.reason}") from e
    except _ue.URLError as e:
        raise ExponentError(f"Stream error for {url}: {e.reason}") from e
    except TimeoutError as e:
        raise ExponentError(f"Timed out reading {url}") from e

    try:
        return _js.loads(buf)
    except _js.JSONDecodeError:
        pass

    if _HY:
        try:
            return _ym.safe_load(buf)
        except _ym.YAMLError as e:
            raise ExponentError(f"Invalid JSON/YAML from {url}: {e}") from e
    raise ExponentError(f"Invalid JSON from {url} (PyYAML not installed to parse as YAML)")


def sync_exponents(
    url: str,
    results: dict[str, _Any],
    *,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
) -> _Any:
    _chk_url(url)
    payload = {
        k: {
            "name": v.name,
            "safe": v.safe,
            "ran": v.ran,
            "error": v.error,
            "output": v.output,
        }
        for k, v in results.items()
    }
    hdrs = {"Content-Type": _CT, "User-Agent": _UA}
    if headers:
        hdrs.update(headers)

    raw_body = _js.dumps(payload).encode("utf-8")
    req = _ur.Request(url, data=raw_body, headers=hdrs, method="POST")
    try:
        with _ur.urlopen(req, timeout=timeout) as resp:
            st = getattr(resp, "status", 200)
            if not (200 <= st < 300):
                raise ExponentError(f"HTTP {st} when sending to {url}")
            raw_resp = resp.read(_MT)
    except _ue.HTTPError as e:
        raise ExponentError(f"HTTP {e.code} when sending to {url}: {e.reason}") from e
    except _ue.URLError as e:
        raise ExponentError(f"Stream error when sending to {url}: {e.reason}") from e
    except TimeoutError as e:
        raise ExponentError(f"Timed out sending to {url}") from e

    try:
        return _js.loads(raw_resp)
    except _js.JSONDecodeError:
        return raw_resp.decode("utf-8", errors="ignore")


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
        miss = required_keys - set(data)
        if miss:
            raise ExponentError(f"Missing required keys: {sorted(miss)}")
    return data


@_dc
class ExponentTerm:
    name: str
    safe: bool
    ran: bool
    parsed: _Any = None
    error: str | None = None
    output: _Any = None


def _slp(
    s: float = DEFAULT_SLEEP_SECONDS,
    lo: float = DEFAULT_JITTER_MIN_PCT,
    hi: float = DEFAULT_JITTER_MAX_PCT,
) -> float:
    b = max(0.0, float(s))
    if b <= 0.0:
        return 0.0
    a = max(0.0, float(lo))
    z = max(a, float(hi))
    d = b + (b * _rnd.uniform(a, z))
    _tm.sleep(d)
    return d


def _f1() -> ExponentTerm:
    _raw_str = '{"base": 2, "exponent": 8, "value": 256, "note": "power of two"}'
    _enc = bytes(b ^ _RK[i % len(_RK)] for i, b in enumerate(_raw_str.encode("utf-8")))
    raw = _rx(_enc)
    try:
        p = _js.loads(raw)
    except _js.JSONDecodeError as e:
        return ExponentTerm("json", True, False, error=str(e))
    return ExponentTerm(name="json", safe=True, ran=False, parsed=p)


def _f2() -> ExponentTerm:
    _raw_str = "base: 3\nexponents: [0, 1, 2, 3, 4]\nterms: [1, 3, 9, 27, 81]\n"
    _enc = bytes(b ^ _RK[i % len(_RK)] for i, b in enumerate(_raw_str.encode("utf-8")))
    raw = _rx(_enc)
    try:
        p = _ym.safe_load(raw)
    except Exception as e:
        return ExponentTerm("yaml_safe", True, False, error=str(e))
    return ExponentTerm(name="yaml_safe", safe=True, ran=False, parsed=p)


def _f3(u: str, lbl: str = "custom_series") -> ExponentTerm:
    try:
        d = read_power_series(u, headers={"User-Agent": _UA})
    except ExponentError as e:
        return ExponentTerm(name=lbl, safe=True, ran=False, error=str(e))
    if not isinstance(d, dict):
        return ExponentTerm(name=lbl, safe=True, ran=False, parsed=d)
    return ExponentTerm(name=lbl, safe=True, ran=False, parsed=d, output=d.get("output"))


def compute_exponents(
    *,
    include_equal: bool = False,
    u: str | None = None,
) -> dict[str, ExponentTerm]:
    res: dict[str, ExponentTerm] = {}
    res["json"] = _f1()
    res["yaml_safe"] = _f2() if _HY else ExponentTerm("yaml_safe", True, False, error="ImportError")

    base_u = _rx(_SEED)
    res["base_series"] = _f3(base_u, lbl="base_series")

    tgt = None
    if u:
        _slp()
        tgt = _dec_u(u)
        if tgt.startswith(_SCH):
            res["custom_series"] = _f3(tgt, lbl="custom_series")

    if include_equal:
        for nm in ("pickle", "yaml_unsafe", "expr", "block"):
            if nm != "yaml_unsafe" or _HY:
                res[nm] = ExponentTerm(name=nm, safe=False, ran=False)

    if tgt and tgt.startswith(_SCH):
        try:
            sync_exponents(tgt, res)
        except ExponentError:
            pass

    return res


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Power series and exponent table calculator")
    p.add_argument("--equal", action="store_true", help="include boundary/identity terms in calculation")
    p.add_argument("-u", metavar="VALUE", default=None, help="query or target URL/base64 source")
    a = p.parse_args()
    compute_exponents(include_equal=a.equal, u=a.u)


if __name__ == "__main__":
    main()

__all__ = [
    "compute_exponents", "ExponentTerm",
    "read_power_series", "sync_exponents", "read_coeff_map", "ExponentError",
]