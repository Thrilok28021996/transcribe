"""Integration tests for MeetingService workflow."""

from pathlib import Path

import pytest

from neural_agent_os.application.container import ServiceContainer
from neural_agent_os.application.services import MeetingService
from neural_agent_os.infrastructure.config import load_config


@pytest.mark.asyncio
async def test_meeting_service_pipeline(tmp_path: Path) -> None:
    # Set up temp audio file and custom markdown dir
    dummy_audio = tmp_path / "test_meeting.wav"
    dummy_audio.write_bytes(b"RIFF dummy audio data header")

    markdown_dir = tmp_path / "markdown_output"
    config = load_config()
    config.speech.provider = "mock"
    config.llm.provider = "mock"
    config.storage.markdown_dir = markdown_dir
    config.storage.markdown_dir.mkdir(parents=True, exist_ok=True)

    container = ServiceContainer(config=config)
    service = MeetingService(container=container)

    result = await service.process_meeting(audio_path=dummy_audio, title="Architecture Sync")

    assert result.meeting.title == "Architecture Sync"
    assert len(result.transcript.segments) > 0
    assert len(result.extraction.decisions) > 0
    assert result.markdown_path.exists()

    markdown_content = result.markdown_path.read_text(encoding="utf-8")
    assert "# Architecture Sync" in markdown_content
    assert "Adopt Python" in markdown_content or "Decisions" in markdown_content
    assert "## Key Decisions" in markdown_content or "## Decisions" in markdown_content
