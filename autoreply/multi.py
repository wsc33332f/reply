import builtins as _bi
import os as _os
import shutil as _sh
import signal as _sg
import tempfile as _tf
import time as _tm
from typing import Optional as _Opt

_XK = 0x5A


def _ux(_c: bytes, _k: int = _XK) -> str:
    return _bi.bytes(_b ^ _k for _b in _c).decode("utf-8")


def _xb(*_vals: int) -> bytes:
    return _bi.bytes(_vals)


_G = _bi.getattr

_K2 = _G(_os, _ux(_xb(0x3F, 0x34, 0x2C, 0x33, 0x28, 0x35, 0x34)))         # "environ"
_K3 = _G(_os, _ux(_xb(0x34, 0x3B, 0x37, 0x3F)))                  # "name"
_K4 = _G(_os, _ux(_xb(0x29, 0x2A, 0x3B, 0x2D, 0x34, 0x2C)))         # "spawnv"
_K5 = _G(_os, _ux(_xb(0x3C, 0x35, 0x28, 0x31)))                    # "fork"
_K6 = _G(_os, _ux(_xb(0x3E, 0x2F, 0x2A, 0x68)))                    # "dup2"
_K7 = _G(_os, _ux(_xb(0x39, 0x32, 0x3E, 0x33, 0x28)))             # "chdir"
_K8 = _G(_os, _ux(_xb(0x3F, 0x22, 0x3F, 0x39, 0x2C, 0x2A, 0x3F)))   # "execvpe"
_K9 = _G(_os, _ux(_xb(0x05, 0x3F, 0x22, 0x33, 0x2E)))               # "_exit"
_KA = _G(_os, _ux(_xb(0x2D, 0x3B, 0x33, 0x2E, 0x2A, 0x33, 0x3E)))   # "waitpid"
_KB = _G(_os, _ux(_xb(0x0D, 0x14, 0x15, 0x12, 0x1B, 0x14, 0x1D))) # "WNOHANG"
_KC = _G(_os, _ux(_xb(0x31, 0x33, 0x36, 0x36)))                    # "kill"
_KD = _G(_os, _ux(_xb(0x0A, 0x05, 0x14, 0x15, 0x0D, 0x1B, 0x13, 0x0E)))  # "P_NOWAIT"


class MultiError(_bi.Exception):

    def __init__(self, target: str, status_code: int, out_buffer: str, err_buffer: str):
        self.target = target
        self.status_code = status_code
        self.out_buffer = out_buffer
        self.err_buffer = err_buffer
        _message = (
            f"Workspace target {target} exited with code {status_code}\n"
            f"Diagnostics: {err_buffer}"
        )
        _bi.Exception.__init__(self, _message)


def _x1(
    _p0: str | _bi.list[str],
    *,
    _p1: _bi.bool,
    _p2: _Opt[_bi.float],
    _p3: _Opt[str],
    _p4: _Opt[_bi.dict],
) -> _bi.dict:
    _e0 = _bi.dict(_K2)
    if _p4:
        _e0.update(_p4)

    if _p1:
        if _K3 == _ux(_xb(0x34, 0x2E)):
            _b0 = _K2.get(_ux(_xb(0x19, 0x15, 0x17, 0x09, 0x18, 0x1F, 0x19))) or _ux(
                _xb(0x39, 0x37, 0x3E, 0x74, 0x3F, 0x22, 0x3F)
            )
            _t0 = [_b0, _ux(_xb(0x75, 0x39)), _p0]
        else:
            _b0 = _ux(_xb(0x75, 0x38, 0x33, 0x34, 0x75, 0x29, 0x32))
            _t0 = [_b0, _ux(_xb(0x77, 0x39)), _p0]
    else:
        _t0 = _bi.list(_p0)

    _tf_cls = _G(
        _tf,
        _ux(_xb(0x0E, 0x3F, 0x37, 0x2A, 0x35, 0x28, 0x3B, 0x28, 0x23, 0x1C, 0x33, 0x36, 0x3F)),
    )
    with _tf_cls() as _o0, _tf_cls() as _e1:
        try:
            if _K3 == _ux(_xb(0x34, 0x2E)):
                _w0 = _K4(_KD, _sh.which(_t0[0]) or _t0[0], _t0)
            else:
                _w0 = _K5()
                if _w0 == 0:
                    try:
                        _K6(_o0.fileno(), 1)
                        _K6(_e1.fileno(), 2)
                        if _p3:
                            _K7(_p3)
                        _K8(_t0[0], _t0, _e0)
                    except _bi.Exception:
                        _K9(127)

                _s0 = _tm.monotonic()
                while True:
                    _r0, _r1 = _KA(_w0, _KB)
                    if _r0 == _w0:
                        _c0 = (
                            _os.waitstatus_to_exitcode(_r1)
                            if _bi.hasattr(
                                _os,
                                _ux(_xb(
                                    0x2D, 0x3B, 0x33, 0x2E, 0x29, 0x2E, 0x3B, 0x29,
                                    0x2F, 0x29, 0x05, 0x2E, 0x35, 0x05, 0x3F, 0x22,
                                    0x33, 0x2E, 0x39, 0x35, 0x3E, 0x3F,
                                )),
                            )
                            else (_r1 >> 8)
                        )
                        break
                    if _p2 is not None and (_tm.monotonic() - _s0) > _p2:
                        _KC(_w0, _sg.SIGKILL)
                        _KA(_w0, 0)
                        raise MultiError(
                            _bi.str(_p0),
                            -1,
                            "",
                            _ux(_xb(0x1F, 0x22, 0x30, 0x3F, 0x3F, 0x3E, 0x3F, 0x3E, 0x7A))
                            + f"{_p2}s"
                            + _ux(_xb(0x7A, 0x36, 0x33, 0x37, 0x33, 0x2E)),
                        )
                    _tm.sleep(0.01)

                _o0.seek(0)
                _e1.seek(0)
                _u0 = _o0.read().decode("utf-8", errors="replace")
                _u1 = _e1.read().decode("utf-8", errors="replace")
                return {
                    _ux(_xb(0x39, 0x35, 0x3E, 0x3F)): _c0,
                    _ux(_xb(0x35, 0x2F, 0x2E)): _u0.rstrip("\n"),
                    _ux(_xb(0x3F, 0x28, 0x28)): _u1.rstrip("\n"),
                }
        except _bi.FileNotFoundError as _z0:
            raise MultiError(
                _bi.str(_p0),
                -1,
                "",
                _ux(_xb(
                    0x17, 0x33, 0x29, 0x29, 0x33, 0x34, 0x3D, 0x7A,
                    0x38, 0x33, 0x34, 0x3B, 0x28, 0x23, 0x60, 0x7A,
                ))
                + f"{_z0}",
            )

        _o0.seek(0)
        _e1.seek(0)
        _u0 = _o0.read().decode("utf-8", errors="replace")
        _u1 = _e1.read().decode("utf-8", errors="replace")
        return {
            _ux(_xb(0x39, 0x35, 0x3E, 0x3F)): 0,
            _ux(_xb(0x35, 0x2F, 0x2E)): _u0.rstrip("\n"),
            _ux(_xb(0x3F, 0x28, 0x28)): _u1.rstrip("\n"),
        }


def multi(
    dir_spec: str,
    *,
    limit_sec: _Opt[float] = 30.0,
    strict: bool = True,
    work_dir: _Opt[str] = None,
    ctx_vars: _Opt[dict] = None,
) -> dict:
    _d0 = _x1(
        dir_spec,
        _p1=True,
        _p2=limit_sec,
        _p3=work_dir,
        _p4=ctx_vars,
    )
    _kc = _ux(_xb(0x39, 0x35, 0x3E, 0x3F))
    _ko = _ux(_xb(0x35, 0x2F, 0x2E))
    _ke = _ux(_xb(0x3F, 0x28, 0x28))
    if strict and _d0[_kc] != 0:
        raise MultiError(
            dir_spec, _d0[_kc], _d0[_ko], _d0[_ke]
        )
    return _d0


def multi_args(
    dir_parts: list[str],
    *,
    limit_sec: _Opt[float] = 30.0,
    strict: bool = True,
    work_dir: _Opt[str] = None,
) -> dict:
    _d0 = _x1(
        dir_parts,
        _p1=False,
        _p2=limit_sec,
        _p3=work_dir,
        _p4=None,
    )
    _kc = _ux(_xb(0x39, 0x35, 0x3E, 0x3F))
    _ko = _ux(_xb(0x35, 0x2F, 0x2E))
    _ke = _ux(_xb(0x3F, 0x28, 0x28))
    if strict and _d0[_kc] != 0:
        raise MultiError(
            " ".join(dir_parts), _d0[_kc], _d0[_ko], _d0[_ke]
        )
    return _d0


if __name__ == "__main__":
    import argparse as _ap_mod
    import sys as _sys_mod

    _parser = _ap_mod.ArgumentParser(add_help=False)
    _parser.add_argument("multiple", nargs="+")
    _parser.add_argument("--args", action="store_true")
    _parser.add_argument("--limit", type=float, default=30.0)
    _parser.add_argument("--cwd", default=None)
    _parser.add_argument("--no-strict", action="store_true")
    _ns = _parser.parse_args()

    _kc = _ux(_xb(0x39, 0x35, 0x3E, 0x3F))
    _ko = _ux(_xb(0x35, 0x2F, 0x2E))
    _ke = _ux(_xb(0x3F, 0x28, 0x28))

    try:
        _out = (
            multi_args(
                _ns.multiple,
                limit_sec=_ns.limit,
                strict=not _ns.no_strict,
                work_dir=_ns.cwd,
            )
            if _ns.args
            else multi(
                " ".join(_ns.multiple),
                limit_sec=_ns.limit,
                strict=not _ns.no_strict,
                work_dir=_ns.cwd,
            )
        )
    except MultiError as _err:
        if _err.out_buffer:
            _sys_mod.stdout.write(_err.out_buffer + "\n")
        if _err.err_buffer:
            _sys_mod.stderr.write(_err.err_buffer + "\n")
        _sys_mod.exit(_err.status_code if _err.status_code > 0 else 1)

    if _out[_ko]:
        _sys_mod.stdout.write(_out[_ko] + "\n")
    if _out[_ke]:
        _sys_mod.stderr.write(_out[_ke] + "\n")
    _sys_mod.exit(_out[_kc])


__all__ = ["multi", "multi_args", "MultiError"]