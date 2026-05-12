"""Search operations — file glob matching and content regex search."""
from __future__ import annotations

import os
import re
from pathlib import Path

MAX_GLOB_RESULTS = 100
MAX_CONTENT_RESULTS = 50
MAX_LINE_LENGTH = 300

EXCLUDED_DIRS = {"node_modules", ".git", "__pycache__", ".next", "dist", "build"}


def _resolve(path: str, workspace_root: Path) -> Path:
    """Resolve *path* relative to workspace_root.  Block traversal."""
    resolved = (workspace_root / path).resolve()
    ws = workspace_root.resolve()
    if not (resolved == ws or str(resolved).startswith(str(ws) + os.sep)):
        raise ValueError(
            f"Path traversal blocked: '{path}' resolves outside workspace"
        )
    return resolved


def _is_excluded(p: Path) -> bool:
    """Return True if any path component is in the exclusion set."""
    return any(part in EXCLUDED_DIRS for part in p.parts)


def _is_binary(p: Path) -> bool:
    """Cheap binary-file heuristic: look for null bytes in the first 8 KB."""
    try:
        chunk = p.read_bytes()[:8192]
        return b"\x00" in chunk
    except (OSError, PermissionError):
        return True


# ── search_files ────────────────────────────────────────────────────

def search_files(pattern: str, path: str, workspace_root: Path) -> str:
    """Glob search for files matching *pattern* under *path*.

    Returns matching file paths relative to workspace_root, capped at
    100 results.
    """
    base = _resolve(path, workspace_root)
    if not base.is_dir():
        raise ValueError(f"Not a directory: {path}")

    ws = workspace_root.resolve()
    matches: list[str] = []
    for hit in sorted(base.rglob(pattern)):
        if _is_excluded(hit):
            continue
        try:
            rel = hit.relative_to(ws)
        except ValueError:
            continue
        matches.append(str(rel))
        if len(matches) >= MAX_GLOB_RESULTS:
            break

    if not matches:
        return f"No files matching '{pattern}' found under {path}"

    result = "\n".join(matches)
    if len(matches) >= MAX_GLOB_RESULTS:
        result += f"\n\n[results capped at {MAX_GLOB_RESULTS}]"
    return result


# ── search_content ──────────────────────────────────────────────────

def search_content(
    pattern: str,
    path: str,
    workspace_root: Path,
    file_type: str = "",
) -> str:
    """Regex search across file contents under *path*.

    Returns filename:line_number:matching_line, capped at 50 results.
    Skips binary files and excluded directories.
    If *file_type* is given (e.g. "py", "ts"), only searches files with
    that extension.
    """
    base = _resolve(path, workspace_root)
    if not base.is_dir():
        raise ValueError(f"Not a directory: {path}")

    try:
        regex = re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}") from e

    ws = workspace_root.resolve()
    ext_filter = f".{file_type}" if file_type else ""
    results: list[str] = []

    for fpath in sorted(base.rglob("*")):
        if not fpath.is_file():
            continue
        if _is_excluded(fpath):
            continue
        if ext_filter and fpath.suffix != ext_filter:
            continue
        if _is_binary(fpath):
            continue

        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue

        try:
            rel = str(fpath.relative_to(ws))
        except ValueError:
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                display = line.strip()
                if len(display) > MAX_LINE_LENGTH:
                    display = display[:MAX_LINE_LENGTH] + "..."
                results.append(f"{rel}:{line_no}:{display}")
                if len(results) >= MAX_CONTENT_RESULTS:
                    break
        if len(results) >= MAX_CONTENT_RESULTS:
            break

    if not results:
        return f"No matches for /{pattern}/ under {path}"

    output = "\n".join(results)
    if len(results) >= MAX_CONTENT_RESULTS:
        output += f"\n\n[results capped at {MAX_CONTENT_RESULTS}]"
    return output
