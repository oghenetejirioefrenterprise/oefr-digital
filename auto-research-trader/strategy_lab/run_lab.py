#!/usr/bin/env python3
"""
Strategy Lab Runner — Tests all current strategies and shows leaderboard
"""
import sys, sqlite3, json
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'sonnet_4h'))

from backtest_engine import run_full_eval, DB_PATH
from structure_entries_15m import generate_all_signals, Signal

# ─── Strategy Variants to Test ────────────────────────────────────────────────

def make_signal_fn(use_regime=True, use_session=True, min_confluence=5):
    def fn(data):
        return generate_all_signals(data, use_regime=use_regime,
                                    use_session=use_session,
                                    min_confluence=min_confluence)
    return fn

def sweep_only(data):
    from structure_entries_15m import detect_sweep_signals, compute_atr
    atr = compute_atr(data['high'], data['low'], data['close'])
    return detect_sweep_signals(data, atr)

def fvg_only(data):
    from structure_entries_15m import detect_fvg_signals, compute_atr
    atr = compute_atr(data['high'], data['low'], data['close'])
    return detect_fvg_signals(data, atr)

def ob_only(data):
    from structure_entries_15m import detect_ob_signals, compute_atr
    atr = compute_atr(data['high'], data['low'], data['close'])
    return detect_ob_signals(data, atr)

def bos_only(data):
    from structure_entries_15m import detect_bos_choch_signals, compute_atr
    atr = compute_atr(data['high'], data['low'], data['close'])
    return detect_bos_choch_signals(data, atr)

def sweep_plus_session(data):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / 'sonnet_4h'))
    from structure_entries_15m import detect_sweep_signals, compute_atr
    from backtest_15m_enhanced import classify_session, classify_regime, compute_adx, compute_efficiency_ratio, compute_atr_percentile
    
    h, l, c = data['high'], data['low'], data['close']
    atr = compute_atr(h, l, c)
    sigs = detect_sweep_signals(data, atr)
    adx_v, _, _ = compute_adx(h, l, c, 14)
    er = compute_efficiency_ratio(c, 10)
    atr_pct = compute_atr_percentile(atr, 100)
    ts = data['timestamp']
    
    filtered = []
    for s in sigs:
        i = s.bar
        if classify_session(int(ts[i])) not in ('us','overlap','europe'):
            continue
        if classify_regime(adx_v, er, atr_pct, i) != 'trend':
            continue
        filtered.append(s)
    return filtered

STRATEGIES = [
    ('all_struct_v1', 'All Patterns (Regime+Session, conf≥5)', make_signal_fn(True, True, 5)),
    ('all_struct_v2', 'All Patterns (Session only, conf≥5)', make_signal_fn(False, True, 5)),
    ('all_struct_v3', 'All Patterns (Regime only, conf≥5)', make_signal_fn(True, False, 5)),
    ('all_struct_v4', 'All Patterns (No filter, conf≥6)', make_signal_fn(False, False, 6)),
    ('all_struct_v5', 'All Patterns (Regime+Session, conf≥6)', make_signal_fn(True, True, 6)),
    ('sweep_session', 'Sweep+Reversal (Regime+Session)', sweep_plus_session),
    ('fvg_raw', 'FVG Fill (no filter)', fvg_only),
    ('ob_raw', 'Order Block (no filter)', ob_only),
    ('bos_raw', 'BOS/CHoCH (no filter)', bos_only),
    ('sweep_raw', 'Sweep+Reversal (no filter)', sweep_only),
]

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--quick', action='store_true', help='Only test top variants')
    a = p.parse_args()
    
    strategies = STRATEGIES[:5] if a.quick else STRATEGIES
    
    results_summary = []
    for sid, name, fn in strategies:
        try:
            bt, fw, is_winner = run_full_eval(sid, name, fn, save=True)
            results_summary.append({
                'id': sid, 'name': name,
                'bt_wr': bt['win_rate'], 'fw_wr': fw['win_rate'],
                'bt_monthly': bt['monthly_return'], 'fw_monthly': fw['monthly_return'],
                'bt_pf': bt['profit_factor'], 'fw_pf': fw['profit_factor'],
                'fw_dd': fw['max_drawdown'],
                'winner': is_winner
            })
        except Exception as e:
            print(f"\n  ERROR on {name}: {e}")
    
    # Leaderboard
    print(f"\n\n{'='*90}")
    print("  STRATEGY LEADERBOARD (sorted by forward WR)")
    print(f"{'='*90}")
    results_summary.sort(key=lambda x: -x['fw_wr'])
    
    print(f"  {'Strategy':<42} {'BT WR':>6} {'FW WR':>6} {'FW Mo%':>7} {'FW PF':>6} {'FW DD':>7} {'WIN':>4}")
    print(f"  {'-'*42} {'-'*6} {'-'*6} {'-'*7} {'-'*6} {'-'*7} {'-'*4}")
    for r in results_summary:
        win_marker = '🏆' if r['winner'] else ''
        print(f"  {r['name'][:42]:<42} {r['bt_wr']:>5.1f}% {r['fw_wr']:>5.1f}% {r['fw_monthly']:>+6.1f}% {r['fw_pf']:>6.3f} {r['fw_dd']:>6.1f}% {win_marker:>4}")
    
    winners = [r for r in results_summary if r['winner']]
    if winners:
        print(f"\n  🏆 {len(winners)} WINNER(S) FOUND!")
    else:
        best = results_summary[0]
        print(f"\n  Best so far: {best['name']}")
        print(f"  Forward WR: {best['fw_wr']:.1f}% | Monthly: {best['fw_monthly']:+.1f}%")
        print(f"  Gap to target: WR +{max(0, 80-best['fw_wr']):.1f}%, Monthly +{max(0, 10-best['fw_monthly']):.1f}%")
    
    print(f"\n  Results saved to: {DB_PATH}")
