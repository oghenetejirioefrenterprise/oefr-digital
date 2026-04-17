"""Plugin infrastructure: generic registry + spec dataclasses + discovery."""
from __future__ import annotations

from .discovery import scan
from .registry import AlreadyRegistered, NotRegistered, Registry
from .specs import AgentSpec, ProviderSpec, ToolSpec

__all__ = [
    "Registry",
    "AlreadyRegistered",
    "NotRegistered",
    "scan",
    "AgentSpec",
    "ProviderSpec",
    "ToolSpec",
]
