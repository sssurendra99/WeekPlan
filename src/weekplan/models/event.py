from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Event:
    # Required fields first so the dataclass is valid (id is auto-assigned by DB)
    title: str
    start: datetime
    end: datetime
    description: str = ""
    color: str = "sky"  # one of: sky sage amber coral lavender rose teal slate
    all_day: bool = False
    rrule: str | None = None
    google_id: str | None = None
    id: int | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError(f"end ({self.end!r}) must be after start ({self.start!r})")
