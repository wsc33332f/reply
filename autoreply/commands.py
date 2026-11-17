import subprocess
import shlex
import sys
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

def command(
    cmd: str,
    *,
    timeout: Optional[float] = 30.0,
    check: bool = True,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
) -> dict:
    try:
        result = subprocess.run(
            cmd,
            shell=True,          # platform default shell: cmd.exe / /bin/sh
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=env,
        )
    except subprocess.TimeoutExpired:
        raise CommandError(cmd, -1, "", f"Timed out after {timeout}s")
    except FileNotFoundError as e:
        raise CommandError(cmd, -1, "", f"Executable not found: {e}")

    out = {
        "returncode": result.returncode,
        "stdout": result.stdout.rstrip("\n"),
        "stderr": result.stderr.rstrip("\n"),
    }

    if check and result.returncode != 0:
        raise CommandError(cmd, result.returncode, out["stdout"], out["stderr"])

    return out


def command_args(
    args: list[str],
    *,
    timeout: Optional[float] = 30.0,
    check: bool = True,
    cwd: Optional[str] = None,
) -> dict:
    """
    Run a command without a shell (safer when arguments are not trusted).
    Example: command_args(["ls", "-la", "/tmp"])
    """
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
    )
    out = {
        "returncode": result.returncode,
        "stdout": result.stdout.rstrip("\n"),
        "stderr": result.stderr.rstrip("\n"),
    }
    if check and result.returncode != 0:
        raise CommandError(" ".join(args), result.returncode, out["stdout"], out["stderr"])
    return out

__all__ = ["command", "command_args", "CommandError"]