"""FastAPI Web application backend for Transcribe AI platform."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from transcribe.application.container import ServiceContainer
from transcribe.application.services.assistant_service import RAGAssistantService
from transcribe.application.services.meeting_service import MeetingService
from transcribe.application.services.search_service import SearchService
from transcribe.infrastructure.config import load_config
from transcribe.infrastructure.graph_store import KnowledgeGraphStore
from transcribe.infrastructure.logging import get_logger
from transcribe.infrastructure.vector_store import LocalVectorStore

logger = get_logger(__name__)


class SearchQueryRequest(BaseModel):
    query: str
    top_k: int = 5


class AskQuestionRequest(BaseModel):
    question: str
    top_k: int = 5


def create_app(container: ServiceContainer | None = None) -> FastAPI:
    """Create and configure the FastAPI web server instance."""
    app = FastAPI(
        title="Transcribe AI — Meeting Memory Platform",
        description="Local-first AI Meeting Memory Web Platform",
        version="0.1.0",
    )

    # Enable CORS for local web access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    cntr = container or ServiceContainer(config=load_config())
    meeting_service = MeetingService(container=cntr)
    search_service = SearchService(container=cntr)
    assistant_service = RAGAssistantService(container=cntr, search_service=search_service)

    # Serve static assets
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def get_index() -> Any:
        """Serve main SPA index.html page."""
        index_file = static_dir / "index.html"
        if index_file.is_file():
            from fastapi.responses import FileResponse
            return FileResponse(index_file)
        return {"message": "Transcribe AI Web API operational."}

    @app.get("/api/stats")
    async def get_stats() -> dict[str, Any]:
        """Get aggregate system statistics."""
        vec_store = search_service.vector_store
        graph_store = search_service.graph_store
        speakers = cntr.speaker_db.list_speakers()

        # Count markdown meeting files
        md_dir = cntr.config.storage.markdown_dir
        md_files = list(md_dir.glob("*.md")) if md_dir.exists() else []

        return {
            "total_meetings": len(md_files),
            "total_speakers": len(speakers),
            "vector_documents": vec_store.count(),
            "graph_nodes": graph_store.stats()["total_nodes"],
            "graph_edges": graph_store.stats()["total_edges"],
            "llm_provider": cntr.config.llm.provider,
            "speech_provider": cntr.config.speech.provider,
        }

    @app.get("/api/meetings")
    async def list_meetings() -> list[dict[str, Any]]:
        """List all processed meetings."""
        md_dir = cntr.config.storage.markdown_dir
        if not md_dir.exists():
            return []

        meetings: list[dict[str, Any]] = []
        for file in sorted(md_dir.glob("*.md"), key=os.path.getmtime, reverse=True):
            content = file.read_text(encoding="utf-8")
            title = file.stem
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line.replace("# ", "").strip()
                    break

            meetings.append({
                "id": file.stem,
                "title": title,
                "file_path": str(file),
                "modified_at": file.stat().st_mtime,
            })

        return meetings

    @app.get("/api/meetings/{meeting_id}")
    async def get_meeting(meeting_id: str) -> dict[str, Any]:
        """Retrieve full details and raw Markdown content for a meeting."""
        md_file = cntr.config.storage.markdown_dir / f"{meeting_id}.md"
        if not md_file.is_file():
            raise HTTPException(status_code=404, detail="Meeting note not found.")

        content = md_file.read_text(encoding="utf-8")
        return {
            "id": meeting_id,
            "markdown": content,
        }

    @app.get("/api/recordings")
    async def list_recordings() -> list[dict[str, Any]]:
        """List all stored raw recording audio files in data/recordings/."""
        rec_dir = cntr.config.storage.recordings_dir
        if not rec_dir.exists():
            return []

        recordings = []
        for file in sorted(rec_dir.glob("*"), key=os.path.getmtime, reverse=True):
            if file.is_file() and file.suffix.lower() in {".wav", ".mp3", ".m4a", ".aac", ".mp4", ".webm", ".flac", ".ogg"}:
                recordings.append({
                    "filename": file.name,
                    "file_path": str(file),
                    "size_mb": round(file.stat().st_size / (1024 * 1024), 2),
                    "created_at": file.stat().st_mtime,
                })
        return recordings

    @app.post("/api/recordings/reprocess")
    async def reprocess_recording(
        filename: str = Form(...),
        title: str = Form(None),
    ) -> dict[str, Any]:
        """Re-run meeting processing pipeline on a stored raw recording file."""
        target_path = cntr.config.storage.recordings_dir / filename
        if not target_path.is_file():
            raise HTTPException(status_code=404, detail=f"Recorded file '{filename}' not found in storage.")

        try:
            res = await meeting_service.process_meeting(audio_path=target_path, title=title or filename)
            return {
                "success": True,
                "meeting_id": res.meeting.id,
                "title": res.meeting.title,
                "decisions_count": len(res.extraction.decisions),
                "tasks_count": len(res.extraction.tasks),
                "markdown_path": str(res.markdown_path),
            }
        except Exception as err:
            logger.error(f"Re-processing recording failed: {err}")
            raise HTTPException(status_code=500, detail=str(err)) from err

    @app.post("/api/process")
    async def process_meeting_endpoint(
        file: UploadFile = File(None),
        file_path: str = Form(None),
        title: str = Form(None),
    ) -> dict[str, Any]:
        """Ingest, save to data/recordings/, and process an audio file into meeting memory."""
        target_path: Path

        if file:
            rec_dir = cntr.config.storage.recordings_dir
            rec_dir.mkdir(parents=True, exist_ok=True)

            from datetime import datetime
            ext = Path(file.filename).suffix or ".webm"
            timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            saved_filename = f"meeting_{timestamp_str}{ext}"
            target_path = rec_dir / saved_filename

            with open(target_path, "wb") as f:
                content = await file.read()
                f.write(content)
        elif file_path:
            target_path = Path(file_path)
        else:
            raise HTTPException(status_code=400, detail="Please upload an audio file or specify file_path.")

        try:
            res = await meeting_service.process_meeting(audio_path=target_path, title=title)
            return {
                "success": True,
                "meeting_id": res.meeting.id,
                "title": res.meeting.title,
                "decisions_count": len(res.extraction.decisions),
                "tasks_count": len(res.extraction.tasks),
                "markdown_path": str(res.markdown_path),
            }
        except Exception as err:
            logger.error(f"Meeting processing failed: {err}")
            raise HTTPException(status_code=500, detail=str(err)) from err

    @app.post("/api/search")
    async def search_endpoint(req: SearchQueryRequest) -> dict[str, Any]:
        """Perform cross-meeting semantic search."""
        res = await search_service.search(query=req.query, top_k=req.top_k)
        return {
            "query": res.query,
            "matches": [
                {
                    "id": m.id,
                    "text": m.text,
                    "doc_type": m.doc_type,
                    "score": m.score,
                    "metadata": m.metadata,
                }
                for m in res.matches
            ],
            "graph_context": res.graph_context,
        }

    @app.post("/api/ask")
    async def ask_endpoint(req: AskQuestionRequest) -> dict[str, Any]:
        """Query local LM Studio RAG assistant."""
        res = await assistant_service.ask(question=req.question, top_k=req.top_k)
        return {
            "question": res.question,
            "answer": res.answer,
            "sources": [
                {
                    "id": s.id,
                    "text": s.text,
                    "doc_type": s.doc_type,
                    "score": s.score,
                }
                for s in res.sources
            ],
            "graph_context": res.graph_context,
        }

    @app.get("/api/speakers")
    async def get_speakers() -> list[dict[str, Any]]:
        """List persistent speaker profiles."""
        speakers = cntr.speaker_db.list_speakers()
        return [
            {
                "id": s.id,
                "name": s.name,
                "aliases": s.aliases,
                "has_embedding": bool(s.embedding),
                "confidence_avg": sum(s.confidence_history) / max(1, len(s.confidence_history)),
                "meeting_count": len(s.confidence_history),
            }
            for s in speakers
        ]

    @app.get("/api/graph")
    async def get_graph() -> dict[str, Any]:
        """Get Knowledge Graph nodes and edges."""
        graph_store = search_service.graph_store
        return {
            "stats": graph_store.stats(),
            "nodes": [n.model_dump(mode="json") for n in graph_store._nodes.values()],
            "edges": [e.model_dump(mode="json") for e in graph_store._edges],
        }

    return app
