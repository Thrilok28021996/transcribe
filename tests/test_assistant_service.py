"""Integration tests for RAGAssistantService."""

from pathlib import Path

import pytest

from transcribe.application.container import ServiceContainer
from transcribe.application.services.assistant_service import RAGAssistantService
from transcribe.application.services.search_service import SearchService
from transcribe.domain.entities import (
    Decision,
    ExtractionResult,
    Meeting,
    Task,
    Transcript,
    TranscriptSegment,
)
from transcribe.infrastructure.config import load_config
from transcribe.infrastructure.graph_store import KnowledgeGraphStore
from transcribe.infrastructure.vector_store import LocalVectorStore


@pytest.mark.asyncio
async def test_rag_assistant_service_ask(tmp_path: Path) -> None:
    config = load_config()
    container = ServiceContainer(config=config)

    vector_store = LocalVectorStore(storage_dir=tmp_path / "vec")
    graph_store = KnowledgeGraphStore(storage_dir=tmp_path / "graph")
    search_service = SearchService(container=container, vector_store=vector_store, graph_store=graph_store)

    meeting = Meeting(title="AI Architecture Review", audio_path="review.wav")
    transcript = Transcript(
        meeting_id=meeting.id,
        segments=[TranscriptSegment(meeting_id=meeting.id, speaker_id="Alice", start=0.0, end=4.0, text="We chose Python and LM Studio.")],
    )
    extraction = ExtractionResult(
        meeting_id=meeting.id,
        summary="Architecture sync on tech stack.",
        decisions=[Decision(meeting_id=meeting.id, description="Use Python and LM Studio", owner="Alice")],
        tasks=[Task(meeting_id=meeting.id, description="Setup LM Studio endpoint", owner="Bob")],
    )

    await search_service.index_meeting(meeting=meeting, transcript=transcript, extraction=extraction)

    assistant = RAGAssistantService(container=container, search_service=search_service)
    result = await assistant.ask(question="What tech stack did we choose?")

    assert result.question == "What tech stack did we choose?"
    assert len(result.sources) > 0
    assert len(result.answer) > 0
