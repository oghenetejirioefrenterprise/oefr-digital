#!/usr/bin/env python3
"""
15m Smart Entry Library — Proper SMC/ICT structure detection
Entries: FVG fill, BOS/CHoCH, OB retest, Liquidity sweep+reversal
"""
import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class Signal:
    bar: int
    direction: str       # 'LONG' or 'SHORT'
    entry: float
    sl: float
    tp: float
    pattern: str         # entry type
    confluence: int      # 0-10
    risk_r: float        # target R:R
    max_tp_r: float = 4.0
    trail_atr_mult: float = 3.5
    trail_tight_mult: float = 2.5
    tighten_at_r: float = 1.5

def compute_atr(h, l, c, period=14):
    tr = np.maximum(h[1:]-l[1:], np.maximum(np.abs(h[1:]-c[:-1]), np.abs(l[1:]-c[:-1])))
    tr = np.insert(tr, 0, h[0]-l[0])
    atr = np.zeros(len(tr)); atr[:period] = np.mean(tr[:period])
    for i in range(period, len(tr)): atr[i] = (atr[i-1]*(period-1)+tr[i])/period
    return atr

def compute_ema(arr, period):
    ema = np.zeros(len(arr)); ema[period-1] = np.mean(arr[:period])
    k = 2.0/(period+1)
    for i in range(period, len(arr)): ema[i] = arr[i]*k + ema[i-1]*(1-k)
    return ema

def find_swing_highs_lows(h, l, lookback=5):
    """Find significant swing highs and lows."""
    swing_highs = []  # (bar_idx, price)
    swing_lows = []
    n = len(h)
    for i in range(lookback, n - lookback):
        if all(h[i] >= h[i-j] for j in range(1, lookback+1)) and \
           all(h[i] >= h[i+j] for j in range(1, lookback+1)):
            swing_highs.append((i, h[i]))
        if all(l[i] <= l[i-j] for j in range(1, lookback+1)) and \
           all(l[i] <= l[i+j] for j in range(1, lookback+1)):
            swing_lows.append((i, l[i]))
    return swing_highs, swing_lows

# ─── Pattern 1: Fair Value Gap (FVG) Fill ─────────────────────────────────────
def detect_fvg_signals(data, atr, min_bars_ago=2, max_bars_ago=30):
    """
    FVG: gap between candle[i-2].high and candle[i].low (bullish)
         gap between candle[i-2].low and candle[i].high (bearish)
    Entry: when price returns to fill the gap
    """
    h, l, c, o = data['high'], data['low'], data['close'], data['open']
    n = len(c)
    signals = []
    
    # Store active FVGs: (type, bar_created, high, low, mid)
    active_fvgs = []
    
    for i in range(3, n):
        cur_atr = atr[i]
        if cur_atr == 0: continue
        
        # Create new FVGs
        # Bullish FVG: candle[i].low > candle[i-2].high
        if l[i] > h[i-2] and (l[i] - h[i-2]) > cur_atr * 0.3:
            fvg_low = h[i-2]
            fvg_high = l[i]
            active_fvgs.append(('bull', i, fvg_high, fvg_low))
        
        # Bearish FVG: candle[i].high < candle[i-2].low
        if h[i] < l[i-2] and (l[i-2] - h[i]) > cur_atr * 0.3:
            fvg_high = l[i-2]
            fvg_low = h[i]
            active_fvgs.append(('bear', i, fvg_high, fvg_low))
        
        # Check if current bar enters any FVG
        for fvg in active_fvgs[:]:
            ftype, fcreated, fhigh, flow = fvg
            age = i - fcreated
            if age < min_bars_ago or age > max_bars_ago:
                if age > max_bars_ago:
                    active_fvgs.remove(fvg)
                continue
            
            fmid = (fhigh + flow) / 2
            
            # Bullish FVG: price dips into the gap, then closes above mid
            if ftype == 'bull' and l[i] <= fhigh and c[i] > fmid:
                entry = c[i]
                sl = flow - cur_atr * 0.5
                risk = entry - sl
                if risk > 0 and risk < cur_atr * 3:
                    signals.append(Signal(
                        bar=i, direction='LONG', entry=entry,
                        sl=sl, tp=entry + risk * 3.5,
                        pattern='FVG_FILL_BULL', confluence=5,
                        risk_r=3.5, max_tp_r=4.0
                    ))
                active_fvgs.remove(fvg)
            
            # Bearish FVG: price rallies into gap, then closes below mid
            elif ftype == 'bear' and h[i] >= flow and c[i] < fmid:
                entry = c[i]
                sl = fhigh + cur_atr * 0.5
                risk = sl - entry
                if risk > 0 and risk < cur_atr * 3:
                    signals.append(Signal(
                        bar=i, direction='SHORT', entry=entry,
                        sl=sl, tp=entry - risk * 3.5,
                        pattern='FVG_FILL_BEAR', confluence=5,
                        risk_r=3.5, max_tp_r=4.0
                    ))
                active_fvgs.remove(fvg)
    
    return signals

# ─── Pattern 2: BOS/CHoCH (Break of Structure) ────────────────────────────────
def detect_bos_choch_signals(data, atr, lookback=5):
    """
    BOS: Break above previous swing high (bullish) or below swing low (bearish)
    CHoCH: Change of Character — trend reversal confirmation
    Entry: on retest of broken level
    """
    h, l, c = data['high'], data['low'], data['close']
    n = len(c)
    signals = []
    
    swing_highs, swing_lows = find_swing_highs_lows(h, l, lookback)
    
    # Track recent swings
    recent_highs = []  # (bar, price)
    recent_lows = []
    
    sh_idx = 0; sl_idx = 0
    
    for i in range(lookback*2, n):
        cur_atr = atr[i]
        if cur_atr == 0: continue
        
        # Update recent swings
        while sh_idx < len(swing_highs) and swing_highs[sh_idx][0] <= i:
            recent_highs.append(swing_highs[sh_idx])
            sh_idx += 1
        while sl_idx < len(swing_lows) and swing_lows[sl_idx][0] <= i:
            recent_lows.append(swing_lows[sl_idx])
            sl_idx += 1
        
        # Keep only last 10 swings
        recent_highs = recent_highs[-10:]
        recent_lows = recent_lows[-10:]
        
        if len(recent_highs) < 2 or len(recent_lows) < 2:
            continue
        
        prev_high_bar, prev_high_price = recent_highs[-2]
        prev_low_bar, prev_low_price = recent_lows[-2]
        last_high_bar, last_high_price = recent_highs[-1]
        last_low_bar, last_low_price = recent_lows[-1]
        
        # Bullish BOS: close above previous swing high
        if c[i] > prev_high_price and c[i-1] <= prev_high_price:
            # Wait for retest of broken level
            level = prev_high_price
            # Signal if price is now retesting (within 1 ATR)
            if abs(c[i] - level) < cur_atr * 1.5 and c[i] > level:
                entry = c[i]
                sl = level - cur_atr * 0.8
                risk = entry - sl
                if risk > 0 and risk < cur_atr * 2.5:
                    signals.append(Signal(
                        bar=i, direction='LONG', entry=entry,
                        sl=sl, tp=entry + risk * 3.0,
                        pattern='BOS_BULL', confluence=6,
                        risk_r=3.0
                    ))
        
        # Bearish BOS: close below previous swing low
        if c[i] < prev_low_price and c[i-1] >= prev_low_price:
            level = prev_low_price
            if abs(c[i] - level) < cur_atr * 1.5 and c[i] < level:
                entry = c[i]
                sl = level + cur_atr * 0.8
                risk = sl - entry
                if risk > 0 and risk < cur_atr * 2.5:
                    signals.append(Signal(
                        bar=i, direction='SHORT', entry=entry,
                        sl=sl, tp=entry - risk * 3.0,
                        pattern='BOS_BEAR', confluence=6,
                        risk_r=3.0
                    ))
    
    return signals

# ─── Pattern 3: Order Block Retest ────────────────────────────────────────────
def detect_ob_signals(data, atr, lookback=3):
    """
    Order Block: last bullish/bearish candle before a strong move
    Entry: when price returns to OB zone
    """
    h, l, c, o, v = data['high'], data['low'], data['close'], data['open'], data['volume']
    n = len(c)
    signals = []
    
    avg_vol = np.zeros(n)
    for i in range(20, n):
        avg_vol[i] = np.mean(v[i-20:i])
    
    active_obs = []  # (type, bar, zone_high, zone_low, strength)
    
    for i in range(5, n):
        cur_atr = atr[i]
        if cur_atr == 0 or avg_vol[i] == 0: continue
        
        # Detect strong moves (displacement)
        body = abs(c[i] - o[i])
        is_strong_bull = c[i] > o[i] and body > cur_atr * 1.5 and v[i] > avg_vol[i] * 1.5
        is_strong_bear = c[i] < o[i] and body > cur_atr * 1.5 and v[i] > avg_vol[i] * 1.5
        
        if is_strong_bull:
            # OB is the last bearish candle before this move
            for j in range(i-1, max(i-lookback-1, 0), -1):
                if c[j] < o[j]:  # bearish candle = bullish OB
                    ob_high = o[j]  # open of bearish candle
                    ob_low = c[j]   # close of bearish candle
                    active_obs.append(('bull_ob', j, ob_high, ob_low, body/cur_atr))
                    break
        
        if is_strong_bear:
            for j in range(i-1, max(i-lookback-1, 0), -1):
                if c[j] > o[j]:  # bullish candle = bearish OB
                    ob_high = c[j]
                    ob_low = o[j]
                    active_obs.append(('bear_ob', j, ob_high, ob_low, body/cur_atr))
                    break
        
        # Check for OB retests
        for ob in active_obs[:]:
            otype, obar, ohigh, olow, strength = ob
            age = i - obar
            if age < 3 or age > 50:
                if age > 50: active_obs.remove(ob)
                continue
            
            if otype == 'bull_ob':
                # Price returns to OB and shows bullish rejection
                if l[i] <= ohigh and l[i] >= olow and c[i] > (olow + ohigh) / 2:
                    entry = c[i]
                    sl = olow - cur_atr * 0.3
                    risk = entry - sl
                    if risk > 0 and risk < cur_atr * 2.5:
                        conf = min(8, 4 + int(strength))
                        signals.append(Signal(
                            bar=i, direction='LONG', entry=entry,
                            sl=sl, tp=entry + risk * 3.5,
                            pattern='OB_BULL', confluence=conf,
                            risk_r=3.5
                        ))
                    active_obs.remove(ob)
            
            elif otype == 'bear_ob':
                if h[i] >= olow and h[i] <= ohigh and c[i] < (olow + ohigh) / 2:
                    entry = c[i]
                    sl = ohigh + cur_atr * 0.3
                    risk = sl - entry
                    if risk > 0 and risk < cur_atr * 2.5:
                        conf = min(8, 4 + int(strength))
                        signals.append(Signal(
                            bar=i, direction='SHORT', entry=entry,
                            sl=sl, tp=entry - risk * 3.5,
                            pattern='OB_BEAR', confluence=conf,
                            risk_r=3.5
                        ))
                    active_obs.remove(ob)
    
    return signals

# ─── Pattern 4: Liquidity Sweep + Reversal ────────────────────────────────────
def detect_sweep_signals(data, atr, lookback=20):
    """
    Liquidity Sweep: price briefly breaks above swing high or below swing low
    then immediately reverses — classic stop hunt
    Entry: after the sweep, on the reversal candle
    """
    h, l, c, o = data['high'], data['low'], data['close'], data['open']
    n = len(c)
    signals = []
    
    for i in range(lookback + 3, n):
        cur_atr = atr[i]
        if cur_atr == 0: continue
        
        # Recent equal/swing highs and lows in lookback window
        window_highs = h[i-lookback:i]
        window_lows = l[i-lookback:i]
        
        # Bearish sweep: wick above recent highs, close back below
        resistance = np.max(window_highs[:-3])  # exclude last 3 bars
        if h[i] > resistance and c[i] < resistance:
            wick_above = h[i] - resistance
            body_size = abs(c[i] - o[i])
            if wick_above > cur_atr * 0.3 and c[i] < o[i]:  # bearish close
                entry = c[i]
                sl = h[i] + cur_atr * 0.2  # above the wick
                risk = sl - entry
                if risk > 0 and risk < cur_atr * 3:
                    signals.append(Signal(
                        bar=i, direction='SHORT', entry=entry,
                        sl=sl, tp=entry - risk * 4.0,
                        pattern='SWEEP_BEAR', confluence=7,
                        risk_r=4.0, trail_atr_mult=3.0
                    ))
        
        # Bullish sweep: wick below recent lows, close back above
        support = np.min(window_lows[:-3])
        if l[i] < support and c[i] > support:
            wick_below = support - l[i]
            if wick_below > cur_atr * 0.3 and c[i] > o[i]:  # bullish close
                entry = c[i]
                sl = l[i] - cur_atr * 0.2
                risk = entry - sl
                if risk > 0 and risk < cur_atr * 3:
                    signals.append(Signal(
                        bar=i, direction='LONG', entry=entry,
                        sl=sl, tp=entry + risk * 4.0,
                        pattern='SWEEP_BULL', confluence=7,
                        risk_r=4.0, trail_atr_mult=3.0
                    ))
    
    return signals

# ─── Combined Signal Generator ────────────────────────────────────────────────
def generate_all_signals(data, use_regime=True, use_session=True, min_confluence=5):
    """Generate signals from all patterns with optional regime/session filtering."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / 'sonnet_4h'))
    
    h, l, c = data['high'], data['low'], data['close']
    atr = compute_atr(h, l, c, 14)
    
    # Collect all pattern signals
    all_signals = []
    all_signals.extend(detect_fvg_signals(data, atr))
    all_signals.extend(detect_bos_choch_signals(data, atr))
    all_signals.extend(detect_ob_signals(data, atr))
    all_signals.extend(detect_sweep_signals(data, atr))
    
    # Sort by bar
    all_signals.sort(key=lambda s: s.bar)
    
    # Deduplicate: same direction within 3 bars = keep highest confluence
    deduped = []
    seen_bars = {}
    for sig in all_signals:
        key = (sig.bar // 3, sig.direction)
        if key not in seen_bars or sig.confluence > seen_bars[key].confluence:
            seen_bars[key] = sig
    deduped = list(seen_bars.values())
    deduped.sort(key=lambda s: s.bar)
    
    # Filter by confluence
    filtered = [s for s in deduped if s.confluence >= min_confluence]
    
    # Optional regime + session filters
    if use_regime or use_session:
        from backtest_15m_enhanced import (
            compute_adx, compute_efficiency_ratio, compute_atr_percentile,
            classify_regime, classify_session
        )
        adx_vals, _, _ = compute_adx(h, l, c, 14)
        er = compute_efficiency_ratio(c, 10)
        atr_pct = compute_atr_percentile(atr, 100)
        ts = data['timestamp']
        
        final = []
        for sig in filtered:
            i = sig.bar
            if use_regime:
                regime = classify_regime(adx_vals, er, atr_pct, i)
                if regime != 'trend':
                    continue
            if use_session:
                session = classify_session(int(ts[i]))
                if session not in ('us', 'overlap', 'europe'):
                    continue
            final.append(sig)
        return final
    
    return filtered

if __name__ == '__main__':
    # Quick test
    import csv, numpy as np
    from pathlib import Path
    
    path = Path(__file__).parent.parent / 'sonnet_4h/data_binance_split/15m_BTC_backtest.csv'
    ts,o,h,l,c,v=[],[],[],[],[],[]
    with open(path) as f:
        for row in csv.DictReader(f):
            ts.append(int(row['timestamp'])); o.append(float(row['open']))
            h.append(float(row['high'])); l.append(float(row['low']))
            c.append(float(row['close'])); v.append(float(row['volume']))
    data = {'timestamp': np.array(ts), 'open': np.array(o), 'high': np.array(h),
            'low': np.array(l), 'close': np.array(c), 'volume': np.array(v)}
    
    sigs = generate_all_signals(data, use_regime=True, use_session=True)
    
    from collections import Counter
    patterns = Counter(s.pattern for s in sigs)
    dirs = Counter(s.direction for s in sigs)
    
    print(f"Total signals: {len(sigs)}")
    print(f"By pattern: {dict(patterns)}")
    print(f"By direction: {dict(dirs)}")
    print(f"Avg confluence: {sum(s.confluence for s in sigs)/len(sigs):.2f}")
