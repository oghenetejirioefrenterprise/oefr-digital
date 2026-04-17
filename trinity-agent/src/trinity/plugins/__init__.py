"""Plugin infrastructure: generic registry + spec dataclasses + discovery."""
from __future__ import annotations

from .registry import AlreadyRegistered, NotRegistered, Registry

__all__ = ["Registry", "AlreadyRegistered", "NotRegistered"]
