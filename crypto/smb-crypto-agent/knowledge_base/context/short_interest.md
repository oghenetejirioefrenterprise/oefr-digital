# Short Interest

> **Reference only — not tradeable on crypto venues.** This file documents concepts from SMB equity trading content that do not have a clean crypto perp/spot analog.

## What it is

Short interest is the percentage of a stock's publicly available float (total tradeable shares) that has been sold short and not yet covered. A high short float (typically >20–40%) signals a large contingent of traders who must eventually buy back shares, creating potential for violent upside moves if a positive catalyst forces those covers — the "short squeeze."

## Mechanic

SMB traders use short float as a pre-trade filter, not a directional signal on its own. The playbook: (1) identify a stock with >10–40% short float; (2) wait for a catalyst (earnings beat, major news, failed breakdown) that threatens the shorts' thesis; (3) enter long only after tape confirmation — large bids that do not drop despite selling pressure, offers stepping away. The squeeze is ridden via 9 EMA continuation on the 1-minute chart. The exit is equally structured: when price consolidates near highs but bids stop advancing price (exhaustion), the position reversal — short the fade after the lower high — is the second half of the trade. A contrasting setup is fading gap-ups on high-float stocks (low short interest = no squeeze fuel; safer to fade into resistance).

## Why it doesn't port to crypto

- **Float is an equity-specific construct.** It refers to shares legally available to trade after accounting for insider lockups, restricted stock, and treasury shares — a concept tied to SEC reporting and corporate capital structure. Crypto tokens do not have a defined "float" in the regulatory sense.
- **Short interest data is reported and public.** FINRA publishes biweekly short interest data; brokers display it in real time. No equivalent centralized, standardized dataset exists for crypto perpetual short exposure.
- **Forced covering mechanics differ.** In equities, short sellers face margin calls and stock borrow recalls that force covering on a timeline determined by their broker. In crypto perps, forced liquidation is driven by the mark-price margin system — mechanically different and not captured by a single public float percentage.

## Near-analogs worth watching (if any)

- Funding squeezes ≈ short-interest squeezes (when perp funding is deeply negative, the short side is paying longs; a catalyst can trigger rapid forced covering as funding flips — analogous dynamics, different data source)
- Open interest skew on Hyperliquid ≈ directional short overhang (large net short OI at key support with extreme negative funding is the closest substitute for high short float pre-squeeze entry)

## Source transcripts

How_to_Get_Into_a_Huge_Stock_Move.transcript.md, How_to_Take_ADVANTAGE_of_a_Short_Squeeze_And_Avoid_Getting_Crushed.transcript.md, The_Juicy_Breakout_Trade_Mistake.transcript.md
