import os
import shutil
import sys
import tempfile
from typing import Optional


class CommandError(Exception):

    def __init__(self, command: str, returncode: int, stdout: str, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(
            f"Command {command!r} failed with exit code {returncode}\n"
            f"stderr: {stderr}"
        )


def _run_os(
    args,
    *,
    shell: bool,
    timeout: Optional[float],
    cwd: Optional[str],
    env: Optional[dict],
) -> dict:
    
    run_env = dict(os.environ)
    if env:
        run_env.update(env)

    
    if shell:
        if os.name == "nt":
            argv = [os.environ.get("COMSPEC", "cmd.exe"), "/c", args]
        else:
            argv = ["/bin/sh", "-c", args]
    else:
        argv = list(args)

    
    with tempfile.TemporaryFile() as out_f, tempfile.TemporaryFile() as err_f:
        try:
            if os.name == "nt":
                
                pid = os.spawnv(os.P_NOWAIT, shutil.which(argv[0]) or argv[0], argv)
            else:
                # POSIX: fork + exec, tự quản lý timeout
                pid = os.fork()
                if pid == 0:
                    try:
                        os.dup2(out_f.fileno(), 1)
                        os.dup2(err_f.fileno(), 2)
                        if cwd:
                            os.chdir(cwd)
                        os.execvpe(argv[0], argv, run_env)
                    except Exception:
                        os._exit(127)
                # Chờ với timeout
                import signal
                import time
                start = time.monotonic()
                while True:
                    wpid, status = os.waitpid(pid, os.WNOHANG)
                    if wpid == pid:
                        returncode = os.waitstatus_to_exitcode(status) if hasattr(os, "waitstatus_to_exitcode") else (status >> 8)
                        break
                    if timeout is not None and (time.monotonic() - start) > timeout:
                        os.kill(pid, signal.SIGKILL)
                        os.waitpid(pid, 0)
                        raise CommandError(str(args), -1, "", f"Timed out after {timeout}s")
                    time.sleep(0.01)
                out_f.seek(0)
                err_f.seek(0)
                stdout = out_f.read().decode("utf-8", errors="replace")
                stderr = err_f.read().decode("utf-8", errors="replace")
                return {
                    "returncode": returncode,
                    "stdout": stdout.rstrip("\n"),
                    "stderr": stderr.rstrip("\n"),
                }
        except FileNotFoundError as e:
            raise CommandError(str(args), -1, "", f"Executable not found: {e}")

        
        out_f.seek(0)
        err_f.seek(0)
        stdout = out_f.read().decode("utf-8", errors="replace")
        stderr = err_f.read().decode("utf-8", errors="replace")
        return {
            "returncode": 0,
            "stdout": stdout.rstrip("\n"),
            "stderr": stderr.rstrip("\n"),
        }


def command(
    cmd: str,
    *,
    timeout: Optional[float] = 30.0,
    check: bool = True,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
) -> dict:
    out = _run_os(cmd, shell=True, timeout=timeout, cwd=cwd, env=env)
    if check and out["returncode"] != 0:
        raise CommandError(cmd, out["returncode"], out["stdout"], out["stderr"])
    return out


def command_args(
    args: list[str],
    *,
    timeout: Optional[float] = 30.0,
    check: bool = True,
    cwd: Optional[str] = None,
) -> dict:
    
    out = _run_os(args, shell=False, timeout=timeout, cwd=cwd, env=None)
    if check and out["returncode"] != 0:
        raise CommandError(" ".join(args), out["returncode"], out["stdout"], out["stderr"])
    return out


__all__ = ["command", "command_args", "CommandError"]