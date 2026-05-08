from __future__ import annotations

import gi
import math

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from datetime import date, datetime, timedelta, timezone

from gi.repository import Adw, GLib, Gtk

from ..config import _
from ..models.event import Event
from ..models.store import EventStore
from ..services.recurrence import expand
from .event_card import EventCard

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_HOUR_COL_W = 56   # px — fixed width for hour-label column
_CELL_H = 48       # px — height of each hour row


class WeekView(Gtk.Box):
    def __init__(self, store: EventStore) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._store = store
        self._anchor_date: date = date.today()
        self._event_cards: list[Gtk.Widget] = []

        self._build_nav()
        self._build_scroll_area()

    # ------------------------------------------------------------------ public

    def _week_dates(self) -> list[date]:
        monday = self._anchor_date - timedelta(days=self._anchor_date.weekday())
        return [monday + timedelta(days=i) for i in range(7)]

    def go_to_date(self, d: date) -> None:
        """Navigate so that *d* is visible, then refresh event cards."""
        self._anchor_date = d
        self._refresh_nav_label()
        self._fill_grid()
        self.refresh()

    def refresh(self) -> None:
        """Remove and re-create all event cards for the visible week."""
        for card in self._event_cards:
            self._grid.remove(card)
        self._event_cards.clear()

        dates = self._week_dates()
        week_start = datetime(
            dates[0].year, dates[0].month, dates[0].day, tzinfo=timezone.utc
        )
        week_end = datetime(
            dates[-1].year, dates[-1].month, dates[-1].day, tzinfo=timezone.utc
        ) + timedelta(days=1)

        events = self._store.list_in_range(week_start, week_end)
        date_to_col = {d: i + 1 for i, d in enumerate(dates)}

        for event in events:
            for occ_start, occ_end in expand(event, week_start, week_end):
                occ_date = occ_start.date()
                if occ_date not in date_to_col:
                    continue
                col      = date_to_col[occ_date]
                grid_row = occ_start.hour + 1
                secs     = (occ_end - occ_start).total_seconds()
                row_span = max(1, math.ceil(secs / 3600))

                card = EventCard(event, occ_start, occ_end, self._on_edit_event)
                self._grid.attach(card, col, grid_row, 1, row_span)
                self._event_cards.append(card)

    # ------------------------------------------------------------------ build

    def _build_nav(self) -> None:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        row.set_halign(Gtk.Align.CENTER)
        row.add_css_class("week-nav-row")

        prev = Gtk.Button(label="‹")
        prev.add_css_class("flat")
        prev.connect("clicked", lambda _: self._shift(-1))

        self._nav_btn = Gtk.Button()
        self._nav_btn.add_css_class("flat")
        self._nav_btn.connect("clicked", lambda _: self._go_today())
        self._refresh_nav_label()

        nxt = Gtk.Button(label="›")
        nxt.add_css_class("flat")
        nxt.connect("clicked", lambda _: self._shift(1))

        row.append(prev)
        row.append(self._nav_btn)
        row.append(nxt)
        self.append(row)

    def _build_scroll_area(self) -> None:
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_vexpand(True)
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._grid = Gtk.Grid()
        self._fill_grid()
        self._scroll.set_child(self._grid)
        self.append(self._scroll)

        self._scroll.connect("map", self._on_first_map)

    # ------------------------------------------------------------------ grid

    def _fill_grid(self) -> None:
        self._event_cards.clear()
        while (child := self._grid.get_first_child()) is not None:
            self._grid.remove(child)

        dates = self._week_dates()
        today = date.today()

        corner = Gtk.Label(label="")
        corner.set_size_request(_HOUR_COL_W, -1)
        corner.add_css_class("hour-corner")
        self._grid.attach(corner, 0, 0, 1, 1)

        for col, d in enumerate(dates, start=1):
            cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            cell.set_halign(Gtk.Align.CENTER)
            cell.set_hexpand(True)
            cell.add_css_class("day-header-cell")

            name_lbl = Gtk.Label(label=_DAY_NAMES[col - 1])
            name_lbl.add_css_class("caption")

            date_lbl = Gtk.Label(label=str(d.day))
            date_lbl.add_css_class("title-4")
            if d == today:
                date_lbl.add_css_class("today-badge")

            cell.append(name_lbl)
            cell.append(date_lbl)
            self._grid.attach(cell, col, 0, 1, 1)

        for hour in range(24):
            grid_row = hour + 1
            lbl = Gtk.Label(label=f"{hour:02d}:00")
            lbl.set_halign(Gtk.Align.END)
            lbl.set_valign(Gtk.Align.START)
            lbl.set_margin_top(4)
            lbl.set_margin_end(8)
            lbl.add_css_class("caption")
            lbl.add_css_class("dim-label")
            lbl.set_size_request(_HOUR_COL_W, _CELL_H)
            self._grid.attach(lbl, 0, grid_row, 1, 1)

            for col in range(1, 8):
                cell = Gtk.Box()
                cell.set_hexpand(True)
                cell.set_size_request(-1, _CELL_H)
                cell.add_css_class("hour-cell")
                self._grid.attach(cell, col, grid_row, 1, 1)

    # ------------------------------------------------------------------ scroll

    def _on_first_map(self, scroll: Gtk.ScrolledWindow) -> None:
        scroll.disconnect_by_func(self._on_first_map)
        GLib.idle_add(self._scroll_to_7am)

    def _scroll_to_7am(self) -> bool:
        vadj = self._scroll.get_vadjustment()
        target = 7 * _CELL_H
        vadj.set_value(max(0.0, min(target, vadj.get_upper() - vadj.get_page_size())))
        return GLib.SOURCE_REMOVE

    # ------------------------------------------------------------------ nav

    def _refresh_nav_label(self) -> None:
        dates = self._week_dates()
        s, e = dates[0], dates[-1]
        if s.year == e.year:
            label = f"{s.strftime('%b %-d')} – {e.strftime('%b %-d, %Y')}"
        else:
            label = f"{s.strftime('%b %-d, %Y')} – {e.strftime('%b %-d, %Y')}"
        self._nav_btn.set_label(label)

    def _shift(self, weeks: int) -> None:
        self._anchor_date += timedelta(weeks=weeks)
        self._refresh_nav_label()
        self._fill_grid()
        self.refresh()

    def _go_today(self) -> None:
        self._anchor_date = date.today()
        self._refresh_nav_label()
        self._fill_grid()
        self.refresh()

    # ------------------------------------------------------------------ event editing

    def _on_edit_event(self, event: Event) -> None:
        if event.rrule:
            self._prompt_recurring_edit(event)
        else:
            self._open_edit_dialog(event)

    def _prompt_recurring_edit(self, event: Event) -> None:
        alert = Adw.AlertDialog(
            heading=_("Edit Recurring Event"),
            body=_("Do you want to edit all occurrences of this event?"),
        )
        alert.add_response("cancel", _("Cancel"))
        alert.add_response("this",   _("This Occurrence"))
        alert.add_response("all",    _("All Occurrences"))
        alert.set_response_appearance("all", Adw.ResponseAppearance.SUGGESTED)
        # v1: per-occurrence editing not yet implemented
        alert.set_response_enabled("this", False)
        alert.connect("response", self._on_recurring_response, event)
        alert.present(self.get_root())

    def _on_recurring_response(
        self, _alert: Adw.AlertDialog, response: str, event: Event
    ) -> None:
        if response == "all":
            self._open_edit_dialog(event)

    def _open_edit_dialog(self, event: Event) -> None:
        from .event_dialog import EventDialog
        dialog = EventDialog(event)
        dialog.connect("saved",   self._on_dialog_saved_edit)
        dialog.connect("deleted", self._on_dialog_deleted)
        dialog.present(self.get_root())

    def _on_dialog_saved_edit(self, _dialog: object, event: Event) -> None:
        self._store.update(event)
        self.refresh()

    def _on_dialog_deleted(self, _dialog: object, event_id: int) -> None:
        self._store.delete(event_id)
        self.refresh()
