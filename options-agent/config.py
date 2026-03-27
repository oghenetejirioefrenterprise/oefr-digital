"""
Options Agent — Central Configuration
All tunable parameters live here. No need to touch other files.
"""

import os
from dataclasses import dataclass, field
from typing import List

# ─── IBKR Connection ─────────────────────────────────────────────────────────
IBKR_HOST = os.getenv("IBKR_HOST", "ib-gateway")
IBKR_PORT = int(os.getenv("IBKR_PORT", "4003"))
IBKR_CLIENT_ID = int(os.getenv("IBKR_CLIENT_ID", "20"))  # unique — don't collide with entryexpert (10/11)

# ─── Underlying ───────────────────────────────────────────────────────────────
UNDERLYING = os.getenv("UNDERLYING", "SPX")          # SPX or SPY
EXCHANGE   = "CBOE" if UNDERLYING == "SPX" else "SMART"

# ─── Strategy Selection ───────────────────────────────────────────────────────
# Options: "BWB" (Broken Wing Butterfly), "CONDOR" (0DTE Iron Condor), "BOTH"
ACTIVE_STRATEGY = os.getenv("ACTIVE_STRATEGY", "BWB")

# ─── BWB (Broken Wing Butterfly) Config ───────────────────────────────────────
@dataclass
class BWBConfig:
    dte_target: int       = 7       # days to expiry at entry
    dte_min: int          = 5       # don't enter if DTE < this
    qty: int              = 1       # number of spreads
    # Strike selection (delta-based, hybrid with floor)
    short_delta_target: float = 0.25   # target delta for short (middle) strikes (absolute)
    min_wing_width: int       = 10     # minimum pts between short and broken wing
    min_net_credit: float     = 0.10   # minimum credit per share to enter
    # Exit rules
    profit_target_pct: float  = 0.50   # close at 50% of max profit
    stop_loss_pct: float      = 2.00   # close at 2x premium received
    max_dte_hold: int         = 1      # force-close if DTE drops to this
    # Entry filters
    min_iv_rank: float    = 20.0    # don't enter if IV rank < 20
    max_iv_rank: float    = 85.0    # don't enter if IV rank > 85

BWB = BWBConfig()

# ─── 0DTE Iron Condor Config ──────────────────────────────────────────────────
@dataclass
class CondorConfig:
    delta_target: float   = 0.10    # sell at ~10-delta strikes
    spread_width: int     = 5       # pts wide each side (SPX)
    qty: int              = 1
    entry_time_start: str = "09:45" # ET — don't enter before this
    entry_time_end: str   = "10:15" # ET — don't enter after this
    # Exit rules
    profit_target_pct: float = 0.50  # 50% of credit
    stop_loss_mult: float    = 2.0   # 2x credit received
    force_close_time: str    = "15:45"  # EOD force-close

CONDOR = CondorConfig()

# ─── Risk / Position Sizing ───────────────────────────────────────────────────
MAX_CONCURRENT_POSITIONS = int(os.getenv("MAX_CONCURRENT", "2"))
MAX_DAILY_LOSS_USD        = float(os.getenv("MAX_DAILY_LOSS", "500"))   # hard stop trading for the day
MAX_POSITION_RISK_USD     = float(os.getenv("MAX_POSITION_RISK", "2500"))  # per-trade max loss

# ─── Scheduling ───────────────────────────────────────────────────────────────
# Times in ET (America/New_York)
MARKET_OPEN_TIME   = "09:30"
MARKET_CLOSE_TIME  = "16:00"
SCAN_INTERVAL_SECS = int(os.getenv("SCAN_INTERVAL", "60"))   # how often to scan for new setups
MONITOR_INTERVAL_SECS = int(os.getenv("MONITOR_INTERVAL", "30"))  # how often to check open positions

# ─── Notifications (Telegram) ─────────────────────────────────────────────────
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ─── Misc ─────────────────────────────────────────────────────────────────────
LOG_LEVEL   = os.getenv("LOG_LEVEL", "INFO")
DATA_DIR    = os.getenv("DATA_DIR", "/app/data")
LOG_DIR     = os.getenv("LOG_DIR", "/app/logs")
DRY_RUN     = os.getenv("DRY_RUN", "false").lower() == "true"  # set true to paper-trade logic only
