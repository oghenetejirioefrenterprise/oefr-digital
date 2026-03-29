"""
Options Agent Dashboard — Electric trading aesthetic.
Reads data from JSON files written by state_writer.py.
Never connects to IBKR directly.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

import numpy as np
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
BACKTEST_FILE   = os.path.join(DATA_DIR, "backtest_results.json")

# ─── Color palette ────────────────────────────────────────────────────────────
C_BG       = "#070b14"
C_SURFACE  = "#0d1320"
C_BORDER   = "#1a2236"
C_BORDER_L = "#253352"
C_TEXT     = "#e0e4ec"
C_DIM      = "#586580"
C_MUTED    = "#2a3548"
C_AMBER    = "#ffb830"
C_AMBER_DK = "#cc9320"
C_GOLD     = "#ffd700"
C_GREEN    = "#00e68a"
C_GREEN_DK = "#00b36b"
C_RED      = "#ff4757"
C_RED_DK   = "#cc3344"
C_BLUE     = "#0099ff"
C_ORANGE   = "#ff6b35"
C_CYAN     = "#00d4ff"
C_CHART_BG = "#060a12"

# ─── CSS ──────────────────────────────────────────────────────────────────────
_CSS = """<style>
  @import url('https://fonts.googleapis.com/css2?family=Urbanist:wght@400;500;600;700;800&family=Azeret+Mono:wght@400;500;600;700&display=swap');

  .stApp {
    background-color: $BG !important;
    background-image:
      radial-gradient(ellipse at 10% 90%, rgba(0,230,138,0.07) 0%, transparent 50%),
      radial-gradient(ellipse at 90% 10%, rgba(0,153,255,0.06) 0%, transparent 50%),
      radial-gradient(ellipse at 50% 50%, rgba(255,107,53,0.03) 0%, transparent 55%);
    color: $TEXT;
  }
  .block-container { padding: 0.6rem 1.5rem 2rem !important; max-width: 100% !important; }
  section[data-testid="stSidebar"], div[data-testid="stDecoration"], footer, #MainMenu, header[data-testid="stHeader"] { display: none !important; }

  .hbar {
    background: linear-gradient(135deg, $SURFACE 0%, #111828 100%);
    border: 1px solid $BORDER;
    border-radius: 14px;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    gap: 18px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
  }
  .hbar::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, $GREEN, $CYAN, $BLUE, $ORANGE);
    opacity: 0.8;
  }
  .agent-name {
    font-family: 'Urbanist', sans-serif;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: $CYAN;
  }
  .agent-sub {
    font-family: 'Urbanist', sans-serif;
    color: $DIM;
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.5px;
  }
  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    font-family: 'Azeret Mono', monospace;
    text-transform: uppercase;
  }
  .badge-dry { background: $GOLD18; color: $GOLD; border: 1px solid $GOLD40; }
  .badge-live { background: $RED18; color: $RED; border: 1px solid $RED40; }
  .badge-halt { background: $RED18; color: $RED; border: 1px solid $RED40; animation: alert-flash 1.2s ease infinite; }
  .badge-online { background: $GREEN18; color: $GREEN; border: 1px solid $GREEN40; }
  .badge-sleep { background: $BLUE18; color: $BLUE; border: 1px solid $BLUE40; }
  .hb-time {
    font-family: 'Azeret Mono', monospace;
    font-size: 11px;
    color: $DIM;
    margin-left: auto;
    letter-spacing: 0.5px;
  }

  .pulse-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: $GREEN;
    box-shadow: 0 0 8px $GREEN88, 0 0 16px $GREEN44;
    animation: aurora-pulse 2.5s ease-in-out infinite;
    margin-right: 10px;
    vertical-align: middle;
  }
  .dead-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: $RED;
    box-shadow: 0 0 6px $RED66;
    margin-right: 10px;
    vertical-align: middle;
  }
  .sleep-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: $BLUE;
    box-shadow: 0 0 6px $BLUE66;
    animation: breathe 3s ease-in-out infinite;
    margin-right: 10px;
    vertical-align: middle;
  }
  @keyframes aurora-pulse {
    0%, 100% { background: $GREEN; box-shadow: 0 0 8px $GREEN88, 0 0 16px $GREEN44; }
    33% { background: $CYAN; box-shadow: 0 0 8px $CYAN88, 0 0 16px $CYAN44; }
    66% { background: $BLUE; box-shadow: 0 0 8px $BLUE88, 0 0 16px $BLUE44; }
  }
  @keyframes breathe {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.2; }
  }
  @keyframes alert-flash {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  .mcard {
    background: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 14px;
    padding: 16px 18px;
    text-align: center;
    height: 100px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
  }
  .mcard::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, $GREEN, $BLUE);
  }
  .mcard:hover {
    border-color: $BORDER_L;
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  }
  .mcard.green::before { background: linear-gradient(90deg, $GREEN, $CYAN); }
  .mcard.red::before { background: linear-gradient(90deg, $RED, $ORANGE); }
  .mcard.amber::before { background: linear-gradient(90deg, $AMBER, $GOLD); }
  .mcard.blue::before { background: linear-gradient(90deg, $BLUE, $CYAN); }
  .mcard.gold::before { background: linear-gradient(90deg, $GOLD, $AMBER); }
  .mcard.muted::before { background: $MUTED; }
  .mlabel {
    font-family: 'Urbanist', sans-serif;
    font-size: 10px;
    color: $DIM;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-weight: 600;
    margin-bottom: 6px;
  }
  .mval {
    font-size: 26px;
    font-weight: 700;
    font-family: 'Azeret Mono', monospace;
    line-height: 1.1;
  }
  .mval.green { color: $GREEN; }
  .mval.red { color: $RED; }
  .mval.amber { color: $AMBER; }
  .mval.blue { color: $BLUE; }
  .mval.gold { color: $GOLD; }
  .mval.muted { color: $DIM; }
  .msub {
    font-family: 'Urbanist', sans-serif;
    font-size: 10px;
    color: $DIM;
    margin-top: 5px;
    font-weight: 500;
  }

  .sec-hdr {
    font-family: 'Urbanist', sans-serif;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 3px;
    font-weight: 700;
    padding-bottom: 8px;
    border-bottom: 1px solid $BORDER;
    margin-bottom: 12px;
    margin-top: 4px;
    color: $CYAN;
  }

  .pos-card {
    background: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 10px;
    font-family: 'Azeret Mono', monospace;
    font-size: 12px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
  }
  .pos-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; bottom: 0;
    width: 3px;
  }
  .pos-card:hover {
    border-color: $BORDER_L;
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(0,0,0,0.3);
  }
  .pos-card.bwb::before { background: linear-gradient(180deg, $GREEN, $CYAN); }
  .pos-card.condor::before { background: linear-gradient(180deg, $BLUE, $CYAN); }
  .strat-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
    font-family: 'Azeret Mono', monospace;
  }
  .strat-bwb { background: $GREEN18; color: $GREEN; border: 1px solid $GREEN40; }
  .strat-condor { background: $BLUE18; color: $BLUE; border: 1px solid $BLUE40; }
  .pos-label {
    font-family: 'Urbanist', sans-serif;
    color: $DIM;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 600;
  }
  .pos-val { color: $TEXT; font-size: 12px; }
  .pos-credit { color: $AMBER; font-weight: 700; }
  .pos-time {
    color: $DIM;
    font-size: 10px;
    font-family: 'Azeret Mono', monospace;
  }

  .logbox {
    background: #060a12;
    border: 1px solid $BORDER;
    border-radius: 12px;
    padding: 12px 14px;
    max-height: 420px;
    overflow-y: auto;
    font-family: 'Azeret Mono', monospace;
    font-size: 10.5px;
    line-height: 1.8;
  }
  .logbox::-webkit-scrollbar { width: 4px; }
  .logbox::-webkit-scrollbar-track { background: transparent; }
  .logbox::-webkit-scrollbar-thumb { background: $BORDER_L; border-radius: 2px; }
  .log-err { color: $RED; }
  .log-warn { color: $GOLD; }
  .log-ok { color: $GREEN; }
  .log-cyan { color: $CYAN; }
  .log-info { color: $DIM; }
  .log-dim { color: #2a3548; }

  .th-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  .th-wrap::-webkit-scrollbar { height: 3px; }
  .th-wrap::-webkit-scrollbar-track { background: transparent; }
  .th-wrap::-webkit-scrollbar-thumb { background: $BORDER_L; border-radius: 2px; }
  .th-row {
    display: flex;
    align-items: center;
    border-bottom: 1px solid $BORDER;
    padding: 7px 0;
    font-size: 11.5px;
    font-family: 'Azeret Mono', monospace;
    min-width: 580px;
  }
  .th-row:last-child { border-bottom: none; }
  .th-time { color: $DIM; width: 140px; flex-shrink: 0; }
  .th-strat { width: 80px; flex-shrink: 0; }
  .th-exp { color: $DIM; width: 100px; flex-shrink: 0; }
  .th-strikes { color: $TEXT; flex: 1; min-width: 60px; }
  .th-pnl { width: 100px; flex-shrink: 0; text-align: right; font-weight: 600; }
  .th-res { width: 60px; flex-shrink: 0; text-align: right; font-weight: 600; }
  .pnl-win { color: $GREEN; }
  .pnl-loss { color: $RED; }
  .pnl-zero { color: $DIM; }

  .risk-bar-bg {
    background: $BORDER;
    border-radius: 4px;
    height: 5px;
    margin-top: 6px;
    overflow: hidden;
  }
  .risk-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.6s cubic-bezier(0.4,0,0.2,1);
  }

  .cfg-item {
    background: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 10px;
    padding: 10px 14px;
    text-align: center;
  }
  .cfg-label {
    font-family: 'Urbanist', sans-serif;
    font-size: 9px;
    color: $DIM;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 600;
  }
  .cfg-val {
    font-family: 'Azeret Mono', monospace;
    font-size: 13px;
    color: $TEXT;
    margin-top: 3px;
    font-weight: 500;
  }

  .empty-state {
    color: $DIM;
    text-align: center;
    padding: 40px 0;
    font-size: 13px;
    font-family: 'Urbanist', sans-serif;
    font-style: italic;
  }

  .stat-mini { text-align: center; padding: 6px 0; }
  .stat-mini .mlabel { margin-bottom: 4px; }
  .stat-mini .stat-val {
    font-size: 15px;
    font-weight: 700;
    font-family: 'Azeret Mono', monospace;
  }
</style>
"""
# Replace color tokens with actual values (longest tokens first to avoid partial matches)
_token_map = {
    "$BORDER_L": C_BORDER_L, "$BORDER": C_BORDER, "$SURFACE": C_SURFACE,
    "$AMBER_DK": C_AMBER_DK, "$AMBER": C_AMBER,
    "$GREEN_DK": C_GREEN_DK, "$GREEN": C_GREEN,
    "$RED_DK": C_RED_DK, "$RED": C_RED,
    "$ORANGE": C_ORANGE, "$MUTED": C_MUTED,
    "$GOLD": C_GOLD, "$CYAN": C_CYAN, "$BLUE": C_BLUE,
    "$TEXT": C_TEXT, "$BG": C_BG, "$DIM": C_DIM,
}
for _tok in sorted(_token_map, key=len, reverse=True):
    _CSS = _CSS.replace(_tok, _token_map[_tok])
st.markdown(_CSS, unsafe_allow_html=True)


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
        return f"{pos.get('strike_high','-')} / {pos.get('strike_mid','-')}x2 / {pos.get('strike_low','-')}"
    elif strat == "CONDOR":
        return (f"P {pos.get('long_put_strike','-')}/{pos.get('short_put_strike','-')}"
                f" · C {pos.get('short_call_strike','-')}/{pos.get('long_call_strike','-')}")
    return "—"


def fmt_expiry(exp: str) -> str:
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
    sh = float(pos.get("strike_high", 0))
    sm = float(pos.get("strike_mid", 0))
    sl = float(pos.get("strike_low", 0))
    credit = float(pos.get("net_credit", 0))
    qty    = int(pos.get("qty", 1))

    if sh == 0 or sm == 0 or sl == 0:
        return None

    lo = min(sl - 20, sm - 35)
    hi = max(sh + 20, sm + 35)
    prices = [lo + (hi - lo) * i / 200 for i in range(201)]

    def put_payoff(K, S):
        return max(K - S, 0.0)

    def bwb_pnl_per_unit(S):
        pnl = (
            put_payoff(sh, S)
            - 2 * put_payoff(sm, S)
            + put_payoff(sl, S)
            + credit
        )
        return pnl * 100

    pnls = [bwb_pnl_per_unit(s) * qty for s in prices]
    fig = go.Figure()

    pos_y = [max(p, 0) for p in pnls]
    neg_y = [min(p, 0) for p in pnls]

    fig.add_trace(go.Scatter(
        x=prices, y=pos_y, fill="tozeroy",
        fillcolor="rgba(0,230,138,0.12)",
        line=dict(color=C_GREEN, width=1.5), name="Profit",
        hovertemplate="$%{x:.0f}: +$%{y:.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=prices, y=neg_y, fill="tozeroy",
        fillcolor="rgba(255,71,87,0.12)",
        line=dict(color=C_RED, width=1.5), name="Loss",
        hovertemplate="$%{x:.0f}: -$%{y:.0f}<extra></extra>",
    ))

    for strike, label, color in [
        (sh, f"H {sh:.0f}", C_CYAN),
        (sm, f"M {sm:.0f}", C_BLUE),
        (sl, f"L {sl:.0f}", C_ORANGE),
    ]:
        fig.add_vline(
            x=strike, line=dict(color=color, width=1, dash="dot"),
            annotation_text=label, annotation_font_size=9, annotation_font_color=color,
        )

    if spx_price and lo < spx_price < hi:
        fig.add_vline(
            x=spx_price, line=dict(color=C_AMBER, width=1.5, dash="dash"),
            annotation_text=f"SPX {spx_price:.0f}",
            annotation_font_size=9, annotation_font_color=C_AMBER,
        )

    fig.add_hline(y=0, line=dict(color=C_BORDER_L, width=1))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=C_CHART_BG, plot_bgcolor=C_CHART_BG,
        margin=dict(l=32, r=8, t=8, b=28), height=160, showlegend=False,
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C_DIM, family="Azeret Mono"), tickformat=".0f"),
        yaxis=dict(showgrid=True, gridcolor=C_BORDER, tickfont=dict(size=9, color=C_DIM, family="Azeret Mono"), tickformat="$.0f", zeroline=False),
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
        fillcolor="rgba(0,230,138,0.12)",
        line=dict(color=C_GREEN, width=1.5), name="Profit",
    ))
    fig.add_trace(go.Scatter(
        x=prices, y=neg_y, fill="tozeroy",
        fillcolor="rgba(255,71,87,0.12)",
        line=dict(color=C_RED, width=1.5), name="Loss",
    ))

    for strike, label, color in [
        (lp, f"{lp:.0f}", C_ORANGE),
        (sp, f"{sp:.0f}", C_BLUE),
        (sc, f"{sc:.0f}", C_BLUE),
        (lc, f"{lc:.0f}", C_ORANGE),
    ]:
        fig.add_vline(x=strike, line=dict(color=color, width=1, dash="dot"),
                      annotation_text=label, annotation_font_size=9, annotation_font_color=color)

    if spx_price and lo < spx_price < hi:
        fig.add_vline(x=spx_price, line=dict(color=C_AMBER, width=1.5, dash="dash"),
                      annotation_text=f"SPX {spx_price:.0f}", annotation_font_size=9,
                      annotation_font_color=C_AMBER)

    fig.add_hline(y=0, line=dict(color=C_BORDER_L, width=1))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=C_CHART_BG, plot_bgcolor=C_CHART_BG,
        margin=dict(l=32, r=8, t=8, b=28), height=160, showlegend=False,
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C_DIM, family="Azeret Mono"), tickformat=".0f"),
        yaxis=dict(showgrid=True, gridcolor=C_BORDER, tickfont=dict(size=9, color=C_DIM, family="Azeret Mono"),
                   tickformat="$.0f", zeroline=False),
    )
    return fig


# ─── P&L cumulative chart ─────────────────────────────────────────────────────

def pnl_chart(trade_history: list) -> go.Figure:
    if not trade_history:
        fig = go.Figure()
        fig.add_annotation(text="Awaiting first trade", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False,
                           font=dict(color=C_MUTED, size=13, family="Urbanist"))
        fig.update_layout(template="plotly_dark", paper_bgcolor=C_CHART_BG,
                          plot_bgcolor=C_CHART_BG, height=280,
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
    color = C_GREEN if final >= 0 else C_RED
    fill  = "rgba(0,230,138,0.08)" if final >= 0 else "rgba(255,71,87,0.08)"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=cumulative,
        mode="lines+markers",
        line=dict(color=color, width=2),
        fill="tozeroy", fillcolor=fill,
        marker=dict(size=4, color=color),
        hovertemplate="<b>%{x}</b><br>Cumulative: $%{y:,.2f}<extra></extra>",
    ))

    fig.add_hline(y=0, line=dict(color=C_BORDER_L, width=1))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=C_CHART_BG, plot_bgcolor=C_CHART_BG,
        height=280,
        margin=dict(l=48, r=16, t=16, b=48),
        showlegend=False,
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color=C_DIM, family="Azeret Mono"), tickangle=-30),
        yaxis=dict(showgrid=True, gridcolor=C_BORDER, tickfont=dict(size=10, color=C_DIM, family="Azeret Mono"), tickprefix="$", zeroline=False),
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

if agent_sleeping:
    dot_html = '<span class="sleep-dot"></span>'
elif agent_alive:
    dot_html = '<span class="pulse-dot"></span>'
else:
    dot_html = '<span class="dead-dot"></span>'

badges = ""
if dry_run:
    badges += f' <span class="badge badge-dry">Paper</span>'
else:
    badges += f' <span class="badge badge-live">Live</span>'
if trading_halted:
    badges += f' <span class="badge badge-halt">Halted</span>'
if agent_sleeping:
    badges += f' <span class="badge badge-sleep">Sleeping</span>'
elif agent_alive and not trading_halted:
    badges += f' <span class="badge badge-online">Online</span>'

hb_str = last_alive_ts.strftime("%H:%M:%S") if last_alive_ts else "—"

st.markdown(f"""
<div class="hbar">
  {dot_html}
  <span class="agent-name">Options Agent</span>
  <span class="agent-sub">{strategy} &middot; {underlying}</span>
  {badges}
  <span class="hb-time">{hb_str} &nbsp;&middot;&nbsp; {datetime.now().strftime("%H:%M:%S")}</span>
</div>
""", unsafe_allow_html=True)


# ─── TOP METRICS (6 cards) ────────────────────────────────────────────────────

m1, m2, m3, m4, m5, m6 = st.columns(6)

pnl_card = "green" if daily_pnl >= 0 else "red"
pnl_val_cls = "green" if daily_pnl >= 0 else "red"
with m1:
    st.markdown(f"""
    <div class="mcard {pnl_card}">
      <div class="mlabel">Daily P&amp;L</div>
      <div class="mval {pnl_val_cls}">{fmt_money_signed(daily_pnl)}</div>
      <div class="msub">of ${max_loss:,.0f} limit</div>
    </div>
    """, unsafe_allow_html=True)

wr_card = "green" if win_rate >= 60 else ("gold" if win_rate >= 40 else "red")
wr_val  = "green" if win_rate >= 60 else ("gold" if win_rate >= 40 else "red")
with m2:
    st.markdown(f"""
    <div class="mcard {wr_card}">
      <div class="mlabel">Win Rate</div>
      <div class="mval {wr_val}">{win_rate:.0f}%</div>
      <div class="msub">{wins}W / {losses_count}L</div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="mcard blue">
      <div class="mlabel">Open Positions</div>
      <div class="mval blue">{len(open_positions)}</div>
      <div class="msub">of {max_pos} max</div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="mcard muted">
      <div class="mlabel">Trades Today</div>
      <div class="mval muted">{total_today}</div>
      <div class="msub">closed</div>
    </div>
    """, unsafe_allow_html=True)

risk_bar_color = C_RED if risk_pct > 80 else (C_GOLD if risk_pct > 50 else C_GREEN)
risk_card = "red" if risk_pct > 80 else ("gold" if risk_pct > 50 else "green")
with m5:
    st.markdown(f"""
    <div class="mcard {risk_card}">
      <div class="mlabel">Risk Used</div>
      <div class="mval {risk_card}">{risk_pct:.0f}%</div>
      <div class="risk-bar-bg"><div class="risk-bar-fill" style="width:{min(risk_pct,100):.0f}%;background:{risk_bar_color};"></div></div>
    </div>
    """, unsafe_allow_html=True)

if trading_halted:
    s_card, s_val_cls, s_val = "red", "red", "Halted"
elif not agent_alive:
    s_card, s_val_cls, s_val = "red", "red", "Offline"
elif agent_sleeping:
    s_card, s_val_cls, s_val = "blue", "blue", "Sleeping"
elif dry_run:
    s_card, s_val_cls, s_val = "amber", "amber", "Paper"
else:
    s_card, s_val_cls, s_val = "green", "green", "Live"

with m6:
    st.markdown(f"""
    <div class="mcard {s_card}">
      <div class="mlabel">Agent Status</div>
      <div class="mval {s_val_cls}">{s_val}</div>
      <div class="msub">uptime {uptime_str(uptime_sec)}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)


# ─── MAIN 3-COLUMN LAYOUT ─────────────────────────────────────────────────────

col_left, col_center, col_right = st.columns([4, 3.5, 2.5])


# ── LEFT: Open positions ──────────────────────────────────────────────────────
with col_left:
    st.markdown('<div class="sec-hdr">Open Positions</div>', unsafe_allow_html=True)

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
                  <span style="color:{C_CYAN};font-size:11px;margin-left:8px;font-family:'Urbanist',sans-serif;">{exp_fmt}</span>
                  <span style="color:{C_DIM};font-size:10px;margin-left:6px;font-family:'Azeret Mono',monospace;">({dte_days}d)</span>
                </div>
                <div style="text-align:right;">
                  <span class="pos-credit">${credit:.2f} cr</span>
                  <span style="color:{C_MUTED};font-size:10px;margin-left:6px;">x{qty}</span>
                </div>
              </div>
              <div style="margin-top:7px;">
                <span class="pos-label">strikes </span>
                <span class="pos-val">{strikes}</span>
              </div>
              <div style="margin-top:4px;">
                <span class="pos-label">max profit </span>
                <span style="color:{C_GREEN};font-size:11px;font-family:'Azeret Mono',monospace;">${max_profit:.2f}</span>
                <span style="margin-left:14px;" class="pos-label">entered </span>
                <span class="pos-time">{et_fmt}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            fig = None
            if strat == "BWB":
                fig = bwb_payoff_chart(pos, spx_price)
            elif strat == "CONDOR":
                fig = condor_payoff_chart(pos, spx_price)
            if fig:
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


# ── CENTER: P&L Chart ─────────────────────────────────────────────────────────
with col_center:
    st.markdown('<div class="sec-hdr">Cumulative P&amp;L</div>', unsafe_allow_html=True)

    fig_pnl = pnl_chart(trade_history)
    st.plotly_chart(fig_pnl, width="stretch", config={"displayModeBar": False})

    if trade_history:
        total_pnl = sum(float(t.get("realized_pnl", t.get("pnl", 0)) or 0) for t in trade_history)
        avg_pnl   = total_pnl / len(trade_history)
        all_wins  = sum(1 for t in trade_history if (t.get("realized_pnl", t.get("pnl", 0)) or 0) > 0)
        all_wr    = all_wins / len(trade_history) * 100

        sa, sb, sc_col = st.columns(3)
        with sa:
            st.markdown(f"""
            <div class="stat-mini">
              <div class="mlabel">All-time P&amp;L</div>
              <div class="stat-val" style="color:{C_GREEN if total_pnl>=0 else C_RED}">{fmt_money_signed(total_pnl)}</div>
            </div>
            """, unsafe_allow_html=True)
        with sb:
            st.markdown(f"""
            <div class="stat-mini">
              <div class="mlabel">Avg / Trade</div>
              <div class="stat-val" style="color:{C_GREEN if avg_pnl>=0 else C_RED}">{fmt_money_signed(avg_pnl)}</div>
            </div>
            """, unsafe_allow_html=True)
        with sc_col:
            st.markdown(f"""
            <div class="stat-mini">
              <div class="mlabel">Win Rate</div>
              <div class="stat-val" style="color:{C_AMBER}">{all_wr:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    st.markdown(f'<div class="sec-hdr">Account</div>', unsafe_allow_html=True)
    ac1, ac2, ac3 = st.columns(3)
    for col_a, label, val in [
        (ac1, "Unrealized", unrealized),
        (ac2, "Realized",   realized),
        (ac3, "SPX Price",  spx_price),
    ]:
        with col_a:
            if label == "SPX Price":
                disp = f"${spx_price:,.2f}" if spx_price else "—"
                color_style = f"color:{C_AMBER}"
            else:
                disp        = fmt_money_signed(val)
                color_style = f"color:{C_GREEN if (val or 0)>=0 else C_RED}"
            st.markdown(f"""
            <div class="stat-mini">
              <div class="mlabel">{label}</div>
              <div class="stat-val" style="{color_style}">{disp}</div>
            </div>
            """, unsafe_allow_html=True)


# ── RIGHT: Live Logs ──────────────────────────────────────────────────────────
with col_right:
    st.markdown('<div class="sec-hdr">Live Logs</div>', unsafe_allow_html=True)

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

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
st.markdown('<div class="sec-hdr">Trade History</div>', unsafe_allow_html=True)

all_trades = []
seen = set()
for t in trade_history:
    key = (t.get("exit_time", t.get("time", "")), t.get("strategy", ""))
    if key not in seen:
        seen.add(key)
        all_trades.append(t)

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
    table_html = f'<div style="background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:12px;padding:10px 14px;"><div class="th-wrap">'
    table_html += f'<div class="th-row" style="color:{C_DIM};font-size:10px;text-transform:uppercase;letter-spacing:1.5px;border-bottom:1px solid {C_BORDER_L};font-family:\'Urbanist\',sans-serif;font-weight:600;"><span class="th-time">Time</span><span class="th-strat">Strategy</span><span class="th-exp">Expiry</span><span class="th-strikes">Strikes</span><span class="th-pnl">P&amp;L</span><span class="th-res">Result</span></div>'

    for t in display_trades:
        ts_raw = t.get("exit_time", t.get("time", ""))
        try:
            ts_fmt = datetime.fromisoformat(ts_raw).strftime("%m/%d %H:%M")
        except Exception:
            ts_fmt = str(ts_raw)[:16]

        strat   = t.get("strategy", "?")
        exp     = fmt_expiry(t.get("expiration", ""))
        pnl_val = float(t.get("realized_pnl", t.get("pnl", 0)) or 0)
        reason  = t.get("exit_reason", "")

        badge_cls  = f"strat-{strat.lower()}" if strat in ("BWB", "CONDOR") else ""
        pnl_cls    = "pnl-win" if pnl_val > 0 else ("pnl-loss" if pnl_val < 0 else "pnl-zero")
        res_txt    = "WIN" if pnl_val > 0 else ("LOSS" if pnl_val < 0 else "—")
        res_color  = C_GREEN if pnl_val > 0 else (C_RED if pnl_val < 0 else C_DIM)

        sh = t.get("strike_high"); sm = t.get("strike_mid"); sl = t.get("strike_low")
        lp = t.get("long_put_strike"); sp_s = t.get("short_put_strike")
        sc_s = t.get("short_call_strike"); lc = t.get("long_call_strike")

        if sh and sm and sl:
            strikes_txt = f"{sh}/{sm}/{sl}"
        elif lp and lc:
            strikes_txt = f"P {lp}/{sp_s} C {sc_s}/{lc}"
        else:
            strikes_txt = reason[:30] if reason else "—"

        table_html += f'<div class="th-row"><span class="th-time">{ts_fmt}</span><span class="th-strat"><span class="strat-badge {badge_cls}">{strat}</span></span><span class="th-exp">{exp}</span><span class="th-strikes">{strikes_txt}</span><span class="th-pnl {pnl_cls}">{fmt_money_signed(pnl_val)}</span><span class="th-res" style="color:{res_color}">{res_txt}</span></div>'

    table_html += '</div></div>'
    st.markdown(table_html, unsafe_allow_html=True)


# ─── CONFIGURATION ROW ────────────────────────────────────────────────────────

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
st.markdown('<div class="sec-hdr">Configuration</div>', unsafe_allow_html=True)

cfg_items = [
    ("Strategy",        strategy),
    ("Underlying",      underlying),
    ("Max Positions",   str(max_pos)),
    ("Daily Loss Limit", f"${max_loss:,.0f}"),
    ("Position Risk",   f"${max_risk:,.0f}"),
    ("Scan Interval",   f"{scan_int}s"),
    ("Mode",            "PAPER" if dry_run else "LIVE"),
    ("IV Rank",         f"{iv_rank:.0f}" if iv_rank else "—"),
]

cfg_cols = st.columns(len(cfg_items))
for col_c, (label, val) in zip(cfg_cols, cfg_items):
    with col_c:
        is_live = (label == "Mode" and val == "LIVE")
        val_color = C_RED if is_live else (C_GOLD if label == "Mode" else C_TEXT)
        st.markdown(f"""
        <div class="cfg-item">
          <div class="cfg-label">{label}</div>
          <div class="cfg-val" style="color:{val_color}">{val}</div>
        </div>
        """, unsafe_allow_html=True)


# ─── BACKTEST RESULTS ────────────────────────────────────────────────────────

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
st.markdown('<div class="sec-hdr">Backtest Results</div>', unsafe_allow_html=True)

bt_data = read_json(BACKTEST_FILE, None)
if bt_data is None:
    st.markdown(
        f'<div class="empty-state">No backtest results yet.<br>'
        f'<span style="font-size:11px;color:{C_DIM};">Run: python -m backtest.run_backtest --strategy both --start 2020-01-01 --end 2024-12-31</span></div>',
        unsafe_allow_html=True,
    )
else:
    # ── Summary metrics row ──
    bt_pnl = bt_data.get("total_pnl", 0)
    bt_wr = bt_data.get("win_rate", 0)
    bt_sharpe = bt_data.get("sharpe_ratio", 0)
    bt_dd = bt_data.get("max_drawdown_pct", 0)
    bt_trades_n = bt_data.get("total_trades", 0)
    bt_avg_m = bt_data.get("avg_monthly_return_pct", 0)
    bt_pf = bt_data.get("profit_factor", 0)
    bt_strats = ", ".join(bt_data.get("strategies", []))

    bm1, bm2, bm3, bm4, bm5, bm6 = st.columns(6)
    with bm1:
        pnl_c = "green" if bt_pnl >= 0 else "red"
        st.markdown(f'<div class="mcard {pnl_c}"><div class="mlabel">Total P&amp;L</div><div class="mval {pnl_c}">{fmt_money_signed(bt_pnl)}</div><div class="msub">{bt_data.get("start_date","")} to {bt_data.get("end_date","")}</div></div>', unsafe_allow_html=True)
    with bm2:
        wr_c = "green" if bt_wr >= 55 else ("gold" if bt_wr >= 45 else "red")
        st.markdown(f'<div class="mcard {wr_c}"><div class="mlabel">Win Rate</div><div class="mval {wr_c}">{bt_wr:.1f}%</div><div class="msub">{bt_data.get("win_count",0)}W / {bt_data.get("loss_count",0)}L</div></div>', unsafe_allow_html=True)
    with bm3:
        sh_c = "green" if bt_sharpe >= 1 else ("gold" if bt_sharpe >= 0.5 else "red")
        st.markdown(f'<div class="mcard {sh_c}"><div class="mlabel">Sharpe Ratio</div><div class="mval {sh_c}">{bt_sharpe:.3f}</div><div class="msub">annualized</div></div>', unsafe_allow_html=True)
    with bm4:
        dd_c = "green" if bt_dd < 10 else ("gold" if bt_dd < 20 else "red")
        st.markdown(f'<div class="mcard {dd_c}"><div class="mlabel">Max Drawdown</div><div class="mval {dd_c}">{bt_dd:.1f}%</div><div class="msub">peak to trough</div></div>', unsafe_allow_html=True)
    with bm5:
        mr_c = "green" if bt_avg_m >= 10 else ("gold" if bt_avg_m >= 5 else "red")
        st.markdown(f'<div class="mcard {mr_c}"><div class="mlabel">Avg Monthly</div><div class="mval {mr_c}">{bt_avg_m:+.1f}%</div><div class="msub">target: 10%</div></div>', unsafe_allow_html=True)
    with bm6:
        st.markdown(f'<div class="mcard blue"><div class="mlabel">Total Trades</div><div class="mval blue">{bt_trades_n}</div><div class="msub">{bt_strats}</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── Equity curve + monthly returns heatmap ──
    bt_eq = bt_data.get("equity_curve", [])
    if bt_eq:
        step = max(1, len(bt_eq) // 1000)
        eq_sampled = bt_eq[::step]
        eq_dates = [p["date"] for p in eq_sampled]
        eq_vals = [p["equity"] for p in eq_sampled]
        final_eq = eq_vals[-1] if eq_vals else 0
        init_eq = bt_data.get("initial_capital", 10000)
        eq_color = C_GREEN if final_eq >= init_eq else C_RED
        eq_fill = "rgba(0,230,138,0.08)" if final_eq >= init_eq else "rgba(255,71,87,0.08)"

        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(
            x=eq_dates, y=eq_vals, mode="lines",
            line=dict(color=eq_color, width=1.5),
            fill="tozeroy", fillcolor=eq_fill,
            hovertemplate="<b>%{x}</b><br>Equity: $%{y:,.2f}<extra></extra>",
        ))
        fig_eq.add_hline(y=init_eq, line=dict(color=C_BORDER_L, width=1, dash="dash"),
                         annotation_text=f"Start ${init_eq:,.0f}", annotation_font_size=9,
                         annotation_font_color=C_DIM)
        fig_eq.update_layout(
            template="plotly_dark", paper_bgcolor=C_CHART_BG, plot_bgcolor=C_CHART_BG,
            height=320, margin=dict(l=56, r=16, t=20, b=40), showlegend=False,
            xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C_DIM, family="Azeret Mono")),
            yaxis=dict(showgrid=True, gridcolor=C_BORDER,
                       tickfont=dict(size=9, color=C_DIM, family="Azeret Mono"),
                       tickprefix="$", zeroline=False),
        )

        bt_col_l, bt_col_r = st.columns([3, 2])
        with bt_col_l:
            st.markdown(
                f'<div style="color:{C_CYAN};font-size:11px;font-weight:600;'
                f'letter-spacing:2px;text-transform:uppercase;'
                f'font-family:\'Urbanist\',sans-serif;margin-bottom:6px;">Equity Curve</div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(fig_eq, use_container_width=True, config={"displayModeBar": False})

        with bt_col_r:
            st.markdown(
                f'<div style="color:{C_CYAN};font-size:11px;font-weight:600;'
                f'letter-spacing:2px;text-transform:uppercase;'
                f'font-family:\'Urbanist\',sans-serif;margin-bottom:6px;">Monthly Returns (%)</div>',
                unsafe_allow_html=True,
            )
            mrp = bt_data.get("monthly_return_pct", {})
            if mrp:
                years_list = sorted(set(k[:4] for k in mrp))
                months_lbl = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
                month_nums = ["01","02","03","04","05","06","07","08","09","10","11","12"]
                z_data = []
                hover_data = []
                for yr in years_list:
                    row, h_row = [], []
                    for mn in month_nums:
                        key = f"{yr}-{mn}"
                        val = mrp.get(key)
                        row.append(val if val is not None else 0)
                        h_row.append(f"{val:+.1f}%" if val is not None else "—")
                    z_data.append(row)
                    hover_data.append(h_row)

                fig_heat = go.Figure(data=go.Heatmap(
                    z=z_data, x=months_lbl, y=years_list,
                    customdata=hover_data,
                    hovertemplate="%{y} %{x}: %{customdata}<extra></extra>",
                    colorscale=[[0, C_RED], [0.45, "#1a1a2e"], [0.55, "#1a1a2e"], [1, C_GREEN]],
                    zmid=0, showscale=False,
                    texttemplate="%{z:+.0f}", textfont=dict(size=9, family="Azeret Mono"),
                ))
                fig_heat.update_layout(
                    template="plotly_dark", paper_bgcolor=C_CHART_BG, plot_bgcolor=C_CHART_BG,
                    height=320, margin=dict(l=40, r=8, t=8, b=32),
                    xaxis=dict(tickfont=dict(size=9, color=C_DIM, family="Azeret Mono"), side="bottom"),
                    yaxis=dict(tickfont=dict(size=9, color=C_DIM, family="Azeret Mono"), autorange="reversed"),
                )
                st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})
            else:
                st.markdown(f'<div class="empty-state">No monthly data</div>', unsafe_allow_html=True)

    # ── Additional stats row ──
    bt_s1, bt_s2, bt_s3, bt_s4 = st.columns(4)
    with bt_s1:
        st.markdown(f'<div class="stat-mini"><div class="mlabel">Avg Win</div><div class="stat-val" style="color:{C_GREEN}">{fmt_money_signed(bt_data.get("avg_win",0))}</div></div>', unsafe_allow_html=True)
    with bt_s2:
        st.markdown(f'<div class="stat-mini"><div class="mlabel">Avg Loss</div><div class="stat-val" style="color:{C_RED}">{fmt_money_signed(bt_data.get("avg_loss",0))}</div></div>', unsafe_allow_html=True)
    with bt_s3:
        st.markdown(f'<div class="stat-mini"><div class="mlabel">Profit Factor</div><div class="stat-val" style="color:{C_AMBER}">{bt_pf:.2f}</div></div>', unsafe_allow_html=True)
    with bt_s4:
        total_ret = bt_pnl / max(bt_data.get("initial_capital", 10000), 1) * 100
        ret_c = C_GREEN if total_ret >= 0 else C_RED
        st.markdown(f'<div class="stat-mini"><div class="mlabel">Total Return</div><div class="stat-val" style="color:{ret_c}">{total_ret:+.1f}%</div></div>', unsafe_allow_html=True)


# ─── FOOTER ───────────────────────────────────────────────────────────────────

st.markdown(f"""
<div style="text-align:center;color:{C_MUTED};font-size:9px;padding:24px 0 8px;letter-spacing:2px;font-family:'Urbanist',sans-serif;font-weight:500;">
  OPTIONS AGENT &middot; IBKR GATEWAY &middot; AUTO-REFRESH 30s
</div>
""", unsafe_allow_html=True)


# ─── AUTO-REFRESH (30 seconds) ────────────────────────────────────────────────

time.sleep(30)
st.rerun()
