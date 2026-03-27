"""
Options Agent Dashboard — Warm Terminal aesthetic.
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

# ─── Color palette ────────────────────────────────────────────────────────────
C_BG       = "#0b0e13"
C_SURFACE  = "#12151c"
C_BORDER   = "#1c2030"
C_BORDER_L = "#262d40"
C_TEXT     = "#c5c8d4"
C_DIM      = "#505672"
C_MUTED    = "#3a3f54"
C_AMBER    = "#d4a847"
C_AMBER_DK = "#b8922e"
C_GOLD     = "#e5c07b"
C_GREEN    = "#4ec9b0"
C_GREEN_DK = "#3a9e8a"
C_RED      = "#e06c75"
C_RED_DK   = "#c25a63"
C_BLUE     = "#61afef"
C_PURPLE   = "#c678dd"
C_CYAN     = "#56b6c2"

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  /* ── Reset & base ── */
  .stApp {{
    background: {C_BG} !important;
    background-image:
      radial-gradient(ellipse at 20% 50%, rgba(212,168,71,0.03) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 20%, rgba(97,175,239,0.02) 0%, transparent 50%);
    color: {C_TEXT};
  }}
  .block-container {{ padding: 0.6rem 1.5rem 2rem 1.5rem !important; max-width: 100% !important; }}
  section[data-testid="stSidebar"] {{ display: none; }}
  div[data-testid="stDecoration"] {{ display: none; }}
  footer {{ display: none !important; }}
  #MainMenu {{ display: none !important; }}
  header[data-testid="stHeader"] {{ display: none !important; }}

  /* ── Typography ── */
  .font-data {{
    font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;
  }}
  .font-ui {{
    font-family: 'DM Sans', 'Segoe UI', system-ui, sans-serif;
  }}

  /* ── Header bar ── */
  .hbar {{
    background: linear-gradient(135deg, {C_SURFACE} 0%, #141824 100%);
    border: 1px solid {C_BORDER};
    border-bottom: 1px solid {C_AMBER}33;
    border-radius: 12px;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    gap: 18px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
  }}
  .hbar::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, {C_AMBER}44, transparent);
  }}
  .agent-name {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 3px;
    color: {C_AMBER};
    text-transform: uppercase;
  }}
  .agent-sub {{
    font-family: 'DM Sans', sans-serif;
    color: {C_DIM};
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.5px;
  }}
  .badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    font-family: 'JetBrains Mono', monospace;
    text-transform: uppercase;
  }}
  .badge-dry  {{ background: {C_GOLD}18; color: {C_GOLD}; border: 1px solid {C_GOLD}40; }}
  .badge-live {{ background: {C_RED}18; color: {C_RED}; border: 1px solid {C_RED}40; }}
  .badge-halt {{ background: {C_RED}18; color: {C_RED}; border: 1px solid {C_RED}40; }}
  .badge-online {{ background: {C_GREEN}18; color: {C_GREEN}; border: 1px solid {C_GREEN}40; }}
  .badge-sleep {{ background: {C_BLUE}18; color: {C_BLUE}; border: 1px solid {C_BLUE}40; }}

  .pulse-dot {{
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: {C_AMBER};
    box-shadow: 0 0 6px {C_AMBER}88, 0 0 12px {C_AMBER}44;
    animation: amber-pulse 2s ease-in-out infinite;
    margin-right: 10px;
    vertical-align: middle;
  }}
  .dead-dot {{
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: {C_RED};
    box-shadow: 0 0 4px {C_RED}66;
    margin-right: 10px;
    vertical-align: middle;
  }}
  .sleep-dot {{
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: {C_BLUE};
    box-shadow: 0 0 4px {C_BLUE}66;
    animation: sleep-fade 3s ease-in-out infinite;
    margin-right: 10px;
    vertical-align: middle;
  }}
  @keyframes amber-pulse {{
    0%, 100% {{ box-shadow: 0 0 6px {C_AMBER}88, 0 0 12px {C_AMBER}44; }}
    50% {{ box-shadow: 0 0 10px {C_AMBER}cc, 0 0 20px {C_AMBER}66; }}
  }}
  @keyframes sleep-fade {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.3; }}
  }}

  .hb-time {{
    font-size: 11px;
    color: {C_DIM};
    margin-left: auto;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.5px;
  }}

  /* ── Metric cards ── */
  .mcard {{
    background: {C_SURFACE};
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    padding: 16px 18px;
    text-align: center;
    height: 100px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
    position: relative;
  }}
  .mcard:hover {{
    border-color: {C_BORDER_L};
    box-shadow: 0 2px 12px rgba(0,0,0,0.3);
  }}
  .mcard.amber  {{ border-left: 3px solid {C_AMBER}; }}
  .mcard.green  {{ border-left: 3px solid {C_GREEN}; }}
  .mcard.red    {{ border-left: 3px solid {C_RED}; }}
  .mcard.blue   {{ border-left: 3px solid {C_BLUE}; }}
  .mcard.gold   {{ border-left: 3px solid {C_GOLD}; }}
  .mcard.muted  {{ border-left: 3px solid {C_MUTED}; }}
  .mlabel {{
    font-family: 'DM Sans', sans-serif;
    font-size: 10px;
    color: {C_DIM};
    text-transform: uppercase;
    letter-spacing: 1.8px;
    font-weight: 600;
    margin-bottom: 6px;
  }}
  .mval {{
    font-size: 24px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.1;
  }}
  .mval.amber  {{ color: {C_AMBER}; }}
  .mval.green  {{ color: {C_GREEN}; }}
  .mval.red    {{ color: {C_RED}; }}
  .mval.blue   {{ color: {C_BLUE}; }}
  .mval.gold   {{ color: {C_GOLD}; }}
  .mval.muted  {{ color: {C_DIM}; }}
  .msub {{
    font-family: 'DM Sans', sans-serif;
    font-size: 10px;
    color: {C_MUTED};
    margin-top: 4px;
    font-weight: 500;
  }}

  /* ── Section headers ── */
  .sec-hdr {{
    font-family: 'DM Sans', sans-serif;
    font-size: 11px;
    color: {C_AMBER};
    text-transform: uppercase;
    letter-spacing: 2.5px;
    font-weight: 700;
    padding-bottom: 8px;
    border-bottom: 1px solid {C_BORDER};
    margin-bottom: 12px;
    margin-top: 4px;
  }}

  /* ── Position cards ── */
  .pos-card {{
    background: {C_SURFACE};
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    position: relative;
    transition: border-color 0.3s ease;
  }}
  .pos-card:hover {{ border-color: {C_BORDER_L}; }}
  .pos-card.bwb   {{ border-left: 3px solid {C_GREEN}; }}
  .pos-card.condor {{ border-left: 3px solid {C_BLUE}; }}
  .strat-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 5px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
    font-family: 'JetBrains Mono', monospace;
  }}
  .strat-bwb    {{ background: {C_GREEN}18; color: {C_GREEN}; border: 1px solid {C_GREEN}44; }}
  .strat-condor {{ background: {C_BLUE}18; color: {C_BLUE}; border: 1px solid {C_BLUE}44; }}
  .pos-label {{
    font-family: 'DM Sans', sans-serif;
    color: {C_DIM};
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    font-weight: 600;
  }}
  .pos-val   {{ color: {C_TEXT}; font-size: 12px; }}
  .pos-credit {{ color: {C_AMBER}; font-weight: 700; }}
  .pos-time {{
    color: {C_MUTED};
    font-size: 10px;
    font-family: 'JetBrains Mono', monospace;
  }}

  /* ── Log viewer ── */
  .logbox {{
    background: #090b10;
    border: 1px solid {C_BORDER};
    border-radius: 10px;
    padding: 12px 14px;
    max-height: 420px;
    overflow-y: auto;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    line-height: 1.8;
  }}
  .logbox::-webkit-scrollbar {{ width: 4px; }}
  .logbox::-webkit-scrollbar-track {{ background: transparent; }}
  .logbox::-webkit-scrollbar-thumb {{ background: {C_BORDER_L}; border-radius: 2px; }}
  .log-err  {{ color: {C_RED}; }}
  .log-warn {{ color: {C_GOLD}; }}
  .log-ok   {{ color: {C_GREEN}; }}
  .log-cyan {{ color: {C_CYAN}; }}
  .log-info {{ color: {C_DIM}; }}
  .log-dim  {{ color: #363c52; }}

  /* ── Trade history table ── */
  .th-row {{
    display: flex;
    align-items: center;
    border-bottom: 1px solid {C_BORDER};
    padding: 7px 0;
    font-size: 11.5px;
    font-family: 'JetBrains Mono', monospace;
  }}
  .th-row:last-child {{ border-bottom: none; }}
  .th-time {{ color: {C_DIM}; width: 140px; flex-shrink: 0; }}
  .th-strat {{ width: 80px; flex-shrink: 0; }}
  .th-exp  {{ color: {C_DIM}; width: 100px; flex-shrink: 0; }}
  .th-strikes {{ color: {C_TEXT}; flex: 1; }}
  .th-pnl  {{ width: 100px; flex-shrink: 0; text-align: right; font-weight: 600; }}
  .th-res  {{ width: 60px; flex-shrink: 0; text-align: right; font-weight: 600; }}
  .pnl-win  {{ color: {C_GREEN}; }}
  .pnl-loss {{ color: {C_RED}; }}
  .pnl-zero {{ color: {C_DIM}; }}

  /* ── Risk bar ── */
  .risk-bar-bg {{
    background: {C_BORDER};
    border-radius: 3px;
    height: 5px;
    margin-top: 6px;
    overflow: hidden;
  }}
  .risk-bar-fill {{
    height: 100%;
    border-radius: 3px;
    transition: width 0.6s cubic-bezier(0.4,0,0.2,1);
  }}

  /* ── Config row ── */
  .cfg-item {{
    background: {C_SURFACE};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 10px 14px;
    text-align: center;
  }}
  .cfg-label {{
    font-family: 'DM Sans', sans-serif;
    font-size: 9px;
    color: {C_DIM};
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 600;
  }}
  .cfg-val {{
    font-size: 13px;
    color: {C_TEXT};
    font-family: 'JetBrains Mono', monospace;
    margin-top: 3px;
    font-weight: 500;
  }}

  /* ── Empty state ── */
  .empty-state {{
    color: {C_MUTED};
    text-align: center;
    padding: 40px 0;
    font-size: 13px;
    font-family: 'DM Sans', sans-serif;
    font-style: italic;
  }}

  /* ── Stat mini-card ── */
  .stat-mini {{
    text-align: center;
    padding: 6px 0;
  }}
  .stat-mini .mlabel {{ margin-bottom: 4px; }}
  .stat-mini .stat-val {{
    font-size: 15px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
  }}
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
        fillcolor=f"rgba(78,201,176,0.10)",
        line=dict(color=C_GREEN, width=1.5), name="Profit",
        hovertemplate="$%{x:.0f}: +$%{y:.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=prices, y=neg_y, fill="tozeroy",
        fillcolor=f"rgba(224,108,117,0.10)",
        line=dict(color=C_RED, width=1.5), name="Loss",
        hovertemplate="$%{x:.0f}: -$%{y:.0f}<extra></extra>",
    ))

    for strike, label, color in [
        (sh, f"H {sh:.0f}", C_CYAN),
        (sm, f"M {sm:.0f}", C_BLUE),
        (sl, f"L {sl:.0f}", C_PURPLE),
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
        template="plotly_dark", paper_bgcolor="#090b10", plot_bgcolor="#090b10",
        margin=dict(l=32, r=8, t=8, b=28), height=160, showlegend=False,
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C_DIM, family="JetBrains Mono"), tickformat=".0f"),
        yaxis=dict(showgrid=True, gridcolor=C_BORDER, tickfont=dict(size=9, color=C_DIM, family="JetBrains Mono"), tickformat="$.0f", zeroline=False),
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
        fillcolor="rgba(78,201,176,0.10)",
        line=dict(color=C_GREEN, width=1.5), name="Profit",
    ))
    fig.add_trace(go.Scatter(
        x=prices, y=neg_y, fill="tozeroy",
        fillcolor="rgba(224,108,117,0.10)",
        line=dict(color=C_RED, width=1.5), name="Loss",
    ))

    for strike, label, color in [
        (lp, f"{lp:.0f}", C_PURPLE),
        (sp, f"{sp:.0f}", C_BLUE),
        (sc, f"{sc:.0f}", C_BLUE),
        (lc, f"{lc:.0f}", C_PURPLE),
    ]:
        fig.add_vline(x=strike, line=dict(color=color, width=1, dash="dot"),
                      annotation_text=label, annotation_font_size=9, annotation_font_color=color)

    if spx_price and lo < spx_price < hi:
        fig.add_vline(x=spx_price, line=dict(color=C_AMBER, width=1.5, dash="dash"),
                      annotation_text=f"SPX {spx_price:.0f}", annotation_font_size=9,
                      annotation_font_color=C_AMBER)

    fig.add_hline(y=0, line=dict(color=C_BORDER_L, width=1))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#090b10", plot_bgcolor="#090b10",
        margin=dict(l=32, r=8, t=8, b=28), height=160, showlegend=False,
        xaxis=dict(showgrid=False, tickfont=dict(size=9, color=C_DIM, family="JetBrains Mono"), tickformat=".0f"),
        yaxis=dict(showgrid=True, gridcolor=C_BORDER, tickfont=dict(size=9, color=C_DIM, family="JetBrains Mono"),
                   tickformat="$.0f", zeroline=False),
    )
    return fig


# ─── P&L cumulative chart ─────────────────────────────────────────────────────

def pnl_chart(trade_history: list) -> go.Figure:
    if not trade_history:
        fig = go.Figure()
        fig.add_annotation(text="Awaiting first trade", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False,
                           font=dict(color=C_MUTED, size=13, family="DM Sans"))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#090b10",
                          plot_bgcolor="#090b10", height=280,
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
    fill  = "rgba(78,201,176,0.06)" if final >= 0 else "rgba(224,108,117,0.06)"

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
        paper_bgcolor="#090b10", plot_bgcolor="#090b10",
        height=280,
        margin=dict(l=48, r=16, t=16, b=48),
        showlegend=False,
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color=C_DIM, family="JetBrains Mono"), tickangle=-30),
        yaxis=dict(showgrid=True, gridcolor=C_BORDER, tickfont=dict(size=10, color=C_DIM, family="JetBrains Mono"), tickprefix="$", zeroline=False),
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
                  <span style="color:{C_BLUE};font-size:11px;margin-left:8px;font-family:'DM Sans',sans-serif;">{exp_fmt}</span>
                  <span style="color:{C_DIM};font-size:10px;margin-left:6px;font-family:'JetBrains Mono',monospace;">({dte_days}d)</span>
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
                <span style="color:{C_GREEN};font-size:11px;font-family:'JetBrains Mono',monospace;">${max_profit:.2f}</span>
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
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── CENTER: P&L Chart ─────────────────────────────────────────────────────────
with col_center:
    st.markdown('<div class="sec-hdr">Cumulative P&amp;L</div>', unsafe_allow_html=True)

    fig_pnl = pnl_chart(trade_history)
    st.plotly_chart(fig_pnl, use_container_width=True, config={"displayModeBar": False})

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
              <div class="stat-val" style="color:{'#4ec9b0' if total_pnl>=0 else '#e06c75'}">{fmt_money_signed(total_pnl)}</div>
            </div>
            """, unsafe_allow_html=True)
        with sb:
            st.markdown(f"""
            <div class="stat-mini">
              <div class="mlabel">Avg / Trade</div>
              <div class="stat-val" style="color:{'#4ec9b0' if avg_pnl>=0 else '#e06c75'}">{fmt_money_signed(avg_pnl)}</div>
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
                color_style = f"color:{'#4ec9b0' if (val or 0)>=0 else '#e06c75'}"
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
    table_html = f'<div style="background:{C_SURFACE};border:1px solid {C_BORDER};border-radius:10px;padding:10px 14px;">'
    table_html += f'<div class="th-row" style="color:{C_DIM};font-size:10px;text-transform:uppercase;letter-spacing:1.5px;border-bottom:1px solid {C_BORDER_L};font-family:\'DM Sans\',sans-serif;font-weight:600;"><span class="th-time">Time</span><span class="th-strat">Strategy</span><span class="th-exp">Expiry</span><span class="th-strikes">Strikes</span><span class="th-pnl">P&amp;L</span><span class="th-res">Result</span></div>'

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

    table_html += '</div>'
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


# ─── FOOTER ───────────────────────────────────────────────────────────────────

st.markdown(f"""
<div style="text-align:center;color:{C_MUTED};font-size:9px;padding:24px 0 8px;letter-spacing:2px;font-family:'DM Sans',sans-serif;font-weight:500;">
  OPTIONS AGENT &middot; IBKR GATEWAY &middot; AUTO-REFRESH 30s
</div>
""", unsafe_allow_html=True)


# ─── AUTO-REFRESH (30 seconds) ────────────────────────────────────────────────

time.sleep(30)
st.rerun()
