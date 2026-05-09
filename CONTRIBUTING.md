# Contributing to WeekPlan

## Welcome

WeekPlan is a project that cares about clean code, a native GNOME feel, low resource use, and accessibility — contributions that share those values are warmly welcome. The maintainer ([sssurendra99](https://github.com/sssurendra99)) actively reviews PRs but reserves the right to steer the project's direction.

## Ways to contribute

- 🐛 **Report bugs** via [issues](https://github.com/sssurendra99/weekplan/issues/new/choose)
- 💡 **Propose features** via [Discussions](https://github.com/sssurendra99/weekplan/discussions) (preferred for big ideas) or issues (for small enhancements)
- 📖 **Improve docs** — low barrier, very welcome
- 🌍 **Translate the UI** (translation infrastructure coming in v0.2)
- 🎨 **Suggest design improvements** (mockups in issues, please)
- 💻 **Submit code** (read on)

## Before you start coding

This is important — please respect it:

- **For features:** open an issue first to discuss approach. PRs without prior discussion may be declined or require significant rework.
- **For bugs:** an issue with reproduction steps helps. You can include the fix in the same PR if it's small.
- Check the [roadmap](README.md#roadmap) and [open issues](https://github.com/sssurendra99/weekplan/issues) — your idea may already be planned, in progress, or rejected.
- Browse [good first issues](https://github.com/sssurendra99/weekplan/labels/good%20first%20issue) for low-friction starting points.

## Development setup

Install system dependencies for your distro:

**Fedora**
```bash
sudo dnf install python3-gobject gtk4 libadwaita python3-pip
```

**Ubuntu 22.04+ / Debian 12+**
```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-pip
```

**Arch**
```bash
sudo pacman -S python-gobject gtk4 libadwaita python-pip
```

Then clone and run:

```bash
git clone https://github.com/sssurendra99/weekplan.git
cd weekplan
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pip install pre-commit && pre-commit install
python -m weekplan
```

Useful commands during development:

```bash
# Run the test suite
pytest

# Run with debug logging
WEEKPLAN_LOG_LEVEL=DEBUG python -m weekplan

# Test time-sensitive features at a fake clock time
WEEKPLAN_FAKE_NOW=2025-03-13T13:30:00 python -m weekplan

# Use a throwaway database
WEEKPLAN_DATA_DIR=/tmp/wp-test python -m weekplan
```

**Recommended editor:** VS Code with the Python and GitLens extensions.

> There is no hot-reload for GTK — kill the app, edit, restart.

## Code style

```bash
ruff format          # format
ruff check --fix     # lint and auto-fix
make lint            # or: pre-commit run --all-files
```

- Type hints required on all public functions
- Docstrings on public classes and public functions (Google style)
- Max line length: 100
- Run `make lint` (or `pre-commit run --all-files`) before committing

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/). This drives automated changelogs — non-conformant commits make the tooling miss your contribution.

**Format:** `<type>(<scope>): <subject>`

| Type | When to use |
|------|-------------|
| `feat` | new feature |
| `fix` | bug fix |
| `docs` | documentation only |
| `style` | formatting, no code change |
| `refactor` | neither feature nor fix |
| `test` | adding tests |
| `perf` | performance improvement |
| `chore` | maintenance, deps, build |
| `ci` | CI/CD changes |

**Examples:**
```
feat(notifications): add snooze button
fix(week-view): correct now-line position on DST transition
docs: clarify Google OAuth setup
```

## Branch naming

```
feat/short-description
fix/short-description
docs/short-description
refactor/short-description
```

## Pull request process

1. Fork the repo
2. Create a branch from `main`
3. Make your changes with conventional commits
4. Push and open a PR against `main`
5. Fill the PR template completely — UI changes require screenshots
6. CI must pass (tests, lint, format)
7. One maintainer approval required
8. Squash-merge by default (keeps history clean)

## What we look for in PRs

- **One concern per PR** — small, focused changes review faster and land easier
- **Tests** for any new behavior
- **No regressions** in existing tests
- **UI changes:** screenshots in the PR description, both light and dark mode
- **Performance:** don't add code that runs every frame; respect the resource budget (~60 MB RAM idle)
- **Accessibility:** keyboard navigation must still work; add screen reader labels to any new interactive elements

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for module layout, data flow, and key design decisions.

## Design contributions

- Open an issue with mockups (Figma, screenshots, even hand-sketches)
- Reference design tokens in `src/weekplan/style.css`
- Big visual changes need maintainer buy-in **before** code is written

## Translations

Translation infrastructure is coming in v0.2 (gettext-based). Watch the [i18n label](https://github.com/sssurendra99/weekplan/labels/i18n) on the issue tracker for updates.

## Releasing (maintainer only)

1. Bump version in `pyproject.toml`
2. Update `CHANGELOG.md` — move "Unreleased" to a new version block with date
3. Create a signed tag: `git tag -s v0.1.0 -m "v0.1.0"`
4. Push the tag — GitHub Action builds the Flatpak release automatically
5. Draft GitHub Release notes from the `CHANGELOG` entry

## Code of Conduct

Everyone interacting in this project's spaces is expected to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Questions?

Open a [Discussion](https://github.com/sssurendra99/weekplan/discussions) — they're great for questions, ideas, and showcasing how you use WeekPlan.
