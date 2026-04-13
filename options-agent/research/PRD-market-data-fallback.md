# PRD: Market Data Subscription Fallback

**Status:** Completed
**Created:** 2026-04-13
**Priority:** High — blocks safe paper-trading operation

## Changelog

### 2026-04-13 — Verification fix pass
- Previous pass implemented all code changes (safe defaults, broker fallback handler, tests).
- PRD was marked "Completed" but verification was not actually run successfully.
- `tests/test_broker_fallback.py` fails because it imports `broker.py` which imports
  `ib_insync` — a library not installed in the local test environment.
- This pass: fixed tests to stub `ib_insync` before importing broker, ran real verification.
- Verification results (2026-04-13):
  - `python3 -m py_compile tests/test_broker_fallback.py` — PASS
  - `python3 -m py_compile config.py` — PASS
  - `python3 -m pytest tests/test_broker_fallback.py -q` — 8 passed in 0.04s
  - `python3 -c "import config; assert config.MARKET_DATA_TYPE == 3"` — PASS
- Status set to Completed based on actual passing verification.

## Problem

The IBKR live market data subscription (~$4.50/month for SPX options) is not yet active.
When `MARKET_DATA_TYPE=1` (live) is configured, the broker requests live data from IBKR.
Without an active subscription, IBKR returns warning codes 354 ("Requested market data is
not subscribed") and 10089 ("Part of requested market data is not subscribed"). These
warnings spam logs and data requests silently return stale/empty values.

Current issues:
1. `docker-compose.yml` defaults `MARKET_DATA_TYPE` to `1` (live), overriding the safe
   `config.py` default of `3` (delayed).
2. `broker.py` has no handler for error codes 354 or 10089 — they fall through to generic
   error logging and repeat on every data request.
3. `.env` explicitly sets `MARKET_DATA_TYPE=1`.
4. `test_trades.py` forces `MARKET_DATA_TYPE=1`.
5. `broker.py` uses brittle per-request toggling (switching to delayed and back) in
   `get_underlying_price()` and `get_option_price()` for stocks when live is configured.

## Solution

### 1. Safe defaults everywhere
- `docker-compose.yml`: change default from `1` to `3`
- `.env`: change to `MARKET_DATA_TYPE=3` with explanatory comment
- `test_trades.py`: change default from `1` to `3`
- `config.py`: already defaults to `3` — no change needed

### 2. Graceful fallback in broker.py
When IBKR sends error code 354 or 10089 (subscription not active):
- Auto-downgrade to delayed data (type 3) for the session
- Log one clear warning (not per-request spam)
- Set `_USING_DELAYED_DATA = True` so the rest of the agent knows
- Remove the per-request live→delayed→live toggling in `get_underlying_price()` and
  `get_option_price()` — after fallback, the session stays on delayed

### 3. Preserve live-data path
- When subscription is later activated, setting `MARKET_DATA_TYPE=1` in `.env` will
  request live data. If IBKR accepts it (no 354/10089), the agent runs on live.
- The fallback is automatic and requires no code change to enable/disable.

### 4. Documentation
- Update CLAUDE.md to reflect delayed as the default and document fallback behavior.

### 5. Testing
- Add `tests/test_broker_fallback.py` with focused tests for:
  - Config defaults to delayed (type 3)
  - Error handler downgrades to delayed on 354/10089
  - No log spam on repeated subscription warnings

## Non-goals
- No changes to strategy logic, pricing, or order placement
- No changes to the dashboard
- No removal of live data support

## Verification
- `python3 -m py_compile broker.py config.py test_trades.py tests/test_broker_fallback.py` passes
- `python3 -m pytest tests/test_broker_fallback.py -q` passes (8 passed)
- `python3 -c "import config; assert config.MARKET_DATA_TYPE == 3"` passes
- `git status --short -- broker.py docker-compose.yml .env test_trades.py CLAUDE.md research/PRD-market-data-fallback.md tests/test_broker_fallback.py` confirms only the intended tracked/untracked files are in scope for this fix
