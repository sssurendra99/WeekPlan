from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Event:
    # Required fields first so the dataclass is valid (id is auto-assigned by DB)
    title: str
    start: datetime
    end: datetime
    description: str = ""
    color: str = "#3584e4"
    rrule: Optional[str] = None
    google_id: Optional[str] = None
    id: Optional[int] = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError(
                f"end ({self.end!r}) must be after start ({self.start!r})"
            )
