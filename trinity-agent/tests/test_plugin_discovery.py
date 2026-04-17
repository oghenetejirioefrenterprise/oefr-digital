"""Tests for entry-point discovery on the Registry."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from trinity.plugins.registry import Registry


def _fake_entry_point(name: str, load_returns):
    """Build a stand-in for importlib.metadata.EntryPoint."""
    ep = MagicMock()
    ep.name = name
    ep.load.return_value = load_returns
    return ep


def test_discover_loads_entry_points():
    reg: Registry[str] = Registry("trinity.fake")
    ep_alpha = _fake_entry_point("alpha", "value-a")

    with patch("trinity.plugins.discovery.entry_points") as eps:
        eps.return_value = [ep_alpha]
        errors = reg.discover()

    assert errors == []
    assert "alpha" in reg
    assert reg.get("alpha") == "value-a"
    assert reg.source_of("alpha") == "entry_points"
    # Ensure the group kwarg is propagated — a regression to the
    # deprecated no-arg form would otherwise sneak past the other checks.
    eps.assert_called_once_with(group="trinity.fake")


def test_discover_handles_load_failure():
    reg: Registry[str] = Registry("trinity.fake")
    bad_ep = MagicMock()
    bad_ep.name = "broken"
    bad_ep.load.side_effect = ImportError("boom")

    with patch("trinity.plugins.discovery.entry_points") as eps:
        eps.return_value = [bad_ep]
        errors = reg.discover()

    assert len(errors) == 1
    assert errors[0][0] == "broken"
    assert "boom" in errors[0][1]
    assert "broken" not in reg


def test_discover_does_not_clobber_existing():
    reg: Registry[str] = Registry("trinity.fake")
    reg.register("alpha", "builtin-value", source="builtin")
    ep_alpha = _fake_entry_point("alpha", "entry-value")

    with patch("trinity.plugins.discovery.entry_points") as eps:
        eps.return_value = [ep_alpha]
        errors = reg.discover()

    assert len(errors) == 1
    assert errors[0][0] == "alpha"
    assert "already registered" in errors[0][1].lower()
    # The builtin wins.
    assert reg.get("alpha") == "builtin-value"
    assert reg.source_of("alpha") == "builtin"


def test_discover_with_override_replaces():
    reg: Registry[str] = Registry("trinity.fake")
    reg.register("alpha", "builtin-value", source="builtin")
    ep_alpha = _fake_entry_point("alpha", "entry-value")

    with patch("trinity.plugins.discovery.entry_points") as eps:
        eps.return_value = [ep_alpha]
        errors = reg.discover(override=True)

    assert errors == []
    assert reg.get("alpha") == "entry-value"
    assert reg.source_of("alpha") == "entry_points"
