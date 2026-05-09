from __future__ import annotations

import threading
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, Gio, Gtk, Pango

from .config import _
from .models.event import Event
from .models.store import EventStore
from .services.preferences import PreferencesStore
from .services.recurrence import expand
from .widgets.week_view import WeekView


class WeekPlanWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        store: EventStore,
        prefs: PreferencesStore,
        google_sync=None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._store = store
        self._prefs = prefs
        self._google_sync = google_sync
        self._syncing_cal = False

        self.set_default_size(1200, 700)
        self.set_title(_("Week Plan"))

        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # ── Header bar ────────────────────────────────────────────────
        header = Adw.HeaderBar()

        add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
        add_btn.set_tooltip_text(_("New event  (N)"))
        add_btn.connect("clicked", self._on_add_clicked)
        header.pack_end(add_btn)

        if google_sync is not None:
            self._sync_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
            self._sync_btn.set_tooltip_text(_("Sync with Google Calendar"))
            self._sync_btn.connect("clicked", lambda _: self.trigger_sync())
            header.pack_end(self._sync_btn)
        else:
            self._sync_btn = None

        menu_model = Gio.Menu()
        menu_model.append(_("Preferences"), "win.show-preferences")
        menu_model.append(_("Quit"), "app.quit")

        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_menu_model(menu_model)
        header.pack_end(menu_btn)

        toolbar_view.add_top_bar(header)

        show_prefs_action = Gio.SimpleAction.new("show-preferences", None)
        show_prefs_action.connect("activate", self._on_show_preferences)
        self.add_action(show_prefs_action)

        # ── Week view ─────────────────────────────────────────────────
        self._week_view = WeekView(store, week_start=prefs.week_start_day)
        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(self._week_view)
        self._toast_overlay.set_hexpand(True)

        # ── Mini calendar sidebar ──────────────────────────────────────
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        sidebar.add_css_class("wp-sidebar")
        sidebar.set_hexpand(False)
        sidebar.set_size_request(210, -1)

        self._mini_cal = Gtk.Calendar()
        self._mini_cal.set_hexpand(False)
        sidebar.append(self._mini_cal)

        sep = Gtk.Separator()
        sep.set_margin_top(4)
        sidebar.append(sep)

        upcoming_lbl = Gtk.Label(label=_("Today"))
        upcoming_lbl.set_halign(Gtk.Align.START)
        upcoming_lbl.set_margin_start(4)
        upcoming_lbl.add_css_class("wp-sidebar-section-title")
        sidebar.append(upcoming_lbl)

        upcoming_scroll = Gtk.ScrolledWindow()
        upcoming_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        upcoming_scroll.set_vexpand(True)

        self._upcoming_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        upcoming_scroll.set_child(self._upcoming_box)
        sidebar.append(upcoming_scroll)

        # ── Body = sidebar + week view ────────────────────────────────
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        body.append(sidebar)
        body.append(self._toast_overlay)
        toolbar_view.set_content(body)

        # Wire up mini cal ↔ week view sync
        self._week_view.set_on_week_changed(self._on_week_changed_by_view)
        self._mini_cal.connect("day-selected", self._on_mini_cal_day_selected)
        prefs.on_changed(self._on_prefs_changed)

        self._week_view.set_on_events_changed(self._refresh_upcoming)
        self._refresh_upcoming()
        # Initialise mini cal to current week's Monday
        monday = date.today() - timedelta(days=date.today().weekday())
        self._sync_mini_cal_to(monday)

        # ── Keyboard shortcuts ────────────────────────────────────────
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

    # ------------------------------------------------------------------ keyboard

    def _on_key_pressed(
        self,
        _controller: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        if state & Gdk.ModifierType.CONTROL_MASK:
            return False
        if keyval == Gdk.KEY_n:
            self._on_add_clicked(None)
            return True
        if keyval == Gdk.KEY_t:
            self._week_view.go_today()
            return True
        if keyval == Gdk.KEY_Left:
            self._week_view.shift_week(-1)
            return True
        if keyval == Gdk.KEY_Right:
            self._week_view.shift_week(1)
            return True
        return False

    # ------------------------------------------------------------------ mini cal sync

    def _sync_mini_cal_to(self, monday: date) -> None:
        self._syncing_cal = True
        gdt = GLib.DateTime.new_local(monday.year, monday.month, monday.day, 0, 0, 0.0)
        self._mini_cal.select_day(gdt)
        self._syncing_cal = False

    def _on_week_changed_by_view(self, monday: date) -> None:
        self._sync_mini_cal_to(monday)

    def _on_mini_cal_day_selected(self, cal: Gtk.Calendar) -> None:
        if self._syncing_cal:
            return
        gdt = cal.get_date()
        d = date(gdt.get_year(), gdt.get_month(), gdt.get_day_of_month())
        self._week_view.go_to_date(d)

    # ------------------------------------------------------------------ event CRUD

    def _on_add_clicked(self, _btn) -> None:
        from .widgets.event_dialog import EventDialog
        dialog = EventDialog()
        dialog.connect("saved", self._on_event_created)
        dialog.present(self)

    def _on_event_created(self, _dialog: object, event: Event) -> None:
        self._store.add(event)
        self._week_view.go_to_date(event.start.date())
        self._refresh_upcoming()

    def _on_prefs_changed(self) -> None:
        self._week_view.set_week_start(self._prefs.week_start_day)

    def _refresh_upcoming(self) -> None:
        while (child := self._upcoming_box.get_first_child()) is not None:
            self._upcoming_box.remove(child)

        today = date.today()
        day_start = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
        day_end   = day_start + timedelta(days=1)
        events = self._store.list_in_range(day_start, day_end)

        occurrences: list[tuple[datetime, Event]] = []
        for event in events:
            for occ_start, _occ_end in expand(event, day_start, day_end):
                occurrences.append((occ_start, event))
        occurrences.sort(key=lambda x: x[0])

        for occ_start, event in occurrences[:10]:
            self._upcoming_box.append(self._make_upcoming_row(event, occ_start))

        if not occurrences:
            empty = Gtk.Label(label=_("Nothing today"))
            empty.set_halign(Gtk.Align.CENTER)
            empty.set_margin_top(12)
            empty.add_css_class("wp-sidebar-empty")
            self._upcoming_box.append(empty)

    def _make_upcoming_row(self, event: Event, occ_start: datetime) -> Gtk.Widget:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.add_css_class("wp-upcoming-row")

        dot = Gtk.Box()
        dot.set_valign(Gtk.Align.CENTER)
        dot.add_css_class("wp-upcoming-dot")
        dot.add_css_class(f"color-{event.color}")
        row.append(dot)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        info.set_hexpand(True)

        title = Gtk.Label(label=event.title)
        title.set_halign(Gtk.Align.START)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.set_max_width_chars(18)
        title.add_css_class("wp-upcoming-title")
        info.append(title)

        local_start = occ_start.astimezone()
        if event.all_day:
            date_str = _("All day")
        else:
            date_str = local_start.strftime("%H:%M")

        time_lbl = Gtk.Label(label=date_str)
        time_lbl.set_halign(Gtk.Align.START)
        time_lbl.add_css_class("wp-upcoming-time")
        info.append(time_lbl)

        row.append(info)
        return row

    def _on_show_preferences(self, _action: Gio.SimpleAction, _param: object) -> None:
        from .widgets.preferences_dialog import PreferencesDialog
        dialog = PreferencesDialog(self._prefs)
        dialog.present(self)

    # ------------------------------------------------------------------ sync

    def trigger_sync(self) -> bool:
        if self._google_sync is None:
            return GLib.SOURCE_REMOVE
        if self._sync_btn and not self._sync_btn.get_sensitive():
            return GLib.SOURCE_REMOVE

        if self._sync_btn:
            spinner = Gtk.Spinner()
            spinner.start()
            self._sync_btn.set_child(spinner)
            self._sync_btn.set_sensitive(False)

        threading.Thread(target=self._do_sync, daemon=True).start()
        return GLib.SOURCE_REMOVE

    def _do_sync(self) -> None:
        try:
            self._google_sync.authenticate()
            n = self._google_sync.sync()
            GLib.idle_add(self._on_sync_done, n, None)
        except Exception as exc:
            GLib.idle_add(self._on_sync_done, 0, exc)

    def _on_sync_done(self, n: int, error: Optional[Exception]) -> bool:
        self._restore_sync_btn()
        if error is None:
            self._week_view.refresh()
            msg = _("Synced {n} events").format(n=n)
        else:
            short = str(error).split("\n")[0][:120]
            msg = _("Sync failed: {error}").format(error=short)
        self._toast_overlay.add_toast(Adw.Toast.new(msg))
        return GLib.SOURCE_REMOVE

    def _restore_sync_btn(self) -> None:
        if self._sync_btn is None:
            return
        icon = Gtk.Image.new_from_icon_name("view-refresh-symbolic")
        self._sync_btn.set_child(icon)
        self._sync_btn.set_sensitive(True)
