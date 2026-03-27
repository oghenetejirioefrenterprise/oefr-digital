"""
state_writer.py — Dashboard State Persistence
Writes agent state to JSON files consumed by the dashboard.
Called by agent.py after every scan/monitor cycle.
All writes are atomic (write to temp, rename) to prevent partial reads.
"""

import json
import os
import copy
import tempfile
import logging
from datetime import datetime
from typing import Optional, List

log = logging.getLogger("state_writer")

DATA_DIR = os.getenv("DATA_DIR", "/app/data")

POSITIONS_FILE     = os.path.join(DATA_DIR, "positions.json")
PORTFOLIO_FILE     = os.path.join(DATA_DIR, "portfolio.json")
CONFIG_FILE        = os.path.join(DATA_DIR, "agent_config.json")
TRADE_HISTORY_FILE = os.path.join(DATA_DIR, "trade_history.json")
HEARTBEAT_FILE     = os.path.join(DATA_DIR, "heartbeat.json")

# Maximum number of trades to keep in trade_history.json (rolling window)
MAX_HISTORY_TRADES = 500


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _atomic_write(path: str, data) -> None:
    """Write JSON atomically — write to a temp file then rename."""
    _ensure_data_dir()
    dir_path = os.path.dirname(path)
    try:
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp_path, path)
        except Exception:
            os.unlink(tmp_path)
            raise
    except Exception as e:
        log.warning(f"state_writer: could not write {path}: {e}")


def _safe_position(pos: dict) -> dict:
    """Strip non-serializable objects (ib_insync Trade/Contract objects etc.)"""
    p = dict(pos)
    # Remove known non-serializable ib_insync fields
    for key in ("trade", "contract", "order", "ticker"):
        p.pop(key, None)
    # Sanitize any remaining non-primitive values
    clean = {}
    for k, v in p.items():
        if isinstance(v, (str, int, float, bool, type(None))):
            clean[k] = v
        elif isinstance(v, (list, dict)):
            try:
                json.dumps(v)
                clean[k] = v
            except (TypeError, ValueError):
                clean[k] = str(v)
        else:
            clean[k] = str(v)
    return clean


# ─── Public API ───────────────────────────────────────────────────────────────

def write_positions(positions: list) -> None:
    """Write current open positions list to positions.json."""
    safe_positions = [_safe_position(p) for p in positions]
    _atomic_write(POSITIONS_FILE, safe_positions)


def write_portfolio(
    spx_price: Optional[float] = None,
    unrealized: float = 0.0,
    realized: float = 0.0,
    daily_pnl: float = 0.0,
    account_ids: Optional[List[str]] = None,
    iv_rank: Optional[float] = None,
) -> None:
    """Write portfolio snapshot to portfolio.json."""
    data = {
        "timestamp": datetime.now().isoformat(),
        "spx_price": spx_price,
        "unrealized_pnl": round(unrealized, 2),
        "realized_pnl": round(realized, 2),
        "daily_pnl": round(daily_pnl, 2),
        "account_ids": account_ids or [],
        "iv_rank": iv_rank,
    }
    _atomic_write(PORTFOLIO_FILE, data)


def write_config(
    strategy: str,
    underlying: str,
    dry_run: bool,
    max_positions: int,
    max_daily_loss: float,
    max_position_risk: float,
    scan_interval: int,
    start_time: datetime,
) -> None:
    """Write agent configuration snapshot to agent_config.json."""
    data = {
        "strategy": strategy,
        "underlying": underlying,
        "dry_run": dry_run,
        "max_positions": max_positions,
        "max_daily_loss": max_daily_loss,
        "max_position_risk": max_position_risk,
        "scan_interval": scan_interval,
        "start_time": start_time.isoformat() if isinstance(start_time, datetime) else str(start_time),
        "uptime_seconds": int((datetime.now() - start_time).total_seconds()) if isinstance(start_time, datetime) else 0,
    }
    _atomic_write(CONFIG_FILE, data)


def append_closed_trade(position: dict, pnl: float, reason: str) -> None:
    """Append a closed trade to trade_history.json (rolling, persists across days)."""
    _ensure_data_dir()
    # Load existing history
    history = []
    if os.path.exists(TRADE_HISTORY_FILE):
        try:
            with open(TRADE_HISTORY_FILE) as f:
                history = json.load(f)
            if not isinstance(history, list):
                history = []
        except Exception:
            history = []

    safe_pos = _safe_position(position)
    entry = {
        **safe_pos,
        "realized_pnl": round(pnl, 2),
        "exit_reason": reason,
        "exit_time": position.get("exit_time", datetime.now().isoformat()),
        "win": pnl > 0,
    }
    history.append(entry)

    # Keep rolling window
    if len(history) > MAX_HISTORY_TRADES:
        history = history[-MAX_HISTORY_TRADES:]

    _atomic_write(TRADE_HISTORY_FILE, history)


def write_heartbeat(mode: str = "trading") -> None:
    """Write a heartbeat timestamp + mode. Called from the main loop to signal liveness."""
    _atomic_write(HEARTBEAT_FILE, {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
    })
