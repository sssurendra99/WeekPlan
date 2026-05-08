from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..config import get_user_config_dir
from ..models.event import Event
from ..models.store import EventStore

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

_DEFAULT_COLOR = "#3584e4"


class GoogleSync:
    def __init__(self, store: EventStore) -> None:
        self._store = store
        creds_path = get_user_config_dir() / "credentials.json"
        if not creds_path.exists():
            raise FileNotFoundError(
                f"Google credentials not found at {creds_path}.\n"
                "Follow the README's 'Google Cloud Setup' section to create "
                "an OAuth 2.0 client ID and download it as credentials.json."
            )
        self._creds_path = creds_path
        self._token_path = get_user_config_dir() / "token.json"
        self._service = None
        # Track last successful sync time; events with updated_at <= this
        # were already pushed and don't need re-patching.
        self._last_sync: datetime = datetime.now(timezone.utc)

    # ------------------------------------------------------------------ auth

    def authenticate(self) -> None:
        creds: Optional[Credentials] = None
        if self._token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self._token_path), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self._creds_path), SCOPES
                )
                creds = flow.run_local_server(port=0)
            self._token_path.parent.mkdir(parents=True, exist_ok=True)
            self._token_path.write_text(creds.to_json())
        self._service = build("calendar", "v3", credentials=creds)

    # ------------------------------------------------------------------ pull

    def pull(self) -> int:
        assert self._service is not None, "Call authenticate() first"
        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=30)).isoformat()
        time_max = (now + timedelta(days=90)).isoformat()

        count = 0
        page_token = None
        while True:
            resp = (
                self._service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=False,
                    pageToken=page_token,
                )
                .execute()
            )
            for item in resp.get("items", []):
                if item.get("status") == "cancelled":
                    continue
                if self._upsert_from_remote(item):
                    count += 1
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return count

    # ------------------------------------------------------------------ push

    def push(self) -> int:
        assert self._service is not None, "Call authenticate() first"
        count = 0
        cutoff = self._last_sync

        # Delete tombstoned events from Google
        for event_id, google_id in self._store.get_tombstones():
            try:
                self._service.events().delete(
                    calendarId="primary", eventId=google_id
                ).execute()
            except Exception:
                pass  # already deleted on remote is acceptable
            self._store.clear_tombstone(event_id)
            count += 1

        # Create / patch local events
        for event in self._store.list_all():
            if event.google_id is None:
                body = self._to_google_body(event)
                try:
                    created = (
                        self._service.events()
                        .insert(calendarId="primary", body=body)
                        .execute()
                    )
                    event.google_id = created["id"]
                    event.updated_at = datetime.now(timezone.utc)
                    self._store.update(event)
                    count += 1
                except Exception as exc:
                    log.warning("Failed to create event %s on Google: %s", event.id, exc)
            elif event.updated_at > cutoff:
                body = self._to_google_body(event)
                try:
                    self._service.events().patch(
                        calendarId="primary",
                        eventId=event.google_id,
                        body=body,
                    ).execute()
                    count += 1
                except Exception as exc:
                    log.warning("Failed to patch event %s: %s", event.id, exc)

        return count

    # ------------------------------------------------------------------ sync

    def sync(self) -> int:
        try:
            pulled = self.pull()
            pushed = self.push()
            self._last_sync = datetime.now(timezone.utc)
            return pulled + pushed
        except Exception as exc:
            log.error("Google Calendar sync failed: %s", exc)
            raise

    # ------------------------------------------------------------------ helpers

    def _parse_google_dt(self, dt_obj: dict) -> datetime:
        if "dateTime" in dt_obj:
            raw = dt_obj["dateTime"]
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            # All-day event — treat as midnight UTC
            dt = datetime.fromisoformat(dt_obj["date"] + "T00:00:00+00:00")
        return dt.astimezone(timezone.utc)

    def _extract_rrule(self, recurrence: list[str]) -> Optional[str]:
        for entry in recurrence:
            if entry.upper().startswith("RRULE:"):
                return entry[6:]
        return None

    def _upsert_from_remote(self, item: dict) -> bool:
        google_id = item["id"]
        remote_updated = datetime.fromisoformat(
            item["updated"].replace("Z", "+00:00")
        )

        try:
            start = self._parse_google_dt(item["start"])
            end = self._parse_google_dt(item["end"])
        except (KeyError, ValueError):
            log.debug("Skipping event %s: unparseable start/end", google_id)
            return False

        if end <= start:
            end = start + timedelta(hours=1)

        rrule = self._extract_rrule(item.get("recurrence", []))
        title = item.get("summary", "(no title)")
        description = item.get("description", "")

        existing = self._store.get_by_google_id(google_id)
        if existing is None:
            event = Event(
                title=title,
                start=start,
                end=end,
                description=description,
                color=_DEFAULT_COLOR,
                rrule=rrule,
                google_id=google_id,
                updated_at=remote_updated,
            )
            self._store.add(event)
            return True

        if remote_updated > existing.updated_at:
            existing.title = title
            existing.start = start
            existing.end = end
            existing.description = description
            existing.rrule = rrule
            existing.updated_at = remote_updated
            self._store.update(existing)
            return True

        return False

    def _to_google_body(self, event: Event) -> dict:
        body: dict = {
            "summary": event.title,
            "description": event.description or "",
            "start": {"dateTime": event.start.isoformat(), "timeZone": "UTC"},
            "end":   {"dateTime": event.end.isoformat(),   "timeZone": "UTC"},
        }
        if event.rrule:
            body["recurrence"] = [f"RRULE:{event.rrule}"]
        return body
