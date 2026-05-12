"""Shell command execution."""
from __future__ import annotations

import subprocess
from pathlib import Path


def run_command(
    command: str,
    workspace_root: Path,
    cwd: str = "",
    timeout: int = 120,
) -> str:
    """Run a shell command and return combined stdout + stderr.

    If *cwd* is given and relative, it is resolved against *workspace_root*.
    Commands are executed via ``/bin/bash -c`` with the specified timeout
    (default 120 seconds).
    """
    if cwd:
        work_dir = Path(cwd)
        if not work_dir.is_absolute():
            work_dir = (workspace_root / work_dir).resolve()
    else:
        work_dir = workspace_root.resolve()

    if not work_dir.is_dir():
        raise FileNotFoundError(f"Working directory does not exist: {work_dir}")

    try:
        result = subprocess.run(
            ["/bin/bash", "-c", command],
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"[command timed out after {timeout}s]"

    output_parts: list[str] = []
    if result.stdout:
        output_parts.append(result.stdout)
    if result.stderr:
        output_parts.append(result.stderr)

    combined = "\n".join(output_parts).strip()
    if result.returncode != 0:
        combined = f"[exit code {result.returncode}]\n{combined}"

    return combined or "[no output]"
