"""Application service managing semantic search, vector indexing, and graph exploration."""

from __future__ import annotations

from typing import Any, NamedTuple

from transcribe.application.container import ServiceContainer
from transcribe.domain.entities import ExtractionResult, Meeting, Transcript
from transcribe.infrastructure.graph_store import GraphEdge, GraphNode, KnowledgeGraphStore
from transcribe.infrastructure.logging import get_logger
from transcribe.infrastructure.vector_store import LocalVectorStore, VectorDocument

logger = get_logger(__name__)


class SearchMatch(NamedTuple):
    """Single match returned by semantic search."""
    id: str
    text: str
    doc_type: str  # e.g., "segment", "decision", "task", "summary"
    score: float
    metadata: dict[str, Any]


class SearchResult(NamedTuple):
    """Aggregate search result containing vector matches and graph relationships."""
    query: str
    matches: list[SearchMatch]
    graph_context: list[str]


class SearchService:
    """Orchestrates indexing and cross-meeting semantic search / graph exploration."""

    def __init__(
        self,
        container: ServiceContainer,
        vector_store: LocalVectorStore | None = None,
        graph_store: KnowledgeGraphStore | None = None,
    ) -> None:
        self.container = container
        self.vector_store = vector_store or LocalVectorStore(
            storage_dir=container.config.storage.base_dir / "vector_db"
        )
        self.graph_store = graph_store or KnowledgeGraphStore(
            storage_dir=container.config.storage.base_dir / "graph_db"
        )

    async def index_meeting(
        self,
        meeting: Meeting,
        transcript: Transcript,
        extraction: ExtractionResult,
    ) -> None:
        """Index meeting transcript, extracted decisions, tasks, and entities into vector & graph stores."""
        embedder = self.container.get_embedding_provider()
        docs_to_index: list[VectorDocument] = []

        # 1. Index full meeting summary
        if extraction.summary:
            summary_vec = await embedder.embed(extraction.summary)
            docs_to_index.append(
                VectorDocument(
                    id=f"summary_{meeting.id}",
                    text=f"Meeting Summary ({meeting.title}): {extraction.summary}",
                    vector=summary_vec,
                    metadata={"meeting_id": meeting.id, "doc_type": "summary", "title": meeting.title},
                )
            )

        # 2. Index transcript segments
        for i, seg in enumerate(transcript.segments):
            if not seg.text:
                continue
            seg_text = f"[{seg.speaker_id}]: {seg.text}"
            vec = await embedder.embed(seg_text)
            docs_to_index.append(
                VectorDocument(
                    id=f"seg_{meeting.id}_{i}",
                    text=seg_text,
                    vector=vec,
                    metadata={
                        "meeting_id": meeting.id,
                        "doc_type": "segment",
                        "speaker_id": seg.speaker_id,
                        "start": seg.start,
                        "end": seg.end,
                    },
                )
            )

        # 3. Index decisions & tasks
        for j, dec in enumerate(extraction.decisions):
            dec_text = f"Decision: {dec.description} (Owner: {dec.owner or 'Unassigned'})"
            d_vec = await embedder.embed(dec_text)
            docs_to_index.append(
                VectorDocument(
                    id=f"dec_{meeting.id}_{j}",
                    text=dec_text,
                    vector=d_vec,
                    metadata={"meeting_id": meeting.id, "doc_type": "decision", "owner": dec.owner},
                )
            )

        for k, task in enumerate(extraction.tasks):
            task_text = f"Task: {task.description} (Assignee: {task.owner or 'Unassigned'}, Deadline: {task.deadline or 'N/A'})"
            t_vec = await embedder.embed(task_text)
            docs_to_index.append(
                VectorDocument(
                    id=f"task_{meeting.id}_{k}",
                    text=task_text,
                    vector=t_vec,
                    metadata={"meeting_id": meeting.id, "doc_type": "task", "owner": task.owner},
                )
            )

        # Batch save into local vector store
        self.vector_store.add_documents(docs_to_index)

        # 4. Index Knowledge Graph Nodes & Edges
        meeting_node = GraphNode(
            id=meeting.id,
            label="Meeting",
            properties={"title": meeting.title, "date": meeting.date.isoformat()},
        )
        self.graph_store.add_node(meeting_node)

        for dec in extraction.decisions:
            dec_node = GraphNode(
                id=dec.id,
                label="Decision",
                properties={"description": dec.description, "owner": dec.owner},
            )
            self.graph_store.add_node(dec_node)
            self.graph_store.add_edge(
                GraphEdge(
                    source_id=meeting.id,
                    target_id=dec.id,
                    relation_type="recorded_decision",
                    confidence=dec.confidence,
                )
            )

        for task in extraction.tasks:
            task_node = GraphNode(
                id=task.id,
                label="Task",
                properties={"description": task.description, "owner": task.owner},
            )
            self.graph_store.add_node(task_node)
            self.graph_store.add_edge(
                GraphEdge(
                    source_id=meeting.id,
                    target_id=task.id,
                    relation_type="assigned_task",
                    confidence=task.confidence,
                )
            )

        for rel in extraction.relationships:
            src_node = GraphNode(id=rel.source_id, label=rel.source_type)
            tgt_node = GraphNode(id=rel.target_id, label=rel.target_type)
            self.graph_store.add_node(src_node)
            self.graph_store.add_node(tgt_node)
            self.graph_store.add_edge(
                GraphEdge(
                    source_id=rel.source_id,
                    target_id=rel.target_id,
                    relation_type=rel.relation_type,
                    confidence=rel.confidence,
                )
            )

    async def search(self, query: str, top_k: int = 5) -> SearchResult:
        """Perform semantic vector search and retrieve graph context for query."""
        embedder = self.container.get_embedding_provider()
        logger.info(f"Performing semantic search for query: '{query}'")

        query_vec = await embedder.embed(query)
        matches_raw = self.vector_store.search(query_vector=query_vec, top_k=top_k)

        matches: list[SearchMatch] = [
            SearchMatch(
                id=doc.id,
                text=doc.text,
                doc_type=doc.metadata.get("doc_type", "unknown"),
                score=score,
                metadata=doc.metadata,
            )
            for doc, score in matches_raw
        ]

        # Retrieve knowledge graph relationship context
        graph_context: list[str] = []
        for match in matches:
            owner = match.metadata.get("owner")
            if owner:
                neighbors = self.graph_store.query_neighbors(owner)
                for src, edge, tgt in neighbors:
                    graph_context.append(f"`{src.id}` --[{edge.relation_type}]--> `{tgt.id}`")

        return SearchResult(
            query=query,
            matches=matches,
            graph_context=list(set(graph_context)),
        )
