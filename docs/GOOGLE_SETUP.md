# Google Calendar setup

WeekPlan can sync with Google Calendar. This is entirely optional — the app works fully without it. If you skip this, the Sync button simply won't appear in the header bar.

---

## 1. Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com).
2. Click the project selector at the top → **New project**.
3. Give it a name (e.g. "WeekPlan") and click **Create**.

> If you already have a personal Google Cloud project you can reuse it. Just make sure you enable the Calendar API in step 2.

---

## 2. Enable the Google Calendar API

1. In the left sidebar choose **APIs & Services → Library**.
2. Search for **Google Calendar API**.
3. Click the result and then click **Enable**.

---

## 3. Configure the OAuth consent screen

This is required before you can create credentials.

1. Go to **APIs & Services → OAuth consent screen**.
2. Choose **External** user type (unless you have a Google Workspace account — then choose **Internal**).
3. Click **Create**.
4. Fill in the required fields:
   - **App name:** WeekPlan
   - **User support email:** your Google account
   - **Developer contact email:** your Google account
5. Click **Save and continue** through the Scopes page (you will add the scope in the next step).
6. On the **Test users** page, click **Add users** and add your own Google account. This allows your account to authorise the app while it is in testing mode.
7. Click **Save and continue**, then **Back to dashboard**.

---

## 4. Create an OAuth 2.0 client ID

1. Go to **APIs & Services → Credentials**.
2. Click **Create credentials → OAuth client ID**.
3. Set **Application type** to **Desktop app**.
4. Give it a name (e.g. "WeekPlan desktop") and click **Create**.
5. A dialog shows your client ID and secret. Click **Download JSON**.
6. Save the downloaded file to:

```
~/.config/weekplan/credentials.json
```

Create the directory if it does not exist:

```bash
mkdir -p ~/.config/weekplan
mv ~/Downloads/client_secret_*.json ~/.config/weekplan/credentials.json
```

---

## 5. Add the Calendar scope

1. Return to **APIs & Services → OAuth consent screen**.
2. Click **Edit app**.
3. On the **Scopes** step, click **Add or remove scopes**.
4. Search for `calendar` and select:
   - `https://www.googleapis.com/auth/calendar` — read and write access to your primary calendar
5. Click **Update**, then **Save and continue**.

| Scope | Why WeekPlan needs it |
|-------|----------------------|
| `https://www.googleapis.com/auth/calendar` | Read events for the pull sync; write and delete events for the push sync |

WeekPlan never stores your Google password or OAuth client secret. The only credential it persists is the OAuth **refresh token** (saved to `token.json` next to `credentials.json`).

---

## 6. First sync

Launch WeekPlan:

```bash
python -m weekplan
```

The **↺ Sync** button appears in the header bar when `credentials.json` is present. Click it. A browser window opens and asks you to sign in to Google and grant WeekPlan calendar access.

After you approve:

- A `token.json` file is saved to `~/.config/weekplan/token.json`.
- The initial sync pulls your primary calendar events for the next 90 days.
- Subsequent syncs are silent — no browser window.

---

## Sync behaviour

| Direction | What happens |
|-----------|-------------|
| **Pull** | Fetches events from Google in a −30 / +90 day window. Remote events are created or updated locally using last-write-wins on `updated_at`. |
| **Push** | Creates new local events on Google Calendar; patches events edited locally since the last sync; deletes events you deleted locally (via a tombstone table). |

Sync runs automatically once at startup (after the window appears) and on each press of the Sync button. There is no continuous background sync — it only runs when you explicitly trigger it or when the app starts.

---

## Revoking access

To disconnect WeekPlan from your Google account:

1. Delete `~/.config/weekplan/token.json` — WeekPlan will no longer sync until you re-authorise.
2. To revoke at Google's end: go to [myaccount.google.com/permissions](https://myaccount.google.com/permissions) and remove "WeekPlan".

---

## Troubleshooting

**"This app is blocked" / "Access denied"**

Your OAuth consent screen is in Testing mode and your account is not in the test users list. Add your account in **OAuth consent screen → Test users**.

**`FileNotFoundError: credentials.json`**

The file is not in `~/.config/weekplan/`. Check the path with:

```bash
ls -la ~/.config/weekplan/
```

**`google.auth.exceptions.RefreshError`**

The refresh token has expired or been revoked. Delete `token.json` and re-authorise by clicking Sync:

```bash
rm ~/.config/weekplan/token.json
```

**Events not appearing after sync**

WeekPlan syncs only your **primary** Google Calendar. If your events are on a secondary calendar (e.g. "Work" or a shared calendar), they will not appear. Multiple-calendar support is on the [roadmap](../README.md#roadmap).
