"""Expand ``@``-prefixed inline references in incoming chat messages.

Supported forms:

- ``@file:path/to/x.py``  — file contents (path resolved against the
  workspace root). 16 KB cap per file.
- ``@folder:path``        — short directory listing (top 200 entries).
- ``@url:https://...``    — fetched body via the existing web tool.
  8 KB cap.
- ``@git:<rev>``          — ``git show <rev>``. 8 KB cap.
- ``@diff``               — ``git diff`` working tree.
- ``@staged``             — ``git diff --cached``.

A workspace-wide budget caps total expansion at 24 KB; references past
that point are replaced with a ``[skipped: budget]`` marker.

A sensitive-path blocklist (.ssh, .aws, credentials, …) makes such
references redact rather than read. The marker tells the agent why so it
can ask the user for the value if needed.
"""
from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


# A reference token consists of the ``@`` prefix, a kind, an optional
# colon and value. The value runs up to whitespace; URLs may contain
# colons / slashes.
_REF_RE = re.compile(
    r"@(file|folder|url|git):(\S+)|@(diff|staged)\b",
    re.IGNORECASE,
)

_SENSITIVE_TOKENS = (
    ".ssh", ".aws", ".gnupg", ".pgpass", ".netrc", ".profile",
    "credentials", "secrets", "private_key", "id_rsa", "id_ed25519",
)

PER_FILE_CAP = 16 * 1024
PER_OTHER_CAP = 8 * 1024
TOTAL_BUDGET = 24 * 1024
FOLDER_LIST_LIMIT = 200


@dataclass
class Expansion:
    kind: str
    target: str
    body: str
    redacted: bool = False


def _is_sensitive(target: str) -> bool:
    t = target.lower()
    return any(tok in t for tok in _SENSITIVE_TOKENS)


def _resolve_workspace_path(workspace_root: Path, target: str) -> Path | None:
    """Resolve ``target`` to an absolute path inside the workspace.

    Refuses paths that escape the workspace root after resolution.
    """
    candidate = (workspace_root / target).expanduser()
    try:
        resolved = candidate.resolve()
    except (OSError, RuntimeError):
        return None
    try:
        resolved.relative_to(workspace_root.resolve())
    except ValueError:
        # Path escapes workspace root.
        return None
    return resolved


def _expand_file(workspace_root: Path, target: str) -> Expansion:
    if _is_sensitive(target):
        return Expansion("file", target, "[redacted: sensitive path]", True)
    path = _resolve_workspace_path(workspace_root, target)
    if path is None or not path.is_file():
        return Expansion("file", target, "[not found or outside workspace]")
    try:
        data = path.read_text(errors="replace")
    except (OSError, UnicodeDecodeError) as e:
        return Expansion("file", target, f"[read failed: {e}]")
    if len(data) > PER_FILE_CAP:
        data = data[:PER_FILE_CAP] + f"\n[truncated at {PER_FILE_CAP} bytes]"
    return Expansion("file", target, data)


def _expand_folder(workspace_root: Path, target: str) -> Expansion:
    if _is_sensitive(target):
        return Expansion("folder", target, "[redacted: sensitive path]", True)
    path = _resolve_workspace_path(workspace_root, target)
    if path is None or not path.is_dir():
        return Expansion("folder", target, "[not found or outside workspace]")
    try:
        entries = sorted(os.listdir(path))[:FOLDER_LIST_LIMIT]
    except OSError as e:
        return Expansion("folder", target, f"[listdir failed: {e}]")
    lines = []
    for name in entries:
        sub = path / name
        try:
            kind = "d" if sub.is_dir() else "f"
            size = sub.stat().st_size if sub.is_file() else 0
        except OSError:
            kind, size = "?", 0
        lines.append(f"{kind} {size:>10}  {name}")
    return Expansion("folder", target, "\n".join(lines))


def _expand_url(target: str) -> Expansion:
    """Best-effort fetch via the existing web tool's helper."""
    try:
        from trinity.tools.web import fetch_url  # type: ignore
    except Exception:
        try:
            import urllib.request
            req = urllib.request.Request(
                target, headers={"User-Agent": "Trinity-Agent/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read(PER_OTHER_CAP + 1).decode(errors="replace")
        except Exception as e:
            return Expansion("url", target, f"[fetch failed: {e}]")
    else:
        try:
            body = fetch_url(target, max_bytes=PER_OTHER_CAP + 1)  # type: ignore[call-arg]
        except Exception as e:
            return Expansion("url", target, f"[fetch failed: {e}]")
    if len(body) > PER_OTHER_CAP:
        body = body[:PER_OTHER_CAP] + f"\n[truncated at {PER_OTHER_CAP} bytes]"
    return Expansion("url", target, body)


def _git(workspace_root: Path, args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"[git failed: {e}]"
    if proc.returncode != 0:
        return f"[git error: {proc.stderr.strip()[:300]}]"
    out = proc.stdout
    if len(out) > PER_OTHER_CAP:
        out = out[:PER_OTHER_CAP] + f"\n[truncated at {PER_OTHER_CAP} bytes]"
    return out


def _expand_git(workspace_root: Path, target: str) -> Expansion:
    # target = revision or refspec
    body = _git(workspace_root, ["show", "--stat", target])
    return Expansion("git", target, body)


def _expand_diff(workspace_root: Path) -> Expansion:
    return Expansion("diff", "(working tree)", _git(workspace_root, ["diff"]))


def _expand_staged(workspace_root: Path) -> Expansion:
    return Expansion("staged", "(index)", _git(workspace_root, ["diff", "--cached"]))


def expand_references(text: str, workspace_root: Path) -> str:
    """Expand any ``@``-references in *text* into appended fenced blocks.

    The original text is preserved verbatim (the references stay in
    place). A ``# Inline references`` section is appended at the end with
    one fenced block per resolved reference. Returns the original text
    unchanged if no references are found.
    """
    if not text or "@" not in text:
        return text

    expansions: list[Expansion] = []
    used = 0
    seen: set[tuple[str, str]] = set()

    for m in _REF_RE.finditer(text):
        kind = (m.group(1) or m.group(3) or "").lower()
        target = (m.group(2) or "").strip()

        key = (kind, target)
        if key in seen:
            continue
        seen.add(key)

        if used >= TOTAL_BUDGET:
            expansions.append(Expansion(kind, target, "[skipped: budget]"))
            continue

        try:
            if kind == "file":
                exp = _expand_file(workspace_root, target)
            elif kind == "folder":
                exp = _expand_folder(workspace_root, target)
            elif kind == "url":
                exp = _expand_url(target)
            elif kind == "git":
                exp = _expand_git(workspace_root, target)
            elif kind == "diff":
                exp = _expand_diff(workspace_root)
            elif kind == "staged":
                exp = _expand_staged(workspace_root)
            else:
                continue
        except Exception as e:
            log.debug("reference expansion failed: %s", e)
            exp = Expansion(kind, target, f"[expansion failed: {e}]")

        used += len(exp.body)
        expansions.append(exp)

    if not expansions:
        return text

    blocks = ["", "# Inline references"]
    for exp in expansions:
        header = f"## @{exp.kind}:{exp.target}" if exp.target else f"## @{exp.kind}"
        blocks.append("")
        blocks.append(header)
        blocks.append("```")
        blocks.append(exp.body)
        blocks.append("```")

    return text + "\n" + "\n".join(blocks)
