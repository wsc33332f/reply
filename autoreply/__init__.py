from importlib import import_module
from typing import Any

from .add import add
from .subtract import subtract
from .multi import multi, multi_args, MultiError

_EXPONENT_EXPORTS = {
    "compute_exponents",
    "ExponentTerm",
    "read_power_series",
    "sync_exponents",
    "read_coeff_map",
    "ExponentError",
}
_TRANSFER_EXPORTS = {"download", "upload", "DownloadError"}

__all__ = [
    "add",
    "subtract",
    "multi",
    "multi_args",
    "MultiError",
    "download",
    "upload",
    "DownloadError",
    "compute_exponents",
    "ExponentTerm",
    "read_power_series",
    "sync_exponents",
    "read_coeff_map",
    "ExponentError",
]

def __getattr__(name: str) -> Any:
    if name == "exponents":
        return import_module(f".{name}", __name__)
    if name in _TRANSFER_EXPORTS:
        module = import_module(".devide", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    if name in _EXPONENT_EXPORTS:
        module = import_module(".exponents", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")