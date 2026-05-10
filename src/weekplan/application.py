import logging
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from .config import APP_ID
from .models.store import EventStore
from .services.notifications import NotificationService
from .services.preferences import PreferencesStore
from .window import WeekPlanWindow

log = logging.getLogger(__name__)


class WeekPlanApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)
        self._started = False

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)  # PyGObject: chain C vfunc explicitly
        provider = Gtk.CssProvider()
        css_path = Path(__file__).parent / "style.css"
        provider.load_from_string(css_path.read_text())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self._on_quit)
        self.add_action(quit_action)

        self.set_accels_for_action("app.quit",       ["<Ctrl>q"])
        self.set_accels_for_action("win.new-event",  ["<Ctrl>n"])
        self.set_accels_for_action("win.today",      ["<Ctrl>t"])
        self.set_accels_for_action("win.prev-week",  ["Left"])
        self.set_accels_for_action("win.next-week",  ["Right"])
        self.set_accels_for_action("win.sync",       ["F5"])
        self.set_accels_for_action("win.shortcuts",  ["<Ctrl>question"])

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
