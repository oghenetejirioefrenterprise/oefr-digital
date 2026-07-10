"""Rank products by signal, build today's work queue.

Phase 0 stub: ranks by revenue, then by status priority. Phase 1 will
read from signals.db (traffic, conversion, refund rate, etc.) and
produce a richer work queue.

The work queue tells the LLM execution cycles (product-loop, morpheus,
seo-operator) which products to prioritize. They consume this queue;
they do not pick their own targets.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .roster import Product, Status, load_roster

# Status priority for tie-breaking when revenue is equal.
# Higher number = more attention.
_STATUS_WEIGHT = {
    Status.SCALING: 5,
    Status.MAINTAIN: 4,
    Status.PRODUCING: 3,
    Status.VALIDATING: 2,
    Status.CANDIDATE: 1,
    Status.SUNSET_PENDING: 0,
    Status.DEAD: -1,
    Status.META: -1,
}


@dataclass
class RankedProduct:
    product: Product
    score: float

    @property
    def name(self) -> str:
        return self.product.name


def rank_products(products: Optional[list[Product]] = None) -> list[RankedProduct]:
    """Return products ranked by allocation priority (highest first).

    Phase 0 scoring:
      score = revenue_30d * 10 + status_weight
    Dead and meta products are excluded.
    """
    if products is None:
        products = load_roster()

    ranked: list[RankedProduct] = []
    for p in products:
        if p.status in (Status.DEAD, Status.META):
            continue
        score = p.revenue_value() * 10 + _STATUS_WEIGHT.get(p.status, 0)
        ranked.append(RankedProduct(product=p, score=score))

    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked


def top_work_queue(n: int = 5) -> list[str]:
    """Return the top N product names that LLM cycles should focus on."""
    return [r.name for r in rank_products()[:n]]
