from datetime import datetime, timedelta, timezone

import pytest

from weekplan.models.event import Event
from weekplan.services.recurrence import expand

UTC = timezone.utc


def make_event(start: datetime, end: datetime, rrule: str | None = None) -> Event:
    return Event(title="Test", start=start, end=end, rrule=rrule)


# ── No rrule ──────────────────────────────────────────────────────────────────

def test_no_rrule_in_range() -> None:
    ev = make_event(
        datetime(2024, 1, 15, 9, 0, tzinfo=UTC),
        datetime(2024, 1, 15, 10, 0, tzinfo=UTC),
    )
    result = expand(ev, datetime(2024, 1, 15, tzinfo=UTC), datetime(2024, 1, 16, tzinfo=UTC))
    assert result == [(ev.start, ev.end)]


def test_no_rrule_out_of_range() -> None:
    ev = make_event(
        datetime(2024, 1, 15, 9, 0, tzinfo=UTC),
        datetime(2024, 1, 15, 10, 0, tzinfo=UTC),
    )
    result = expand(ev, datetime(2024, 2, 1, tzinfo=UTC), datetime(2024, 2, 8, tzinfo=UTC))
    assert result == []


def test_no_rrule_at_range_end_is_excluded() -> None:
    """range_end is exclusive — event starting exactly there must not appear."""
    ev = make_event(
        datetime(2024, 1, 15, 9, 0, tzinfo=UTC),
        datetime(2024, 1, 15, 10, 0, tzinfo=UTC),
    )
    # range_end == event.start → excluded
    result = expand(
        ev,
        datetime(2024, 1, 14, tzinfo=UTC),
        datetime(2024, 1, 15, 9, 0, tzinfo=UTC),
    )
    assert result == []


# ── Daily ─────────────────────────────────────────────────────────────────────

def test_daily_count_in_one_week() -> None:
    ev = make_event(
        datetime(2024, 1, 1, 9, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 9, 15, tzinfo=UTC),
        rrule="FREQ=DAILY",
    )
    result = expand(ev, datetime(2024, 1, 8, tzinfo=UTC), datetime(2024, 1, 15, tzinfo=UTC))
    assert len(result) == 7  # Jan 8–14


def test_daily_duration_preserved() -> None:
    ev = make_event(
        datetime(2024, 1, 1, 9, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 9, 15, tzinfo=UTC),
        rrule="FREQ=DAILY",
    )
    result = expand(ev, datetime(2024, 1, 8, tzinfo=UTC), datetime(2024, 1, 15, tzinfo=UTC))
    for start, end in result:
        assert end - start == timedelta(minutes=15)


def test_daily_first_occurrence_date() -> None:
    ev = make_event(
        datetime(2024, 1, 1, 9, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 9, 15, tzinfo=UTC),
        rrule="FREQ=DAILY",
    )
    result = expand(ev, datetime(2024, 1, 8, tzinfo=UTC), datetime(2024, 1, 15, tzinfo=UTC))
    assert result[0][0] == datetime(2024, 1, 8, 9, 0, tzinfo=UTC)


# ── Weekly ────────────────────────────────────────────────────────────────────

def test_weekly_count_in_two_weeks() -> None:
    # Jan 1 2024 is a Monday
    ev = make_event(
        datetime(2024, 1, 1, 9, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        rrule="FREQ=WEEKLY",
    )
    # Jan 1 (inc) → Jan 15 (exc): Jan 1 and Jan 8 only
    result = expand(ev, datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 15, tzinfo=UTC))
    assert len(result) == 2


def test_weekly_all_on_same_weekday() -> None:
    ev = make_event(
        datetime(2024, 1, 1, 9, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        rrule="FREQ=WEEKLY",
    )
    result = expand(ev, datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 2, 1, tzinfo=UTC))
    assert all(s.weekday() == 0 for s, _ in result)  # all Mondays


# ── Weekdays ──────────────────────────────────────────────────────────────────

def test_weekdays_only_count() -> None:
    ev = make_event(
        datetime(2024, 1, 1, 9, 0, tzinfo=UTC),   # Monday
        datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        rrule="FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
    )
    # Jan 1 (Mon) → Jan 8 (Mon, exc): Mon–Fri of first week = 5
    result = expand(ev, datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 8, tzinfo=UTC))
    assert len(result) == 5


def test_weekdays_no_weekend() -> None:
    ev = make_event(
        datetime(2024, 1, 1, 9, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        rrule="FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
    )
    result = expand(ev, datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 15, tzinfo=UTC))
    for start, _ in result:
        assert start.weekday() < 5  # 0=Mon … 4=Fri


# ── Custom BYDAY ──────────────────────────────────────────────────────────────

def test_custom_byday_mwf() -> None:
    ev = make_event(
        datetime(2024, 1, 1, 9, 0, tzinfo=UTC),   # Monday
        datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        rrule="FREQ=WEEKLY;BYDAY=MO,WE,FR",
    )
    # Jan 1 → Jan 8 (exc): Mon Jan 1, Wed Jan 3, Fri Jan 5
    result = expand(ev, datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 8, tzinfo=UTC))
    assert len(result) == 3
    assert [s.weekday() for s, _ in result] == [0, 2, 4]  # Mon, Wed, Fri


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_empty_range_returns_nothing() -> None:
    ev = make_event(
        datetime(2024, 1, 1, 9, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        rrule="FREQ=DAILY",
    )
    # range_start == range_end → empty half-open interval
    same = datetime(2024, 1, 8, tzinfo=UTC)
    assert expand(ev, same, same) == []


def test_rrule_before_dtstart_returns_nothing() -> None:
    ev = make_event(
        datetime(2024, 6, 1, 9, 0, tzinfo=UTC),
        datetime(2024, 6, 1, 10, 0, tzinfo=UTC),
        rrule="FREQ=DAILY",
    )
    # Query a range entirely before the event's dtstart
    result = expand(ev, datetime(2024, 1, 1, tzinfo=UTC), datetime(2024, 1, 8, tzinfo=UTC))
    assert result == []
