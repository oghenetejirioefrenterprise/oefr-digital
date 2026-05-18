"""Regression tests for the telegram bot watchdog → supervisor restart path.

Background: on 2026-05-11 a 4-day daemon outage occurred because the bot
watchdog (no successful poll in 600s, triggered by a DNS outage to
api.telegram.org) called ``break`` instead of raising. The supervisor in
``cli.py:cmd_start`` only restarts on ``Exception``, so a clean return
exited the supervisor and left no process to restart. These tests pin
the contract that watchdog timeouts must raise.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import requests

from trinity.telegram import bot as bot_module


def _make_config(tmp_workspace):
    return SimpleNamespace(
        trinity_dir=tmp_workspace / ".trinity",
        telegram=SimpleNamespace(
            get_bot_token=lambda: "test-token-123",
            poll_timeout=1,
            bot_token_env="TEST_TOKEN",
        ),
    )


def test_watchdog_timeout_raises_for_supervisor_restart(tmp_workspace, monkeypatch):
    """Watchdog timeout must raise RuntimeError, not return cleanly.

    Without this, the supervisor's `except Exception` clause never fires
    and the daemon dies permanently the first time the network blips.
    """
    monkeypatch.setattr(bot_module, "WATCHDOG_TIMEOUT_S", 0)

    counter = iter(range(10_000))
    monkeypatch.setattr(bot_module.time, "monotonic", lambda: next(counter))
    monkeypatch.setattr(bot_module.time, "sleep", lambda _s: None)
    monkeypatch.setattr(bot_module.signal, "signal", lambda _sig, _h: None)

    mock_api = MagicMock()
    mock_api.get_me.return_value = {"username": "test_bot", "id": 12345}
    mock_api.delete_webhook.return_value = None
    mock_api.get_updates.side_effect = requests.exceptions.ConnectionError("DNS fail")
    mock_api.reset_session.return_value = None
    monkeypatch.setattr(bot_module, "TelegramAPI", lambda _token: mock_api)

    monkeypatch.setattr(bot_module, "AccessControl", lambda *a, **kw: MagicMock())

    config = _make_config(tmp_workspace)
    handle_message = MagicMock()

    with pytest.raises(RuntimeError, match="Watchdog timeout"):
        bot_module.run_bot(config, handle_message)
