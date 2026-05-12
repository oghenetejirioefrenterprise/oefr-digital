"""Cross-workspace registry.

Tracks other Trinity workspaces on this machine so the memory agent can
search across them when local recall is insufficient. Auto-scans
``~/apps/*/.trinity/`` and persists the index at ``~/.trinity/workspaces.json``.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from trinity._io import atomic_write_json


def _registry_path() -> Path:
    return Path.home() / ".trinity" / "workspaces.json"


def _load_registry() -> dict[str, dict[str, Any]]:
    p = _registry_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_registry(reg: dict[str, dict[str, Any]]) -> None:
    atomic_write_json(_registry_path(), reg)


def scan_workspaces(root: Path | None = None) -> list[Path]:
    """Discover Trinity workspaces under a root directory (default: ~/apps)."""
    if root is None:
        root = Path.home() / "apps"
    if not root.exists():
        return []
    found: list[Path] = []
    for sub in root.iterdir():
        if not sub.is_dir():
            continue
        if (sub / ".trinity").is_dir():
            found.append(sub)
    return found


def rescan(
    root: Path | None = None,
    current: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Refresh the registry. Excludes *current* workspace (self-reference)."""
    reg = _load_registry()
    now = dt.datetime.now().isoformat(timespec="seconds")
    current_resolved = current.resolve() if current else None

    for ws in scan_workspaces(root):
        resolved = ws.resolve()
        if current_resolved and resolved == current_resolved:
            continue
        name = ws.name
        entry = reg.get(name, {})
        entry["path"] = str(resolved)
        entry["last_seen"] = now

        toml_path = resolved / "trinity.toml"
        if toml_path.exists():
            try:
                import tomllib
                with toml_path.open("rb") as f:
                    data = tomllib.load(f)
                entry["company"] = data.get("company", {}).get("name", "")
                entry["description"] = data.get("company", {}).get("description", "")
            except Exception:
                pass
        reg[name] = entry

    _save_registry(reg)
    return reg


def list_workspaces(current: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return registry entries, excluding *current* workspace if provided."""
    reg = _load_registry()
    if current is None:
        return reg
    current_resolved = current.resolve()
    return {
        name: info for name, info in reg.items()
        if Path(info.get("path", "")).resolve() != current_resolved
    }


def get_workspace_path(name: str) -> Path | None:
    """Resolve a workspace name to its root path, if registered."""
    info = _load_registry().get(name)
    if info and "path" in info:
        p = Path(info["path"])
        if p.exists():
            return p
    return None
