#!/usr/bin/env python3
"""
Strategy Research Cron — Runs every 6h
1. Researches new quant strategies via web
2. Implements variations of best current strategies
3. Backtests all new variants
4. Reports best results to Telegram
5. Updates MISSION_CONTROL with progress

Target: WR > 80%, Monthly Return > 10%
"""
import sys, sqlite3, json, subprocess, os
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'sonnet_4h'))

from backtest_engine import run_full_eval, DB_PATH, load_split, compute_atr
from structure_entries_15m import (
    generate_all_signals, Signal, compute_ema,
    detect_fvg_signals, detect_sweep_signals, detect_ob_signals, detect_bos_choch_signals
)

TELEGRAM_CHAT = "1366707521"

def send_telegram(msg):
    try:
        subprocess.run(['openclaw', 'message', 'send', '--channel', 'telegram',
                       '--to', TELEGRAM_CHAT, '--message', msg],
                      capture_output=True, timeout=10)
    except:
        pass

def get_best_results():
    """Get current best from DB."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT s.name, f.win_rate, f.monthly_return, f.profit_factor, f.max_drawdown
                 FROM forward_test_results f
                 JOIN strategies s ON s.id = f.strategy_id
                 ORDER BY f.win_rate DESC LIMIT 10''')
    rows = c.fetchall()
    conn.close()
    return rows

def tight_fvg_signals(data, min_rr=3.0, require_volume=True, require_body_size=True):
    """FVG signals with extra filters for higher precision."""
    from structure_entries_15m import compute_atr
    h, l, c, o, v = data['high'], data['low'], data['close'], data['open'], data['volume']
    atr = compute_atr(h, l, c)
    n = len(c)

    avg_vol = [0]*n
    for i in range(20, n):
        avg_vol[i] = sum(v[i-20:i])/20

    raw = detect_fvg_signals(data, atr)
    filtered = []
    for sig in raw:
        i = sig.bar
        if i >= n: continue
        if require_volume and avg_vol[i] > 0 and v[i] < avg_vol[i] * 0.8:
            continue  # Skip low volume
        body = abs(c[i] - o[i])
        if require_body_size and body < atr[i] * 0.3:
            continue  # Skip tiny body candles
        risk = abs(sig.entry - sig.sl)
        if risk > 0 and abs(sig.tp - sig.entry)/risk < min_rr:
            # Extend TP to meet min R:R
            is_long = sig.direction == 'LONG'
            sig.tp = sig.entry + risk*min_rr if is_long else sig.entry - risk*min_rr
            sig.risk_r = min_rr
        filtered.append(sig)
    return filtered

def sweep_with_confirmation(data):
    """Sweep + reversal with additional momentum confirmation."""
    from structure_entries_15m import compute_atr
    h, l, c, o = data['high'], data['low'], data['close'], data['open']
    atr = compute_atr(h, l, c)
    raw = detect_sweep_signals(data, atr)
    
    ema21 = compute_ema(c, 21)
    ema50 = compute_ema(c, 50)
    
    filtered = []
    for sig in raw:
        i = sig.bar
        if i < 50: continue
        is_long = sig.direction == 'LONG'
        # Require EMA trend alignment
        if is_long and not (ema21[i] > ema50[i]):
            continue
        if not is_long and not (ema21[i] < ema50[i]):
            continue
        # Require candle close in signal direction
        if is_long and c[i] <= o[i]:
            continue
        if not is_long and c[i] >= o[i]:
            continue
        filtered.append(sig)
    return filtered

def ob_with_fvg_combo(data):
    """Order Block + nearby FVG confluence."""
    from structure_entries_15m import compute_atr
    h, l, c = data['high'], data['low'], data['close']
    atr = compute_atr(h, l, c)
    
    obs = detect_ob_signals(data, atr)
    fvgs = detect_fvg_signals(data, atr)
    fvg_bars = {s.bar: s for s in fvgs}
    
    combo = []
    for ob in obs:
        # Look for FVG within 5 bars
        for offset in range(-5, 6):
            fb = ob.bar + offset
            if fb in fvg_bars and fvg_bars[fb].direction == ob.direction:
                ob.confluence = min(10, ob.confluence + 2)
                combo.append(ob)
                break
        else:
            if ob.confluence >= 7:
                combo.append(ob)  # High confluence OB alone
    return combo

def multi_timeframe_sweep(data):
    """Sweep signals that also align with 30m trend."""
    from structure_entries_15m import compute_atr, detect_sweep_signals
    from backtest_15m_enhanced import downsample_to_htf, compute_ema as ema30
    import numpy as np

    h, l, c = data['high'], data['low'], data['close']
    atr = compute_atr(h, l, c)
    raw = detect_sweep_signals(data, atr)

    # Derive 30m (2 bars per 30m on 15m data)
    data_30m = downsample_to_htf(data, 2)
    ema30_fast = compute_ema(data_30m['close'], 8)
    ema30_slow = compute_ema(data_30m['close'], 21)

    filtered = []
    for sig in raw:
        i = sig.bar
        idx_30m = i // 2
        if idx_30m >= len(ema30_fast): continue
        fast = ema30_fast[idx_30m]; slow = ema30_slow[idx_30m]
        if fast == 0 or slow == 0: continue
        is_long = sig.direction == 'LONG'
        if is_long and fast <= slow: continue
        if not is_long and fast >= slow: continue
        filtered.append(sig)
    return filtered

def fvg_with_session_regime(data):
    """FVG + tight session + regime."""
    from backtest_15m_enhanced import classify_session, classify_regime, compute_adx, compute_efficiency_ratio, compute_atr_percentile
    from structure_entries_15m import compute_atr
    import numpy as np

    h, l, c = data['high'], data['low'], data['close']
    atr = compute_atr(h, l, c)
    raw = detect_fvg_signals(data, atr)
    atr_pct = compute_atr_percentile(atr, 100)
    adx_v, _, _ = compute_adx(h, l, c, 14)
    er = compute_efficiency_ratio(c, 10)
    ts = data['timestamp']

    filtered = []
    for sig in raw:
        i = sig.bar
        session = classify_session(int(ts[i]))
        if session not in ('us', 'overlap'):  # Only strongest sessions
            continue
        regime = classify_regime(adx_v, er, atr_pct, i)
        if regime != 'trend':
            continue
        filtered.append(sig)
    return filtered


# New strategies to test this run
NEW_STRATEGIES = [
    ('tight_fvg_v1', 'FVG Tight (vol+body filter, 3R min)', tight_fvg_signals),
    ('sweep_confirm_v1', 'Sweep+EMA Confirmation', sweep_with_confirmation),
    ('ob_fvg_combo_v1', 'OB+FVG Confluence', ob_with_fvg_combo),
    ('mtf_sweep_v1', 'Multi-TF Sweep (15m+30m)', multi_timeframe_sweep),
    ('fvg_us_session_v1', 'FVG US/Overlap Session+Regime', fvg_with_session_regime),
]

def main():
    print(f"\n{'='*72}")
    print(f"  STRATEGY RESEARCH CRON — {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Target: WR≥80%, Monthly≥10%")
    print(f"{'='*72}")

    # Get current best
    best = get_best_results()
    if best:
        print(f"\n  Current best (by forward WR):")
        for row in best[:3]:
            wr = row[1] or 0; mo = row[2] or 0; pf = row[3] or 0
        print(f"    {row[0][:40]}: WR={wr:.1f}% Monthly={mo:+.1f}% PF={pf:.3f}")

    # Run new strategies
    results = []
    for sid, name, fn in NEW_STRATEGIES:
        print(f"\n  Testing: {name}")
        try:
            bt, fw, is_winner = run_full_eval(sid, name, fn, save=True)
            results.append((name, bt, fw, is_winner))
            if is_winner:
                msg = f"🏆 WINNER FOUND!\n{name}\nWR: {fw['win_rate']:.1f}% | Monthly: {fw['monthly_return']:+.1f}% | PF: {fw['profit_factor']:.3f}"
                send_telegram(msg)
        except Exception as e:
            print(f"    ERROR: {e}")

    # Report
    results.sort(key=lambda x: -x[2]['win_rate'])
    best_fw = results[0] if results else None

    # Log to DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO research_log (run_date,sources_checked,strategies_found,strategies_implemented,best_result,notes)
                 VALUES (?,?,?,?,?,?)''',
              (datetime.now(tz=timezone.utc).isoformat(),
               'structure_variants', len(NEW_STRATEGIES), len(results),
               f"{best_fw[0]}: WR={best_fw[2]['win_rate']:.1f}%" if best_fw else 'none',
               json.dumps({r[0]: {'fw_wr': r[2]['win_rate'], 'fw_monthly': r[2]['monthly_return']} for r in results})))
    conn.commit(); conn.close()

    # Summary
    print(f"\n{'─'*72}")
    print(f"  RESULTS THIS RUN")
    print(f"{'─'*72}")
    print(f"  {'Strategy':<42} {'FW WR':>6} {'FW Mo%':>7} {'FW PF':>6}")
    for name, bt, fw, win in results:
        marker = ' 🏆' if win else ''
        print(f"  {name[:42]:<42} {fw['win_rate']:>5.1f}% {fw['monthly_return']:>+6.1f}% {fw['profit_factor']:>6.3f}{marker}")

    if best_fw:
        msg = (f"📊 Strategy Lab Update\n"
               f"Tested {len(results)} variants\n"
               f"Best FW WR: {best_fw[2]['win_rate']:.1f}% ({best_fw[0][:30]})\n"
               f"Target: 80% WR, 10%/mo\n"
               f"Gap: WR {max(0,80-best_fw[2]['win_rate']):.1f}%, Mo {max(0,10-best_fw[2]['monthly_return']):.1f}%")
        send_telegram(msg)

if __name__ == '__main__':
    main()
