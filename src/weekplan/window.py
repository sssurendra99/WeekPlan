from __future__ import annotations

import threading
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gio, Gtk

from .config import _
from .models.event import Event
from .models.store import EventStore
from .services.preferences import PreferencesStore
from .widgets.week_view import WeekView


class WeekPlanWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        store: EventStore,
        prefs: PreferencesStore,
        google_sync=None,   # Optional[GoogleSync] — avoid circular import at module level
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._store = store
        self._prefs = prefs
        self._google_sync = google_sync

        self.set_default_size(1100, 700)
        self.set_title(_("Week Plan"))

        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        header = Adw.HeaderBar()

        add_btn = Gtk.Button.new_from_icon_name("list-add-symbolic")
        add_btn.set_tooltip_text(_("New event"))
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

        self._week_view = WeekView(store)
        self._toast_overlay = Adw.ToastOverlay()
        self._toast_overlay.set_child(self._week_view)
        toolbar_view.set_content(self._toast_overlay)

    # ------------------------------------------------------------------ event CRUD

    def _on_add_clicked(self, _btn: Gtk.Button) -> None:
        from .widgets.event_dialog import EventDialog
        dialog = EventDialog()
        dialog.connect("saved", self._on_event_created)
        dialog.present(self)

    def _on_event_created(self, _dialog: object, event: Event) -> None:
        self._store.add(event)
        self._week_view.go_to_date(event.start.date())

    def _on_show_preferences(self, _action: Gio.SimpleAction, _param: object) -> None:
        from .widgets.preferences_dialog import PreferencesDialog
        dialog = PreferencesDialog(self._prefs)
        dialog.present(self)

    # ------------------------------------------------------------------ sync

    def trigger_sync(self) -> bool:
        """Start a background sync. Returns GLib.SOURCE_REMOVE (for idle_add compat)."""
        if self._google_sync is None:
            return GLib.SOURCE_REMOVE
        if self._sync_btn and not self._sync_btn.get_sensitive():
            return GLib.SOURCE_REMOVE  # already syncing

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
