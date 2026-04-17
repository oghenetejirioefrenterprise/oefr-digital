"""Tests for the generic plugin registry."""
from __future__ import annotations

import pytest

from trinity.plugins.registry import Registry, AlreadyRegistered, NotRegistered


def test_register_and_get():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "value-a")
    assert reg.get("alpha") == "value-a"


def test_get_unknown_raises():
    reg: Registry[str] = Registry("test.group")
    with pytest.raises(NotRegistered):
        reg.get("missing")


def test_double_register_without_override_raises():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "first")
    with pytest.raises(AlreadyRegistered):
        reg.register("alpha", "second")


def test_double_register_with_override_succeeds():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "first")
    reg.register("alpha", "second", override=True)
    assert reg.get("alpha") == "second"


def test_names_returns_sorted():
    reg: Registry[str] = Registry("test.group")
    reg.register("charlie", "c")
    reg.register("alpha", "a")
    reg.register("bravo", "b")
    assert reg.names() == ["alpha", "bravo", "charlie"]


def test_unregister_removes_entry():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "a")
    reg.unregister("alpha")
    assert reg.names() == []
    with pytest.raises(NotRegistered):
        reg.get("alpha")


def test_unregister_unknown_raises():
    reg: Registry[str] = Registry("test.group")
    with pytest.raises(NotRegistered):
        reg.unregister("missing")


def test_source_tracking():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "a", source="builtin")
    reg.register("bravo", "b", source="entry_points")
    assert reg.source_of("alpha") == "builtin"
    assert reg.source_of("bravo") == "entry_points"


def test_contains():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "a")
    assert "alpha" in reg
    assert "missing" not in reg


def test_items_returns_copy():
    reg: Registry[str] = Registry("test.group")
    reg.register("alpha", "a")
    snapshot = reg.items()
    snapshot["beta"] = "b"  # mutate the returned dict
    assert "beta" not in reg  # internal state unaffected
