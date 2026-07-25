from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


def _dec(v) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v))


class EpisodeStatus(str, Enum):
    IDLE = "idle"
    WATCHING = "watching"
    CONFIRMED = "confirmed"
    DISTRIBUTING = "distributing"
    CLOSED = "closed"
    EXPIRED = "expired"
    STOPPED = "stopped"


class OrderPurpose(str, Enum):
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    LADDER_050 = "LADDER_050"
    LADDER_062 = "LADDER_062"
    LADDER_0786 = "LADDER_0786"
    BREAKOUT = "BREAKOUT"
    EXIT1 = "EXIT1"
    MIRROR = "MIRROR"
    STOP = "STOP"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderKind(str, Enum):
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    MARKET = "market"


@dataclass(frozen=True, slots=True)
class Bar:
    date: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    @staticmethod
    def from_json(row: dict) -> "Bar":
        return Bar(date=row["date"][:10], open=_dec(row["o"]), high=_dec(row["h"]),
                   low=_dec(row["l"]), close=_dec(row["c"]))


@dataclass(frozen=True, slots=True)
class Week:
    monday: str
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class OnChain:
    date: str
    realized: Decimal
    balanced: Decimal

    @property
    def midpoint(self) -> Decimal:
        return (self.realized + self.balanced) / Decimal(2)


@dataclass(frozen=True, slots=True)
class DesiredOrder:
    purpose: OrderPurpose
    side: OrderSide
    kind: OrderKind
    price: Decimal | None
    units: Decimal


@dataclass(frozen=True, slots=True)
class EpisodeState:
    status: EpisodeStatus = EpisodeStatus.IDLE
    trigger_date: str | None = None
    prior_ath: Decimal | None = None
    scope_start: str | None = None
    running_low: Decimal | None = None
    el_star: Decimal | None = None
    operative_lh: Decimal | None = None
    lh_confirmed_at: str | None = None
    bos_date: str | None = None
    bos_week_high: Decimal | None = None
    exit1_done: bool = False


@dataclass(frozen=True, slots=True)
class EngineResult:
    state: EpisodeState
    orders: tuple[DesiredOrder, ...]
