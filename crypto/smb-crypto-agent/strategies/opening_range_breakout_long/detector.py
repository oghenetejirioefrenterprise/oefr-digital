"""
Detector for opening_range_breakout_long.
Category: opening_range_breakout   Timeframe: scalp   Confidence: high
Venues: Hyperliquid perps, Binance spot/futures

NOT IMPLEMENTED. Implement `find_candidates` so it emits dict candidates consumed by
`core/judge.py`. See playbook.md in this directory for the distilled rules.
"""
from dataclasses import dataclass


@dataclass
class Candidate:
    symbol: str
    venue: str
    direction: str
    setup: str
    features: dict


def find_candidates(market_ctx) -> list[Candidate]:
    raise NotImplementedError("implement detector from playbook.md")
