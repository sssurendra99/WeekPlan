from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import get_user_data_dir
from .event import Event

_SCHEMA_VERSION = 4

# Maps old hex color values to the new named-category system
_HEX_TO_COLOR_NAME: dict[str, str] = {
    "#3584e4": "sky",
    "#e66100": "amber",
    "#2ec27e": "sage",
    "#e01b24": "coral",
    "#9141ac": "lavender",
    "#f5c211": "amber",
    "#1c9ca0": "teal",
}
_VALID_COLOR_NAMES = frozenset(
    ["sky", "sage", "amber", "coral", "lavender", "rose", "teal", "slate"]
)


class EventStore:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = get_user_data_dir() / "events.db"
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    # ------------------------------------------------------------------ schema

    def _migrate(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        )
        row = cur.execute("SELECT version FROM schema_version").fetchone()
        version = row["version"] if row else 0
        if version < 1:
            self._apply_v1(cur)
        if version < 2:
            self._apply_v2(cur)
        if version < 3:
            self._apply_v3(cur)
        if version < 4:
            self._apply_v4(cur)
        self._conn.commit()

    def _apply_v1(self, cur: sqlite3.Cursor) -> None:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                start       TEXT    NOT NULL,
                end         TEXT    NOT NULL,
                description TEXT    NOT NULL DEFAULT '',
                color       TEXT    NOT NULL DEFAULT '#3584e4',
                rrule       TEXT,
                google_id   TEXT,
                updated_at  TEXT    NOT NULL
            )
        """)
        cur.execute("DELETE FROM schema_version")
        cur.execute("INSERT INTO schema_version (version) VALUES (1)")

    def _apply_v2(self, cur: sqlite3.Cursor) -> None:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tombstones (
                event_id   INTEGER NOT NULL,
                google_id  TEXT    NOT NULL,
                deleted_at TEXT    NOT NULL
            )
        """)
        cur.execute("DELETE FROM schema_version")
        cur.execute("INSERT INTO schema_version (version) VALUES (2)")

    def _apply_v4(self, cur: sqlite3.Cursor) -> None:
        cur.execute("ALTER TABLE events ADD COLUMN all_day INTEGER NOT NULL DEFAULT 0")
        cur.execute("DELETE FROM schema_version")
        cur.execute("INSERT INTO schema_version (version) VALUES (4)")

    def _apply_v3(self, cur: sqlite3.Cursor) -> None:
        for hex_color, name in _HEX_TO_COLOR_NAME.items():
            cur.execute(
                "UPDATE events SET color=? WHERE LOWER(color)=LOWER(?)",
                (name, hex_color),
            )
        placeholders = ",".join("?" * len(_VALID_COLOR_NAMES))
        cur.execute(
            f"UPDATE events SET color='sky' WHERE color NOT IN ({placeholders})",
            tuple(_VALID_COLOR_NAMES),
        )
        cur.execute("DELETE FROM schema_version")
        cur.execute("INSERT INTO schema_version (version) VALUES (3)")

    # --------------------------------------------------------------- datetime helpers

    @staticmethod
    def _to_iso(dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _from_iso(s: str) -> datetime:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    # --------------------------------------------------------------- row mapping

    def _row_to_event(self, row: sqlite3.Row) -> Event:
        return Event(
            title=row["title"],
            start=self._from_iso(row["start"]),
            end=self._from_iso(row["end"]),
            description=row["description"],
            color=row["color"],
            all_day=bool(row["all_day"]),
            rrule=row["rrule"],
            google_id=row["google_id"],
            id=row["id"],
            updated_at=self._from_iso(row["updated_at"]),
        )

    # --------------------------------------------------------------- public API

    def add(self, event: Event) -> Event:
        cur = self._conn.execute(
            """
            INSERT INTO events (title, start, end, description, color, all_day, rrule, google_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.title,
                self._to_iso(event.start),
                self._to_iso(event.end),
                event.description,
                event.color,
                int(event.all_day),
                event.rrule,
                event.google_id,
                self._to_iso(event.updated_at),
            ),
        )
        self._conn.commit()
        event.id = cur.lastrowid
        return event

    def update(self, event: Event) -> None:
        if event.id is None:
            raise ValueError("Cannot update an event that has no id")
        self._conn.execute(
            """
            UPDATE events
               SET title=?, start=?, end=?, description=?, color=?, all_day=?,
                   rrule=?, google_id=?, updated_at=?
             WHERE id=?
            """,
            (
                event.title,
                self._to_iso(event.start),
                self._to_iso(event.end),
                event.description,
                event.color,
                int(event.all_day),
                event.rrule,
                event.google_id,
                self._to_iso(event.updated_at),
                event.id,
            ),
        )
        self._conn.commit()

    def delete(self, event_id: int) -> None:
        row = self._conn.execute(
            "SELECT google_id FROM events WHERE id=?", (event_id,)
        ).fetchone()
        if row and row["google_id"]:
            self._conn.execute(
                "INSERT INTO tombstones (event_id, google_id, deleted_at) VALUES (?, ?, ?)",
                (event_id, row["google_id"], self._to_iso(datetime.now(timezone.utc))),
            )
        self._conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        self._conn.commit()

    def get(self, event_id: int) -> Optional[Event]:
        row = self._conn.execute(
            "SELECT * FROM events WHERE id=?", (event_id,)
        ).fetchone()
        return self._row_to_event(row) if row else None

    def get_by_google_id(self, google_id: str) -> Optional[Event]:
        row = self._conn.execute(
            "SELECT * FROM events WHERE google_id=?", (google_id,)
        ).fetchone()
        return self._row_to_event(row) if row else None

    def list_all(self) -> list[Event]:
        rows = self._conn.execute("SELECT * FROM events").fetchall()
        return [self._row_to_event(r) for r in rows]

    def get_tombstones(self) -> list[tuple[int, str]]:
        rows = self._conn.execute(
            "SELECT event_id, google_id FROM tombstones"
        ).fetchall()
        return [(r["event_id"], r["google_id"]) for r in rows]

    def clear_tombstone(self, event_id: int) -> None:
        self._conn.execute("DELETE FROM tombstones WHERE event_id=?", (event_id,))
        self._conn.commit()

    def list_in_range(self, start_dt: datetime, end_dt: datetime) -> list[Event]:
        rows = self._conn.execute(
            """
            SELECT * FROM events
             WHERE (start >= ? AND start < ?)
                OR rrule IS NOT NULL
            """,
            (self._to_iso(start_dt), self._to_iso(end_dt)),
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
