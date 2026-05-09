#!/usr/bin/env bash
# Seeds initial good-first-issues. Run ONCE after the repo is pushed and gh authenticated.
set -euo pipefail

create_issue() {
  local title="$1"
  local body="$2"
  local labels="$3"
  gh issue create --title "$title" --body "$body" --label "$labels"
}

create_issue \
  "Add 'Tomorrow' shortcut button next to Today" \
  "$(cat <<'EOF'
## Context
The header bar currently has chevron-left, Today, chevron-right. Power users often want to jump to tomorrow specifically.

## Goal
Add a 'Tomorrow' button (or maybe a dropdown menu on Today: Today / Tomorrow / Pick date) so users can jump one day forward without clicking through.

## Suggested approach
- File: `src/weekplan/widgets/week_view.py`
- Add a new Gtk.Button or Gtk.MenuButton in the header bar
- Wire to a method that sets `self._anchor_date = date.today() + timedelta(days=1)` and calls refresh()

## Definition of done
- Button visible in header
- Click jumps to tomorrow's week (which may or may not be the same week as today)
- Keyboard shortcut wired (suggest Ctrl+Shift+T)
- Manually verified
- Screenshot in PR

## Estimated effort
1 hour
EOF
)" \
  "good first issue,enhancement"

create_issue \
  "Add Esc key to close event dialog without saving" \
  "$(cat <<'EOF'
## Context
EventDialog opens for create/edit. Currently users must click Cancel. Esc should also close.

## Goal
Pressing Esc in EventDialog closes it as if Cancel was clicked.

## Suggested approach
- File: `src/weekplan/widgets/event_dialog.py`
- Add a Gtk.EventControllerKey to the dialog
- On key-pressed, if keyval is GDK_KEY_Escape, call self.close()

## Definition of done
- Esc closes dialog without saving
- Existing Cancel button still works
- Tests still pass
- Verified manually

## Estimated effort
30 minutes
EOF
)" \
  "good first issue,enhancement"

create_issue \
  "Improve empty state copy when no events this week" \
  "$(cat <<'EOF'
## Context
When the visible week has zero events, the grid is empty. Currently the live banner shows 'Nothing happening right now / All clear for today' but there's no message in the grid itself.

## Goal
Add a subtle, friendly empty state in the grid area when 0 events are visible. Should NOT be obtrusive — small, low-contrast, dismissible feel.

## Suggested approach
- File: `src/weekplan/widgets/week_view.py`
- Add an Adw.StatusPage or simple Gtk.Label centered in the grid
- Show only when refresh() returns 0 occurrences for the visible week
- Hide as soon as an event is added

## Suggested copy options (pick or propose your own)
1. 'A clean week ahead. Press Ctrl+N to plan something.'
2. 'No events scheduled. Time to make some plans?'
3. 'Your week is wide open.'

## Definition of done
- Empty state visible when week has 0 events
- Hidden when events exist
- Light + dark mode look correct
- Screenshot of both states in PR

## Estimated effort
1 hour
EOF
)" \
  "good first issue,enhancement,design"

create_issue \
  "Add unit test for recurrence.expand with FREQ=MONTHLY" \
  "$(cat <<'EOF'
## Context
`tests/test_recurrence.py` covers DAILY, WEEKLY, BYDAY but not MONTHLY.

## Goal
Add tests for monthly recurrence patterns:
1. `FREQ=MONTHLY` (same day each month)
2. `FREQ=MONTHLY;BYDAY=1MO` (first Monday of each month)
3. `FREQ=MONTHLY;BYMONTHDAY=15` (15th of each month)

## Suggested approach
- File: `tests/test_recurrence.py`
- Follow existing test patterns
- Use a fixed anchor date and assert exact occurrence dates in a 6-month window

## Definition of done
- 3 new test cases pass
- pytest runs green
- Coverage of services/recurrence.py increases

## Estimated effort
1 hour
EOF
)" \
  "good first issue,test"

create_issue \
  "Document WEEKPLAN_FAKE_NOW env var in DEVELOPMENT.md" \
  "$(cat <<'EOF'
## Context
The codebase supports an env var `WEEKPLAN_FAKE_NOW` that overrides 'now' for testing live-feel features. It's used in services/timefmt.py but not well documented.

## Goal
Add a clear section to docs/DEVELOPMENT.md explaining:
- What it does
- Why it exists (testing time-based UI without waiting)
- Examples
- Limitations (only affects code that calls services.timefmt.now(), not datetime.now())

## Definition of done
- Section added under 'Running the app in development'
- 2-3 example commands shown
- Cross-link from CONTRIBUTING.md

## Estimated effort
30 minutes
EOF
)" \
  "good first issue,documentation"

create_issue \
  "Show event count badge on day headers" \
  "$(cat <<'EOF'
## Context
Day headers show 'MON' and the date. They could also show a small badge with event count for that day, helping users glance at busy/empty days.

## Goal
Add a small numeric badge next to the day number when count > 0.

## Suggested approach
- File: `src/weekplan/widgets/week_view.py`
- Modify day header construction to include a Gtk.Label with class .wp-day-badge
- Add CSS: small pill, muted background, only visible when count > 0
- Compute count in refresh() per day

## Design constraint
Must not be louder than the day number. Subtle, informational.

## Definition of done
- Badges visible when day has events
- Hidden for empty days
- Updates when events added/deleted
- Screenshots of busy and empty days in PR
- Light + dark mode

## Estimated effort
2 hours
EOF
)" \
  "good first issue,enhancement,design"

create_issue \
  "Replace placeholder app icon with a polished version" \
  "$(cat <<'EOF'
## Context
The current icon at `data/icons/com.weekplan.app.svg` is a quick draft. It needs a proper, GNOME HIG-compliant version.

## Specifications
- 128x128 SVG base, scalable
- Follow GNOME HIG icon style: https://developer.gnome.org/hig/guidelines/app-icons.html
- Accent color: #3584E4 (matches app)
- Should evoke 'week / planning / time'
- Symbolic version (single color, simpler) needed too — save as com.weekplan.app-symbolic.svg

## Suggested concepts (pick or propose)
- A weekly grid with one day highlighted
- A clock face with a week wedge
- Stacked horizontal lines (a week as bars)

## Definition of done
- Two SVGs committed: full color and symbolic
- Renders correctly at 16, 24, 32, 48, 64, 128, 256 px
- Looks good on light AND dark backgrounds
- Screenshots in PR showing icon at multiple sizes

## Estimated effort
3 hours (mostly design iteration)
EOF
)" \
  "good first issue,design"

echo "✅ 7 good-first-issues created."
echo "View them: https://github.com/sssurendra99/weekplan/labels/good%20first%20issue"
