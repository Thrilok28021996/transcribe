"""Gmail OAuth2 connector for drafting and sending emails via Google API."""

from __future__ import annotations

import base64
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from neural_agent_os.infrastructure.logging import get_logger

logger = get_logger(__name__)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
]


class GmailConnector:
    """OAuth2 Gmail connector for drafting and sending emails via the Google Gmail API."""

    def __init__(
        self,
        credentials_file: str = "credentials.json",
        token_file: str = "gmail_token.json",
    ) -> None:
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self._service: Any = None
        self.is_authorized = False

    def authenticate(self) -> bool:
        """Run OAuth2 flow. Opens browser on first use for user consent.
        
        Returns True if authentication succeeded, False if credentials.json is missing
        or google-auth packages are not installed.
        """
        if not self.credentials_file.exists():
            logger.debug(
                f"Gmail credentials file not found at '{self.credentials_file}'. "
                "Place credentials.json from Google Cloud Console to enable Gmail integration."
            )
            return False
        try:
            from google.auth.transport.requests import Request  # type: ignore[import]
            from google.oauth2.credentials import Credentials  # type: ignore[import]
            from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore[import]
            from googleapiclient.discovery import build  # type: ignore[import]

            creds = None
            if self.token_file.exists():
                creds = Credentials.from_authorized_user_file(str(self.token_file), GMAIL_SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), GMAIL_SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                self.token_file.write_text(creds.to_json())

            self._service = build("gmail", "v1", credentials=creds)
            self.is_authorized = True
            logger.info("Gmail OAuth2 authentication successful.")
            return True
        except ImportError:
            logger.debug(
                "Google API packages not installed. Run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
            )
            return False
        except Exception as err:
            logger.warning(f"Gmail authentication failed: {err}")
            return False

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        sender: str = "me",
    ) -> dict[str, Any]:
        """Create an email draft in Gmail (for 1-click approval flow)."""
        if not self._service:
            return {"status": "not_authorized", "reason": "Gmail OAuth not configured"}
        try:
            msg = MIMEText(body)
            msg["to"] = to
            msg["from"] = sender
            msg["subject"] = subject
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            draft = self._service.users().drafts().create(
                userId="me",
                body={"message": {"raw": raw}},
            ).execute()
            logger.info(f"Gmail draft created: {draft.get('id')}")
            return {"status": "draft_created", "draft_id": str(draft.get("id", ""))}
        except Exception as err:
            logger.error(f"Failed to create Gmail draft: {err}")
            return {"status": "error", "reason": str(err)}

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        sender: str = "me",
    ) -> dict[str, Any]:
        """Send email immediately via Gmail API."""
        if not self._service:
            return {"status": "not_authorized", "reason": "Gmail OAuth not configured"}
        try:
            msg = MIMEText(body)
            msg["to"] = to
            msg["from"] = sender
            msg["subject"] = subject
            raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            sent = self._service.users().messages().send(
                userId="me",
                body={"raw": raw},
            ).execute()
            logger.info(f"Gmail message sent: {sent.get('id')}")
            return {"status": "sent", "message_id": str(sent.get("id", ""))}
        except Exception as err:
            logger.error(f"Failed to send Gmail message: {err}")
            return {"status": "error", "reason": str(err)}

    def send_draft(
        self,
        draft_id: str,
    ) -> dict[str, Any]:
        """Send a previously created draft by draft_id."""
        if not self._service:
            return {"status": "not_authorized", "reason": "Gmail OAuth not configured"}
        try:
            sent = self._service.users().drafts().send(
                userId="me",
                body={"id": draft_id},
            ).execute()
            return {"status": "sent", "message_id": str(sent.get("id", ""))}
        except Exception as err:
            logger.error(f"Failed to send Gmail draft {draft_id}: {err}")
            return {"status": "error", "reason": str(err)}
