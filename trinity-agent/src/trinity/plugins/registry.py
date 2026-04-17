"""Generic named registry with source tracking.

The registry holds name→item mappings and records how each entry arrived
(``"builtin"``, ``"entry_points"``, ``"manual"``). This powers the
``trinity plugins list`` CLI and lets us distinguish first-party defaults
from third-party additions when debugging.
"""
from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class AlreadyRegistered(Exception):
    """Raised when registering a name that already exists without ``override=True``."""


class NotRegistered(KeyError):
    """Raised when looking up a name that is not registered."""


class Registry(Generic[T]):
    """Name→item registry with source tracking.

    ``group`` is the entry-point group name (e.g. ``"trinity.providers"``)
    used by :meth:`discover`.
    """

    def __init__(self, group: str) -> None:
        self.group = group
        self._items: dict[str, T] = {}
        self._sources: dict[str, str] = {}

    def register(
        self,
        name: str,
        item: T,
        *,
        source: str = "manual",
        override: bool = False,
    ) -> None:
        if name in self._items and not override:
            raise AlreadyRegistered(
                f"{self.group}: '{name}' is already registered "
                f"(source={self._sources[name]!r}). "
                f"Pass override=True to replace."
            )
        self._items[name] = item
        self._sources[name] = source

    def unregister(self, name: str) -> None:
        if name not in self._items:
            raise NotRegistered(f"{self.group}: '{name}' is not registered")
        del self._items[name]
        del self._sources[name]

    def get(self, name: str) -> T:
        if name not in self._items:
            raise NotRegistered(
                f"{self.group}: '{name}' is not registered. "
                f"Known: {self.names()}"
            )
        return self._items[name]

    def names(self) -> list[str]:
        return sorted(self._items)

    def items(self) -> dict[str, T]:
        return dict(self._items)

    def source_of(self, name: str) -> str:
        if name not in self._sources:
            raise NotRegistered(f"{self.group}: '{name}' is not registered")
        return self._sources[name]

    def __contains__(self, name: object) -> bool:
        return name in self._items
