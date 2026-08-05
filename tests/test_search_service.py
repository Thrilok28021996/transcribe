"""Integration tests for SearchService."""

from pathlib import Path

import pytest

from transcribe.application.container import ServiceContainer
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
async def test_search_service_indexing_and_search(tmp_path: Path) -> None:
    config = load_config()
    container = ServiceContainer(config=config)

    vector_store = LocalVectorStore(storage_dir=tmp_path / "vec")
    graph_store = KnowledgeGraphStore(storage_dir=tmp_path / "graph")

    search_service = SearchService(container=container, vector_store=vector_store, graph_store=graph_store)

    meeting = Meeting(title="Architecture Sync", audio_path="dummy.wav")
    transcript = Transcript(
        meeting_id=meeting.id,
        segments=[TranscriptSegment(meeting_id=meeting.id, speaker_id="Alice", start=0.0, end=5.0, text="We adopt Python.")],
    )
    extraction = ExtractionResult(
        meeting_id=meeting.id,
        summary="Decided on Python.",
        decisions=[Decision(meeting_id=meeting.id, description="Adopt Python for backend", owner="Alice")],
        tasks=[Task(meeting_id=meeting.id, description="Setup CI pipeline", owner="Bob")],
    )

    await search_service.index_meeting(meeting=meeting, transcript=transcript, extraction=extraction)

    assert vector_store.count() > 0
    assert graph_store.stats()["total_nodes"] > 0

    res = await search_service.search(query="Python backend", top_k=3)
    assert len(res.matches) > 0
