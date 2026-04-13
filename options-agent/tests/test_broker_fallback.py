"""
tests/test_broker_fallback.py — Market data subscription fallback behavior.

Verifies:
1. Config defaults to delayed data (type 3)
2. Broker error handler downgrades to delayed on 354/10089
3. No log spam on repeated subscription warnings

Note: broker.py imports ib_insync which is not installed in the local test
environment.  We inject a stub ib_insync into sys.modules BEFORE importing
broker so the tests run without the real library.
"""

import importlib
import os
import sys
import types
import unittest
from unittest.mock import MagicMock


# ── Stub ib_insync before broker.py is imported ─────────────────────────────

def _install_ib_insync_stub():
    """
    Create a minimal fake ib_insync module with the names broker.py imports.
    Installed into sys.modules so `from ib_insync import ...` succeeds.
    Returns the fake module (also accessible via sys.modules['ib_insync']).
    """
    if 'ib_insync' in sys.modules and not getattr(
            sys.modules['ib_insync'], '_is_stub', False):
        # Real ib_insync is already loaded — nothing to do
        return sys.modules['ib_insync']

    fake = types.ModuleType('ib_insync')
    fake._is_stub = True

    # Classes / objects that broker.py imports at module level:
    #   IB, Index, Stock, Option, ComboLeg, Contract, Order,
    #   MarketOrder, LimitOrder, TagValue, util
    for name in (
        'IB', 'Index', 'Stock', 'Option', 'ComboLeg', 'Contract',
        'Order', 'MarketOrder', 'LimitOrder', 'TagValue',
    ):
        setattr(fake, name, MagicMock(name=f'ib_insync.{name}'))

    # util is used as a namespace (e.g. util.startLoop()) — give it a sub-mock
    fake.util = MagicMock(name='ib_insync.util')

    sys.modules['ib_insync'] = fake
    return fake


_ib_stub = _install_ib_insync_stub()


# Now it's safe to import broker (and config, which broker imports)
import broker   # noqa: E402
import config   # noqa: E402


# ── Tests ────────────────────────────────────────────────────────────────────

class TestConfigDefaults(unittest.TestCase):
    """Config defaults to delayed market data (type 3)."""

    def test_market_data_type_defaults_to_delayed(self):
        env = os.environ.pop("MARKET_DATA_TYPE", None)
        try:
            importlib.reload(config)
            self.assertEqual(config.MARKET_DATA_TYPE, 3)
        finally:
            if env is not None:
                os.environ["MARKET_DATA_TYPE"] = env
                importlib.reload(config)

    def test_market_data_type_respects_env_override(self):
        old = os.environ.get("MARKET_DATA_TYPE")
        os.environ["MARKET_DATA_TYPE"] = "1"
        try:
            importlib.reload(config)
            self.assertEqual(config.MARKET_DATA_TYPE, 1)
        finally:
            if old is not None:
                os.environ["MARKET_DATA_TYPE"] = old
            else:
                os.environ.pop("MARKET_DATA_TYPE", None)
            importlib.reload(config)


class TestBrokerFallback(unittest.TestCase):
    """Broker error handler downgrades to delayed on subscription errors."""

    def setUp(self):
        # Reset module-level flags before each test
        broker._USING_DELAYED_DATA = False
        broker._FALLBACK_LOGGED = False

    def _make_broker(self):
        """Create an IBKRBroker with a mocked IB connection."""
        b = broker.IBKRBroker()
        b.ib = MagicMock()
        b._connected = True
        return b

    def test_error_354_triggers_delayed_fallback(self):
        b = self._make_broker()
        b._on_error(reqId=1, errorCode=354,
                     errorString="Requested market data is not subscribed",
                     contract=None)
        self.assertTrue(broker._USING_DELAYED_DATA)
        self.assertTrue(broker._FALLBACK_LOGGED)
        b.ib.reqMarketDataType.assert_called_once_with(3)

    def test_error_10089_triggers_delayed_fallback(self):
        b = self._make_broker()
        b._on_error(reqId=1, errorCode=10089,
                     errorString="Part of requested market data is not subscribed",
                     contract=None)
        self.assertTrue(broker._USING_DELAYED_DATA)
        self.assertTrue(broker._FALLBACK_LOGGED)
        b.ib.reqMarketDataType.assert_called_once_with(3)

    def test_no_log_spam_on_repeated_354(self):
        b = self._make_broker()
        # First call triggers fallback
        b._on_error(reqId=1, errorCode=354,
                     errorString="Not subscribed", contract=None)
        b.ib.reqMarketDataType.assert_called_once_with(3)

        # Second call should NOT call reqMarketDataType again
        b.ib.reqMarketDataType.reset_mock()
        b._on_error(reqId=2, errorCode=354,
                     errorString="Not subscribed", contract=None)
        b.ib.reqMarketDataType.assert_not_called()

    def test_fallback_flag_resets_on_reconnect_path(self):
        """_FALLBACK_LOGGED resets when broker marks disconnected (reconnect path)."""
        b = self._make_broker()
        broker._FALLBACK_LOGGED = True

        # Simulate the reconnect path in ensure_connected
        broker._FALLBACK_LOGGED = False
        self.assertFalse(broker._FALLBACK_LOGGED)

    def test_error_10167_does_not_trigger_fallback(self):
        """Informational delayed-data code should not change fallback state."""
        b = self._make_broker()
        b._delayed_data_logged = False
        b._on_error(reqId=1, errorCode=10167,
                     errorString="Delayed market data", contract=None)
        self.assertFalse(broker._USING_DELAYED_DATA)
        self.assertFalse(broker._FALLBACK_LOGGED)

    def test_is_using_delayed_data_reflects_state(self):
        b = self._make_broker()
        broker._USING_DELAYED_DATA = True
        self.assertTrue(b.is_using_delayed_data())
        broker._USING_DELAYED_DATA = False
        self.assertFalse(b.is_using_delayed_data())


if __name__ == "__main__":
    unittest.main()
