# WeekPlan

A minimal, beautiful week-view calendar for GNOME Linux.

## Running the app

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m weekplan
```

## Google Cloud Setup

WeekPlan can sync with Google Calendar. This is optional — the app works fully without it.

### 1. Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project (or select an existing one).

### 2. Enable the Google Calendar API

1. In the left sidebar choose **APIs & Services → Library**.
2. Search for **Google Calendar API** and click **Enable**.

### 3. Create an OAuth 2.0 client ID

1. Go to **APIs & Services → Credentials**.
2. Click **Create Credentials → OAuth client ID**.
3. If prompted, configure the OAuth consent screen first:
   - Choose **External** (or Internal if you have a Workspace account).
   - Fill in the required fields (app name, support email).
   - Under **Scopes**, add `.../auth/calendar` (full calendar access).
   - Add your own Google account as a **test user**.
4. Back on Create Credentials, choose **Application type: Desktop app**.
5. Give it a name (e.g. "WeekPlan") and click **Create**.
6. Click **Download JSON** and save the file as:

```
~/.config/weekplan/credentials.json
```

### 4. First sync

Launch WeekPlan. The **Sync** button (↺) appears in the header bar.

On the first click a browser window opens asking you to authorise the app. After you approve, a `token.json` is saved next to `credentials.json` — subsequent syncs are silent.

### Scopes used

| Scope | Why |
|---|---|
| `https://www.googleapis.com/auth/calendar` | Read and write events on your primary calendar. |

WeekPlan never reads or stores your Google credentials beyond the OAuth token — all network access goes directly to the Google Calendar API.

### Two-way sync behaviour

- **Pull**: fetches events from Google in a ±30/+90 day window. Remote events are created or updated locally using last-write-wins on `updated_at`.
- **Push**: creates new local events on Google; patches events you edited locally since the last sync; deletes events you deleted locally (via a tombstone table).
- Sync runs automatically once at startup (after the window is shown) and on each press of the Sync button.
