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
IBKR_CLIENT_ID = int(os.getenv("IBKR_CLIENT_ID", "30"))  # unique — don't collide with entryexpert (10, 20)

# Market data type: 1=Live, 2=Frozen, 3=Delayed, 4=Delayed Frozen
# Use type 3 (delayed) for paper trading without live subscriptions.
# Use type 1 (live) for production with proper market data subscriptions.
MARKET_DATA_TYPE = int(os.getenv("MARKET_DATA_TYPE", "3"))  # default: delayed

# ─── Underlying ───────────────────────────────────────────────────────────────
UNDERLYING = os.getenv("UNDERLYING", "SPX")          # SPX or SPY
EXCHANGE   = "CBOE" if UNDERLYING == "SPX" else "SMART"

# ─── Strategy Selection ───────────────────────────────────────────────────────
# Options: "BWB", "CONDOR", "CALL_SPREAD", "LONG_CALL", "PUT_CREDIT_SPREAD",
#          "CALENDAR_SPREAD", "JADE_LIZARD",
#          "BOTH" (BWB+CONDOR), "ALL" (all 7 strategies),
#          "SMB" (score-driven auto-selection)
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
    entry_time_end: str   = "10:30" # ET — widened from 10:15 (more opportunity window)
    # Exit rules — optimized for 10%+ returns
    profit_target_pct: float = 0.60  # 60% of credit (was 50% — 0DTE theta decays fast, capture more)
    stop_loss_mult: float    = 1.5   # 1.5x credit received (was 2x — tighter risk on 0DTE)
    force_close_time: str    = "15:45"  # EOD force-close

CONDOR = CondorConfig()

# ─── Bull Call Spread Config ──────────────────────────────────────────────────
@dataclass
class CallSpreadConfig:
    delta_target: float   = 0.45   # long call delta target (near ATM)
    spread_width: int     = 15     # pts between long and short call (was 10 — wider = more profit potential)
    dte_target: int       = 7      # days to expiry at entry
    dte_min: int          = 5      # don't enter if DTE < this
    qty: int              = 1
    # Exit rules — optimized for 10%+ returns
    profit_target_pct: float = 0.75  # close at 75% of max profit (was 50% — directional needs room to run)
    stop_loss_pct: float     = 1.5   # close at 1.5x debit paid (was 2x — tighter risk)
    max_dte_hold: int        = 2     # force-close if DTE drops to this
    min_smb_score: int       = 5     # minimum SMB score to enter
    max_iv_rank: float       = 60.0  # don't buy premium if IV rank > 60

CALL_SPREAD = CallSpreadConfig()

# ─── Long Call Config ─────────────────────────────────────────────────────────
@dataclass
class LongCallConfig:
    delta_target: float   = 0.50   # ATM call
    dte_target: int       = 7      # days to expiry at entry
    dte_min: int          = 5      # don't enter if DTE < this
    qty: int              = 1
    # Exit rules — optimized for 10%+ returns
    profit_target_pct: float = 0.75  # close at 75% gain (was 100% — capture more consistently)
    stop_loss_pct: float     = 0.40  # close if we lose 40% of premium (was 50% — tighter)
    max_dte_hold: int        = 1     # force-close if DTE drops to this
    min_smb_score: int       = 7     # minimum SMB score (strong breakout only)
    max_iv_rank: float       = 45.0  # only buy when vol is cheap

LONG_CALL = LongCallConfig()

# ─── Put Credit Spread Config ────────────────────────────────────────────────
# Best risk-adjusted strategy (Sharpe 0.93, 69% WR at 30-delta).
# Phase 2 grid search optimal: delta=0.30, sw=10, pt=50%, sl=2x.
# With HV>20% filter + qty=3: 17% avg monthly (see data/backtest_report.md).
@dataclass
class PutCreditSpreadConfig:
    delta_target: float   = 0.30   # sell ~30-delta put (Phase 2 optimal — more premium than 15d)
    spread_width: int     = 10     # pts between short and long put
    dte_target: int       = 7      # days to expiry at entry
    dte_min: int          = 5      # don't enter if DTE < this
    qty: int              = 2      # Phase 2 optimal: 2 contracts (sweet spot for $10k capital)
    # Exit rules — Phase 2 optimized
    profit_target_pct: float = 0.50  # close at 50% of credit (grid search optimal)
    stop_loss_pct: float     = 2.00  # close at 2x credit received (wider stop avoids whipsaws)
    max_dte_hold: int        = 1     # force-close if DTE drops to this
    # Entry filters
    min_iv_rank: float    = 25.0    # want elevated premium to sell
    max_iv_rank: float    = 85.0    # don't sell in extreme vol (tail risk)
    max_smb_score: int    = 6       # don't sell puts in breakout (wrong side)

PUT_CREDIT_SPREAD = PutCreditSpreadConfig()

# ─── Calendar Spread Config (NEW) ────────────────────────────────────────────
# Theta play: sell near-term, buy longer-term at same strike.
# Near-term decays faster → profit from theta differential.
@dataclass
class CalendarSpreadConfig:
    delta_target: float    = 0.50   # ATM (max theta differential)
    right: str             = "P"    # use puts (put calendars)
    front_dte_target: int  = 7      # front month: 7 DTE
    front_dte_min: int     = 5      # minimum DTE for front leg
    back_dte_target: int   = 21     # back month: 21 DTE
    back_dte_min: int      = 14     # minimum DTE for back leg
    qty: int               = 1
    # Exit rules
    profit_target_pct: float = 0.25  # 25% of net debit (calendars have limited profit zone)
    stop_loss_pct: float     = 1.00  # 100% of debit (max loss = debit paid)
    min_front_dte_hold: int  = 2     # close when front month hits 2 DTE
    # Entry filters
    min_iv_rank: float    = 25.0    # need moderate vol
    max_iv_rank: float    = 70.0    # not extreme vol (back month gets crushed too)

CALENDAR_SPREAD = CalendarSpreadConfig()

# ─── Jade Lizard Config (NEW) ────────────────────────────────────────────────
# Short OTM put + short call spread. No upside risk if total credit > call spread width.
# Collects premium from both directions.
@dataclass
class JadeLizardConfig:
    put_delta_target: float    = 0.20   # sell ~20-delta put
    call_delta_target: float   = 0.15   # sell ~15-delta call
    call_spread_width: int     = 10     # pts between short and long call
    dte_target: int            = 7      # days to expiry at entry
    dte_min: int               = 5      # don't enter if DTE < this
    qty: int                   = 1
    # Exit rules
    profit_target_pct: float   = 0.50   # close at 50% of total credit
    stop_loss_pct: float       = 1.50   # close at 1.5x total credit
    max_dte_hold: int          = 1      # force-close if DTE drops to this
    # Entry filters
    min_iv_rank: float     = 30.0    # need elevated vol for premium
    max_iv_rank: float     = 85.0    # not extreme vol

JADE_LIZARD = JadeLizardConfig()

# ─── SMB Scorer Config ────────────────────────────────────────────────────────
@dataclass
class SMBConfig:
    rescore_interval_secs: int = 300  # how often to re-run SMB checks (5 min)

SMB = SMBConfig()

# ─── Risk / Position Sizing ───────────────────────────────────────────────────
MAX_CONCURRENT_POSITIONS = int(os.getenv("MAX_CONCURRENT", "4"))     # Phase 2: 4 concurrent (was 2)
MAX_DAILY_LOSS_USD        = float(os.getenv("MAX_DAILY_LOSS", "1000"))  # Phase 2: $1k daily limit (was $500)
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
DRY_RUN     = os.getenv("DRY_RUN", "true").lower() == "true"  # set true to paper-trade logic only


# ─── Config Validation ────────────────────────────────────────────────────────
def validate_config():
    """
    Validate configuration at startup.
    Raises ValueError for critical misconfigurations that would cause bugs.
    """
    errors = []

    # Validate ACTIVE_STRATEGY
    valid_strategies = {"BWB", "CONDOR", "CALL_SPREAD", "LONG_CALL", "PUT_CREDIT_SPREAD",
                        "CALENDAR_SPREAD", "JADE_LIZARD", "BOTH", "ALL", "SMB"}
    if ACTIVE_STRATEGY not in valid_strategies:
        errors.append(f"ACTIVE_STRATEGY '{ACTIVE_STRATEGY}' is not valid. Must be one of: {', '.join(sorted(valid_strategies))}")

    # Critical: max_dte_hold must be LESS than dte_min to prevent same-day exit bug
    # If max_dte_hold >= dte_min, positions would exit immediately after entry
    if BWB.max_dte_hold >= BWB.dte_min:
        errors.append(
            f"BWB config error: max_dte_hold ({BWB.max_dte_hold}) must be < dte_min ({BWB.dte_min})"
        )
    if CALL_SPREAD.max_dte_hold >= CALL_SPREAD.dte_min:
        errors.append(
            f"CALL_SPREAD config error: max_dte_hold ({CALL_SPREAD.max_dte_hold}) must be < dte_min ({CALL_SPREAD.dte_min})"
        )
    if LONG_CALL.max_dte_hold >= LONG_CALL.dte_min:
        errors.append(
            f"LONG_CALL config error: max_dte_hold ({LONG_CALL.max_dte_hold}) must be < dte_min ({LONG_CALL.dte_min})"
        )
    if PUT_CREDIT_SPREAD.max_dte_hold >= PUT_CREDIT_SPREAD.dte_min:
        errors.append(
            f"PUT_CREDIT_SPREAD config error: max_dte_hold ({PUT_CREDIT_SPREAD.max_dte_hold}) must be < dte_min ({PUT_CREDIT_SPREAD.dte_min})"
        )
    if JADE_LIZARD.max_dte_hold >= JADE_LIZARD.dte_min:
        errors.append(
            f"JADE_LIZARD config error: max_dte_hold ({JADE_LIZARD.max_dte_hold}) must be < dte_min ({JADE_LIZARD.dte_min})"
        )
    if CALENDAR_SPREAD.min_front_dte_hold >= CALENDAR_SPREAD.front_dte_min:
        errors.append(
            f"CALENDAR_SPREAD config error: min_front_dte_hold ({CALENDAR_SPREAD.min_front_dte_hold}) "
            f"must be < front_dte_min ({CALENDAR_SPREAD.front_dte_min})"
        )

    if errors:
        raise ValueError(
            "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )


# Run validation at import time
validate_config()
