from datetime import UTC, datetime
from pathlib import Path

import pytest

from weekplan.models.event import Event
from weekplan.models.store import EventStore

# ------------------------------------------------------------------ helpers

JAN = datetime(2024, 1, 15, 9, 0, tzinfo=UTC)
JAN_END = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
FEB = datetime(2024, 2, 15, 9, 0, tzinfo=UTC)
FEB_END = datetime(2024, 2, 15, 10, 0, tzinfo=UTC)


def make_event(**kwargs) -> Event:
    defaults = {"title": "Test Event", "start": JAN, "end": JAN_END}
    defaults.update(kwargs)
    return Event(**defaults)


@pytest.fixture
def store(tmp_path: Path) -> EventStore:
    s = EventStore(db_path=tmp_path / "test.db")
    yield s
    s.close()


# ------------------------------------------------------------------ tests


def test_add_get_roundtrip(store: EventStore) -> None:
    event = make_event(title="Meeting", description="Weekly sync", color="#ff0000")
    added = store.add(event)

    assert added.id is not None
    retrieved = store.get(added.id)
    assert retrieved is not None
    assert retrieved.title == "Meeting"
    assert retrieved.description == "Weekly sync"
    assert retrieved.color == "#ff0000"
    assert retrieved.start == JAN
    assert retrieved.end == JAN_END


def test_add_returns_same_object_with_id(store: EventStore) -> None:
    event = make_event()
    result = store.add(event)
    assert result is event
    assert event.id is not None


def test_get_missing_returns_none(store: EventStore) -> None:
    assert store.get(9999) is None


def test_update(store: EventStore) -> None:
    event = store.add(make_event(title="Original"))
    event.title = "Updated"
    store.update(event)

    retrieved = store.get(event.id)
    assert retrieved.title == "Updated"


def test_update_without_id_raises(store: EventStore) -> None:
    event = make_event()  # id is None
    with pytest.raises(ValueError):
        store.update(event)


def test_delete(store: EventStore) -> None:
    event = store.add(make_event())
    event_id = event.id
    store.delete(event_id)
    assert store.get(event_id) is None


def test_delete_nonexistent_is_silent(store: EventStore) -> None:
    store.delete(9999)  # should not raise


def test_list_in_range_filters_correctly(store: EventStore) -> None:
    store.add(make_event(title="January", start=JAN, end=JAN_END))
    store.add(make_event(title="February", start=FEB, end=FEB_END))

    results = store.list_in_range(
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 2, 1, tzinfo=UTC),
    )
    titles = {e.title for e in results}
    assert "January" in titles
    assert "February" not in titles


def test_list_in_range_end_boundary_exclusive(store: EventStore) -> None:
    # Event starting exactly at end_dt should NOT be included
    store.add(make_event(title="Boundary", start=FEB, end=FEB_END))

    results = store.list_in_range(
        datetime(2024, 1, 1, tzinfo=UTC),
        FEB,  # end_dt == event.start → excluded
    )
    titles = {e.title for e in results}
    assert "Boundary" not in titles


def test_rrule_events_returned_regardless_of_date(store: EventStore) -> None:
    store.add(
        make_event(
            title="Daily Standup",
            start=datetime(2024, 1, 1, 9, 0, tzinfo=UTC),
            end=datetime(2024, 1, 1, 9, 30, tzinfo=UTC),
            rrule="FREQ=DAILY",
        )
    )
    store.add(make_event(title="January One-Off", start=JAN, end=JAN_END))

    # Query February — rrule event must appear; one-off must not
    results = store.list_in_range(
        datetime(2024, 2, 1, tzinfo=UTC),
        datetime(2024, 3, 1, tzinfo=UTC),
    )
    titles = {e.title for e in results}
    assert "Daily Standup" in titles
    assert "January One-Off" not in titles


def test_end_equal_to_start_raises() -> None:
    t = datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
    with pytest.raises(ValueError):
        make_event(start=t, end=t)


def test_end_before_start_raises() -> None:
    with pytest.raises(ValueError):
        make_event(
            start=datetime(2024, 1, 15, 10, 0, tzinfo=UTC),
            end=datetime(2024, 1, 15, 9, 0, tzinfo=UTC),
        )


def test_datetime_roundtrip_preserves_utc(store: EventStore) -> None:
    event = store.add(make_event())
    retrieved = store.get(event.id)
    assert retrieved.start.tzinfo is not None
    assert retrieved.end.tzinfo is not None
    assert retrieved.updated_at.tzinfo is not None


def test_rrule_and_google_id_nullable(store: EventStore) -> None:
    event = store.add(make_event(rrule=None, google_id=None))
    retrieved = store.get(event.id)
    assert retrieved.rrule is None
    assert retrieved.google_id is None


def test_rrule_and_google_id_stored(store: EventStore) -> None:
    event = store.add(
        make_event(
            rrule="FREQ=WEEKLY;BYDAY=MO",
            google_id="abc123",
        )
    )
    retrieved = store.get(event.id)
    assert retrieved.rrule == "FREQ=WEEKLY;BYDAY=MO"
    assert retrieved.google_id == "abc123"
