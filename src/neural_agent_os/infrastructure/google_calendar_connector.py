"""Google Calendar OAuth2 connector for fetching and creating calendar events."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from neural_agent_os.infrastructure.logging import get_logger

logger = get_logger(__name__)

GCAL_SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarConnector:
    """OAuth2 Google Calendar connector for fetching events and creating calendar entries."""

    def __init__(
        self,
        credentials_file: str = "credentials.json",
        token_file: str = "gcal_token.json",
    ) -> None:
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self._service: Any = None
        self.is_authorized = False

    def authenticate(self) -> bool:
        """Run OAuth2 flow. Opens browser on first use for user consent.
        
        Returns True if authentication succeeded.
        """
        if not self.credentials_file.exists():
            logger.debug(
                f"Google Calendar credentials file not found at '{self.credentials_file}'. "
                "Place credentials.json from Google Cloud Console to enable Calendar integration."
            )
            return False
        try:
            from google.auth.transport.requests import Request  # type: ignore[import]
            from google.oauth2.credentials import Credentials  # type: ignore[import]
            from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import]
            from googleapiclient.discovery import build  # type: ignore[import]

            creds = None
            if self.token_file.exists():
                creds = Credentials.from_authorized_user_file(str(self.token_file), GCAL_SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), GCAL_SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                self.token_file.write_text(creds.to_json())

            self._service = build("calendar", "v3", credentials=creds)
            self.is_authorized = True
            logger.info("Google Calendar OAuth2 authentication successful.")
            return True
        except ImportError:
            logger.debug(
                "Google API packages not installed. Run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
            )
            return False
        except Exception as err:
            logger.warning(f"Google Calendar authentication failed: {err}")
            return False

    def list_upcoming(
        self,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Fetch upcoming calendar events with meeting join links."""
        if not self._service:
            return []
        try:
            now = datetime.now(timezone.utc).isoformat()
            events_result = self._service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()
            items = events_result.get("items", [])
            results: list[dict[str, Any]] = []
            for ev in items:
                description = ev.get("description") or ""
                results.append({
                    "title": ev.get("summary", "Untitled"),
                    "start_time": ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date", "")),
                    "description": description,
                    "meeting_url": ev.get("hangoutLink") or self._extract_meeting_url(description),
                    "source": "Google Calendar",
                    "event_id": ev.get("id", ""),
                })
            return results
        except Exception as err:
            logger.warning(f"Failed to fetch Google Calendar events: {err}")
            return []

    def create_event(
        self,
        title: str,
        start_iso: str,
        duration_minutes: int = 60,
        description: str = "",
    ) -> dict[str, Any]:
        """Create a Google Calendar event and return the event URL."""
        if not self._service:
            return {"status": "not_authorized", "reason": "Google Calendar OAuth not configured"}
        try:
            try:
                start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
            except ValueError:
                start = datetime.now(timezone.utc) + timedelta(hours=1)
            end = start + timedelta(minutes=duration_minutes)

            event_body = {
                "summary": title[:200],
                "description": description,
                "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
            }
            created = self._service.events().insert(
                calendarId="primary",
                body=event_body,
            ).execute()
            logger.info(f"Google Calendar event created: {created.get('htmlLink')}")
            return {
                "status": "created",
                "event_id": str(created.get("id", "")),
                "html_link": str(created.get("htmlLink", "")),
                "title": title,
            }
        except Exception as err:
            logger.error(f"Failed to create Google Calendar event: {err}")
            return {"status": "error", "reason": str(err)}

    def _extract_meeting_url(self, text: str) -> str | None:
        """Extract a Teams/Meet/Zoom URL from event description text."""
        m = re.search(
            r"(https?://[^\s]+(?:meet\.google|teams|zoom)[^\s]+)",
            text,
            re.IGNORECASE,
        )
        return str(m.group(1)) if m else None
