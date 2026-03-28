#!/usr/bin/env python3
"""
BTC Cycle Phase Monitor
=======================
Tracks BTC's position in the macro market cycle and sends
Telegram + email notifications on phase transitions or weekly updates.

Phases:
  ACCUMULATE - BTC < 200W SMA (deep value zone)
  HOLD       - BTC > 200W SMA, pre-halving or early post-halving
  RIDE       - Post-halving bull run (halving to Q4 of year+1)
  DISTRIBUTE - Q4 of year after halving OR on-chain metrics overheating
  GRIND      - Post-distribution, bear market / active trading mode

Data sources (all free, no auth):
  - Weekly candles: Kraken API (XBTUSD, 10080-min interval)
  - Daily candles:  Binance.US API (BTCUSD, 1d interval)
  - MVRV ratio:     CoinMetrics community API (optional, graceful fallback)

Usage:
  python3 cycle_monitor.py
"""

import json
import os
import sys
import subprocess
import requests
import statistics
from datetime import datetime, timezone, date
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / "cycle_state.json"
HISTORY_FILE = BASE_DIR / "cycle_history.json"

TELEGRAM_CHAT_ID = -1003766961821

# Email-webhook app (running on port 3500)
EMAIL_WEBHOOK_URL = "http://localhost:3500/api/webhook/e7c94802-443d-4d57-a6c9-ed475955c2cc"

# Halving dates (UTC)
HALVING_DATES = [
    date(2012, 11, 28),
    date(2016, 7, 9),
    date(2020, 5, 11),
    date(2024, 4, 19),  # Last halving
]
NEXT_HALVING = date(2028, 3, 15)  # Approximate

# Phase thresholds
MVRV_OVERHEATED = 5.0
MVRV_UNDERVALUED = 0.5
PI_CYCLE_WARNING_PCT = 0.02  # 2% proximity = approaching cross

# ─── Data Fetching ────────────────────────────────────────────────────────────

def fetch_weekly_candles(limit: int = 600) -> list:
    """
    Fetch BTC/USD weekly candles from Kraken (no auth needed).
    Kraken interval 10080 = 1 week in minutes.
    Returns list of dicts with 'date' and 'close'.
    Falls back to binance.us if Kraken fails.
    """
    # Try Kraken first (has data back to 2017)
    try:
        # Kraken: fetch since 2016 to get 300+ weekly candles for 300W SMA
        since_ts = int(datetime(2016, 1, 1, tzinfo=timezone.utc).timestamp())
        url = f"https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=10080&since={since_ts}"
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        if data.get("error"):
            raise ValueError(f"Kraken error: {data['error']}")
        candles_raw = data["result"]["XXBTZUSD"]
        # Kraken format: [timestamp, open, high, low, close, vwap, volume, count]
        candles = [
            {
                "open_time": int(c[0]),
                "close": float(c[4]),
                "date": datetime.fromtimestamp(int(c[0]), tz=timezone.utc).date(),
            }
            for c in candles_raw
        ]
        # Only keep the most recent `limit` candles
        candles = candles[-limit:]
        print(f"[*] Kraken weekly candles fetched: {len(candles)} (latest: {candles[-1]['date']})")
        return candles
    except Exception as e:
        print(f"[WARN] Kraken weekly fetch failed: {e}", file=sys.stderr)

    # Fallback: binance.us
    try:
        url = "https://api.binance.us/api/v3/klines"
        params = {"symbol": "BTCUSD", "interval": "1w", "limit": limit}
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        candles = r.json()
        result = [
            {
                "open_time": int(c[0]),
                "close": float(c[4]),
                "date": datetime.fromtimestamp(int(c[0]) / 1000, tz=timezone.utc).date(),
            }
            for c in candles
        ]
        print(f"[*] Binance.US weekly candles fetched: {len(result)}")
        return result
    except Exception as e:
        print(f"[ERROR] Binance.US weekly fetch failed: {e}", file=sys.stderr)

    return []


def fetch_daily_candles(limit: int = 400) -> list:
    """
    Fetch BTC/USD daily candles from Binance.US (no auth needed).
    Falls back to Kraken daily if Binance.US fails.
    """
    # Try binance.us first
    try:
        url = "https://api.binance.us/api/v3/klines"
        params = {"symbol": "BTCUSD", "interval": "1d", "limit": limit}
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        candles = r.json()
        result = [
            {
                "open_time": int(c[0]),
                "close": float(c[4]),
                "date": datetime.fromtimestamp(int(c[0]) / 1000, tz=timezone.utc).date(),
            }
            for c in candles
        ]
        print(f"[*] Binance.US daily candles fetched: {len(result)}")
        return result
    except Exception as e:
        print(f"[WARN] Binance.US daily fetch failed: {e}", file=sys.stderr)

    # Fallback: Kraken daily (1440 min = 1 day)
    try:
        since_ts = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())
        url = f"https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440&since={since_ts}"
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        candles_raw = data["result"]["XXBTZUSD"]
        result = [
            {
                "open_time": int(c[0]),
                "close": float(c[4]),
                "date": datetime.fromtimestamp(int(c[0]), tz=timezone.utc).date(),
            }
            for c in candles_raw[-limit:]
        ]
        print(f"[*] Kraken daily candles fetched: {len(result)}")
        return result
    except Exception as e:
        print(f"[ERROR] Kraken daily fetch failed: {e}", file=sys.stderr)

    return []


def fetch_mvrv() -> float | None:
    """
    Fetch MVRV ratio from CoinMetrics community API. Returns None on failure.
    Uses page_size=1 to get the latest value (CoinMetrics sorts descending by default).
    """
    url = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
    params = {
        "assets": "btc",
        "metrics": "CapMVRVCur",
        "frequency": "1d",
        "page_size": 1,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        series = data.get("data", [])
        if series:
            val = series[0].get("CapMVRVCur")
            if val is not None:
                return float(val)
    except Exception as e:
        print(f"[WARN] CoinMetrics MVRV fetch failed (skipping): {e}", file=sys.stderr)
    return None


def fetch_balanced_price() -> float | None:
    """Read balanced price from BM Pro scraper cache."""
    cache_file = BASE_DIR / "bmpro_cache.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            price = float(data.get("balanced_price_Balanced Price", 0))
            if price > 0:
                print(f"[*] Balanced price (BM Pro cache): ${price:,.0f}")
                return price
        except Exception:
            pass
    return None


def fetch_mvrv_zscore() -> float | None:
    """Read MVRV-Z Score from BM Pro scraper cache."""
    cache_file = BASE_DIR / "bmpro_cache.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            z = float(data.get("mvrv_zscore_Z-Score", 0))
            if z != 0:
                print(f"[*] MVRV-Z Score (BM Pro cache): {z:.2f}")
                return z
        except Exception:
            pass
    return None


def fetch_realized_price_bmpro() -> float | None:
    """Read realized price from BM Pro scraper cache."""
    cache_file = BASE_DIR / "bmpro_cache.json"
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            price = float(data.get("realized_price_Realized Price", 0))
            if price > 0:
                print(f"[*] Realized price (BM Pro cache): ${price:,.0f}")
                return price
        except Exception:
            pass
    return None


def fetch_realized_price() -> float | None:
    """
    Fetch realized price. Derived from MVRV + current price since CoinMetrics
    community API blocks CapRealUSD.
    realized_price = price / MVRV
    Returns None on failure.
    """
    try:
        mvrv = fetch_mvrv()
        if mvrv and mvrv > 0:
            r = requests.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD", timeout=10)
            r.raise_for_status()
            data = r.json()
            price = float(data["result"]["XXBTZUSD"]["c"][0])

            realized_price = price / mvrv
            print(f"[*] Realized price (derived from MVRV): ${realized_price:,.0f}")
            return realized_price
    except Exception as e:
        print(f"[WARN] Realized price fetch failed: {e}", file=sys.stderr)
    return None


# ─── Indicator Calculations ───────────────────────────────────────────────────

def calculate_sma(prices: list, period: int) -> float | None:
    """Calculate simple moving average over the last `period` values."""
    if len(prices) < period:
        return None
    return statistics.mean(prices[-period:])


def calculate_200w_sma(weekly_candles: list) -> float | None:
    """Calculate the 200-week SMA from weekly close prices."""
    closes = [c["close"] for c in weekly_candles]
    return calculate_sma(closes, 200)


def calculate_300w_sma(weekly_candles: list) -> float | None:
    """Calculate the 300-week SMA from weekly close prices."""
    closes = [c["close"] for c in weekly_candles]
    return calculate_sma(closes, 300)


def calculate_pi_cycle(daily_candles: list) -> dict:
    """
    Pi Cycle Top Indicator:
      - 111-day MA
      - 350-day MA × 2
    Cross = potential cycle top (DISTRIBUTE signal).
    """
    closes = [c["close"] for c in daily_candles]

    ma_111 = calculate_sma(closes, 111)
    ma_350 = calculate_sma(closes, 350)

    if ma_111 is None or ma_350 is None:
        return {"ma_111": None, "ma_350x2": None, "status": "insufficient_data"}

    ma_350x2 = ma_350 * 2
    current_price = closes[-1]

    if ma_111 >= ma_350x2:
        status = "CROSSED"
    else:
        gap_pct = (ma_350x2 - ma_111) / ma_350x2
        if gap_pct <= PI_CYCLE_WARNING_PCT:
            status = "approaching_cross"
        else:
            status = "normal"

    return {
        "ma_111": round(ma_111, 2),
        "ma_350x2": round(ma_350x2, 2),
        "current_price": round(current_price, 2),
        "gap_pct": round((ma_350x2 - ma_111) / ma_350x2 * 100, 2),
        "status": status,
    }


# ─── Phase Determination ──────────────────────────────────────────────────────

def get_last_halving() -> date:
    """Return the most recent halving date on or before today."""
    today = date.today()
    past = [h for h in HALVING_DATES if h <= today]
    return past[-1] if past else HALVING_DATES[-1]


def get_days_since_halving(last_halving: date) -> int:
    return (date.today() - last_halving).days


def is_distribute_window() -> bool:
    """Q4 of year after halving = DISTRIBUTE window."""
    last_halving = get_last_halving()
    year_after_halving = last_halving.year + 1
    today = date.today()
    q4_start = date(year_after_halving, 10, 1)
    q4_end = date(year_after_halving, 12, 31)
    return q4_start <= today <= q4_end


def determine_phase(
    btc_price: float,
    sma_200w: float | None,
    mvrv: float | None,
    pi_cycle: dict,
) -> tuple:
    """
    Determine current BTC cycle phase.
    Returns (phase: str, reasoning: str).

    Priority order:
    1. ACCUMULATE — BTC below 200W SMA (most important buy signal)
    2. DISTRIBUTE — Q4 year-after-halving OR Pi Cycle crossed OR MVRV overheated
    3. RIDE — Post-halving bull, pre-distribution window
    4. GRIND — Post-distribution bear market
    5. HOLD — Default pre-halving / early cycle
    """
    today = date.today()
    last_halving = get_last_halving()
    days_since_halving = get_days_since_halving(last_halving)

    # ── ACCUMULATE: BTC below 200W SMA ──────────────────────────────────────
    if sma_200w is not None and btc_price < sma_200w:
        reason = f"BTC ${btc_price:,.0f} < 200W SMA ${sma_200w:,.0f} (deep value zone)"
        if mvrv is not None and mvrv <= MVRV_UNDERVALUED:
            reason += f" + MVRV {mvrv:.2f} confirms undervaluation"
        return "ACCUMULATE", reason

    # ── DISTRIBUTE: Multiple top signals ────────────────────────────────────
    if is_distribute_window():
        year_after = last_halving.year + 1
        return "DISTRIBUTE", f"Q4 {year_after} (year after halving) — peak distribution window"

    if pi_cycle.get("status") == "CROSSED":
        return "DISTRIBUTE", (
            f"Pi Cycle Top crossed! 111MA (${pi_cycle.get('ma_111', 0):,.0f}) ≥ "
            f"350MA×2 (${pi_cycle.get('ma_350x2', 0):,.0f}) — cycle top signal"
        )

    if mvrv is not None and mvrv >= MVRV_OVERHEATED:
        return "DISTRIBUTE", f"MVRV {mvrv:.2f} ≥ {MVRV_OVERHEATED} — market severely overheated"

    # ── RIDE: Post-halving bull run (pre-distribution) ──────────────────────
    if days_since_halving > 0:
        year_after = last_halving.year + 1
        distribute_start = date(year_after, 10, 1)
        if today < distribute_start:
            reason = (
                f"{days_since_halving}d since halving ({last_halving}), "
                f"bull run phase — distribution window opens {distribute_start}"
            )
            if sma_200w:
                pct = ((btc_price - sma_200w) / sma_200w) * 100
                reason += f" | BTC {pct:+.1f}% above 200W SMA"
            if pi_cycle.get("status") == "approaching_cross":
                gap = pi_cycle.get("gap_pct", 0)
                reason += f" | ⚠️ Pi Cycle Top approaching (gap: {gap:.1f}%)"
            return "RIDE", reason

    # ── GRIND: Post-distribution, waiting for next cycle ────────────────────
    year_after = last_halving.year + 1
    distribute_end = date(year_after, 12, 31)
    if today > distribute_end:
        days_to_next = (NEXT_HALVING - today).days
        return "GRIND", (
            f"Post-distribution bear market phase — "
            f"next halving in ~{days_to_next}d ({NEXT_HALVING}), run active trading"
        )

    # ── HOLD: Default (pre-halving accumulation / early cycle) ──────────────
    days_to_next_halving = (NEXT_HALVING - today).days
    sma_str = f"${sma_200w:,.0f}" if sma_200w else "N/A"
    return "HOLD", (
        f"BTC ${btc_price:,.0f} > 200W SMA {sma_str}, "
        f"{days_to_next_halving}d to next halving ({NEXT_HALVING})"
    )


# ─── State Management ─────────────────────────────────────────────────────────

def load_state() -> dict:
    """Load previous cycle state from JSON."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"phase": None, "last_update": None, "last_monday_update": None}


def save_state(state: dict) -> None:
    """Persist current cycle state."""
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def append_history(entry: dict) -> None:
    """Append a record to cycle history."""
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass
    history.append(entry)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, default=str))


# ─── Notifications ────────────────────────────────────────────────────────────

def build_telegram_message(
    phase: str,
    prev_phase: str | None,
    btc_price: float,
    sma_200w: float | None,
    sma_300w: float | None,
    mvrv: float | None,
    realized_price: float | None,
    balanced_price: float | None,
    mvrv_zscore: float | None,
    pi_cycle: dict,
    reasoning: str,
    is_transition: bool,
) -> str:
    """Build the Telegram notification message."""

    phase_emojis = {
        "ACCUMULATE": "🟢",
        "HOLD": "🟡",
        "RIDE": "🚀",
        "DISTRIBUTE": "🔴",
        "GRIND": "⚙️",
    }
    phase_actions = {
        "ACCUMULATE": "DCA aggressively. Max allocation.",
        "HOLD": "Hold spot. Minimal trading.",
        "RIDE": "Hold spot. Add on dips >20%.",
        "DISTRIBUTE": "Scale out 25%/month. Take profits.",
        "GRIND": "Run active trading. Leverage on dips.",
    }

    emoji = phase_emojis.get(phase, "📊")
    action = phase_actions.get(phase, "Monitor closely.")

    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if is_transition and prev_phase:
        header = f"🔔 *BTC Cycle Phase Transition*\n{prev_phase} → {phase} {emoji}"
    else:
        header = f"📊 *BTC Cycle Weekly Update*\n{emoji} Phase: *{phase}*"

    sma_str = f"${sma_200w:,.0f}" if sma_200w else "N/A"
    dist_pct = ""
    if sma_200w:
        pct = ((btc_price - sma_200w) / sma_200w) * 100
        sign = "+" if pct >= 0 else ""
        dist_pct = f" ({sign}{pct:.1f}% vs SMA)"

    sma_300w_str = f"${sma_300w:,.0f}" if sma_300w else "N/A"
    dist_300_pct = ""
    if sma_300w:
        pct300 = ((btc_price - sma_300w) / sma_300w) * 100
        sign300 = "+" if pct300 >= 0 else ""
        dist_300_pct = f" ({sign300}{pct300:.1f}% vs SMA)"

    realized_str = f"${realized_price:,.0f}" if realized_price else "N/A"
    balanced_str = f"${balanced_price:,.0f}" if balanced_price else "N/A (cache stale)"

    mvrv_str = f"{mvrv:.2f}" if mvrv is not None else "N/A"
    mvrv_z_str = f"{mvrv_zscore:.2f}" if mvrv_zscore is not None else "N/A"

    pi_status = pi_cycle.get("status", "N/A")
    if pi_cycle.get("ma_111") and pi_cycle.get("ma_350x2"):
        gap = pi_cycle.get("gap_pct", 0)
        pi_str = f"{pi_status} | 111MA: ${pi_cycle['ma_111']:,.0f} | 350×2: ${pi_cycle['ma_350x2']:,.0f} (gap: {gap:.1f}%)"
    else:
        pi_str = pi_status

    last_halving = get_last_halving()
    days_halving = get_days_since_halving(last_halving)
    days_to_next = (NEXT_HALVING - date.today()).days

    msg = f"""
{header}

💰 BTC Price: ${btc_price:,.0f}
📈 200W SMA: {sma_str}{dist_pct}
📊 300W SMA: {sma_300w_str}{dist_300_pct}
🧮 MVRV Ratio: {mvrv_str}
📐 MVRV-Z Score: {mvrv_z_str}
💎 Realized Price: {realized_str}
⚖️ Balanced Price: {balanced_str}
🥧 Pi Cycle: {pi_str}
⛏️ Last halving: {last_halving} ({days_halving}d ago)
🔮 Next halving: {NEXT_HALVING} ({days_to_next}d)

📋 Reasoning: _{reasoning}_

✅ Action: *{action}*

🕐 {now}
""".strip()

    return msg


def send_telegram_message(msg: str) -> None:
    """
    Print the Telegram message to stdout.
    The calling system (OpenClaw/main agent) handles actual delivery to
    chat_id: -1003766961821 (All Things Crypto group).
    """
    print("\n" + "=" * 60)
    print(f"TELEGRAM → chat_id: {TELEGRAM_CHAT_ID}")
    print("=" * 60)
    print(msg)
    print("=" * 60 + "\n")


def send_email_webhook(payload: dict) -> bool:
    """POST phase data to the email-webhook app."""
    try:
        r = requests.post(
            EMAIL_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        r.raise_for_status()
        resp = r.json()
        print(f"[OK] Email webhook triggered: triggerId={resp.get('triggerId')}")
        return True
    except Exception as e:
        print(f"[WARN] Email webhook failed: {e}", file=sys.stderr)
        return False


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    now = datetime.now(tz=timezone.utc)
    today = now.date()
    is_monday = today.weekday() == 0  # Monday = 0

    print(f"[{now.isoformat()}] BTC Cycle Phase Monitor starting...")
    print(f"[*] Today: {today} ({'Monday' if is_monday else today.strftime('%A')})")

    # 1. Fetch data
    print("\n[*] Fetching weekly candles (Kraken → binance.us fallback)...")
    weekly = fetch_weekly_candles(600)
    if not weekly:
        print("[ERROR] No weekly candle data. Aborting.", file=sys.stderr)
        sys.exit(1)

    print("[*] Fetching daily candles (binance.us → Kraken fallback)...")
    daily = fetch_daily_candles(400)

    print("[*] Fetching MVRV from CoinMetrics community API...")
    mvrv = fetch_mvrv()

    print("[*] Fetching realized price...")
    realized_price = fetch_realized_price()

    print("[*] Refreshing BM Pro metrics (balanced price, MVRV-Z, realized price)...")
    try:
        subprocess.run(
            [sys.executable, str(BASE_DIR / "scrape_bmpro.py")],
            capture_output=True, text=True, timeout=120,
            env=os.environ.copy(),
            cwd=str(BASE_DIR)
        )
    except Exception as e:
        print(f"[WARN] BM Pro scrape failed: {e}", file=sys.stderr)

    balanced_price = fetch_balanced_price()
    mvrv_zscore = fetch_mvrv_zscore()
    realized_price_bmpro = fetch_realized_price_bmpro()

    # 2. Calculate indicators
    btc_price = weekly[-1]["close"]
    sma_200w = calculate_200w_sma(weekly)
    sma_300w = calculate_300w_sma(weekly)
    pi_cycle = calculate_pi_cycle(daily) if daily else {"status": "insufficient_data"}

    print(f"\n[*] BTC Price:  ${btc_price:,.2f}")
    if sma_200w:
        pct = ((btc_price - sma_200w) / sma_200w) * 100
        print(f"[*] 200W SMA:   ${sma_200w:,.2f}  ({pct:+.1f}% from SMA)")
    else:
        print(f"[*] 200W SMA:   insufficient data (need {len(weekly)}/200 weekly candles)")
    if sma_300w:
        pct300 = ((btc_price - sma_300w) / sma_300w) * 100
        print(f"[*] 300W SMA:   ${sma_300w:,.2f}  ({pct300:+.1f}% from SMA)")
    else:
        print(f"[*] 300W SMA:   insufficient data (need {len(weekly)}/300 weekly candles)")
    print(f"[*] MVRV:       {mvrv:.4f}" if mvrv is not None else "[*] MVRV:       unavailable (CoinMetrics skipped)")
    print(f"[*] Pi Cycle:   {pi_cycle}")

    # 3. Determine phase
    phase, reasoning = determine_phase(btc_price, sma_200w, mvrv, pi_cycle)
    print(f"\n[*] Current Phase: {phase}")
    print(f"[*] Reasoning:     {reasoning}")

    # 4. Load previous state
    state = load_state()
    prev_phase = state.get("phase")
    last_monday_update = state.get("last_monday_update")

    is_transition = prev_phase is not None and prev_phase != phase
    already_sent_monday = (last_monday_update == str(today)) if is_monday else True
    should_notify = is_transition or (is_monday and not already_sent_monday)

    print(f"\n[*] Previous phase:    {prev_phase}")
    print(f"[*] Phase transition:  {is_transition}")
    print(f"[*] Is Monday:         {is_monday}")
    print(f"[*] Already sent Mon:  {already_sent_monday}")
    print(f"[*] Will notify:       {should_notify}")

    # 5. Build payload
    last_halving = get_last_halving()
    days_since_halving = get_days_since_halving(last_halving)
    days_to_next_halving = (NEXT_HALVING - today).days
    sma_distance_pct = ((btc_price - sma_200w) / sma_200w * 100) if sma_200w else None
    sma_300w_distance_pct = ((btc_price - sma_300w) / sma_300w * 100) if sma_300w else None

    payload = {
        "event": "cycle_phase_change" if is_transition else "cycle_weekly_update",
        "phase": phase,
        "previous_phase": prev_phase,
        "btc_price": round(btc_price, 2),
        "sma_200w": round(sma_200w, 2) if sma_200w else None,
        "sma_300w": round(sma_300w, 2) if sma_300w else None,
        "distance_pct": round(sma_distance_pct, 2) if sma_distance_pct is not None else None,
        "distance_300w_pct": round(sma_300w_distance_pct, 2) if sma_300w_distance_pct is not None else None,
        "realized_price": round(realized_price, 2) if realized_price else None,
        "balanced_price": round(balanced_price, 2) if balanced_price else None,
        "mvrv": round(mvrv, 4) if mvrv is not None else None,
        "mvrv_zscore": round(mvrv_zscore, 4) if mvrv_zscore is not None else None,
        "pi_cycle_status": pi_cycle.get("status"),
        "pi_cycle_ma_111": pi_cycle.get("ma_111"),
        "pi_cycle_ma_350x2": pi_cycle.get("ma_350x2"),
        "pi_cycle_gap_pct": pi_cycle.get("gap_pct"),
        "last_halving": str(last_halving),
        "days_since_halving": days_since_halving,
        "next_halving": str(NEXT_HALVING),
        "days_to_next_halving": days_to_next_halving,
        "reasoning": reasoning,
        "action": {
            "ACCUMULATE": "DCA aggressively. Max allocation.",
            "HOLD": "Hold spot. Minimal trading.",
            "RIDE": "Hold spot. Add on dips >20%.",
            "DISTRIBUTE": "Scale out 25%/month. Take profits.",
            "GRIND": "Run active trading. Leverage on dips.",
        }.get(phase, "Monitor."),
        "timestamp": now.isoformat(),
        "is_transition": is_transition,
        "is_monday_update": is_monday,
    }

    # 6. Send notifications
    if should_notify:
        tg_msg = build_telegram_message(
            phase=phase,
            prev_phase=prev_phase,
            btc_price=btc_price,
            sma_200w=sma_200w,
            sma_300w=sma_300w,
            mvrv=mvrv,
            realized_price=realized_price,
            balanced_price=balanced_price,
            mvrv_zscore=mvrv_zscore,
            pi_cycle=pi_cycle,
            reasoning=reasoning,
            is_transition=is_transition,
        )
        payload["telegram_message"] = tg_msg

        send_telegram_message(tg_msg)
        send_email_webhook(payload)
    else:
        print("\n[*] No notification needed (no phase change, not Monday or already sent)")

    # 7. Update state
    new_state = {
        "phase": phase,
        "btc_price": round(btc_price, 2),
        "sma_200w": round(sma_200w, 2) if sma_200w else None,
        "sma_300w": round(sma_300w, 2) if sma_300w else None,
        "distance_pct": round(sma_distance_pct, 2) if sma_distance_pct is not None else None,
        "distance_300w_pct": round(sma_300w_distance_pct, 2) if sma_300w_distance_pct is not None else None,
        "realized_price": round(realized_price, 2) if realized_price else None,
        "balanced_price": round(balanced_price, 2) if balanced_price else None,
        "mvrv": round(mvrv, 4) if mvrv is not None else None,
        "mvrv_zscore": round(mvrv_zscore, 4) if mvrv_zscore is not None else None,
        "pi_cycle": pi_cycle,
        "last_halving": str(last_halving),
        "days_since_halving": days_since_halving,
        "next_halving": str(NEXT_HALVING),
        "days_to_next_halving": days_to_next_halving,
        "reasoning": reasoning,
        "last_update": now.isoformat(),
        "last_monday_update": str(today) if (is_monday and should_notify) else last_monday_update,
    }
    save_state(new_state)
    print(f"\n[*] State saved to {STATE_FILE}")

    # 8. Append to history
    history_entry = {
        "timestamp": now.isoformat(),
        "phase": phase,
        "prev_phase": prev_phase,
        "is_transition": is_transition,
        "btc_price": round(btc_price, 2),
        "sma_200w": round(sma_200w, 2) if sma_200w else None,
        "sma_300w": round(sma_300w, 2) if sma_300w else None,
        "distance_pct": round(sma_distance_pct, 2) if sma_distance_pct is not None else None,
        "distance_300w_pct": round(sma_300w_distance_pct, 2) if sma_300w_distance_pct is not None else None,
        "realized_price": round(realized_price, 2) if realized_price else None,
        "balanced_price": round(balanced_price, 2) if balanced_price else None,
        "mvrv": round(mvrv, 4) if mvrv is not None else None,
        "mvrv_zscore": round(mvrv_zscore, 4) if mvrv_zscore is not None else None,
        "pi_cycle_status": pi_cycle.get("status"),
        "reasoning": reasoning,
        "notified": should_notify,
    }
    append_history(history_entry)
    print(f"[*] History appended to {HISTORY_FILE}")

    # 9. Print summary
    print("\n" + "=" * 60)
    print("BTC CYCLE PHASE MONITOR — SUMMARY")
    print("=" * 60)
    print(f"  Phase:          {phase}")
    if prev_phase:
        print(f"  Prev Phase:     {prev_phase}")
    print(f"  BTC Price:      ${btc_price:,.2f}")
    if sma_200w:
        pct = ((btc_price - sma_200w) / sma_200w) * 100
        sign = "+" if pct >= 0 else ""
        print(f"  200W SMA:       ${sma_200w:,.2f} ({sign}{pct:.1f}% from SMA)")
    if sma_300w:
        pct300 = ((btc_price - sma_300w) / sma_300w) * 100
        sign300 = "+" if pct300 >= 0 else ""
        print(f"  300W SMA:       ${sma_300w:,.2f} ({sign300}{pct300:.1f}% from SMA)")
    if realized_price:
        print(f"  Realized Price: ${realized_price:,.2f}")
    if balanced_price:
        print(f"  Balanced Price: ${balanced_price:,.2f}")
    if mvrv is not None:
        print(f"  MVRV:           {mvrv:.4f}")
    if mvrv_zscore is not None:
        print(f"  MVRV-Z Score:   {mvrv_zscore:.4f}")
    print(f"  Pi Cycle:       {pi_cycle.get('status', 'N/A')}")
    print(f"  Last Halving:   {last_halving} ({days_since_halving}d ago)")
    print(f"  Next Halving:   {NEXT_HALVING} ({days_to_next_halving}d)")
    print(f"  Reasoning:      {reasoning}")
    print(f"  Notified:       {'Yes' if should_notify else 'No'}")
    print("=" * 60)

    return phase, payload


if __name__ == "__main__":
    main()
