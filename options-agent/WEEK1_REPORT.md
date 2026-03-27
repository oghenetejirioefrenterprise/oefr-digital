🏁 WEEK 1 FORWARD TEST — FINAL REPORT
Period: Mar 26–27, 2026 (2 trading days)

SCORECARD
Total Trades: 5 (3 scratch exits + 2 open at EOD)
Wins: 0 (0%) | Losses: 0 | Scratch: 3
Total P&L (realized): $0.00
Open P&L at EOD: ~-$104 (2 positions, unrealized)
Avg P&L per trade: $0.00 (realized only)
Profit Factor: N/A
Avg days in trade: less than 1 day

TOP TRADE: None — all exits were scratch ($0.00 PnL)
WORST TRADE: Mar 27 positions (6280/6275P + 6285/6280P, Apr 6 expiry) showing -$51/-$53 at market close when force-cleanup triggered

STRATEGY BREAKDOWN
BWB: 0 trades — NEVER executed (all configs returned net debits)
PUT VERTICAL (fallback): 5 entries
  3 closed scratch — reason: max_dte_hold triggered same day as entry
  2 open at EOD, force-closed by market cleanup
  Credits collected: $107, $104, $106, $125, $127
  Exit limits on 2 open positions: $1.86 / $1.90 (vs entry $1.25/$1.27)
  Implied EOD loss: approx -$55 to -$65 per position

CRITICAL ISSUES FOUND
[1] BWB never executed — IV rank ~37, IV ~22% too low for BWB to generate a net credit at 7-10 DTE. All 4 strike configurations returned debits both days.

[2] Strategy mismatch bug — config says BWB but agent entered PUT VERTICALS. Notifier still expects BWB strike keys causing KeyError on every entry. All trade notifications failed silently.

[3] Same-day open/close bug — 3 positions opened and immediately closed (reason: max_dte_hold at 7 DTE). The DTE exit threshold equals the entry DTE. Critical config error.

[4] Delayed market data — constant 10167 warnings throughout. Agent running on delayed quotes — unacceptable for live trading.

[5] IBKR disconnect at 16:50 ET — TWS connection lost end of day. No reconnect handling.

RECOMMENDATION
DO NOT GO LIVE — extend paper trading

Key risks observed:
- BWB structurally broken in current IV regime
- Wrong strategy executing (verticals mislabeled as BWB)
- Same-day exit bug destroys any edge
- No live market data subscription
- Zero wins — no statistical edge to evaluate

Suggested config changes:
1. Fix strategy routing — decouple BWB from PUT VERTICAL
2. Fix max_dte_hold threshold (cannot equal entry DTE)
3. Fix notifier strike key lookup for vertical spreads
4. Upgrade to live market data subscription
5. Raise IV rank minimum OR switch primary to PUT VERTICAL (structurally working)
6. Add IBKR TWS reconnect logic

Next milestone: 2 full weeks paper, 10+ clean trades with correct exits before go-live decision.