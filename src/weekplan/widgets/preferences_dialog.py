from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from ..config import _
from ..services.preferences import PreferencesStore


class PreferencesDialog(Adw.PreferencesDialog):
    def __init__(self, prefs: PreferencesStore) -> None:
        super().__init__()
        self._prefs = prefs
        self.set_title(_("Preferences"))

        page = Adw.PreferencesPage()
        self.add(page)

        group = Adw.PreferencesGroup()
        group.set_title(_("Notifications"))
        page.add(group)

        self._lead_row = Adw.SpinRow.new_with_range(1, 120, 1)
        self._lead_row.set_title(_("Notify before event"))
        self._lead_row.set_subtitle(_("Minutes"))
        self._lead_row.set_value(prefs.lead_time_minutes)
        self._lead_row.connect("notify::value", self._on_value_changed)
        group.add(self._lead_row)

        cal_group = Adw.PreferencesGroup()
        cal_group.set_title(_("Calendar"))
        page.add(cal_group)

        self._week_start_row = Adw.ComboRow()
        self._week_start_row.set_title(_("Week starts on"))
        self._week_start_row.set_model(Gtk.StringList.new([_("Monday"), _("Sunday")]))
        self._week_start_row.set_selected(0 if prefs.week_start_day == 0 else 1)
        self._week_start_row.connect("notify::selected", self._on_week_start_changed)
        cal_group.add(self._week_start_row)

    def _on_value_changed(self, row: Adw.SpinRow, _pspec: object) -> None:
        self._prefs.lead_time_minutes = int(row.get_value())

    def _on_week_start_changed(self, row: Adw.ComboRow, _pspec: object) -> None:
        self._prefs.week_start_day = 0 if row.get_selected() == 0 else 6
