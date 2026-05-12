"""Git operations — status, diff, and commit."""
from __future__ import annotations

import subprocess
from pathlib import Path


def _git(args: list[str], workspace_root: Path) -> str:
    """Run a git command in the workspace and return output."""
    result = subprocess.run(
        ["git"] + args,
        cwd=str(workspace_root.resolve()),
        capture_output=True,
        text=True,
        timeout=60,
    )
    output = (result.stdout + "\n" + result.stderr).strip()
    if result.returncode != 0:
        output = f"[exit code {result.returncode}]\n{output}"
    return output or "[no output]"


def git_status(workspace_root: Path) -> str:
    """Return ``git status`` output for the workspace."""
    return _git(["status"], workspace_root)


def git_diff(workspace_root: Path, args: str = "") -> str:
    """Return ``git diff`` output with optional extra arguments.

    *args* is a string that gets split into separate arguments,
    e.g. ``"--stat"`` or ``"HEAD~1"``.
    """
    cmd = ["diff"]
    if args:
        cmd.extend(args.split())
    return _git(cmd, workspace_root)


def git_commit(message: str, files: list[str], workspace_root: Path) -> str:
    """Stage *files* and create a commit with *message*.

    Returns the short commit hash on success.
    """
    if not files:
        return "No files specified — nothing to commit"

    # Stage files
    stage_result = _git(["add", "--"] + files, workspace_root)
    if stage_result.startswith("[exit code"):
        return f"Failed to stage files:\n{stage_result}"

    # Commit
    commit_result = _git(["commit", "-m", message], workspace_root)
    if commit_result.startswith("[exit code"):
        return f"Commit failed:\n{commit_result}"

    # Extract short hash
    hash_result = _git(["rev-parse", "--short", "HEAD"], workspace_root)
    return f"Committed {hash_result.strip()}: {message}"
