"""CEO orchestration helpers — dispatch downstream employees as subprocesses."""
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]


class DispatchError(Exception):
    """Raised when a dispatched employee subprocess fails."""


def dispatch_employee(employee: str, task: str, timeout_sec: int = 3600) -> str:
    """Spawn `trinity run "<task>" -e <employee>` from the workspace.

    Returns stdout on success. Raises DispatchError on non-zero exit.
    """
    cmd = ["trinity", "run", task, "-e", employee]
    result = subprocess.run(
        cmd,
        cwd=str(WORKSPACE),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    if result.returncode != 0:
        raise DispatchError(
            f"trinity run -e {employee} failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout
