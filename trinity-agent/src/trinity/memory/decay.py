"""Decay calculations for the three-tier memory system.

Memories lose effective importance over time based on their tier,
segment, and access patterns.  Corrections and preferences decay
more slowly; context decays fastest.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from trinity.config import MemoryConfig
from trinity.memory.store import (
    SEGMENT_DECAY_MODIFIERS,
    TIERS,
    list_memories,
    recall_memory,
)


def effective_importance(memory: dict, config: MemoryConfig) -> float:
    """Calculate a memory's current importance after time-based decay.

    Permanent memories do not decay.
    Half-life is tier-dependent, modified by segment.
    """
    tier = memory.get("tier", "short-term")
    base_importance = float(memory.get("importance", 0.5))

    # Permanent tier: no decay
    if tier == "permanent":
        return base_importance

    # Determine tier half-life in hours
    if tier == "short-term":
        tier_half_life = config.short_term_decay_hours
    elif tier == "long-term":
        tier_half_life = config.long_term_decay_days * 24
    else:
        tier_half_life = config.short_term_decay_hours

    # Apply segment modifier
    segment = memory.get("segment", "context")
    modifier = SEGMENT_DECAY_MODIFIERS.get(segment, 1.0)
    half_life = tier_half_life * modifier

    # Guard against zero half-life
    if half_life <= 0:
        return base_importance

    # Decay is measured from the last *reinforcement* (store/update), NOT from
    # the last read — so merely recalling a memory no longer resets its decay
    # clock. Falls back to last_accessed for legacy rows without the field.
    reference = memory.get("last_reinforced") or memory.get("last_accessed", "")
    if not reference:
        return base_importance

    try:
        last_dt = dt.datetime.fromisoformat(reference)
    except (ValueError, TypeError):
        return base_importance

    hours_since = (dt.datetime.now() - last_dt).total_seconds() / 3600.0
    if hours_since < 0:
        hours_since = 0

    return base_importance * (0.5 ** (hours_since / half_life))


def check_promotions(trinity_dir: Path, config: MemoryConfig) -> list[str]:
    """Find memories eligible for promotion to a higher tier.

    Short-term -> long-term:
        accessed 3+ times, age > 24h, importance > 0.6
        corrections/preferences get 2x access_count multiplier

    Long-term -> permanent:
        accessed 10+ times, age > 7 days, importance > config.promotion_threshold
        corrections/preferences get 2x access_count multiplier
    """
    promotable: list[str] = []
    now = dt.datetime.now()

    all_memories = list_memories(trinity_dir)

    for entry in all_memories:
        memory_id = entry["id"]
        tier = entry.get("tier", "short-term")
        segment = entry.get("segment", "context")
        access_count = entry.get("access_count", 0)
        importance = float(entry.get("importance", 0.5))

        # Apply multiplier for corrections and preferences
        effective_access = access_count
        if segment in ("corrections", "preferences"):
            effective_access = access_count * 2

        created_str = entry.get("created", "")
        try:
            created_dt = dt.datetime.fromisoformat(created_str)
        except (ValueError, TypeError):
            continue

        age_hours = (now - created_dt).total_seconds() / 3600.0

        if tier == "short-term":
            # Promote to long-term
            if (
                effective_access >= 3
                and age_hours > 24
                and importance > 0.6
            ):
                promotable.append(memory_id)

        elif tier == "long-term":
            # Promote to permanent
            age_days = age_hours / 24.0
            if (
                effective_access >= 10
                and age_days > 7
                and importance > config.promotion_threshold
            ):
                promotable.append(memory_id)

    return promotable


def check_demotions(trinity_dir: Path, config: MemoryConfig) -> list[str]:
    """Find memories whose effective importance has dropped below 0.1.

    These are candidates for deletion (forgetting).
    Open issues are protected from demotion — they must be resolved first.
    """
    demotable: list[str] = []
    all_memories = list_memories(trinity_dir)

    for entry in all_memories:
        tier = entry.get("tier", "short-term")
        # Never demote permanent memories
        if tier == "permanent":
            continue

        # Protect open issues from demotion
        if entry.get("kind") == "issue" and entry.get("status") == "open":
            continue

        eff = effective_importance(entry, config)
        if eff < 0.1:
            demotable.append(entry["id"])

    return demotable
