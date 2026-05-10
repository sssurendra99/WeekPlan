# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Sumal Surendra

from __future__ import annotations

import math

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from gi.repository import Adw, GLib, Gtk

from ..config import _
from ..models.event import Event
from ..models.store import EventStore
from ..services.recurrence import expand
from .event_card import EventCard

_DAY_NAMES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
_HOUR_COL_W = 60  # px — width of the hour-label column
_CELL_H = 56  # px — height of each hour row
_MIN_DRAG_PX = 20  # minimum vertical drag to open create dialog


class WeekView(Gtk.Box):
    def __init__(self, store: EventStore, week_start: int = 0) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._store = store
        self._anchor_date: date = date.today()
        self._week_start: int = week_start  # 0 = Monday, 6 = Sunday
        self._event_cards: list[Gtk.Widget] = []
        self._allday_cells: list[Gtk.Box] = []
        self._hour_labels: list[Gtk.Label] = []
        self._on_week_changed: Callable[[date], None] | None = None
        self._on_events_changed: Callable[[], None] | None = None

        # Drag-to-create state
        self._drag_col: int | None = None
        self._drag_start_hour: int = 0
        self._drag_end_hour: int = 1

        self._build_nav()
        self._build_day_header()
        self._build_allday_banner()
        self._build_scroll_area()
        self.refresh()

    # ------------------------------------------------------------------ public

    def set_on_week_changed(self, callback: Callable[[date], None]) -> None:
        self._on_week_changed = callback

    def set_on_events_changed(self, callback: Callable[[], None]) -> None:
        self._on_events_changed = callback

    def set_week_start(self, day: int) -> None:
        if self._week_start == day:
            return
        self._week_start = day
        self._refresh_day_headers()
        self._fill_grid()
        self.refresh()
        self._update_time_indicator()

    def shift_week(self, n: int) -> None:
        self._shift(n)

    def go_today(self) -> None:
        self._go_today()

    def _week_dates(self) -> list[date]:
        if self._week_start == 0:  # Monday
            start = self._anchor_date - timedelta(days=self._anchor_date.weekday())
        else:  # Sunday (week_start == 6)
            start = self._anchor_date - timedelta(days=(self._anchor_date.weekday() + 1) % 7)
        return [start + timedelta(days=i) for i in range(7)]

    def go_to_date(self, d: date) -> None:
        self._anchor_date = d
        self._refresh_nav_label()
        self._refresh_day_headers()
        self._fill_grid()
        self.refresh()
        self._update_time_indicator()

    def refresh(self) -> None:
        """Remove and re-create all event cards using time-aware mode detection."""
        for card in self._event_cards:
            self._grid.remove(card)
        self._event_cards.clear()

        for cell in self._allday_cells:
            while (child := cell.get_first_child()) is not None:
                cell.remove(child)

        dates = self._week_dates()
        week_start_dt = datetime(dates[0].year, dates[0].month, dates[0].day, tzinfo=UTC)
        week_end_dt = datetime(
            dates[-1].year, dates[-1].month, dates[-1].day, tzinfo=UTC
        ) + timedelta(days=1)

        events = self._store.list_in_range(week_start_dt, week_end_dt)
        date_to_col = {d: i + 1 for i, d in enumerate(dates)}
        now = datetime.now(UTC)
        today = date.today()

        # All-day events → banner row
        for event in events:
            if not event.all_day:
                continue
            for occ_start, _occ_end in expand(event, week_start_dt, week_end_dt):
                d = occ_start.date()
                if d not in date_to_col:
                    continue
                col_idx = date_to_col[d] - 1
                btn = Gtk.Button(label=event.title)
                btn.add_css_class("wp-allday-tag")
                btn.add_css_class(f"color-{event.color}")
                btn.connect("clicked", lambda _b, e=event: self._on_edit_event(e))
                self._allday_cells[col_idx].append(btn)

        # Timed events → hour grid
        # Pass 1: collect occurrences and find next-up event on today
        occurrences: list[tuple[Event, datetime, datetime]] = []
        next_up_start: datetime | None = None
        next_up_event_id: int | None = None

        for event in events:
            if event.all_day:
                continue
            for occ_start, occ_end in expand(event, week_start_dt, week_end_dt):
                if occ_start.date() not in date_to_col:
                    continue
                occurrences.append((event, occ_start, occ_end))
                if (
                    occ_start.date() == today
                    and occ_start > now
                    and (next_up_start is None or occ_start < next_up_start)
                ):
                    next_up_start = occ_start
                    next_up_event_id = event.id

        # Pass 2: create cards with the appropriate mode
        for event, occ_start, occ_end in occurrences:
            occ_date = occ_start.date()
            col = date_to_col[occ_date]
            grid_row = occ_start.hour
            secs = (occ_end - occ_start).total_seconds()
            row_span = max(1, math.ceil(secs / 3600))

            if occ_date == today:
                if occ_start <= now < occ_end:
                    mode = "live"
                elif occ_end <= now:
                    mode = "past"
                elif occ_start == next_up_start and event.id == next_up_event_id:
                    mode = "solid"
                else:
                    mode = "tinted"
            else:
                mode = "tinted"

            card = EventCard(
                event,
                occ_start,
                occ_end,
                self._on_edit_event,
                mode=mode,
                on_resize=self._on_event_resize,
            )
            self._grid.attach(card, col, grid_row, 1, row_span)
            self._event_cards.append(card)

        has_events = bool(self._event_cards) or any(
            c.get_first_child() is not None for c in self._allday_cells
        )
        self._content_stack.set_visible_child_name("grid" if has_events else "empty")

    # ------------------------------------------------------------------ build

    def _build_nav(self) -> None:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        row.set_halign(Gtk.Align.CENTER)
        row.add_css_class("week-nav-row")

        prev = Gtk.Button(label="‹")  # noqa: RUF001
        prev.add_css_class("flat")
        prev.add_css_class("nav-arrow")
        prev.connect("clicked", lambda _: self._shift(-1))

        self._nav_btn = Gtk.Button()
        self._nav_btn.add_css_class("flat")
        self._nav_btn.add_css_class("week-nav-label")
        self._nav_btn.set_tooltip_text(_("Go to today"))
        self._nav_btn.connect("clicked", lambda _: self._go_today())
        self._refresh_nav_label()

        nxt = Gtk.Button(label="›")  # noqa: RUF001
        nxt.add_css_class("flat")
        nxt.add_css_class("nav-arrow")
        nxt.connect("clicked", lambda _: self._shift(1))

        row.append(prev)
        row.append(self._nav_btn)
        row.append(nxt)
        self.append(row)

    def _build_day_header(self) -> None:
        """Non-scrolling header row with day names and date numbers."""
        self._header_grid = Gtk.Grid()
        self._header_grid.add_css_class("week-header-bar")

        corner = Gtk.Box()
        corner.set_size_request(_HOUR_COL_W, -1)
        corner.add_css_class("header-corner-spacer")
        self._header_grid.attach(corner, 0, 0, 1, 1)

        self._day_header_cells: list[Gtk.Box] = []
        for i in range(7):
            cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            cell.set_hexpand(True)
            cell.set_halign(Gtk.Align.FILL)
            cell.add_css_class("day-header-cell")
            self._header_grid.attach(cell, i + 1, 0, 1, 1)
            self._day_header_cells.append(cell)

        self.append(self._header_grid)
        self._refresh_day_headers()

    def _build_allday_banner(self) -> None:
        self._allday_banner = Gtk.Grid()
        self._allday_banner.add_css_class("wp-allday-banner")

        corner = Gtk.Box()
        corner.set_size_request(_HOUR_COL_W, -1)
        self._allday_banner.attach(corner, 0, 0, 1, 1)

        self._allday_cells = []
        for i in range(7):
            cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            cell.set_hexpand(True)
            cell.set_margin_top(3)
            cell.set_margin_bottom(3)
            cell.set_margin_start(2)
            cell.set_margin_end(2)
            cell.add_css_class("wp-allday-cell")
            self._allday_banner.attach(cell, i + 1, 0, 1, 1)
            self._allday_cells.append(cell)

        self.append(self._allday_banner)

    def _build_scroll_area(self) -> None:
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_vexpand(True)
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._scroll.set_overlay_scrolling(True)

        self._grid = Gtk.Grid()
        self._fill_grid()

        self._time_indicator = self._make_time_indicator()

        # Drag-to-create preview (hidden by default)
        self._drag_preview = Gtk.Box()
        self._drag_preview.add_css_class("wp-drag-preview")
        self._drag_preview.set_valign(Gtk.Align.START)
        self._drag_preview.set_halign(Gtk.Align.START)
        self._drag_preview.set_can_target(False)
        self._drag_preview.set_visible(False)

        self._grid_overlay = Gtk.Overlay()
        self._grid_overlay.set_child(self._grid)
        self._grid_overlay.add_overlay(self._time_indicator)
        self._grid_overlay.add_overlay(self._drag_preview)

        # Drag gesture for creating new events
        drag = Gtk.GestureDrag()
        drag.set_button(1)
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self._grid_overlay.add_controller(drag)

        self._scroll.set_child(self._grid_overlay)

        self._empty_state = Adw.StatusPage()
        self._empty_state.set_icon_name("x-office-calendar-symbolic")
        self._empty_state.set_title(_("A clean week ahead"))
        self._empty_state.set_description(_("Press Ctrl+N or click + to add an event"))
        self._empty_state.set_vexpand(True)

        self._content_stack = Gtk.Stack()
        self._content_stack.set_vexpand(True)
        self._content_stack.add_named(self._scroll, "grid")
        self._content_stack.add_named(self._empty_state, "empty")
        self.append(self._content_stack)

        self._scroll.connect("map", self._on_first_map)
        self._update_time_indicator()
        GLib.timeout_add(60_000, self._update_time_indicator)

    # ------------------------------------------------------------------ header refresh

    def _refresh_day_headers(self) -> None:
        dates = self._week_dates()
        today = date.today()
        for cell, d in zip(self._day_header_cells, dates, strict=False):
            while (child := cell.get_first_child()) is not None:
                cell.remove(child)

            name_lbl = Gtk.Label(label=d.strftime("%a").upper()[:3])
            name_lbl.set_halign(Gtk.Align.CENTER)
            name_lbl.add_css_class("wp-day-name")
            if d == today:
                name_lbl.add_css_class("today")

            date_lbl = Gtk.Label(label=str(d.day))
            date_lbl.set_halign(Gtk.Align.CENTER)
            date_lbl.add_css_class("wp-day-number")
            if d == today:
                date_lbl.add_css_class("today")

            cell.append(name_lbl)
            cell.append(date_lbl)

    # ------------------------------------------------------------------ grid

    def _fill_grid(self) -> None:
        self._event_cards.clear()
        self._hour_labels.clear()
        while (child := self._grid.get_first_child()) is not None:
            self._grid.remove(child)

        dates = self._week_dates()
        today = date.today()

        for hour in range(24):
            lbl = Gtk.Label(label=f"{hour:02d}")
            lbl.set_halign(Gtk.Align.END)
            lbl.set_valign(Gtk.Align.START)
            lbl.add_css_class("wp-hour-label")
            lbl.set_size_request(_HOUR_COL_W, _CELL_H)
            self._grid.attach(lbl, 0, hour, 1, 1)
            self._hour_labels.append(lbl)

            for col in range(1, 8):
                cell = Gtk.Box()
                cell.set_hexpand(True)
                cell.set_size_request(-1, _CELL_H)
                cell.add_css_class("wp-hour-cell")
                if hour % 2 == 1:
                    cell.add_css_class("alt-hour")
                if dates[col - 1].weekday() >= 5:
                    cell.add_css_class("weekend-cell")
                if dates[col - 1] == today:
                    cell.add_css_class("today-cell")
                self._grid.attach(cell, col, hour, 1, 1)

    # ------------------------------------------------------------------ time indicator

    def _make_time_indicator(self) -> Gtk.Box:
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        container.set_valign(Gtk.Align.START)
        container.set_halign(Gtk.Align.FILL)
        container.set_hexpand(True)
        container.set_can_target(False)

        dot = Gtk.Box()
        dot.add_css_class("wp-now-dot")
        dot.set_valign(Gtk.Align.CENTER)
        dot.set_margin_start(_HOUR_COL_W - 5)

        line = Gtk.Box()
        line.set_hexpand(True)
        line.set_valign(Gtk.Align.CENTER)
        line.add_css_class("wp-now-line")

        container.append(dot)
        container.append(line)
        return container

    def _update_time_indicator(self) -> bool:
        now_hour = datetime.now().hour

        for i, lbl in enumerate(self._hour_labels):
            if i == now_hour:
                lbl.add_css_class("now")
            else:
                lbl.remove_css_class("now")

        if date.today() in self._week_dates():
            self._time_indicator.set_visible(True)
            now = datetime.now()
            y = int((now.hour + now.minute / 60.0) * _CELL_H)
            self._time_indicator.set_margin_top(max(0, y - 5))
        else:
            self._time_indicator.set_visible(False)
        return GLib.SOURCE_CONTINUE

    # ------------------------------------------------------------------ drag to create

    def _xy_to_col_hour(self, x: float, y: float) -> tuple[int, int] | None:
        if x < _HOUR_COL_W:
            return None
        alloc_w = self._grid.get_allocation().width
        col_w = (alloc_w - _HOUR_COL_W) / 7
        if col_w <= 0:
            return None
        col = int((x - _HOUR_COL_W) / col_w)
        hour = int(y / _CELL_H)
        if col < 0 or col >= 7 or hour < 0 or hour >= 24:
            return None
        return col, hour

    def _on_drag_begin(self, gesture: Gtk.GestureDrag, start_x: float, start_y: float) -> None:
        result = self._xy_to_col_hour(start_x, start_y)
        if result is None:
            gesture.set_sequence_state(
                gesture.get_current_sequence(), Gtk.EventSequenceState.DENIED
            )
            self._drag_col = None
            return
        self._drag_col, self._drag_start_hour = result
        self._drag_end_hour = min(self._drag_start_hour + 1, 24)
        self._show_drag_preview()

    def _on_drag_update(self, gesture: Gtk.GestureDrag, offset_x: float, offset_y: float) -> None:
        if self._drag_col is None:
            return
        ok, _sx, sy = gesture.get_start_point()
        if not ok:
            return
        end_hour = max(self._drag_start_hour + 1, math.ceil((sy + offset_y) / _CELL_H))
        self._drag_end_hour = min(end_hour, 24)
        self._show_drag_preview()

    def _on_drag_end(self, gesture: Gtk.GestureDrag, offset_x: float, offset_y: float) -> None:
        if self._drag_col is None:
            return
        self._drag_preview.set_visible(False)

        # Ignore tiny drags (misclicks)
        if abs(offset_y) < _MIN_DRAG_PX and abs(offset_x) < _MIN_DRAG_PX:
            self._drag_col = None
            return

        dates = self._week_dates()
        drag_date = dates[self._drag_col]
        default_start = datetime(
            drag_date.year,
            drag_date.month,
            drag_date.day,
            self._drag_start_hour,
            0,
            tzinfo=UTC,
        )
        default_end = datetime(
            drag_date.year,
            drag_date.month,
            drag_date.day,
            min(self._drag_end_hour, 23),
            0,
            tzinfo=UTC,
        )
        if default_end <= default_start:
            default_end = default_start + timedelta(hours=1)

        self._drag_col = None

        from .event_dialog import EventDialog

        dialog = EventDialog(default_start=default_start, default_end=default_end)
        dialog.connect("saved", self._on_dialog_saved_new)
        dialog.present(self.get_root())

    def _show_drag_preview(self) -> None:
        if self._drag_col is None:
            self._drag_preview.set_visible(False)
            return
        alloc_w = self._grid.get_allocation().width
        col_w = (alloc_w - _HOUR_COL_W) / 7
        if col_w <= 0:
            return
        margin_top = self._drag_start_hour * _CELL_H
        margin_start = int(_HOUR_COL_W + self._drag_col * col_w) + 3
        margin_end = max(3, int(alloc_w - margin_start - col_w) + 3)
        height = max(4, (self._drag_end_hour - self._drag_start_hour) * _CELL_H - 4)
        self._drag_preview.set_margin_top(margin_top)
        self._drag_preview.set_margin_start(margin_start)
        self._drag_preview.set_margin_end(margin_end)
        self._drag_preview.set_size_request(-1, height)
        self._drag_preview.set_visible(True)

    # ------------------------------------------------------------------ event resize

    def _on_event_resize(self, event: Event, delta_px: float) -> None:
        if abs(delta_px) < 4:
            return
        new_end = event.end + timedelta(hours=delta_px / _CELL_H)
        # Round to nearest 30 minutes
        total_min = new_end.hour * 60 + new_end.minute
        rounded = round(total_min / 30) * 30
        rounded = max(0, min(rounded, 23 * 60 + 30))
        new_end = new_end.replace(hour=rounded // 60, minute=rounded % 60, second=0, microsecond=0)
        if new_end <= event.start:
            new_end = event.start + timedelta(minutes=30)
        event.end = new_end
        event.updated_at = datetime.now(UTC)
        self._store.update(event)
        self.refresh()

    # ------------------------------------------------------------------ scroll

    def _on_first_map(self, scroll: Gtk.ScrolledWindow) -> None:
        scroll.disconnect_by_func(self._on_first_map)
        GLib.idle_add(self._scroll_to_8am)

    def _scroll_to_8am(self) -> bool:
        vadj = self._scroll.get_vadjustment()
        target = 8 * _CELL_H
        vadj.set_value(max(0.0, min(target, vadj.get_upper() - vadj.get_page_size())))
        return GLib.SOURCE_REMOVE

    # ------------------------------------------------------------------ nav

    def _refresh_nav_label(self) -> None:
        dates = self._week_dates()
        s, e = dates[0], dates[-1]
        if s.month == e.month and s.year == e.year:
            label = f"{s.strftime('%b %-d')}–{e.strftime('%-d, %Y')}"  # noqa: RUF001
        elif s.year == e.year:
            label = f"{s.strftime('%b %-d')} – {e.strftime('%b %-d, %Y')}"  # noqa: RUF001
        else:
            label = f"{s.strftime('%b %-d, %Y')} – {e.strftime('%b %-d, %Y')}"  # noqa: RUF001
        self._nav_btn.set_label(label)
        if self._on_week_changed:
            self._on_week_changed(dates[0])

    def _shift(self, weeks: int) -> None:
        self._anchor_date += timedelta(weeks=weeks)
        self._refresh_nav_label()
        self._refresh_day_headers()
        self._fill_grid()
        self.refresh()
        self._update_time_indicator()

    def _go_today(self) -> None:
        self._anchor_date = date.today()
        self._refresh_nav_label()
        self._refresh_day_headers()
        self._fill_grid()
        self.refresh()
        self._update_time_indicator()

    # ------------------------------------------------------------------ event editing

    def _on_dialog_saved_new(self, _dialog: object, event: Event) -> None:
        self._store.add(event)
        self.go_to_date(event.start.date())
        if self._on_events_changed:
            self._on_events_changed()

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
        alert.add_response("this", _("This Occurrence"))
        alert.add_response("all", _("All Occurrences"))
        alert.set_response_appearance("all", Adw.ResponseAppearance.SUGGESTED)
        alert.set_response_enabled("this", False)
        alert.connect("response", self._on_recurring_response, event)
        alert.present(self.get_root())

    def _on_recurring_response(self, _alert: Adw.AlertDialog, response: str, event: Event) -> None:
        if response == "all":
            self._open_edit_dialog(event)

    def _open_edit_dialog(self, event: Event) -> None:
        from .event_dialog import EventDialog

        dialog = EventDialog(event)
        dialog.connect("saved", self._on_dialog_saved_edit)
        dialog.connect("deleted", self._on_dialog_deleted)
        dialog.present(self.get_root())

    def _on_dialog_saved_edit(self, _dialog: object, event: Event) -> None:
        self._store.update(event)
        self.refresh()
        if self._on_events_changed:
            self._on_events_changed()

    def _on_dialog_deleted(self, _dialog: object, event_id: int) -> None:
        self._store.delete(event_id)
        self.refresh()
        if self._on_events_changed:
            self._on_events_changed()
