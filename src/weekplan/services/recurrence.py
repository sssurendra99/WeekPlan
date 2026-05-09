from __future__ import annotations

from datetime import UTC, datetime

from dateutil.rrule import rrulestr

from ..models.event import Event


def expand(
    event: Event,
    range_start: datetime,
    range_end: datetime,
) -> list[tuple[datetime, datetime]]:
    """Return (start, end) pairs for every occurrence of *event* in [range_start, range_end).

    For non-recurring events returns zero or one pair.
    For recurring events every occurrence whose start falls in the half-open
    interval is returned; each pair has the same duration as the master event.
    """
    duration = event.end - event.start

    if event.rrule is None:
        if range_start <= event.start < range_end:
            return [(event.start, event.end)]
        return []

    # dateutil works most reliably with naive UTC datetimes — strip tzinfo,
    # compute, then re-attach UTC before returning.
    def _naive(dt: datetime) -> datetime:
        return dt.astimezone(UTC).replace(tzinfo=None)

    dtstart_n = _naive(event.start)
    rs_n = _naive(range_start)
    re_n = _naive(range_end)

    rule = rrulestr(event.rrule, dtstart=dtstart_n, ignoretz=True)

    # between(a, b, inc=True) → a ≤ x ≤ b.
    # The guard `dt < re_n` makes the right boundary exclusive, matching
    # the store's list_in_range semantics.
    return [
        (
            occ.replace(tzinfo=UTC),
            (occ + duration).replace(tzinfo=UTC),
        )
        for occ in rule.between(rs_n, re_n, inc=True)
        if occ < re_n
    ]
