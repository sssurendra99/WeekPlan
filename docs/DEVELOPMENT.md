# Development guide

## Local setup

### 1. Install system dependencies

GTK4 and libadwaita must be installed at the system level — they cannot come from pip.

**Fedora 40+**

```bash
sudo dnf install \
    python3-devel python3-gobject python3-gobject-devel \
    gtk4 gtk4-devel libadwaita libadwaita-devel \
    gobject-introspection gobject-introspection-devel \
    python3-pip pkgconf
```

**Ubuntu 22.04+ / Debian 12+**

```bash
sudo apt install \
    python3-dev python3-gi python3-gi-cairo \
    gir1.2-gtk-4.0 gir1.2-adw-1 \
    libgirepository1.0-dev libcairo2-dev \
    python3-pip pkg-config
```

**Arch**

```bash
sudo pacman -S \
    python python-gobject gtk4 libadwaita \
    gobject-introspection python-pip pkgconf
```

### 2. Clone and set up the venv

```bash
git clone https://github.com/sssurendra99/weekplan.git
cd weekplan
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install pre-commit && pre-commit install
```

### Troubleshooting

**`ModuleNotFoundError: No module named 'gi'`**

`gi` (PyGObject) is a system package; it is not pip-installable on its own. Your venv needs to see the system's `gi` installation. Create the venv with `--system-site-packages`:

```bash
python -m venv --system-site-packages .venv
```

**`gi.repository.GLib.GError: Namespace Adw not available`**

libadwaita is not installed, or the version is too old. On Ubuntu 22.04 ensure `gir1.2-adw-1` is installed. On Fedora, `libadwaita`. The minimum required version is 1.4 (GNOME 45).

```bash
python -c "import gi; gi.require_version('Adw','1'); from gi.repository import Adw; print(Adw.VERSION_STRING)"
```

**Wayland: window does not appear / crashes on launch**

Some compositors need the Wayland backend selected explicitly:

```bash
GDK_BACKEND=wayland python -m weekplan
```

If running under XWayland, try `GDK_BACKEND=x11` instead.

**`dbus.exceptions.DBusException` on notifications**

Notifications require a running session bus. In a minimal environment (CI, containers) you may need `dbus-launch`:

```bash
dbus-launch python -m weekplan
```

---

## Project layout

```
weekplan/
├── src/weekplan/          ← all importable Python lives here
│   ├── __main__.py        ← entry point only — no logic
│   ├── application.py     ← Adw.Application subclass
│   ├── window.py          ← main window
│   ├── config.py          ← constants, paths, env vars, gettext stub
│   ├── style.css          ← custom CSS loaded at startup
│   ├── models/            ← pure data — no GTK imports allowed here
│   │   ├── event.py
│   │   └── store.py
│   ├── widgets/           ← GTK widget subclasses
│   │   ├── week_view.py
│   │   ├── event_card.py
│   │   ├── event_dialog.py
│   │   └── preferences_dialog.py
│   └── services/          ← side effects (DB, network, OS)
│       ├── recurrence.py
│       ├── notifications.py
│       ├── google_sync.py
│       └── preferences.py
├── tests/                 ← pytest tests
│   ├── test_store.py
│   └── test_recurrence.py
├── docs/                  ← you are here
├── data/                  ← non-Python assets (Flatpak manifest, icons)
├── pyproject.toml
└── .pre-commit-config.yaml
```

**What goes where:**

| Directory | What belongs | What does NOT belong |
|-----------|-------------|----------------------|
| `models/` | Dataclasses, DB logic | GTK imports, UI state |
| `widgets/` | GTK widget subclasses | Business logic, network calls |
| `services/` | Side effects, I/O | Widget construction |
| `tests/` | pytest files | App state, GTK |

---

## Running the app

```bash
# Standard run
python -m weekplan

# Debug logs (very verbose — shows DB queries, sync steps)
WEEKPLAN_LOG_LEVEL=DEBUG python -m weekplan

# Simulate a specific time (useful for testing the now-line and banner)
WEEKPLAN_FAKE_NOW=2026-03-13T13:30:00 python -m weekplan

# Isolated database (throwaway — safe to delete)
WEEKPLAN_DATA_DIR=/tmp/wp-test python -m weekplan

# Open GTK Inspector on launch (widget tree, CSS, signals)
GTK_DEBUG=interactive python -m weekplan
```

> There is no hot-reload for GTK. Kill the process, edit, relaunch.

---

## Testing

### Automated tests

```bash
# Run all tests
pytest

# With coverage report in the terminal
pytest --cov=weekplan --cov-report=term-missing

# Run a single file
pytest tests/test_store.py -v

# Run tests matching a name pattern
pytest -k "recurrence" -v
```

Tests live in `tests/`. They cover the `models/` and `services/` layers — the parts that can run without a display. GTK widgets are tested manually.

### Manual smoke checklist

Run through this before opening a PR that touches UI:

- [ ] App launches without errors in the terminal
- [ ] Week view shows the correct week with today highlighted
- [ ] `←` / `→` navigate weeks; `Ctrl+T` returns to today
- [ ] `Ctrl+N` opens the new-event dialog
- [ ] Create a one-off event — card appears on the correct day and column
- [ ] Edit the event — changes persist after dialog close
- [ ] Delete the event — card disappears
- [ ] Create a daily recurring event starting last week — it appears on every day of the current week
- [ ] Navigate three weeks forward — recurring event still appears
- [ ] Set a notification lead time, wait for it to fire (or use `WEEKPLAN_FAKE_NOW` to move time)
- [ ] Dark mode: toggle in GNOME Settings — app follows immediately
- [ ] Keyboard navigation: Tab through all dialog fields, Enter to confirm
- [ ] `Ctrl+Q` quits cleanly (no traceback)

---

## Debugging tips

### GTK Inspector

```bash
GTK_DEBUG=interactive python -m weekplan
```

This opens the inspector on launch. The **Widget Tree** tab shows every widget and its CSS classes. The **CSS** tab lets you live-edit styles. The **Object** tab shows property values and signals.

### libadwaita documentation

- API reference: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/
- GNOME HIG: https://developer.gnome.org/hig/

### Common pitfalls

**Calling GTK from a background thread**

```python
# WRONG — crashes or silently corrupts state
def sync_thread():
    result = fetch_from_google()
    self._store.add(result)      # DB write from thread — OK
    self._week_view.refresh()    # GTK call — NOT OK

# RIGHT
def sync_thread():
    result = fetch_from_google()
    self._store.add(result)
    GLib.idle_add(self._week_view.refresh)  # posted to main thread
```

**CSS not loading**

CSS is loaded in `application.py` via `Gtk.CssProvider`. If your new style class has no effect:
1. Check the class name in GTK Inspector.
2. Verify the CSS file path in `config.py` is correct.
3. Check for typos — GTK silently ignores invalid CSS rules.

**Signals not disconnecting**

Connecting a signal without disconnecting it holds a reference to both objects. For widgets that are created and destroyed repeatedly (like `EventCard`), always store the handler ID and call `widget.disconnect(handler_id)` in the widget's destroy handler, or use `connect_once` / a `WeakRef` wrapper.

---

## Contributing your first feature

This section walks through adding a **"Mark as done" toggle** to events — a realistic, self-contained change that touches every layer of the stack. Follow it as a template for your own features.

### Step 0: open an issue first

Before writing any code, open an issue describing the feature. Get a 👍 from the maintainer. This avoids the scenario where you spend a weekend coding something that gets declined because it doesn't fit the project direction.

For this example, the issue would be:
> **[Feature]: Mark event as done**
> Users want to check off one-off events without deleting them. Completed events should appear faded with a strikethrough.

### Step 1: create a branch

```bash
git checkout -b feat/event-done-toggle
```

### Step 2: add the field to the data model

Open `src/weekplan/models/event.py` and add `done` to the dataclass:

```python
@dataclass
class Event:
    title: str
    start: datetime
    end: datetime
    # ... existing fields ...
    done: bool = False          # ← add this
```

`done` defaults to `False` so existing code that constructs `Event(...)` without it continues to work.

### Step 3: migrate the database schema

Open `src/weekplan/models/store.py`. Find `_migrate()` and add a new migration step:

```python
def _migrate(self) -> None:
    version = self._conn.execute("SELECT version FROM schema_version").fetchone()[0]

    if version < 2:
        self._conn.execute("ALTER TABLE events ADD COLUMN done INTEGER NOT NULL DEFAULT 0")
        self._conn.execute("UPDATE schema_version SET version = 2")
        self._conn.commit()
```

Also update the `INSERT` and `SELECT` statements to include `done`. Search for `INSERT INTO events` and add `done` to both the column list and the values tuple. Search for `SELECT` and add `done` to the column list.

> **Never drop or rename a column in a migration.** SQLite's `ALTER TABLE` is limited — restructuring requires a table rename, copy, and drop. Avoid it unless absolutely necessary.

### Step 4: add the UI control in the dialog

Open `src/weekplan/widgets/event_dialog.py`. In `_build_form()`, add an `Adw.SwitchRow` after the existing fields:

```python
self._done_row = Adw.SwitchRow()
self._done_row.set_title(_("Mark as done"))
self._done_row.set_subtitle(_("Fades the event and adds a strikethrough"))
form.add(self._done_row)
```

In `_populate(event)`, populate the new field:

```python
self._done_row.set_active(event.done)
```

In `_on_save()`, read it back:

```python
event.done = self._done_row.get_active()
```

> **Rule:** `_populate()` must set every field. Missing a field causes the previous value to silently survive into the saved event. (This has caused bugs before — see memory note on `feedback_populate_pattern.md`.)

### Step 5: apply visual style in the event card

Open `src/weekplan/widgets/event_card.py`. In the method that applies event properties (likely `_refresh()` or `__init__`), add:

```python
if event.done:
    self.add_css_class("done")
else:
    self.remove_css_class("done")
```

Then open `src/weekplan/style.css` and add:

```css
.wp-event.done {
    opacity: 0.5;
}

.wp-event.done label {
    text-decoration: line-through;
}
```

Launch the app (`python -m weekplan`), mark an event as done, close the dialog, and confirm the card visually fades.

### Step 6: write a test

Open `tests/test_store.py` and add a round-trip test:

```python
def test_done_field_roundtrip(store: EventStore) -> None:
    event = store.add(make_event(done=True))
    retrieved = store.get(event.id)
    assert retrieved.done is True


def test_done_defaults_to_false(store: EventStore) -> None:
    event = store.add(make_event())
    retrieved = store.get(event.id)
    assert retrieved.done is False
```

Run the tests:

```bash
pytest tests/test_store.py -v
```

Both new tests should pass. If the migration runs correctly, the existing tests should also still pass.

### Step 7: run the linter

```bash
pre-commit run --all-files
```

Fix any issues before committing.

### Step 8: commit with a conventional commit message

```bash
git add -p   # stage hunks interactively, or just: git add src/ tests/
git commit -m "feat(events): add mark-as-done toggle"
```

The commit message format is `feat(<scope>): <subject>`. See [CONTRIBUTING.md](../CONTRIBUTING.md#commit-messages) for the full type list.

### Step 9: open the pull request

Push your branch and open a PR against `main`:

```bash
git push -u origin feat/event-done-toggle
gh pr create --title "feat(events): add mark-as-done toggle" \
  --body "Closes #<issue-number>

## What
Adds a 'Mark as done' toggle to the event dialog. Completed events display faded with a strikethrough.

## Screenshots
<!-- drag and drop before/after screenshots here, light AND dark mode -->

## Testing
- [x] Existing tests pass
- [x] New round-trip tests added
- [x] Manually verified on GNOME 46 (Wayland)
- [x] Verified in dark mode
"
```

That's the full loop — from issue to merged PR. Every feature follows this same pattern, regardless of size.
