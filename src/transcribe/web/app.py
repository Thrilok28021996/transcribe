"""FastAPI Web application backend for Transcribe AI platform."""

from __future__ import annotations

import os
import subprocess
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
from transcribe.infrastructure.logging import get_logger

logger = get_logger(__name__)


class SearchQueryRequest(BaseModel):
    query: str
    top_k: int = 5


class AskQuestionRequest(BaseModel):
    question: str
    top_k: int = 5


class UpdateSettingsRequest(BaseModel):
    storage_dir: str | None = None
    stt_model_size: str | None = None
    stt_device: str | None = None
    stt_provider: str | None = None
    stt_language: str | None = None
    llm_model_name: str | None = None
    llm_provider: str | None = None
    llm_api_base: str | None = None
    llm_temperature: float | None = None



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

    active_backend_recording: list[dict[str, Any]] = []

    @app.get("/api/audio/devices")
    async def get_audio_devices() -> dict[str, Any]:
        """Get system audio hardware devices and loopback hook diagnostic status."""
        from transcribe.infrastructure.system_audio_hook import SystemAudioHook
        hook = SystemAudioHook()
        devices = hook.list_devices()
        status = hook.get_setup_status()
        return {
            "devices": [dev.model_dump() for dev in devices],
            "setup_status": status.model_dump(),
        }

    @app.post("/api/audio/record_start")
    async def start_backend_recording(
        mode: str = Form("mic"),
        mic_device: str | None = Form(None),
        system_device: str | None = Form(None),
    ) -> dict[str, Any]:
        """Start native backend audio recording using SystemAudioHook (FFmpeg)."""
        import subprocess
        import time

        from transcribe.infrastructure.system_audio_hook import SystemAudioHook

        if active_backend_recording:
            info = active_backend_recording.pop(0)
            p = info.get("process")
            if p and p.poll() is None:
                p.terminate()

        hook = SystemAudioHook()
        rec_dir = cntr.config.storage.recordings_dir
        rec_dir.mkdir(parents=True, exist_ok=True)
        filename = f"live_native_{int(time.time() * 1000)}.wav"
        out_path = rec_dir / filename

        cmd = hook.build_ffmpeg_record_cmd(
            output_path=out_path,
            duration_seconds=3600,
            mode=mode,
            mic_device=mic_device,
            system_device=system_device,
        )

        try:
            p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            # Brief check to ensure process didn't fail immediately due to permission error
            time.sleep(0.35)
            if p.poll() is not None:
                err_bytes = p.stderr.read() if p.stderr else b""
                err_text = err_bytes.decode("utf-8", errors="ignore")
                logger.error(f"Backend live recording start failed: {err_text}")
                if "Permission denied" in err_text or "Operation not permitted" in err_text:
                    raise HTTPException(
                        status_code=500,
                        detail="macOS Microphone Permission Denied: Please allow microphone access for Transcribe AI (or your Terminal) in System Settings -> Privacy & Security -> Microphone."
                    )
                raise HTTPException(status_code=500, detail=f"Failed to start hardware recording: {err_text[:200] if err_text else 'Process exited'}")

            active_backend_recording.append({
                "process": p,
                "output_path": out_path,
                "filename": filename,
                "start_time": time.time(),
            })
            return {"status": "started", "filename": filename, "mode": mode}
        except HTTPException:
            raise
        except Exception as err:
            logger.error(f"Backend live recording start failed: {err}")
            raise HTTPException(status_code=500, detail=f"Failed to start native recording: {err}")

    @app.post("/api/audio/record_stop")
    async def stop_backend_recording(
        title: str | None = Form(None),
    ) -> dict[str, Any]:
        """Stop native backend audio recording and process meeting memory."""
        import time
        if not active_backend_recording:
            raise HTTPException(status_code=400, detail="No active backend recording process.")

        rec_info = active_backend_recording.pop(0)
        p: subprocess.Popen = rec_info["process"]
        out_path: Path = rec_info["output_path"]

        if p and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()

        if not out_path.exists() or out_path.stat().st_size == 0:
            with open(out_path, "wb") as f:
                f.write(b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00')

        m_title = title or f"Live Meeting ({time.strftime('%H:%M:%S')})"
        try:
            res = await meeting_service.process_meeting(audio_path=out_path, title=m_title)
            return {
                "success": True,
                "meeting_id": res.meeting.id,
                "title": res.meeting.title,
                "decisions_count": len(res.extraction.decisions),
                "tasks_count": len(res.extraction.tasks),
                "markdown_path": str(res.markdown_path),
            }
        except Exception as err:
            logger.error(f"Processing recorded meeting failed: {err}")
            raise HTTPException(status_code=500, detail=f"Meeting processing failed: {err}")

    @app.get("/api/settings")
    async def get_settings() -> dict[str, Any]:
        """Get system settings and available models."""
        import json
        import urllib.request

        available_llm_models: list[str] = []
        api_base = cntr.config.llm.api_base.rstrip("/")
        models_url = f"{api_base}/models"
        try:
            req = urllib.request.Request(models_url, headers={"User-Agent": "Transcribe-AI/0.1.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    for m in data.get("data", []):
                        if isinstance(m, dict) and "id" in m:
                            available_llm_models.append(m["id"])
        except Exception:
            logger.debug("LM Studio models endpoint unavailable. Using fallback default models.")

        if not available_llm_models:
            available_llm_models = ["default", "qwen2.5-7b-instruct", "llama-3.2-3b-instruct", "mistral-7b-instruct"]

        return {
            "storage": {
                "base_dir": str(cntr.config.storage.base_dir),
                "meetings_dir": str(cntr.config.storage.meetings_dir),
                "recordings_dir": str(cntr.config.storage.recordings_dir),
                "markdown_dir": str(cntr.config.storage.markdown_dir),
                "speakers_dir": str(cntr.config.storage.speakers_dir),
            },
            "speech": {
                "provider": cntr.config.speech.provider,
                "model_size": cntr.config.speech.model_size,
                "device": cntr.config.speech.device,
                "language": cntr.config.speech.language,
                "available_models": ["tiny", "base", "small", "medium", "large-v3-turbo", "large-v3"],
                "available_devices": ["auto", "mps", "cuda", "cpu"],
                "available_providers": ["faster-whisper", "mock"],
            },
            "llm": {
                "provider": cntr.config.llm.provider,
                "model_name": cntr.config.llm.model_name,
                "api_base": cntr.config.llm.api_base,
                "temperature": cntr.config.llm.temperature,
                "available_providers": ["lm-studio", "ollama", "mock"],
                "available_models": available_llm_models,
            },
        }

    @app.post("/api/settings")
    async def update_settings(req: UpdateSettingsRequest) -> dict[str, Any]:
        """Update system settings for STT, LM Studio local models, and user storage path."""
        from transcribe.infrastructure.config import save_config

        if req.storage_dir is not None and req.storage_dir.strip():
            new_base = Path(req.storage_dir).expanduser().resolve()
            cntr.config.storage.base_dir = new_base
            cntr.config.storage.meetings_dir = new_base / "meetings"
            cntr.config.storage.recordings_dir = new_base / "recordings"
            cntr.config.storage.speakers_dir = new_base / "speakers"
            cntr.config.storage.markdown_dir = new_base / "markdown"

            new_base.mkdir(parents=True, exist_ok=True)
            cntr.config.storage.meetings_dir.mkdir(parents=True, exist_ok=True)
            cntr.config.storage.recordings_dir.mkdir(parents=True, exist_ok=True)
            cntr.config.storage.speakers_dir.mkdir(parents=True, exist_ok=True)
            cntr.config.storage.markdown_dir.mkdir(parents=True, exist_ok=True)

        if req.stt_model_size is not None:
            cntr.config.speech.model_size = req.stt_model_size
        if req.stt_device is not None:
            cntr.config.speech.device = req.stt_device  # type: ignore
        if req.stt_provider is not None:
            cntr.config.speech.provider = req.stt_provider
        if req.stt_language is not None:
            cntr.config.speech.language = req.stt_language

        if req.llm_model_name is not None:
            cntr.config.llm.model_name = req.llm_model_name
        if req.llm_provider is not None:
            cntr.config.llm.provider = req.llm_provider
        if req.llm_api_base is not None:
            cntr.config.llm.api_base = req.llm_api_base
        if req.llm_temperature is not None:
            cntr.config.llm.temperature = req.llm_temperature

        save_config(cntr.config)
        cntr.reload_plugins()

        logger.info(f"Updated settings: Storage='{cntr.config.storage.base_dir}', STT='{cntr.config.speech.model_size}', LLM='{cntr.config.llm.model_name}'")

        return {
            "success": True,
            "message": "System settings updated successfully.",
            "storage_dir": str(cntr.config.storage.base_dir),
            "speech": cntr.config.speech.model_dump(),
            "llm": cntr.config.llm.model_dump(),
        }


    @app.post("/api/cleanup")
    async def cleanup_endpoint(
        delete_all: bool = Form(False),
        delete_recordings: bool = Form(True),
    ) -> dict[str, Any]:
        """Clean up accumulated raw audio recordings or reset full data storage."""
        from transcribe.infrastructure.config import cleanup_storage
        res = cleanup_storage(cntr.config, delete_recordings=delete_recordings, delete_all=delete_all)

        if delete_all:
            if hasattr(search_service, "vector_store") and hasattr(search_service.vector_store, "clear"):
                search_service.vector_store.clear()
            if hasattr(search_service, "graph_store") and hasattr(search_service.graph_store, "clear"):
                search_service.graph_store.clear()
            if hasattr(cntr.speaker_db, "clear"):
                cntr.speaker_db.clear()


        return {
            "success": True,
            "deleted_files": res["deleted_files"],
            "freed_mb": round(res["freed_bytes"] / (1024 * 1024), 2),
            "message": f"Storage cleanup complete. Removed {res['deleted_files']} files ({round(res['freed_bytes'] / (1024 * 1024), 2)} MB freed).",
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

    @app.post("/api/speakers")
    async def create_speaker(
        name: str = Form(...),
        aliases: str | None = Form(None),
    ) -> dict[str, Any]:
        """Create a new persistent speaker profile."""
        import uuid

        from transcribe.domain.models import Speaker
        alias_list = [a.strip() for a in aliases.split(",") if a.strip()] if aliases else []
        speaker_id = f"spk_{uuid.uuid4().hex[:8]}"
        spk = Speaker(id=speaker_id, name=name.strip(), aliases=alias_list)
        cntr.speaker_db.add_speaker(spk)
        return {
            "success": True,
            "speaker": {
                "id": spk.id,
                "name": spk.name,
                "aliases": spk.aliases,
            }
        }

    @app.post("/api/speakers/{speaker_id}")
    async def update_speaker(
        speaker_id: str,
        name: str = Form(...),
        aliases: str | None = Form(None),
    ) -> dict[str, Any]:
        """Update persistent speaker display name and aliases."""
        speaker = cntr.speaker_db.get_speaker(speaker_id)
        if not speaker:
            raise HTTPException(status_code=404, detail=f"Speaker '{speaker_id}' not found.")

        alias_list = [a.strip() for a in aliases.split(",") if a.strip()] if aliases is not None else None
        updated = cntr.speaker_db.update_speaker_details(speaker_id, name=name, aliases=alias_list)
        return {
            "success": True,
            "speaker": {
                "id": updated.id,
                "name": updated.name,
                "aliases": updated.aliases,
            }
        }

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
