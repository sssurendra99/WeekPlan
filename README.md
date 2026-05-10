<div align="center">

# WeekPlan

A beautiful, fast, week-at-a-glance calendar for GNOME Linux.

[![License](https://img.shields.io/github/license/sssurendra99/WeekPlan?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)](https://www.python.org/)
[![GTK](https://img.shields.io/badge/GTK-4-blue?style=flat-square)](https://gtk.org/)
[![Last commit](https://img.shields.io/github/last-commit/sssurendra99/WeekPlan?style=flat-square)](https://github.com/sssurendra99/WeekPlan/commits/main)
[![Issues](https://img.shields.io/github/issues/sssurendra99/WeekPlan?style=flat-square)](https://github.com/sssurendra99/WeekPlan/issues)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square)](CONTRIBUTING.md)
[![Contributor Covenant](https://img.shields.io/badge/code%20of%20conduct-Contributor%20Covenant%202.1-purple?style=flat-square)](CODE_OF_CONDUCT.md)

![WeekPlan screenshot](docs/images/screenshot.png)

</div>

---

## Features

- ✨ **Live now-line and progress bars** — see what's happening at a glance
- 📅 **Weekly view with all 7 days and 24 hours**, smooth scrolling
- 🔁 **Recurring events** — daily, weekly, weekdays, custom RRULE
- 🔔 **Native GNOME notifications** with configurable lead time
- ☁️ **Two-way Google Calendar sync**
- 🎨 **Native libadwaita design** — looks at home on GNOME
- ⚡ **Lightweight** — ~60 MB RAM idle (vs. 300+ MB for Electron alternatives)
- ⌨️ **Full keyboard shortcuts**
- 🌗 **Light and dark mode** support

---

## Install

### From Flathub

Coming soon. Track progress in [issue #1](https://github.com/sssurendra99/weekplan/issues/1).

### From source — Flatpak (recommended)

This is the cleanest way to run WeekPlan. It installs into an isolated sandbox with all dependencies bundled.

**1. Install prerequisites**

<details>
<summary>Ubuntu / Debian</summary>

```bash
sudo apt install flatpak flatpak-builder
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//49 org.gnome.Sdk//49
```

</details>

<details>
<summary>Fedora</summary>

```bash
sudo dnf install flatpak flatpak-builder
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//49 org.gnome.Sdk//49
```

</details>

<details>
<summary>Arch</summary>

```bash
sudo pacman -S flatpak flatpak-builder
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install flathub org.gnome.Platform//49 org.gnome.Sdk//49
```

</details>

**2. Clone, build, and run**

```bash
git clone https://github.com/sssurendra99/weekplan.git
cd weekplan
make flatpak-build   # builds and installs locally (~2 min first time)
make flatpak-run
```

> Subsequent builds are cached — only changed modules are rebuilt.

To uninstall:

```bash
flatpak uninstall com.weekplan.app
```

---

### From source — development

Use this if you want to hack on the code. PyGObject must come from your system package manager — it cannot be installed via pip.

**1. Install system dependencies**

<details>
<summary>Ubuntu / Debian</summary>

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
  python3-full libgirepository1.0-dev
```

</details>

<details>
<summary>Fedora</summary>

```bash
sudo dnf install python3-gobject python3-gobject-devel gtk4 libadwaita \
  gobject-introspection-devel
```

</details>

<details>
<summary>Arch</summary>

```bash
sudo pacman -S python-gobject gtk4 libadwaita
```

</details>

**2. Create a venv that can see system packages**

PyGObject is installed system-wide, so the venv needs `--system-site-packages`:

```bash
git clone https://github.com/sssurendra99/weekplan.git
cd weekplan
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**3. Run**

```bash
.venv/bin/python -m weekplan
```

Or with the venv active:

```bash
python -m weekplan
```

---

## Quick start

- Press **Ctrl+N** to add an event.
- Use **← →** to navigate weeks, **Ctrl+T** to jump to today.
- Press **F5** to sync with Google Calendar.
- Connect your Google account in Settings to enable sync (see [docs/GOOGLE_SETUP.md](docs/GOOGLE_SETUP.md)).

---

## Keyboard shortcuts

| Action | Shortcut |
|---|---|
| New event | `Ctrl+N` |
| Today | `Ctrl+T` |
| Previous week | `←` |
| Next week | `→` |
| Sync | `F5` |
| Quit | `Ctrl+Q` |
| Open shortcuts dialog | `Ctrl+?` |

---

## Screenshots

| Light mode | Dark mode |
|---|---|
| ![Week view — light mode](docs/images/screenshot.png) | ![Week view — dark mode](docs/images/screenshot-dark.png) |

---

## Contributing

Contributions of all sizes are welcome — bug reports, feature suggestions, documentation, translations, and code. Start with [CONTRIBUTING.md](CONTRIBUTING.md), or browse [good first issues](https://github.com/sssurendra99/weekplan/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) if you're looking for a place to start. Have a question or idea? Open a [Discussion](https://github.com/sssurendra99/weekplan/discussions).

---

## Roadmap

- [x] Week view
- [x] Recurring events
- [x] Notifications
- [x] Google Calendar sync
- [ ] Month view
- [ ] Multiple calendars with toggleable visibility
- [ ] iCal import/export
- [ ] CalDAV support (Nextcloud, Fastmail)
- [ ] Natural language quick-add ("lunch with Sara tomorrow 1pm")
- [ ] Translations (i18n)

---

## Built with

Python · GTK4 · libadwaita · SQLite · python-dateutil · Google Calendar API · ❤️ for the GNOME desktop

---

## License

MIT © 2026 Sumal Surendra. See [LICENSE](LICENSE) for details.

---

## Acknowledgments

Inspired by GNOME Calendar. Built on the shoulders of the libadwaita and PyGObject teams. Thanks to every contributor who files an issue or sends a PR.

---

![Star History](https://api.star-history.com/svg?repos=sssurendra99/weekplan&type=Date)
