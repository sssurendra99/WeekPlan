from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gio

from ..models.store import EventStore
from ..services.recurrence import expand
from .preferences import PreferencesStore

if TYPE_CHECKING:
    pass


def _make_fire_callback(
    app: Adw.Application,
    title: str,
    body: str,
    notif_id: str,
) -> callable:
    def _fire() -> bool:
        notif = Gio.Notification.new(f"Coming up: {title}")
        notif.set_body(body)
        notif.set_icon(Gio.ThemedIcon.new("x-office-calendar"))
        notif.set_priority(Gio.NotificationPriority.HIGH)
        app.send_notification(notif_id, notif)
        return GLib.SOURCE_REMOVE

    return _fire


class NotificationService:
    def __init__(
        self,
        app: Adw.Application,
        store: EventStore,
        prefs: PreferencesStore,
    ) -> None:
        self._app = app
        self._store = store
        self._prefs = prefs
        self._scheduled: set[str] = set()

    def start(self) -> None:
        self.schedule_upcoming()
        GLib.timeout_add(60_000 * 15, self._rescan)

    def _rescan(self) -> bool:
        self.schedule_upcoming()
        return GLib.SOURCE_CONTINUE

    def schedule_upcoming(self) -> None:
        now = datetime.now(timezone.utc)
        window_end = now + timedelta(hours=24)

        events = self._store.list_in_range(now, window_end)
        lead = self._prefs.lead_time_minutes

        for event in events:
            for occ_start, occ_end in expand(event, now, window_end):
                notif_id = f"weekplan-{event.id}-{occ_start.strftime('%Y%m%dT%H%M%S')}"
                if notif_id in self._scheduled:
                    continue

                fire_at = occ_start - timedelta(minutes=lead)
                if fire_at <= now:
                    continue

                delay_ms = int((fire_at - now).total_seconds() * 1000)

                time_str = occ_start.strftime("%H:%M")
                body_parts = [time_str]
                if event.description:
                    body_parts.append(event.description)
                body = " — ".join(body_parts)

                GLib.timeout_add(
                    delay_ms,
                    _make_fire_callback(self._app, event.title, body, notif_id),
                )
                self._scheduled.add(notif_id)
