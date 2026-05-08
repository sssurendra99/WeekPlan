import logging
import sys
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, GLib, Gio, Gtk

from .config import APP_ID
from .models.store import EventStore
from .services.notifications import NotificationService
from .services.preferences import PreferencesStore
from .window import WeekPlanWindow

log = logging.getLogger(__name__)

_CSS = """
/* ── Navigation row ─────────────────────────────────────────────────── */
.week-nav-row {
    padding: 4px 0;
    border-bottom: 1px solid rgba(127,127,127,0.25);
}

/* ── Header cells (day names + date numbers) ─────────────────────────── */
.day-header-cell {
    padding-top: 8px;
    padding-bottom: 8px;
    border-left: 1px solid rgba(127,127,127,0.2);
    border-bottom: 1px solid rgba(127,127,127,0.4);
}

/* Corner (top-left of the grid, above hour labels) */
.hour-corner {
    border-bottom: 1px solid rgba(127,127,127,0.4);
}

/* ── Hour cells ──────────────────────────────────────────────────────── */
.hour-cell {
    border-left: 1px solid rgba(127,127,127,0.18);
    border-bottom: 1px solid rgba(127,127,127,0.12);
}

/* ── Today badge (circle around today's date number) ─────────────────── */
label.today-badge {
    background-color: @accent_bg_color;
    color: @accent_fg_color;
    border-radius: 50%;
    min-width: 30px;
    min-height: 30px;
    padding: 2px 4px;
}

/* ── Event cards ─────────────────────────────────────────────────────── */
button.event-card {
    padding: 0;
    min-height: 0;
    box-shadow: none;
    border: none;
    outline: none;
}

button.event-card:hover {
    filter: brightness(1.08);
}

button.event-card:focus-visible {
    outline: 2px solid @accent_color;
    outline-offset: -2px;
}
"""


class WeekPlanApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)
        self._started = False

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)   # PyGObject: chain C vfunc explicitly
        provider = Gtk.CssProvider()
        provider.load_from_string(_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)

    def _on_quit(self, _action: Gio.SimpleAction, _param: object) -> None:
        self.release()
        self.quit()

    def do_activate(self) -> None:
        win = self.get_active_window()
        if win is None:
            store = EventStore()
            prefs = PreferencesStore()
            google_sync = self._create_google_sync(store)
            if not self._started:
                self._started = True
                notif_service = NotificationService(self, store, prefs)
                notif_service.start()
                self.hold()
            win = WeekPlanWindow(
                store=store, prefs=prefs, google_sync=google_sync, application=self
            )
            if google_sync is not None:
                GLib.idle_add(win.trigger_sync)
        win.present()

    def _create_google_sync(self, store: EventStore):
        try:
            from .services.google_sync import GoogleSync
            return GoogleSync(store)
        except FileNotFoundError as exc:
            log.info("Google sync unavailable: %s", exc)
            return None


def main() -> int:
    app = WeekPlanApplication()
    return app.run(sys.argv)
