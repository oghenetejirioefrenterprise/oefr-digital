"""
Detector for leader_lagger_pair_trade.
Category: relative_strength   Timeframe: swing   Confidence: high
Venues: Hyperliquid (both legs as perps), Binance

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
