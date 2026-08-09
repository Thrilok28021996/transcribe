"""Action Item Dispatcher enforcing Tiered Autonomy for Calendar & Email execution."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from neural_agent_os.application.services.connectors_service import ExternalConnectorsService
from neural_agent_os.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ActionItemDispatcher:
    """Dispatches meeting action items to external connectors under Tiered Autonomy controls."""

    def __init__(self, connectors: Optional[ExternalConnectorsService] = None) -> None:
        self.connectors = connectors or ExternalConnectorsService()
        self.approval_queue: List[Dict[str, Any]] = []
        self.execution_history: List[Dict[str, Any]] = []

    def process_meeting_action_items(self, meeting_title: str, action_items: List[str]) -> Dict[str, Any]:
        """Parse action items and dispatch them under Tiered Autonomy rules."""
        auto_calendar_created: List[Dict[str, Any]] = []
        email_drafts_queued: List[Dict[str, Any]] = []

        for item in action_items:
            item_lower = item.lower()
            if "email" in item_lower or "mail" in item_lower or "send" in item_lower or "notify" in item_lower:
                # Tier 2: Draft Email & Queue for 1-Click Approval
                draft_id = f"draft_{int(time.time() * 1000)}"
                draft = {
                    "draft_id": draft_id,
                    "meeting_title": meeting_title,
                    "recipient": "team@company.com",
                    "subject": f"Meeting Action Item: {meeting_title}",
                    "body": f"Hi Team,\n\nFollowing up on our recent meeting '{meeting_title}':\n\nAction Item: {item}\n\nBest regards,\nNeural Agent OS Assistant",
                    "status": "pending_approval",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                # Also create local Mail.app draft
                self.connectors.prepare_email_draft(
                    recipient=draft["recipient"],
                    subject=draft["subject"],
                    body=draft["body"],
                )
                self.approval_queue.append(draft)
                email_drafts_queued.append(draft)

            elif "schedule" in item_lower or "calendar" in item_lower or "call" in item_lower or "book" in item_lower:
                # Tier 1: Auto-Execute Calendar Event Draft
                event = self.connectors.create_calendar_event(
                    title=f"Follow-up: {item[:40]}...",
                    start_time=time.strftime("%Y-%m-%d 15:00:00"),
                    description=f"Action item generated from meeting: {meeting_title}\nItem: {item}",
                )
                auto_calendar_created.append(event)
                self.execution_history.append({"type": "calendar_event", "details": event})

        return {
            "status": "processed",
            "auto_calendar_created": auto_calendar_created,
            "email_drafts_queued": email_drafts_queued,
            "pending_approval_count": len(self.approval_queue),
        }

    def approve_and_send_email(self, draft_id: str) -> Dict[str, Any]:
        """Approve and immediately send a queued email draft."""
        for draft in self.approval_queue:
            if draft["draft_id"] == draft_id:
                draft["status"] = "approved_and_sent"
                sent_res = self.connectors.send_email_now(
                    recipient=draft["recipient"],
                    subject=draft["subject"],
                    body=draft["body"],
                )
                self.approval_queue.remove(draft)
                self.execution_history.append({"type": "email_sent", "details": sent_res})
                return sent_res

        return {"status": "error", "message": f"Draft ID '{draft_id}' not found in approval queue."}

    def get_approval_queue(self) -> List[Dict[str, Any]]:
        """Return all emails waiting for 1-click user approval."""
        return self.approval_queue
