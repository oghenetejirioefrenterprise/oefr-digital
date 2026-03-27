"""
Options Agent Dashboard — Professional dark-theme real-time monitor.
Reads data from JSON files written by state_writer.py.
Never connects to IBKR directly.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ─── Page config (must be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="Options Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── File paths ───────────────────────────────────────────────────────────────
DATA_DIR        = os.getenv("DATA_DIR", "/data")
LOG_DIR         = os.getenv("LOG_DIR", "/logs")
AGENT_LOG       = os.path.join(LOG_DIR, "agent.log")
RISK_STATE      = os.path.join(DATA_DIR, "risk_state.json")
POSITIONS_FILE  = os.path.join(DATA_DIR, "positions.json")
HISTORY_FILE    = os.path.join(DATA_DIR, "trade_history.json")
CONFIG_FILE     = os.path.join(DATA_DIR, "agent_config.json")
PORTFOLIO_FILE  = os.path.join(DATA_DIR, "portfolio.json")
HEARTBEAT_FILE  = os.path.join(DATA_DIR, "heartbeat.json")

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Reset & base ── */
  .stApp { background: #0a0c10 !important; color: #d0d4dc; }
  .block-container { padding: 0.75rem 1.25rem 2rem 1.25rem !important; max-width: 100% !important; }
  section[data-testid="stSidebar"] { display: none; }
  div[data-testid="stDecoration"] { display: none; }
  footer { display: none !important; }
  #MainMenu { display: none !important; }
  header[data-testid="stHeader"] { display: none !important; }

  /* ── Metric cards ── */
  .mcard {
    background: #13161d;
    border: 1px solid #222;
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
    height: 96px;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  .mcard.green  { border-color: #00e676; }
  .mcard.red    { border-color: #ff1744; }
  .mcard.blue   { border-color: #2979ff; }
  .mcard.yellow { border-color: #ffd600; }
  .mcard.gray   { border-color: #444; }
  .mlabel {
    font-size: 10px;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 4px;
  }
  .mval {
    font-size: 26px;
    font-weight: 700;
    font-family: 'SF Mono', 'Consolas', monospace;
    line-height: 1.1;
  }
  .mval.green  { color: #00e676; }
  .mval.red    { color: #ff1744; }
  .mval.blue   { color: #2979ff; }
  .mval.yellow { color: #ffd600; }
  .mval.gray   { color: #888; }
  .msub { font-size: 11px; color: #555; margin-top: 3px; }

  /* ── Header bar ── */
  .hbar {
    background: #13161d;
    border: 1px solid #1e222c;
    border-radius: 10px;
    padding: 12px 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 12px;
  }
  .agent-name {
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 2px;
    color: #e0e4ef;
    font-family: 'SF Mono', 'Consolas', monospace;
  }
  .badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    font-family: 'SF Mono', 'Consolas', monospace;
  }
  .badge-dry  { background: #ffd60022; color: #ffd600; border: 1px solid #ffd60055; }
  .badge-live { background: #ff174422; color: #ff1744; border: 1px solid #ff174455; }
  .badge-halt { background: #ff174422; color: #ff1744; border: 1px solid #ff174455; }
  .badge-online { background: #00e67622; color: #00e676; border: 1px solid #00e67655; }

  .pulse-dot {
    display: inline-block;
    width: 9px; height: 9px;
    border-radius: 50%;
    background: #00e676;
    box-shadow: 0 0 0 0 #00e67666;
    animation: pulse-ring 1.8s ease-out infinite;
    margin-right: 8px;
    vertical-align: middle;
  }
  .dead-dot {
    display: inline-block;
    width: 9px; height: 9px;
    border-radius: 50%;
    background: #ff1744;
    margin-right: 8px;
    vertical-align: middle;
  }
  @keyframes pulse-ring {
    0%   { box-shadow: 0 0 0 0 #00e67666; }
    70%  { box-shadow: 0 0 0 7px #00e67600; }
    100% { box-shadow: 0 0 0 0 #00e67600; }
  }

  .hb-time { font-size: 12px; color: #555; margin-left: auto; font-family: 'SF Mono', 'Consolas', monospace; }

  /* ── Section headers ── */
  .sec-hdr {
    font-size: 11px;
    color: #555;
    text-transform: uppercase;
    letter-spacing: 2px;
    padding-bottom: 7px;
    border-bottom: 1px solid #1a1e27;
    margin-bottom: 10px;
    margin-top: 4px;
  }

  /* ── Position cards ── */
  .pos-card {
    background: #13161d;
    border: 1px solid #1e222c;
    border-left: 3px solid #2979ff;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-family: 'SF Mono', 'Consolas', monospace;
    font-size: 12px;
  }
  .pos-card.bwb   { border-left-color: #00e676; }
  .pos-card.condor { border-left-color: #2979ff; }
  .strat-badge {
    display: inline-block;
    padding: 1px 7px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
  }
  .strat-bwb    { background: #00e67622; color: #00e676; border: 1px solid #00e67655; }
  .strat-condor { background: #2979ff22; color: #2979ff; border: 1px solid #2979ff55; }
  .pos-label { color: #555; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; }
  .pos-val   { color: #c8cdd8; font-size: 12px; }
  .pos-credit { color: #00e676; font-weight: 700; }
  .pos-time { color: #444; font-size: 10px; }

  /* ── Log viewer ── */
  .logbox {
    background: #0d0f14;
    border: 1px solid #1a1e27;
    border-radius: 8px;
    padding: 10px 12px;
    max-height: 420px;
    overflow-y: auto;
    font-family: 'SF Mono', 'Consolas', monospace;
    font-size: 11px;
    line-height: 1.7;
  }
  .log-err  { color: #ff1744; }
  .log-warn { color: #ff9100; }
  .log-ok   { color: #00e676; }
  .log-cyan { color: #00b0ff; }
  .log-info { color: #607080; }
  .log-dim  { color: #404858; }

  /* ── Trade history table ── */
  .th-row {
    display: flex;
    align-items: center;
    border-bottom: 1px solid #1a1e27;
    padding: 5px 0;
    font-size: 12px;
    font-family: 'SF Mono', 'Consolas', monospace;
  }
  .th-row:last-child { border-bottom: none; }
  .th-time { color: #555; width: 160px; flex-shrink: 0; }
  .th-strat { width: 70px; flex-shrink: 0; }
  .th-exp  { color: #888; width: 90px; flex-shrink: 0; }
  .th-strikes { color: #aaa; flex: 1; }
  .th-pnl  { width: 90px; flex-shrink: 0; text-align: right; font-weight: 700; }
  .th-res  { width: 50px; flex-shrink: 0; text-align: right; }
  .pnl-win  { color: #00e676; }
  .pnl-loss { color: #ff1744; }
  .pnl-zero { color: #888; }

  /* ── Risk bar ── */
  .risk-bar-bg {
    background: #1a1e27;
    border-radius: 4px;
    height: 6px;
    margin-top: 5px;
    overflow: hidden;
  }
  .risk-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.4s ease;
  }

  /* ── Config row ── */
  .cfg-item {
    background: #13161d;
    border: 1px solid #1a1e27;
    border-radius: 6px;
    padding: 8px 12px;
    text-align: center;
  }
  .cfg-label { font-size: 10px; color: #555; text-transform: uppercase; letter-spacing: 1px; }
  .cfg-val   { font-size: 14px; color: #c8cdd8; font-family: 'SF Mono', 'Consolas', monospace; margin-top: 2px; }

  /* ── Empty state ── */
  .empty-state { color: #444; text-align: center; padding: 40px 0; font-size: 13px; }
</style>
""", unsafe_allow_html=True)


# ─── Data helpers ─────────────────────────────────────────────────────────────

def read_json(path: str, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def read_log_tail(path: str, n: int = 40) -> list:
    try:
        with open(path, "rb") as f:
            # Efficient tail: seek from end
            f.seek(0, 2)
            size = f.tell()
            block = min(size, 32768)
            f.seek(-block, 2)
            raw = f.read().decode("utf-8", errors="replace")
        lines = raw.splitlines()
        return lines[-n:]
    except Exception:
        return []


def money(val, plus=True) -> str:
    if val is None:
        return "$0.00"
    sign = "+" if (val > 0 and plus) else ""
    return f"{sign}${abs(val):,.2f}" if val < 0 else f"{sign}${val:,.2f}"


def fmt_money_signed(val) -> str:
    if val is None or val == 0:
        return "$0.00"
    if val > 0:
        return f"+${val:,.2f}"
    return f"-${abs(val):,.2f}"


def strikes_display(pos: dict) -> str:
    strat = pos.get("strategy", "")
    if strat == "BWB":
        return f"{pos.get('strike_high','-')} / {pos.get('strike_mid','-')}×2 / {pos.get('strike_low','-')}"
    elif strat == "CONDOR":
        return (f"P {pos.get('long_put_strike','-')}/{pos.get('short_put_strike','-')}"
                f" · C {pos.get('short_call_strike','-')}/{pos.get('long_call_strike','-')}")
    return "—"


def fmt_expiry(exp: str) -> str:
    """20260402 → Apr 02 '26"""
    try:
        d = datetime.strptime(str(exp), "%Y%m%d")
        return d.strftime("%b %d '%y")
    except Exception:
        return str(exp)


def dte(exp: str) -> int:
    try:
        d = datetime.strptime(str(exp), "%Y%m%d")
        return (d.date() - datetime.now().date()).days
    except Exception:
        return 0


# ─── BWB payoff diagram ───────────────────────────────────────────────────────

def bwb_payoff_chart(pos: dict, spx_price: float = None) -> go.Figure:
    """
    BWB (Broken Wing Butterfly) payoff at expiration.
    Structure: long 1x strike_high put, short 2x strike_mid put, long 1x strike_low put
    wing_high = strike_high - strike_mid  (wide wing)
    wing_low  = strike_mid  - strike_low  (narrow wing)
    Credit received = net_credit per share × 100
    Max profit at strike_mid = wing_high × 100 - debit (or + credit)
    """
    sh = float(pos.get("strike_high", 0))
    sm = float(pos.get("strike_mid", 0))
    sl = float(pos.get("strike_low", 0))
    credit = float(pos.get("net_credit", 0))   # per share
    qty    = int(pos.get("qty", 1))

    if sh == 0 or sm == 0 or sl == 0:
        return None

    wing_wide   = sh - sm   # upper wing width
    wing_narrow = sm - sl   # lower wing width

    # Price range: ±30 pts around sm, at minimum covering all strikes with padding
    lo = min(sl - 20, sm - 35)
    hi = max(sh + 20, sm + 35)
    prices = [lo + (hi - lo) * i / 200 for i in range(201)]

    def put_payoff(K, S):
        return max(K - S, 0.0)

    def bwb_pnl_per_unit(S):
        # Long 1x high put, short 2x mid put, long 1x low put + credit
        pnl = (
            put_payoff(sh, S)
            - 2 * put_payoff(sm, S)
            + put_payoff(sl, S)
            + credit
        )
        return pnl * 100  # per-contract ($)

    pnls = [bwb_pnl_per_unit(s) * qty for s in prices]

    # Split into gain/loss segments for fill coloring
    fig = go.Figure()

    # Green fill — profit zones
    pos_y = [max(p, 0) for p in pnls]
    neg_y = [min(p, 0) for p in pnls]

    fig.add_trace(go.Scatter(
        x=prices, y=pos_y,
        fill="tozeroy",
        fillcolor="rgba(0,230,118,0.12)",
        line=dict(color="#00e676", width=1.5),
        name="Profit",
        hovertemplate="$%{x:.0f}: +$%{y:.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=prices, y=neg_y,
        fill="tozeroy",
        fillcolor="rgba(255,23,68,0.12)",
        line=dict(color="#ff1744", width=1.5),
        name="Loss",
        hovertemplate="$%{x:.0f}: -$%{y:.0f}<extra></extra>",
    ))

    # Key price markers
    for strike, label, color in [
        (sh, f"H {sh:.0f}", "#00b0ff"),
        (sm, f"M {sm:.0f}", "#2979ff"),
        (sl, f"L {sl:.0f}", "#7c4dff"),
    ]:
        fig.add_vline(
            x=strike,
            line=dict(color=color, width=1, dash="dot"),
            annotation_text=label,
            annotation_font_size=9,
            annotation_font_color=color,
        )

    # SPX current price
    if spx_price and lo < spx_price < hi:
        fig.add_vline(
            x=spx_price,
            line=dict(color="#ffd600", width=1.5, dash="dash"),
            annotation_text=f"SPX {spx_price:.0f}",
            annotation_font_size=9,
            annotation_font_color="#ffd600",
        )

    # Zero line
    fig.add_hline(y=0, line=dict(color="#333", width=1))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d0f14",
        plot_bgcolor="#0d0f14",
        margin=dict(l=32, r=8, t=8, b=28),
        height=160,
        showlegend=False,
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=9, color="#555"),
            tickformat=".0f",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#1a1e27",
            tickfont=dict(size=9, color="#555"),
            tickformat="$.0f",
            zeroline=False,
        ),
    )
    return fig


def condor_payoff_chart(pos: dict, spx_price: float = None) -> go.Figure:
    lp = float(pos.get("long_put_strike", 0))
    sp = float(pos.get("short_put_strike", 0))
    sc = float(pos.get("short_call_strike", 0))
    lc = float(pos.get("long_call_strike", 0))
    credit = float(pos.get("net_credit", 0))
    qty = int(pos.get("qty", 1))

    if not all([lp, sp, sc, lc]):
        return None

    lo = lp - 20
    hi = lc + 20
    prices = [lo + (hi - lo) * i / 200 for i in range(201)]

    def put_p(K, S): return max(K - S, 0.0)
    def call_p(K, S): return max(S - K, 0.0)

    def condor_pnl(S):
        pnl = (
            -put_p(lp, S) + put_p(sp, S)
            + put_p(sc, S) - call_p(lc, S)  # wrong — condor is put spread + call spread
        )
        # Iron condor: sell put spread + sell call spread
        # = (short put sp - long put lp) + (short call sc - long call lc) + credit
        pnl = (
            (-put_p(lp, S) + put_p(sp, S))
            + (-call_p(lc, S) + call_p(sc, S))
            + credit
        )
        return pnl * 100 * qty

    pnls = [condor_pnl(s) for s in prices]

    fig = go.Figure()
    pos_y = [max(p, 0) for p in pnls]
    neg_y = [min(p, 0) for p in pnls]

    fig.add_trace(go.Scatter(
        x=prices, y=pos_y, fill="tozeroy",
        fillcolor="rgba(0,230,118,0.12)",
        line=dict(color="#00e676", width=1.5), name="Profit",
    ))
    fig.add_trace(go.Scatter(
        x=prices, y=neg_y, fill="tozeroy",
        fillcolor="rgba(255,23,68,0.12)",
        line=dict(color="#ff1744", width=1.5), name="Loss",
    ))

    for strike, label, color in [
        (lp, f"{lp:.0f}", "#7c4dff"),
        (sp, f"{sp:.0f}", "#2979ff"),
        (sc, f"{sc:.0f}", "#2979ff"),
        (lc, f"{lc:.0f}", "#7c4dff"),
    ]:
        fig.add_vline(x=strike, line=dict(color=color, width=1, dash="dot"),
                      annotation_text=label, annotation_font_size=9, annotation_font_color=color)

    if spx_price and lo < spx_price < hi:
        fig.add_vline(x=spx_price, line=dict(color="#ffd600", width=1.5, dash="dash"),
                      annotation_text=f"SPX {spx_price:.0f}", annotation_font_size=9,
                      annotation_font_color="#ffd600")

    fig.add_hline(y=0, line=dict(color="#333", width=1))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0d0f14", plot_bgcolor="#0d0f14",
        margin=dict(l=32, r=8, t=8, b=28), height=160, showlegend=False,
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color="#555"), tickformat=".0f"),
        yaxis=dict(showgrid=True, gridcolor="#1a1e27", tickfont=dict(size=9, color="#555"),
                   tickformat="$.0f", zeroline=False),
    )
    return fig


# ─── P&L cumulative chart ─────────────────────────────────────────────────────

def pnl_chart(trade_history: list) -> go.Figure:
    if not trade_history:
        fig = go.Figure()
        fig.add_annotation(text="No closed trades yet", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False,
                           font=dict(color="#444", size=14))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0d0f14",
                          plot_bgcolor="#0d0f14", height=300,
                          margin=dict(l=40, r=16, t=16, b=40))
        return fig

    trades = sorted(trade_history, key=lambda t: t.get("exit_time", t.get("time", "")))
    pnls   = [float(t.get("realized_pnl", t.get("pnl", 0)) or 0) for t in trades]
    labels = []
    for i, t in enumerate(trades):
        ts = t.get("exit_time", t.get("time", ""))
        try:
            labels.append(datetime.fromisoformat(ts).strftime("%m/%d %H:%M"))
        except Exception:
            labels.append(f"#{i+1}")

    cumulative = []
    running = 0.0
    for p in pnls:
        running += p
        cumulative.append(round(running, 2))

    final = cumulative[-1] if cumulative else 0
    color = "#00e676" if final >= 0 else "#ff1744"
    fill  = "rgba(0,230,118,0.08)" if final >= 0 else "rgba(255,23,68,0.08)"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels,
        y=cumulative,
        mode="lines+markers",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=fill,
        marker=dict(size=4, color=color),
        hovertemplate="<b>%{x}</b><br>Cumulative: $%{y:,.2f}<extra></extra>",
    ))

    fig.add_hline(y=0, line=dict(color="#333", width=1))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d0f14",
        plot_bgcolor="#0d0f14",
        height=300,
        margin=dict(l=48, r=16, t=16, b=48),
        showlegend=False,
        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=10, color="#555"),
            tickangle=-30,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#1a1e27",
            tickfont=dict(size=10, color="#555"),
            tickprefix="$",
            zeroline=False,
        ),
    )
    return fig


# ─── Load all data ────────────────────────────────────────────────────────────

risk_state    = read_json(RISK_STATE, {})
positions     = read_json(POSITIONS_FILE, []) or []
portfolio     = read_json(PORTFOLIO_FILE, {})
cfg           = read_json(CONFIG_FILE, {})
trade_history = read_json(HISTORY_FILE, []) or []
heartbeat     = read_json(HEARTBEAT_FILE, {})
log_lines     = read_log_tail(AGENT_LOG, 40)

# ── Derived values ────────────────────────────────────────────────────────────
# Agent liveness — check heartbeat first, fall back to log timestamp
agent_alive    = False
agent_sleeping = False
last_alive_ts  = None

hb_ts   = heartbeat.get("timestamp")
hb_mode = heartbeat.get("mode", "trading")
if hb_ts:
    try:
        hb_dt = datetime.fromisoformat(hb_ts)
        age   = (datetime.now() - hb_dt).total_seconds()
        if age < 120:
            agent_alive    = True
            agent_sleeping = (hb_mode == "sleeping")
        last_alive_ts = hb_dt
    except Exception:
        pass

if not last_alive_ts and log_lines:
    try:
        last_alive_ts = datetime.strptime(log_lines[-1][:19], "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - last_alive_ts).total_seconds() < 300:
            agent_alive = True
    except Exception:
        pass

trading_halted = risk_state.get("halted", False)
halt_reason    = risk_state.get("halt_reason", "")

daily_pnl    = risk_state.get("daily_pnl", portfolio.get("daily_pnl", 0.0)) or 0.0
trades_today = risk_state.get("trades", []) or []
wins         = sum(1 for t in trades_today if t.get("win", False))
losses_count = sum(1 for t in trades_today if not t.get("win", False))
total_today  = len(trades_today)

strategy    = cfg.get("strategy",      risk_state.get("strategy",   "BWB"))
underlying  = cfg.get("underlying",    "SPX")
dry_run     = cfg.get("dry_run",       True)
max_pos     = int(cfg.get("max_positions", 2))
max_loss    = float(cfg.get("max_daily_loss", 500))
max_risk    = float(cfg.get("max_position_risk", 2500))
scan_int    = int(cfg.get("scan_interval", 60))
start_time  = cfg.get("start_time", "")
uptime_sec  = int(cfg.get("uptime_seconds", 0))

spx_price   = portfolio.get("spx_price")
unrealized  = portfolio.get("unrealized_pnl", 0.0) or 0.0
realized    = portfolio.get("realized_pnl",   0.0) or 0.0
iv_rank     = portfolio.get("iv_rank")

open_positions = [p for p in positions if p.get("status") == "open"]
win_rate       = (wins / total_today * 100) if total_today > 0 else 0.0
risk_pct       = (abs(daily_pnl) / max_loss * 100) if max_loss else 0.0

def uptime_str(s: int) -> str:
    if s <= 0:
        return "—"
    h, rem = divmod(s, 3600)
    m, sc  = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sc:02d}"


# ─── HEADER BAR ───────────────────────────────────────────────────────────────

dot_html = '<span class="pulse-dot"></span>' if agent_alive else '<span class="dead-dot"></span>'

badges = ""
if dry_run:
    badges += ' <span class="badge badge-dry">DRY RUN</span>'
else:
    badges += ' <span class="badge badge-live">⬤ LIVE</span>'
if trading_halted:
    badges += ' <span class="badge badge-halt">⚠ HALTED</span>'
if agent_alive and not trading_halted:
    badges += ' <span class="badge badge-online">ONLINE</span>'

hb_str = last_alive_ts.strftime("Last heartbeat %H:%M:%S") if last_alive_ts else "No heartbeat"

st.markdown(f"""
<div class="hbar">
  {dot_html}
  <span class="agent-name">OPTIONS AGENT</span>
  <span style="color:#444;font-size:12px;">{strategy} · {underlying}</span>
  {badges}
  <span class="hb-time">{hb_str} &nbsp;·&nbsp; {datetime.now().strftime("%H:%M:%S")}</span>
</div>
""", unsafe_allow_html=True)


# ─── TOP METRICS (6 cards) ────────────────────────────────────────────────────

m1, m2, m3, m4, m5, m6 = st.columns(6)

pnl_color = "green" if daily_pnl >= 0 else "red"
with m1:
    st.markdown(f"""
    <div class="mcard {pnl_color}">
      <div class="mlabel">Daily P&amp;L</div>
      <div class="mval {pnl_color}">{fmt_money_signed(daily_pnl)}</div>
      <div class="msub">of ${max_loss:,.0f} limit</div>
    </div>
    """, unsafe_allow_html=True)

wr_color = "green" if win_rate >= 60 else ("yellow" if win_rate >= 40 else "red")
with m2:
    st.markdown(f"""
    <div class="mcard {wr_color}">
      <div class="mlabel">Win Rate</div>
      <div class="mval {wr_color}">{win_rate:.0f}%</div>
      <div class="msub">{wins}W / {losses_count}L</div>
    </div>
    """, unsafe_allow_html=True)

pos_color = "red" if len(open_positions) >= max_pos else "blue"
with m3:
    st.markdown(f"""
    <div class="mcard {pos_color}">
      <div class="mlabel">Open Positions</div>
      <div class="mval blue">{len(open_positions)}</div>
      <div class="msub">of {max_pos} max</div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="mcard gray">
      <div class="mlabel">Trades Today</div>
      <div class="mval gray">{total_today}</div>
      <div class="msub">closed</div>
    </div>
    """, unsafe_allow_html=True)

risk_bar_color = "#ff1744" if risk_pct > 80 else ("#ff9100" if risk_pct > 50 else "#00e676")
risk_card_cls  = "red" if risk_pct > 80 else ("yellow" if risk_pct > 50 else "green")
with m5:
    st.markdown(f"""
    <div class="mcard {risk_card_cls}">
      <div class="mlabel">Risk Used</div>
      <div class="mval {'red' if risk_pct > 80 else 'yellow' if risk_pct > 50 else 'green'}">{risk_pct:.0f}%</div>
      <div class="risk-bar-bg"><div class="risk-bar-fill" style="width:{min(risk_pct,100):.0f}%;background:{risk_bar_color};"></div></div>
    </div>
    """, unsafe_allow_html=True)

if trading_halted:
    s_cls, s_val = "red", "HALTED"
elif not agent_alive:
    s_cls, s_val = "red", "OFFLINE"
elif agent_sleeping:
    s_cls, s_val = "blue", "SLEEPING"
elif dry_run:
    s_cls, s_val = "yellow", "DRY RUN"
else:
    s_cls, s_val = "green", "ONLINE"

with m6:
    st.markdown(f"""
    <div class="mcard {s_cls}">
      <div class="mlabel">Agent Status</div>
      <div class="mval {s_cls}">{s_val}</div>
      <div class="msub">uptime {uptime_str(uptime_sec)}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


# ─── MAIN 3-COLUMN LAYOUT ─────────────────────────────────────────────────────

col_left, col_center, col_right = st.columns([4, 3.5, 2.5])


# ── LEFT: Open positions ──────────────────────────────────────────────────────
with col_left:
    st.markdown('<div class="sec-hdr">📊 Open Positions</div>', unsafe_allow_html=True)

    if not open_positions:
        st.markdown('<div class="empty-state">No open positions</div>', unsafe_allow_html=True)
    else:
        for pos in open_positions:
            strat      = pos.get("strategy", "?")
            exp        = pos.get("expiration", "?")
            credit     = pos.get("net_credit", 0) or 0
            max_profit = pos.get("max_profit", 0) or 0
            entry_time = pos.get("entry_time", "")
            qty        = pos.get("qty", 1)
            st_class   = strat.lower() if strat in ("BWB", "CONDOR") else "other"
            badge_cls  = f"strat-{strat.lower()}"
            exp_fmt    = fmt_expiry(exp)
            dte_days   = dte(exp)
            strikes    = strikes_display(pos)
            try:
                et_fmt = datetime.fromisoformat(entry_time).strftime("%m/%d %H:%M")
            except Exception:
                et_fmt = entry_time[:16] if entry_time else "—"

            st.markdown(f"""
            <div class="pos-card {st_class}">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                  <span class="strat-badge {badge_cls}">{strat}</span>
                  <span style="color:#88a0c0;font-size:11px;margin-left:8px;">{exp_fmt}</span>
                  <span style="color:#555;font-size:10px;margin-left:6px;">({dte_days}d)</span>
                </div>
                <div style="text-align:right;">
                  <span class="pos-credit">${credit:.2f} cr</span>
                  <span style="color:#444;font-size:10px;margin-left:6px;">×{qty}</span>
                </div>
              </div>
              <div style="margin-top:5px;">
                <span class="pos-label">strikes </span>
                <span class="pos-val">{strikes}</span>
              </div>
              <div style="margin-top:3px;">
                <span class="pos-label">max profit </span>
                <span style="color:#00e676;font-size:11px;">${max_profit:.2f}</span>
                <span style="margin-left:14px;" class="pos-label">entered </span>
                <span class="pos-time">{et_fmt}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Payoff diagram
            fig = None
            if strat == "BWB":
                fig = bwb_payoff_chart(pos, spx_price)
            elif strat == "CONDOR":
                fig = condor_payoff_chart(pos, spx_price)

            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── CENTER: P&L Chart ─────────────────────────────────────────────────────────
with col_center:
    st.markdown('<div class="sec-hdr">📈 Cumulative P&amp;L</div>', unsafe_allow_html=True)

    fig_pnl = pnl_chart(trade_history)
    st.plotly_chart(fig_pnl, use_container_width=True, config={"displayModeBar": False})

    # Quick stats below chart
    if trade_history:
        total_pnl = sum(float(t.get("realized_pnl", t.get("pnl", 0)) or 0) for t in trade_history)
        avg_pnl   = total_pnl / len(trade_history)
        all_wins  = sum(1 for t in trade_history if (t.get("realized_pnl", t.get("pnl", 0)) or 0) > 0)
        all_wr    = all_wins / len(trade_history) * 100

        sa, sb, sc_col = st.columns(3)
        with sa:
            c = "green" if total_pnl >= 0 else "red"
            st.markdown(f"""
            <div style="text-align:center;">
              <div class="mlabel">All-time P&L</div>
              <div style="font-size:16px;font-weight:700;color:{'#00e676' if total_pnl>=0 else '#ff1744'};
                           font-family:monospace;">{fmt_money_signed(total_pnl)}</div>
            </div>
            """, unsafe_allow_html=True)
        with sb:
            st.markdown(f"""
            <div style="text-align:center;">
              <div class="mlabel">Avg P&L / Trade</div>
              <div style="font-size:16px;font-weight:700;color:{'#00e676' if avg_pnl>=0 else '#ff1744'};
                           font-family:monospace;">{fmt_money_signed(avg_pnl)}</div>
            </div>
            """, unsafe_allow_html=True)
        with sc_col:
            st.markdown(f"""
            <div style="text-align:center;">
              <div class="mlabel">Historical Win%</div>
              <div style="font-size:16px;font-weight:700;color:#2979ff;font-family:monospace;">{all_wr:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # Account P&L row
    st.markdown('<div class="sec-hdr" style="margin-top:8px;">💰 Account</div>', unsafe_allow_html=True)
    ac1, ac2, ac3 = st.columns(3)
    for col_a, label, val in [
        (ac1, "Unrealized", unrealized),
        (ac2, "Realized",   realized),
        (ac3, "SPX Price",  spx_price),
    ]:
        with col_a:
            if label == "SPX Price":
                disp = f"${spx_price:,.2f}" if spx_price else "—"
                color_style = "color:#2979ff"
            else:
                disp        = fmt_money_signed(val)
                color_style = f"color:{'#00e676' if (val or 0)>=0 else '#ff1744'}"
            st.markdown(f"""
            <div style="text-align:center;">
              <div class="mlabel">{label}</div>
              <div style="font-size:15px;font-weight:700;{color_style};font-family:monospace;">{disp}</div>
            </div>
            """, unsafe_allow_html=True)


# ── RIGHT: Live Logs ──────────────────────────────────────────────────────────
with col_right:
    st.markdown('<div class="sec-hdr">📋 Live Logs</div>', unsafe_allow_html=True)

    if log_lines:
        log_html = '<div class="logbox">'
        for raw_line in log_lines:
            line = raw_line.strip().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if not line:
                continue
            ll = line.lower()
            if "error" in ll or "fatal" in ll or "critical" in ll:
                css = "log-err"
            elif "warning" in ll or "warn" in ll:
                css = "log-warn"
            elif "entered" in ll or "opened" in ll or "position open" in ll:
                css = "log-ok"
            elif "closed" in ll or "exit" in ll or "exited" in ll:
                css = "log-cyan"
            elif "info" in ll:
                css = "log-info"
            else:
                css = "log-dim"
            log_html += f'<div class="{css}">{line}</div>'
        log_html += "</div>"
        st.markdown(log_html, unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-state">No log file found</div>', unsafe_allow_html=True)


# ─── TRADE HISTORY TABLE ──────────────────────────────────────────────────────

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.markdown('<div class="sec-hdr">📜 Trade History (last 20)</div>', unsafe_allow_html=True)

# Merge risk_state trades + trade_history file, deduplicate by exit_time+strategy
all_trades = []
seen = set()
for t in trade_history:
    key = (t.get("exit_time", t.get("time", "")), t.get("strategy", ""))
    if key not in seen:
        seen.add(key)
        all_trades.append(t)

# Also include risk_state trades not already in history
for t in trades_today:
    key = (t.get("time", ""), t.get("strategy", ""))
    if key not in seen:
        seen.add(key)
        all_trades.append({
            "exit_time": t.get("time", ""),
            "strategy": t.get("strategy", "?"),
            "expiration": t.get("expiration", ""),
            "realized_pnl": t.get("pnl", 0),
            "win": t.get("win", False),
            "exit_reason": "",
        })

all_trades.sort(key=lambda t: t.get("exit_time", t.get("time", "")), reverse=True)
display_trades = all_trades[:20]

if not display_trades:
    st.markdown('<div class="empty-state">No trades yet</div>', unsafe_allow_html=True)
else:
    # Header
    st.markdown("""
    <div class="th-row" style="color:#555;font-size:10px;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid #2a2e3a;">
      <span class="th-time">Time</span>
      <span class="th-strat">Strategy</span>
      <span class="th-exp">Expiry</span>
      <span class="th-strikes">Strikes</span>
      <span class="th-pnl">P&amp;L</span>
      <span class="th-res">Result</span>
    </div>
    """, unsafe_allow_html=True)

    rows_html = ""
    for t in display_trades:
        ts_raw = t.get("exit_time", t.get("time", ""))
        try:
            ts_fmt = datetime.fromisoformat(ts_raw).strftime("%m/%d %H:%M")
        except Exception:
            ts_fmt = str(ts_raw)[:16]

        strat   = t.get("strategy", "?")
        exp     = fmt_expiry(t.get("expiration", ""))
        pnl_val = float(t.get("realized_pnl", t.get("pnl", 0)) or 0)
        is_win  = pnl_val > 0
        reason  = t.get("exit_reason", "")

        badge_cls  = f"strat-{strat.lower()}" if strat in ("BWB", "CONDOR") else ""
        pnl_cls    = "pnl-win" if pnl_val > 0 else ("pnl-loss" if pnl_val < 0 else "pnl-zero")
        res_txt    = "WIN" if is_win else ("LOSS" if pnl_val < 0 else "—")
        res_color  = "#00e676" if is_win else ("#ff1744" if pnl_val < 0 else "#666")

        # Build strikes string from position keys
        sh = t.get("strike_high"); sm = t.get("strike_mid"); sl = t.get("strike_low")
        lp = t.get("long_put_strike"); sp_s = t.get("short_put_strike")
        sc_s = t.get("short_call_strike"); lc = t.get("long_call_strike")

        if sh and sm and sl:
            strikes_txt = f"{sh}/{sm}/{sl}"
        elif lp and lc:
            strikes_txt = f"P {lp}/{sp_s} C {sc_s}/{lc}"
        else:
            strikes_txt = reason[:30] if reason else "—"

        rows_html += f"""
        <div class="th-row">
          <span class="th-time">{ts_fmt}</span>
          <span class="th-strat"><span class="strat-badge {badge_cls}">{strat}</span></span>
          <span class="th-exp">{exp}</span>
          <span class="th-strikes">{strikes_txt}</span>
          <span class="th-pnl {pnl_cls}">{fmt_money_signed(pnl_val)}</span>
          <span class="th-res" style="color:{res_color}">{res_txt}</span>
        </div>
        """

    st.markdown(f'<div style="background:#13161d;border:1px solid #1a1e27;border-radius:8px;padding:8px 12px;">{rows_html}</div>',
                unsafe_allow_html=True)


# ─── CONFIGURATION ROW ────────────────────────────────────────────────────────

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.markdown('<div class="sec-hdr">⚙️ Configuration</div>', unsafe_allow_html=True)

cfg_items = [
    ("Strategy",        strategy),
    ("Underlying",      underlying),
    ("Max Positions",   str(max_pos)),
    ("Daily Loss Limit", f"${max_loss:,.0f}"),
    ("Position Risk",   f"${max_risk:,.0f}"),
    ("Scan Interval",   f"{scan_int}s"),
    ("Mode",            "DRY RUN" if dry_run else "LIVE"),
    ("IV Rank",         f"{iv_rank:.0f}" if iv_rank else "—"),
]

cfg_cols = st.columns(len(cfg_items))
for col_c, (label, val) in zip(cfg_cols, cfg_items):
    with col_c:
        is_live = (label == "Mode" and val == "LIVE")
        val_color = "#ff1744" if is_live else ("#ffd600" if label == "Mode" else "#c8cdd8")
        st.markdown(f"""
        <div class="cfg-item">
          <div class="cfg-label">{label}</div>
          <div class="cfg-val" style="color:{val_color}">{val}</div>
        </div>
        """, unsafe_allow_html=True)


# ─── FOOTER ───────────────────────────────────────────────────────────────────

st.markdown("""
<div style="text-align:center;color:#2a2e3a;font-size:10px;padding:20px 0 8px;letter-spacing:1px;">
  OPTIONS AGENT DASHBOARD · IBKR GATEWAY · AUTO-REFRESH 30s
</div>
""", unsafe_allow_html=True)


# ─── AUTO-REFRESH (30 seconds) ────────────────────────────────────────────────

time.sleep(30)
st.rerun()
