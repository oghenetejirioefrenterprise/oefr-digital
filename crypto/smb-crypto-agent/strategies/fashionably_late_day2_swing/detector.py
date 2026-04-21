"""
Detector for fashionably_late_day2_swing.
Category: fashionably_late   Timeframe: swing   Confidence: high
Venues: Hyperliquid perps, Binance spot

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
