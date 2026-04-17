"""File-system operations — read, write, edit, list.

All paths are resolved relative to *workspace_root* and must stay within
that boundary.  Path traversal is blocked with a ValueError.  A short
denylist of home-directory secrets (ssh keys, cloud credentials, shell
rc files) is enforced regardless of workspace layout.
"""
from __future__ import annotations

from pathlib import Path

MAX_READ_BYTES = 50 * 1024  # 50 KB
MAX_DIR_ENTRIES = 200


def _deny_paths() -> list[Path]:
    """Sensitive home-directory paths that tools must never touch."""
    home = Path.home()
    return [
        home / ".ssh",
        home / ".aws",
        home / ".gnupg",
        home / ".docker",
        home / ".config" / "gcloud",
        home / ".config" / "solana",
        home / ".kube",
        home / ".profile",
        home / ".bashrc",
        home / ".zshrc",
        home / ".bash_history",
        home / ".zsh_history",
        home / ".netrc",
        home / ".pgpass",
    ]


def _resolve(path: str, workspace_root: Path) -> Path:
    """Resolve *path* relative to workspace_root.  Block traversal and secrets."""
    resolved = (workspace_root / path).resolve()
    ws = workspace_root.resolve()
    # Path.is_relative_to handles symlink prefix confusion that the
    # older startswith check missed.
    if resolved != ws and not resolved.is_relative_to(ws):
        raise ValueError(
            f"Path traversal blocked: '{path}' resolves outside workspace"
        )
    for deny in _deny_paths():
        try:
            deny_resolved = deny.resolve()
        except OSError:
            continue
        if resolved == deny_resolved or resolved.is_relative_to(deny_resolved):
            raise ValueError(
                f"Access denied: '{path}' targets a protected system path"
            )
    return resolved


# ── read_file ───────────────────────────────────────────────────────

def read_file(path: str, workspace_root: Path) -> str:
    """Read a file and return its contents with line numbers (cat -n style).

    Caps output at 50 KB.  Raises FileNotFoundError for missing files and
    ValueError for paths that escape the workspace.
    """
    target = _resolve(path, workspace_root)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not target.is_file():
        raise ValueError(f"Not a file: {path}")

    raw = target.read_bytes()
    if len(raw) > MAX_READ_BYTES:
        text = raw[:MAX_READ_BYTES].decode("utf-8", errors="replace")
        truncated = True
    else:
        text = raw.decode("utf-8", errors="replace")
        truncated = False

    lines = text.splitlines()
    numbered = [f"{i + 1}\t{line}" for i, line in enumerate(lines)]
    result = "\n".join(numbered)
    if truncated:
        result += f"\n\n[truncated — file exceeds {MAX_READ_BYTES // 1024} KB]"
    return result


# ── write_file ──────────────────────────────────────────────────────

def write_file(path: str, content: str, workspace_root: Path) -> str:
    """Create or overwrite a file.  Creates parent directories as needed.

    Returns a confirmation string with the number of bytes written.
    """
    target = _resolve(path, workspace_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Wrote {len(content.encode('utf-8'))} bytes to {path}"


# ── edit_file ───────────────────────────────────────────────────────

def edit_file(path: str, old_text: str, new_text: str, workspace_root: Path) -> str:
    """Find-and-replace in a file.

    Raises FileNotFoundError if the file does not exist, ValueError if
    *old_text* is not found or appears more than once (ambiguous edit).
    """
    target = _resolve(path, workspace_root)
    if not target.exists():
        raise FileNotFoundError(f"File not found: {path}")

    content = target.read_text(encoding="utf-8")
    count = content.count(old_text)
    if count == 0:
        raise ValueError(f"old_text not found in {path}")
    if count > 1:
        raise ValueError(
            f"old_text appears {count} times in {path} — provide more context to make it unique"
        )

    updated = content.replace(old_text, new_text, 1)
    target.write_text(updated, encoding="utf-8")
    return f"Edited {path} — replaced 1 occurrence"


# ── list_directory ──────────────────────────────────────────────────

def list_directory(path: str, workspace_root: Path) -> str:
    """List directory contents showing type, name, and size.

    Returns at most 200 entries.
    """
    target = _resolve(path, workspace_root)
    if not target.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    if not target.is_dir():
        raise ValueError(f"Not a directory: {path}")

    entries: list[str] = []
    for i, item in enumerate(sorted(target.iterdir())):
        if i >= MAX_DIR_ENTRIES:
            entries.append(f"... ({len(list(target.iterdir()))} total, showing first {MAX_DIR_ENTRIES})")
            break
        if item.is_dir():
            entries.append(f"[dir]  {item.name}/")
        elif item.is_file():
            size = item.stat().st_size
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            entries.append(f"[file] {item.name}  ({size_str})")
        else:
            entries.append(f"[other] {item.name}")

    if not entries:
        return f"{path} is empty"
    return "\n".join(entries)
