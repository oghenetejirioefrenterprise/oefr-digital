"""Trinity Rules — deterministic Python layer between sensors and LLM cycles.

The agent loop cannot rationalize past these rules because they run as code,
not as prompt instructions. LLM cycles synthesize and execute; rules gate.

Modules:
    roster      — read/write product-roster.md as structured data
    killer      — apply kill rules, transition product statuses
    allocator   — rank products by signal, build today's work queue
    governance  — opportunity validation gate + LLM output guardrails
"""
from .roster import (
    load_roster,
    save_roster,
    Product,
    Status,
    PORTFOLIO_MAX,
    SUNSET_GRACE_DAYS,
)
from .killer import apply_kill_rules, KillerReport
from .allocator import rank_products
from .governance import (
    check_opportunity,
    check_llm_output,
    GovernanceResult,
    NETWORKING_KEYWORDS,
)

__all__ = [
    "load_roster",
    "save_roster",
    "Product",
    "Status",
    "PORTFOLIO_MAX",
    "SUNSET_GRACE_DAYS",
    "apply_kill_rules",
    "KillerReport",
    "rank_products",
    "check_opportunity",
    "check_llm_output",
    "GovernanceResult",
    "NETWORKING_KEYWORDS",
]
