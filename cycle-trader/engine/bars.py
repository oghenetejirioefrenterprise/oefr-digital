from __future__ import annotations
from datetime import date as _date, timedelta
from engine.types import Bar, Week


def monday_of(date: str) -> str:
    y, m, dd = (int(x) for x in date[:10].split("-"))
    d = _date(y, m, dd)
    return (d - timedelta(days=d.weekday())).isoformat()


def to_weeks(bars: list[Bar]) -> list[Week]:
    """Aggregate daily bars into ISO-Monday-anchored weeks, in date order.

    Week high = max of daily highs, low = min of daily lows,
    close = close of the last daily bar present in that week.
    """
    buckets: dict[str, list[Bar]] = {}
    for b in sorted(bars, key=lambda x: x.date):
        buckets.setdefault(monday_of(b.date), []).append(b)
    weeks = []
    for monday in sorted(buckets):
        group = buckets[monday]
        weeks.append(Week(
            monday=monday,
            high=max(g.high for g in group),
            low=min(g.low for g in group),
            close=group[-1].close,
        ))
    return weeks
