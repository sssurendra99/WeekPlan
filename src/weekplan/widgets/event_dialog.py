# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Sumal Surendra

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from datetime import UTC, date, datetime

from gi.repository import Adw, GObject, Gtk

from ..config import _
from ..models.event import Event

_REPEAT_OPTIONS: list[tuple[str, str | None]] = [
    ("Does not repeat", None),
    ("Daily", "FREQ=DAILY"),
    ("Weekly", "FREQ=WEEKLY"),
    ("Weekdays only", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"),
    ("Custom (RRULE)", None),  # user types the string themselves
]
_CUSTOM_IDX = len(_REPEAT_OPTIONS) - 1

_PRESET_COLORS: list[tuple[str, str]] = [
    ("sky", "Sky"),
    ("sage", "Sage"),
    ("amber", "Amber"),
    ("coral", "Coral"),
    ("lavender", "Lavender"),
    ("rose", "Rose"),
    ("teal", "Teal"),
    ("slate", "Slate"),
]


class EventDialog(Adw.Dialog):
    __gsignals__ = {  # noqa: RUF012
        "saved": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,)),
        "deleted": (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    def __init__(
        self,
        event: Event | None = None,
        default_start: datetime | None = None,
        default_end: datetime | None = None,
    ) -> None:
        super().__init__()
        self._event = event
        is_edit = event is not None

        self.set_title(_("Edit Event") if is_edit else _("New Event"))
        self.set_content_width(420)

        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)

        # ---- Header bar ----
        header = Adw.HeaderBar()
        header.set_show_start_title_buttons(False)
        header.set_show_end_title_buttons(False)

        cancel_btn = Gtk.Button(label=_("Cancel"))
        cancel_btn.add_css_class("flat")
        cancel_btn.connect("clicked", lambda _: self.close())
        header.pack_start(cancel_btn)

        if is_edit:
            del_btn = Gtk.Button(label=_("Delete"))
            del_btn.add_css_class("destructive-action")
            del_btn.connect("clicked", self._on_delete)
            header.pack_start(del_btn)

        save_btn = Gtk.Button(label=_("Save"))
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        header.pack_end(save_btn)

        toolbar_view.add_top_bar(header)

        # ---- Content — ScrolledWindow lets dialog fit in small windows ----
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(8)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_propagate_natural_height(True)
        scroll.set_max_content_height(560)
        scroll.set_child(content)
        toolbar_view.set_content(scroll)

        # ── Group 1: Title ────────────────────────────────────────────
        title_group = Adw.PreferencesGroup()
        self._title_row = Adw.EntryRow()
        self._title_row.set_title(_("Title"))
        title_group.add(self._title_row)
        content.append(title_group)

        # ── Group 2: Date & Time ──────────────────────────────────────
        dt_group = Adw.PreferencesGroup()
        dt_group.set_title(_("Date and Time"))

        init_date = default_start.date() if default_start else date.today()
        init_start_h = default_start.hour if default_start else 9
        init_start_m = default_start.minute if default_start else 0
        init_end_h = default_end.hour if default_end else 10
        init_end_m = default_end.minute if default_end else 0

        # All-day switch
        self._allday_row = Adw.SwitchRow()
        self._allday_row.set_title(_("All day"))
        self._allday_row.connect("notify::active", self._on_allday_toggled)
        dt_group.add(self._allday_row)

        self._year_spin = self._make_spin(2000, 2100, value=init_date.year, width=5)
        self._month_spin = self._make_spin(1, 12, value=init_date.month, width=2)
        self._day_spin = self._make_spin(1, 31, value=init_date.day, width=2)
        dt_group.add(
            self._make_dt_row(
                _("Date"), self._joined(self._year_spin, "/", self._month_spin, "/", self._day_spin)
            )
        )

        self._start_h = self._make_spin(0, 23, value=init_start_h, width=2)
        self._start_m = self._make_spin(0, 59, step=5, value=init_start_m, width=2)
        self._start_row = self._make_dt_row(
            _("Start"), self._joined(self._start_h, ":", self._start_m)
        )
        dt_group.add(self._start_row)

        self._end_h = self._make_spin(0, 23, value=init_end_h, width=2)
        self._end_m = self._make_spin(0, 59, step=5, value=init_end_m, width=2)
        self._end_row = self._make_dt_row(_("End"), self._joined(self._end_h, ":", self._end_m))
        dt_group.add(self._end_row)

        content.append(dt_group)

        # ── Group 3: Recurrence ───────────────────────────────────────
        recur_group = Adw.PreferencesGroup()
        recur_group.set_title(_("Recurrence"))

        self._repeat_row = Adw.ComboRow()
        self._repeat_row.set_title(_("Repeat"))
        self._repeat_row.set_model(Gtk.StringList.new([label for label, _ in _REPEAT_OPTIONS]))
        self._repeat_row.connect("notify::selected", self._on_repeat_changed)
        recur_group.add(self._repeat_row)

        self._custom_rrule_row = Adw.EntryRow()
        self._custom_rrule_row.set_title(_("RRULE string"))
        self._custom_rrule_row.set_show_apply_button(False)
        self._custom_rrule_row.set_visible(False)
        recur_group.add(self._custom_rrule_row)

        content.append(recur_group)

        # ── Group 4: Color ────────────────────────────────────────────
        color_group = Adw.PreferencesGroup()
        color_group.set_title(_("Appearance"))
        self._color_row = Adw.ComboRow()
        self._color_row.set_title(_("Color"))
        self._color_row.set_model(Gtk.StringList.new([name for _, name in _PRESET_COLORS]))
        color_group.add(self._color_row)
        content.append(color_group)

        # ── Group 5: Notes ────────────────────────────────────────────
        desc_group = Adw.PreferencesGroup()
        desc_group.set_title(_("Notes"))
        self._desc_view = Gtk.TextView()
        self._desc_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._desc_view.set_accepts_tab(False)
        self._desc_view.add_css_class("card")
        desc_sw = Gtk.ScrolledWindow()
        desc_sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        desc_sw.set_min_content_height(70)
        desc_sw.set_margin_top(4)
        desc_sw.set_margin_bottom(4)
        desc_sw.set_child(self._desc_view)
        desc_group.add(desc_sw)
        content.append(desc_group)

        # ── Populate edit mode ────────────────────────────────────────
        if is_edit:
            self._populate(event)

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _make_dt_row(title: str, content: Gtk.Widget) -> Adw.PreferencesRow:
        """Row with a left label (hexpand) and right content — avoids Adw suffix squish."""
        row = Adw.PreferencesRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(16)
        box.set_margin_end(12)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        lbl = Gtk.Label(label=title)
        lbl.set_halign(Gtk.Align.START)
        lbl.set_hexpand(True)
        box.append(lbl)
        box.append(content)
        row.set_child(box)
        return row

    @staticmethod
    def _make_spin(
        lower: int, upper: int, *, value: int = 0, step: int = 1, width: int = 2
    ) -> Gtk.SpinButton:
        adj = Gtk.Adjustment.new(value, lower, upper, step, step, 0)
        spin = Gtk.SpinButton()
        spin.set_adjustment(adj)
        spin.set_numeric(True)
        spin.set_snap_to_ticks(True)
        spin.set_width_chars(width)
        spin.set_max_width_chars(width)
        spin.set_hexpand(False)  # GtkEntry subclass defaults hexpand=True; override it
        return spin

    @staticmethod
    def _joined(*items: Gtk.Widget | str) -> Gtk.Box:
        """Build a horizontal box alternating widgets and separator labels."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_valign(Gtk.Align.CENTER)
        box.set_hexpand(False)  # prevent suffix from stealing title-label space
        box.set_halign(Gtk.Align.END)
        for item in items:
            if isinstance(item, str):
                box.append(Gtk.Label(label=item))
            else:
                box.append(item)
        return box

    def _on_repeat_changed(self, combo: Adw.ComboRow, _pspec: object) -> None:
        self._custom_rrule_row.set_visible(combo.get_selected() == _CUSTOM_IDX)

    def _on_allday_toggled(self, row: Adw.SwitchRow, _pspec: object) -> None:
        is_allday = row.get_active()
        self._start_row.set_visible(not is_allday)
        self._end_row.set_visible(not is_allday)

    def _populate(self, event: Event) -> None:
        self._title_row.set_text(event.title)

        d = event.start.date()
        self._year_spin.set_value(d.year)
        self._month_spin.set_value(d.month)
        self._day_spin.set_value(d.day)

        self._allday_row.set_active(event.all_day)
        self._start_row.set_visible(not event.all_day)
        self._end_row.set_visible(not event.all_day)

        self._start_h.set_value(event.start.hour)
        self._start_m.set_value(event.start.minute)
        self._end_h.set_value(event.end.hour)
        self._end_m.set_value(event.end.minute)

        # Recurrence
        if event.rrule is None:
            self._repeat_row.set_selected(0)
        else:
            matched = False
            for i, (_, rule_str) in enumerate(_REPEAT_OPTIONS[:-1]):  # skip Custom
                if rule_str and rule_str.upper() == event.rrule.upper():
                    self._repeat_row.set_selected(i)
                    matched = True
                    break
            if not matched:
                self._repeat_row.set_selected(_CUSTOM_IDX)
                self._custom_rrule_row.set_text(event.rrule)
                self._custom_rrule_row.set_visible(True)

        for i, (name, _) in enumerate(_PRESET_COLORS):
            if name == event.color:
                self._color_row.set_selected(i)
                break

        if event.description:
            self._desc_view.get_buffer().set_text(event.description)

    def _build_event(self) -> Event | None:
        title = self._title_row.get_text().strip()
        if not title:
            return None

        try:
            d = date(
                self._year_spin.get_value_as_int(),
                self._month_spin.get_value_as_int(),
                self._day_spin.get_value_as_int(),
            )
        except ValueError:
            return None

        all_day = self._allday_row.get_active()
        if all_day:
            from datetime import timedelta

            start_dt = datetime(d.year, d.month, d.day, 0, 0, tzinfo=UTC)
            end_dt = start_dt + timedelta(hours=23, minutes=59)
        else:
            sh, sm = self._start_h.get_value_as_int(), self._start_m.get_value_as_int()
            eh, em = self._end_h.get_value_as_int(), self._end_m.get_value_as_int()
            start_dt = datetime(d.year, d.month, d.day, sh, sm, tzinfo=UTC)
            end_dt = datetime(d.year, d.month, d.day, eh, em, tzinfo=UTC)
            if end_dt <= start_dt:
                return None

        color = _PRESET_COLORS[self._color_row.get_selected()][0]
        buf = self._desc_view.get_buffer()
        desc = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)

        # Recurrence
        sel = self._repeat_row.get_selected()
        if sel == _CUSTOM_IDX:
            rrule: str | None = self._custom_rrule_row.get_text().strip() or None
        else:
            rrule = _REPEAT_OPTIONS[sel][1]

        if self._event is not None:
            self._event.title = title
            self._event.start = start_dt
            self._event.end = end_dt
            self._event.color = color
            self._event.all_day = all_day
            self._event.description = desc
            self._event.rrule = rrule
            self._event.updated_at = datetime.now(UTC)
            return self._event

        return Event(
            title=title,
            start=start_dt,
            end=end_dt,
            color=color,
            all_day=all_day,
            description=desc,
            rrule=rrule,
        )

    # ------------------------------------------------------------------ signal handlers

    def _on_save(self, _btn: Gtk.Button) -> None:
        event = self._build_event()
        if event is None:
            return
        self.emit("saved", event)
        self.close()

    def _on_delete(self, _btn: Gtk.Button) -> None:
        self.emit("deleted", self._event.id)
        self.close()
