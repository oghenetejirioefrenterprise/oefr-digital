from __future__ import annotations
from dataclasses import dataclass
from datetime import date as _date
from decimal import Decimal, InvalidOperation, localcontext
from engine.context import CTX
from enum import Enum


def _dec(v) -> Decimal:
    """Coerce a numeric value to Decimal, exactly and loudly.

    Goes via ``str`` so a float never reaches ``Decimal`` directly: ``290.0``
    becomes ``Decimal("290")`` rather than the binary-float expansion.
    Non-finite values (NaN, +/-Infinity) are rejected — NaN compares False
    under ``==`` without complaint but raises ``InvalidOperation`` under
    ``<`` and ``min()``, so a bad feed value would surface far from its
    origin, in the middle of a running-min.
    """
    if isinstance(v, Decimal):
        d = v
    else:
        try:
            d = Decimal(str(v))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"not a numeric value: {v!r}") from exc
    if not d.is_finite():
        raise ValueError(f"value must be finite, got {v!r}")
    return d


def _iso(v) -> str:
    """Validate and normalise a UTC date to an ISO ``YYYY-MM-DD`` string.

    Accepts a full timestamp (``"2020-03-16T00:00:00Z"``) by taking the date
    part, but the result must genuinely parse. Slicing alone is a truncation,
    not a parse: ``"16/03/2020extra"[:10]`` yields ``"16/03/2020"``, which
    would become a dict key that never matches any on-chain row, silently
    leaving that day without an accumulation line.
    """
    s = str(v)[:10]
    if len(s) != 10 or s[4] != "-" or s[7] != "-":
        raise ValueError(f"date must be an ISO YYYY-MM-DD string, got {v!r}")
    try:
        _date.fromisoformat(s)
    except ValueError as exc:
        raise ValueError(f"date must be an ISO YYYY-MM-DD string, got {v!r}") from exc
    return s


def _normalise(obj, decimals: tuple[str, ...] = (), dates: tuple[str, ...] = (),
               enums: tuple[tuple[str, type], ...] = ()) -> None:
    """Coerce fields in place on a frozen dataclass.

    ``object.__setattr__`` is the sanctioned escape hatch for ``__post_init__``
    on a frozen dataclass, and works under ``slots=True``. ``None`` is left
    alone so optional fields stay optional — except for ``enums``, where a
    ``None`` status is not an "unset optional" but an unusable state, so it is
    rejected with everything else the enum does not recognise.

    **Enums need this for the same reason Decimals do, and it is easier to
    miss.** These are ``str, Enum`` members, so a value read back from JSON
    (``"watching"``) compares equal, prints the same and serialises the same as
    the member — while failing every ``is`` comparison. ``engine/orders.py``
    dispatches with both ``in`` and ``is``, so an uncoerced status takes the
    wrong branch on four of seven values, in both directions. Coercing at
    construction means no consumer has to know which comparison it is holding.
    """
    for name in decimals:
        value = getattr(obj, name)
        if value is not None:
            object.__setattr__(obj, name, _dec(value))
    for name in dates:
        value = getattr(obj, name)
        if value is not None:
            object.__setattr__(obj, name, _iso(value))
    for name, enum_cls in enums:
        value = getattr(obj, name)
        try:
            object.__setattr__(obj, name, enum_cls(value))
        except ValueError as exc:
            raise ValueError(
                f"{name} must be one of "
                f"{[m.value for m in enum_cls]}, got {value!r}") from exc


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

    def __post_init__(self) -> None:
        _normalise(self, decimals=("open", "high", "low", "close"), dates=("date",))

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

    def __post_init__(self) -> None:
        _normalise(self, decimals=("high", "low", "close"), dates=("monday",))


@dataclass(frozen=True, slots=True)
class OnChain:
    date: str
    realized: Decimal
    balanced: Decimal

    def __post_init__(self) -> None:
        _normalise(self, decimals=("realized", "balanced"), dates=("date",))

    @property
    def midpoint(self) -> Decimal:
        """T2, the midpoint accumulation line (SPEC §3).

        This is a **fill price**, not a display value: `lines_for` hands it
        straight to the buy-limit primitive. The division is inexact, so it runs
        in the engine's pinned context (`engine/context.py`) — the same treatment
        as the identical expression in `levels.mirror_target`. Measured on EP3's
        fill day 2018-11-26, it is ambient-dependent from prec <= 10 (3e-7 at
        prec 10, 0.006 at prec 6, 0.114 at prec 4), a wider window than any other
        computation in the engine.
        """
        with localcontext(CTX):
            return (self.realized + self.balanced) / Decimal(2)


@dataclass(frozen=True, slots=True)
class DesiredOrder:
    purpose: OrderPurpose
    side: OrderSide
    kind: OrderKind
    price: Decimal | None
    units: Decimal

    def __post_init__(self) -> None:
        _normalise(self, decimals=("price", "units"))


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

    def __post_init__(self) -> None:
        _normalise(
            self,
            decimals=("prior_ath", "running_low", "el_star", "operative_lh",
                      "bos_week_high"),
            dates=("trigger_date", "scope_start", "lh_confirmed_at", "bos_date"),
            # The only field on the only type that comes back INTO the engine
            # from storage: M2 persists this state to Supabase and reads it
            # again next run, so `status` arrives as a JSON string.
            enums=(("status", EpisodeStatus),),
        )


@dataclass(frozen=True, slots=True)
class EngineResult:
    state: EpisodeState
    orders: tuple[DesiredOrder, ...]
