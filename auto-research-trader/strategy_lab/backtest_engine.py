#!/usr/bin/env python3
"""
Strategy Lab Backtest Engine
Runs backtest + forward test for any strategy, stores results in SQLite
Target: WR > 80%, Return > 10%/month
"""
import sys, csv, json, sqlite3, hashlib, numpy as np
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import asdict

sys.path.insert(0, str(Path(__file__).parent.parent / 'sonnet_4h'))
sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent.parent / 'sonnet_4h/data_binance_split'
DB_PATH = Path(__file__).parent / 'strategies.db'

CAPITAL = 1000.0
RISK_PCT = 0.01
FEE_RATE = 0.0006
BARS_PER_DAY = 96  # 15m
MAX_HOLD_DAYS = 5

def load_split(coin, split, tf='15m'):
    path = DATA_DIR / f"{tf}_{coin}_{split}.csv"
    ts,o,h,l,c,v=[],[],[],[],[],[]
    with open(path) as f:
        for row in csv.DictReader(f):
            ts.append(int(row['timestamp'])); o.append(float(row['open']))
            h.append(float(row['high'])); l.append(float(row['low']))
            c.append(float(row['close'])); v.append(float(row['volume']))
    return {'timestamp':np.array(ts),'open':np.array(o),'high':np.array(h),
            'low':np.array(l),'close':np.array(c),'volume':np.array(v)}

def compute_atr(data, period=14):
    h,l,c = data['high'],data['low'],data['close']
    tr = np.maximum(h[1:]-l[1:], np.maximum(np.abs(h[1:]-c[:-1]), np.abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, h[0]-l[0])
    atr = np.zeros(len(tr)); atr[:period] = np.mean(tr[:period])
    for i in range(period, len(tr)): atr[i] = (atr[i-1]*(period-1)+tr[i])/period
    return atr

def simulate_trade(data, atr, sig):
    bar = sig.bar; entry = sig.entry; sl = sig.sl
    tp = sig.tp; direction = sig.direction
    trail_mult = sig.trail_atr_mult; tight_mult = sig.trail_tight_mult
    tighten_r = sig.tighten_at_r

    risk_dist = abs(entry - sl)
    if risk_dist == 0: return 0.0, 'skip'
    pos = (CAPITAL * RISK_PCT) / risk_dist
    efee = pos * entry * FEE_RATE
    is_long = direction == 'LONG'
    current_sl = sl; best_price = entry
    max_bar = min(bar + BARS_PER_DAY * MAX_HOLD_DAYS, len(data['high']))
    exit_price = None; exit_reason = 'timeout'

    for j in range(bar + 1, max_bar):
        hi = data['high'][j]; lo_p = data['low'][j]
        cur_atr = atr[j] if j < len(atr) else atr[-1]
        if is_long:
            if lo_p <= current_sl: exit_price = current_sl; exit_reason = 'sl'; break
            if hi >= tp: exit_price = tp; exit_reason = 'tp'; break
            if hi > best_price:
                best_price = hi
                r_now = (best_price - entry) / risk_dist
                mult = tight_mult if r_now >= tighten_r else trail_mult
                new_sl = best_price - cur_atr * mult
                if new_sl > current_sl: current_sl = new_sl
        else:
            if hi >= current_sl: exit_price = current_sl; exit_reason = 'sl'; break
            if lo_p <= tp: exit_price = tp; exit_reason = 'tp'; break
            if lo_p < best_price:
                best_price = lo_p
                r_now = (entry - best_price) / risk_dist
                mult = tight_mult if r_now >= tighten_r else trail_mult
                new_sl = best_price + cur_atr * mult
                if new_sl < current_sl: current_sl = new_sl

    if exit_price is None:
        exit_price = data['close'][min(max_bar-1, len(data['close'])-1)]
    if is_long:
        pnl = pos * (exit_price - entry) - efee - pos * exit_price * FEE_RATE
    else:
        pnl = pos * (entry - exit_price) - efee - pos * exit_price * FEE_RATE
    return pnl, exit_reason

def run_backtest(signal_fn, split, tf='15m', coins=['BTC','ETH','SOL']):
    """Run backtest for a signal function on given split."""
    all_pnls = []; coin_results = []
    pattern_stats = {}

    for coin in coins:
        data = load_split(coin, split, tf)
        atr = compute_atr(data)
        signals = signal_fn(data)

        pnls = []; wins = 0; losses = 0
        for sig in signals:
            pnl, reason = simulate_trade(data, atr, sig)
            pnls.append(pnl); all_pnls.append(pnl)
            if pnl > 0: wins += 1
            else: losses += 1
            # Track by pattern
            p = sig.pattern
            if p not in pattern_stats:
                pattern_stats[p] = {'wins':0,'losses':0,'pnl':0.0}
            if pnl > 0: pattern_stats[p]['wins'] += 1
            else: pattern_stats[p]['losses'] += 1
            pattern_stats[p]['pnl'] += pnl

        coin_results.append({'coin':coin,'trades':wins+losses,'wins':wins,'pnl':sum(pnls)})

    # Aggregate
    tt = sum(r['trades'] for r in coin_results)
    tw = sum(r['wins'] for r in coin_results)
    tpnl = sum(all_pnls)
    gp = sum(p for p in all_pnls if p > 0)
    gl = abs(sum(p for p in all_pnls if p <= 0)) or 1

    eq = [CAPITAL]
    for p in all_pnls: eq.append(eq[-1]+p)
    peak=eq[0]; mdd=0
    for e in eq:
        if e>peak: peak=e
        dd=(peak-e)/peak if peak>0 else 0
        if dd>mdd: mdd=dd

    # Monthly return estimate (backtest = ~18 months, forward = ~5 months)
    days = 584 if split == 'backtest' else 146
    months = days / 30
    monthly_return = ((eq[-1] / CAPITAL) ** (1/months) - 1) * 100 if months > 0 else 0

    return {
        'trades': tt, 'wins': tw, 'losses': tt-tw,
        'win_rate': tw/tt*100 if tt else 0,
        'return_pct': tpnl/CAPITAL*100,
        'profit_factor': gp/gl,
        'max_drawdown': mdd*100,
        'final_equity': eq[-1],
        'monthly_return': monthly_return,
        'coins': coin_results,
        'pattern_stats': pattern_stats,
    }

def save_results(strategy_id, split, results, is_forward=False):
    """Save backtest/forward results to database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now(tz=timezone.utc).isoformat()

    if is_forward:
        is_winner = 1 if (results['win_rate'] >= 80 and results['monthly_return'] >= 10) else 0
        c.execute('''INSERT INTO forward_test_results
            (strategy_id,run_date,trades,wins,win_rate,return_pct,profit_factor,
             max_drawdown,monthly_return,is_winner,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (strategy_id, now, results['trades'], results['wins'],
             results['win_rate'], results['return_pct'], results['profit_factor'],
             results['max_drawdown'], results['monthly_return'], is_winner,
             json.dumps(results.get('pattern_stats',{}))))
    else:
        c.execute('''INSERT INTO backtest_results
            (strategy_id,split,run_date,trades,wins,losses,win_rate,return_pct,
             profit_factor,max_drawdown,final_equity,monthly_return,coins,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (strategy_id, split, now, results['trades'], results['wins'],
             results['losses'], results['win_rate'], results['return_pct'],
             results['profit_factor'], results['max_drawdown'], results['final_equity'],
             results['monthly_return'], json.dumps([r['coin'] for r in results['coins']]),
             json.dumps(results.get('pattern_stats',{}))))

    conn.commit(); conn.close()

def print_results(results, label):
    print(f"\n  {label}")
    print(f"    Trades:        {results['trades']} ({results['wins']}W / {results['losses']}L)")
    print(f"    Win Rate:      {results['win_rate']:.1f}%  {'✅' if results['win_rate']>=50 else '❌'}")
    print(f"    Return:        {results['return_pct']:+.2f}%")
    print(f"    Monthly Est:   {results['monthly_return']:+.2f}%  {'✅' if results['monthly_return']>=10 else '❌'}")
    print(f"    Profit Factor: {results['profit_factor']:.3f}  {'✅' if results['profit_factor']>=1.5 else '❌'}")
    print(f"    Max Drawdown:  {results['max_drawdown']:.1f}%")
    print(f"    Final Equity:  ${results['final_equity']:.2f}")
    if results.get('pattern_stats'):
        print(f"    Pattern breakdown:")
        for p, stats in sorted(results['pattern_stats'].items(), key=lambda x: -x[1]['pnl']):
            total = stats['wins']+stats['losses']
            wr = stats['wins']/total*100 if total else 0
            print(f"      {p:<20} {total:>4} trades  WR:{wr:.0f}%  PnL:${stats['pnl']:.2f}")

def run_full_eval(strategy_id, strategy_name, signal_fn, save=True):
    """Full evaluation: backtest + forward test + save to DB."""
    print(f"\n{'='*72}")
    print(f"  {strategy_name}")
    print(f"  Target: WR≥80%, Monthly≥10%")
    print(f"{'='*72}")

    bt = run_backtest(signal_fn, 'backtest')
    fw = run_backtest(signal_fn, 'forward')

    print(f"\n  📊 BACKTEST (Mar2024-Oct2025, ~18 months)")
    print_results(bt, "Results")
    print(f"\n  🔮 FORWARD (Oct2025-Mar2026, ~5 months)")
    print_results(fw, "Results")

    is_winner = fw['win_rate'] >= 80 and fw['monthly_return'] >= 10
    print(f"\n  {'🏆 WINNER — Targets met!' if is_winner else '❌ Not yet — keep iterating'}")

    if save:
        # Register strategy if not exists
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO strategies (id,name,description,timeframe,category,source,created_at,status) VALUES (?,?,?,?,?,?,?,?)',
                  (strategy_id, strategy_name, '', '15m', 'structure', 'lab',
                   datetime.now(tz=timezone.utc).isoformat(), 'tested'))
        conn.commit(); conn.close()
        save_results(strategy_id, 'backtest', bt, is_forward=False)
        save_results(strategy_id, 'forward', fw, is_forward=True)
        print(f"  💾 Results saved to database")

    return bt, fw, is_winner
