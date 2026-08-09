"""Unit & Integration tests for Vexa Meeting Bot, Steno Hook, and External Connectors."""

import pytest
from fastapi.testclient import TestClient

from neural_agent_os.application.services.action_dispatcher import ActionItemDispatcher
from neural_agent_os.application.services.connectors_service import ExternalConnectorsService
from neural_agent_os.infrastructure.steno_passive_hook import StenoPassiveHook
from neural_agent_os.infrastructure.vexa_bot import VexaMeetingBot
from neural_agent_os.web.app import create_app


def test_vexa_bot_detect_platform() -> None:
    bot = VexaMeetingBot()
    assert bot.detect_platform("https://meet.google.com/abc-defg-hij") == "google_meet"
    assert bot.detect_platform("https://teams.microsoft.com/l/meetup-join/123") == "microsoft_teams"
    assert bot.detect_platform("https://zoom.us/j/123456789") == "zoom"


def test_vexa_bot_join_and_stop(tmp_path) -> None:
    bot = VexaMeetingBot(output_dir=str(tmp_path))
    res = bot.join_meeting("https://meet.google.com/abc-defg-hij", duration_seconds=5)
    assert res["status"] in ("joined", "joined_fallback")
    assert res["platform"] == "google_meet"

    stop_res = bot.stop_meeting()
    assert stop_res["status"] == "stopped"


def test_steno_passive_hook(tmp_path) -> None:
    hook = StenoPassiveHook(output_dir=str(tmp_path))
    status = hook.check_call_status()
    assert "is_call_active" in status

    mon = hook.start_passive_monitoring()
    assert mon["status"] == "monitoring_active"

    stop_res = hook.stop_passive_monitoring()
    assert stop_res["status"] == "stopped"


def test_connectors_service_and_dispatcher() -> None:
    connectors = ExternalConnectorsService()
    upcoming = connectors.fetch_upcoming_meetings()
    assert len(upcoming) >= 1

    dispatcher = ActionItemDispatcher(connectors=connectors)
    res = dispatcher.process_meeting_action_items(
        meeting_title="Sprint Planning",
        action_items=[
            "Schedule follow-up call with design team",
            "Send meeting notes email to stakeholders",
        ],
    )
    assert res["status"] == "processed"
    assert len(res["auto_calendar_created"]) == 1
    assert len(res["email_drafts_queued"]) == 1

    queue = dispatcher.get_approval_queue()
    assert len(queue) == 1
    draft_id = queue[0]["draft_id"]

    approve_res = dispatcher.approve_and_send_email(draft_id)
    assert approve_res["status"] == "sent"
    assert len(dispatcher.get_approval_queue()) == 0


def test_web_connector_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSCRIBE_SPEECH__PROVIDER", "mock")
    monkeypatch.setenv("TRANSCRIBE_LLM__PROVIDER", "mock")
    app = create_app()
    client = TestClient(app)

    res_steno = client.get("/api/connectors/steno/status")
    assert res_steno.status_code == 200
    assert "is_call_active" in res_steno.json()

    res_cal = client.get("/api/connectors/calendar/upcoming")
    assert res_cal.status_code == 200
    assert len(res_cal.json()) >= 1

    res_bot = client.post("/api/connectors/bot/join", json={"url": "https://meet.google.com/test-url"})
    assert res_bot.status_code == 200
    assert "status" in res_bot.json()
