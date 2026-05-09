# WeekPlan

A minimal, beautiful week-view calendar for GNOME Linux.

## Goals
- Show the current week in a clean 7-column grid
- Schedule single and recurring events
- Desktop notifications before events
- Two-way sync with Google Calendar
- Low resource usage (target idle <80 MB RAM)

## Tech stack (do not change without explicit instruction)
- Python 3.11+, PyGObject
- GTK4 + libadwaita (Adw.*)
- SQLite via stdlib `sqlite3`
- python-dateutil for recurrence (rrule)
- google-api-python-client + google-auth-oauthlib for sync
- Native Gio.Notification for notifications
- Distribution via Flatpak

## Project layout
src/weekplan/
  __main__.py        — entry point, calls application.main()
  application.py     — Adw.Application subclass
  window.py          — main Adw.ApplicationWindow
  config.py          — XDG paths, app id "com.weekplan.app"
  models/
    event.py         — Event dataclass (frozen=False so we can mutate, with __post_init__)
    store.py         — EventStore: SQLite wrapper, all DB access goes through it
  widgets/
    week_view.py     — Adw widget showing 7-day grid
    event_card.py    — single event tile
    event_dialog.py  — Adw.Dialog for create/edit
  services/
    notifications.py — schedule + fire Gio.Notifications
    recurrence.py    — expand rrule strings into datetimes for a date range
    google_sync.py   — OAuth + two-way sync logic

## Coding conventions
- Type hints on every public function
- Dataclasses for data, classes for behavior
- No global state except the Adw.Application instance
- Use GLib.idle_add / GLib.timeout_add for any async-ish work, not threading.Thread (GTK is not thread-safe)
- All UI strings should be wrapped in `_()` so we can add translations later (set up gettext stub in config.py)
- Database schema migrations: keep a `schema_version` table, write upgrade functions

## Testing
- Each stage has a manual verification step. Run it before moving on.
- For storage and recurrence logic, write small pytest tests in tests/ directory.
- For UI, manual smoke testing via `python -m weekplan` is fine.

## Style for the UI
- Follow GNOME HIG (Human Interface Guidelines)
- Use libadwaita components (Adw.HeaderBar, Adw.Dialog, Adw.PreferencesPage, etc.) over raw Gtk where possible
- Respect system color scheme (light/dark)
- Use semantic colors via Adw style classes ("accent", "destructive-action") not hardcoded hex

## What NOT to do
- Don't add a tray icon (GNOME deprecated tray; use background portal if needed)
- Don't pull in heavy deps (no pandas, no Qt, no Electron, no web frameworks)
- Don't write your own date library — use datetime + dateutil
- Don't block the GTK main loop; long operations go in GLib.idle_add chunks or threads with idle_add for UI updates
