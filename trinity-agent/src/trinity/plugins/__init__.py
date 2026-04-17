"""Plugin infrastructure: generic registry + spec dataclasses + discovery."""
from __future__ import annotations

from .discovery import scan
from .registry import AlreadyRegistered, NotRegistered, Registry

__all__ = ["Registry", "AlreadyRegistered", "NotRegistered", "scan"]
