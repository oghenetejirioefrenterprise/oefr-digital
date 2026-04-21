# Options Expression

> **Reference only — not tradeable on crypto venues.** This file documents concepts from SMB equity trading content that do not have a clean crypto perp/spot analog.

## What it is

"Options expression" refers to the price dynamics that arise as equity options approach and reach their expiration date. As 0DTE (zero days to expiration) or weekly options expire, dealers who have sold options must hedge their exposure by buying or selling the underlying stock, creating systematic intraday price flows that experienced traders anticipate. SMB specifically studies which market-breadth conditions produce trending days versus mean-reverting days for 0DTE trading.

## Mechanic

The SMB content identifies seven market-breadth conditions (e.g., advancing issues vs. declining issues ratio, NYSE TICK distribution, VIX behavior at open) that classify the session as a trend day, balance day, or reversal day. On trend days, 0DTE directional spreads are held longer; on balance days, trades are faded quickly near range extremes. The key edge is that option dealer gamma hedging amplifies moves on trend days and suppresses moves (pins price) on balance/expiration days — recognizing which regime is in effect before 10 AM is the skill.

## Why it doesn't port to crypto

- **No standardized listed options market on crypto perps.** Hyperliquid and Binance (the target venues for this agent) are perp and spot markets. Deribit offers BTC/ETH vanilla options, but there is no equivalent 0DTE weekly options ecosystem across the altcoin universe where the SMB setups were built.
- **No gamma-dealer hedging flows.** The options expression dynamic is driven by market makers delta-hedging large structured books. Crypto options markets are thinner, less standardized, and do not yet generate the systematic expiry-day flows that underpin the 0DTE breadth-day classification system.
- **Market breadth tools don't transfer.** NYSE TICK, advance/decline ratios, and ARMS index are equity-market-infrastructure metrics. No direct crypto equivalents exist at the asset-class level.

## Near-analogs worth watching (if any)

- Volatility surface compression ≈ option expiry pinning (Deribit max-pain levels on BTC/ETH monthly expirations can create pinning behavior — worth monitoring on the last Friday of each month for BTC/ETH spot positions, but not actionable for perp strategies on Hyperliquid)

## Source transcripts

Top_7_Market_Breadth_Days_for_0_DTE_Options_Trading.transcript.md
