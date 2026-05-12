"""Commitment record dataclass."""
from __future__ import annotations

import datetime as dt
import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


# Status values
PENDING = "pending"
SENT = "sent"
DISMISSED = "dismissed"
SNOOZED = "snoozed"
EXPIRED = "expired"

# Kind values
KIND_EVENT_CHECK_IN = "event_check_in"
KIND_DEADLINE_CHECK = "deadline_check"
KIND_OPEN_LOOP = "open_loop"


@dataclass
class CommitmentRecord:
    id: str
    kind: str
    text: str
    chat_id: str
    due_at: str             # ISO timestamp
    dedupe_key: str
    confidence: float
    status: str = PENDING
    created_at: str = field(
        default_factory=lambda: dt.datetime.now().isoformat()
    )
    sent_at: str | None = None
    snoozed_until: str | None = None
    nudge_text: str | None = None  # what to say when firing

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommitmentRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


def make_id() -> str:
    return f"cmt_{uuid.uuid4().hex[:12]}"


def make_dedupe_key(chat_id: str, kind: str, text: str) -> str:
    """Produce a stable hash so the same promise extracted twice merges."""
    blob = f"{chat_id}|{kind}|{text.strip().lower()}".encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]
