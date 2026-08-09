"""Tests for Personal Agent service and automation endpoints."""

import pytest
from fastapi.testclient import TestClient

from neural_agent_os.application.services.agent_service import AgentService
from neural_agent_os.web.app import create_app


def test_agent_service_available_tasks(tmp_path) -> None:
    service = AgentService(storage_dir=str(tmp_path))
    tasks = service.get_available_tasks()
    assert len(tasks) >= 4
    task_ids = [t["id"] for t in tasks]
    assert "executive_briefing" in task_ids
    assert "organize_files" in task_ids
    assert "system_cleanup" in task_ids
    assert "system_diagnostics" in task_ids


def test_agent_service_executive_briefing(tmp_path) -> None:
    service = AgentService(storage_dir=str(tmp_path))
    result = service.execute_task("executive_briefing")
    assert result.status == "success"
    assert result.task_id == "executive_briefing"
    assert len(result.artifacts) > 0
    assert (tmp_path / "meetings" / "Executive_Briefing.md").exists()


def test_agent_service_organize_files(tmp_path) -> None:
    rec_dir = tmp_path / "recordings"
    rec_dir.mkdir()
    (rec_dir / "sample.mp3").write_text("dummy audio", encoding="utf-8")
    (rec_dir / "doc.pdf").write_text("dummy pdf", encoding="utf-8")

    service = AgentService(storage_dir=str(tmp_path))
    result = service.execute_task("organize_files", target_path=str(rec_dir))
    assert result.status == "success"
    assert (rec_dir / "Audio" / "sample.mp3").exists()
    assert (rec_dir / "Documents" / "doc.pdf").exists()


def test_agent_service_system_cleanup(tmp_path) -> None:
    scratch_dir = tmp_path / "scratch"
    scratch_dir.mkdir()
    (scratch_dir / "temp1.tmp").write_text("temp content", encoding="utf-8")

    service = AgentService(storage_dir=str(tmp_path))
    result = service.execute_task("system_cleanup")
    assert result.status == "success"
    assert not (scratch_dir / "temp1.tmp").exists()


def test_agent_service_custom_task(tmp_path) -> None:
    service = AgentService(storage_dir=str(tmp_path))
    result = service.execute_task("custom", prompt="Organize my desktop notes")
    assert result.status == "success"
    assert "cleanly" in result.summary


def test_agent_service_convert_document(tmp_path) -> None:
    service = AgentService(storage_dir=str(tmp_path))
    result = service.execute_task("convert_document")
    assert result.status == "success"
    assert len(result.artifacts) > 0


def test_agent_service_voice_reminder(tmp_path) -> None:
    service = AgentService(storage_dir=str(tmp_path))
    result = service.execute_task("voice_reminder", prompt="Meeting starting in 5 minutes")
    assert result.status == "success"
    assert "Meeting starting in 5 minutes" in result.summary


def test_agent_service_biometrics(tmp_path) -> None:
    service = AgentService(storage_dir=str(tmp_path))
    result = service.execute_task("biometric_gate")
    assert result.status == "success"
    assert "biometrics" in result.summary.lower()


def test_agent_service_desktop_automation(tmp_path) -> None:
    service = AgentService(storage_dir=str(tmp_path))
    result = service.execute_task("desktop_automation", prompt="Arrange floating windows")
    assert result.status == "success"
    assert "Arrange floating windows" in result.summary


def test_web_agent_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSCRIBE_SPEECH__PROVIDER", "mock")
    monkeypatch.setenv("TRANSCRIBE_LLM__PROVIDER", "mock")
    app = create_app()
    client = TestClient(app)

    res = client.get("/api/agent/tasks")
    assert res.status_code == 200
    tasks = res.json()
    assert isinstance(tasks, list)

    res_exec = client.post("/api/agent/execute", json={"task_id": "system_diagnostics"})
    assert res_exec.status_code == 200
    exec_data = res_exec.json()
    assert exec_data["status"] == "success"

    res_hist = client.get("/api/agent/history")
    assert res_hist.status_code == 200
    history = res_hist.json()
    assert len(history) >= 1
