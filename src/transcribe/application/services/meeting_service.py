"""Application service orchestrating end-to-end meeting processing workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from transcribe.application.container import ServiceContainer
from transcribe.domain.entities import ExtractionResult, Meeting, Transcript
from transcribe.domain.reconciler import reconcile_transcript_with_diarization
from transcribe.infrastructure.audio import AudioProcessor
from transcribe.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ProcessingPipelineResult(NamedTuple):
    """Result returned upon successful meeting pipeline processing."""
    meeting: Meeting
    transcript: Transcript
    extraction: ExtractionResult
    markdown_path: Path


class MeetingService:
    """Orchestrates audio ingestion, transcription, diarization, extraction, and export."""

    def __init__(
        self,
        container: ServiceContainer,
        audio_processor: AudioProcessor | None = None,
    ) -> None:
        self.container = container
        self.config = container.config
        self.audio_processor = audio_processor or AudioProcessor()

    async def process_meeting(
        self,
        audio_path: str | Path,
        title: str | None = None,
    ) -> ProcessingPipelineResult:
        """Run the complete local meeting processing pipeline."""
        path = Path(audio_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Audio file not found: {path}")

        meeting_title = title or path.stem.replace("_", " ").title()
        audio_metadata = self.audio_processor.get_metadata(path)
        logger.info(
            f"Starting pipeline for meeting '{meeting_title}' ({path.name}, duration={audio_metadata.duration_seconds:.1f}s)"
        )

        # 1. Ingest & initialize domain entity
        meeting = Meeting(
            id=path.stem,
            title=meeting_title,
            date=datetime.now(timezone.utc),
            audio_path=str(path),
            duration_seconds=audio_metadata.duration_seconds,
        )

        # 2. Speech Recognition
        recognizer = self.container.get_speech_recognizer()
        logger.info(f"Step 1/6: Transcribing audio using [{recognizer.name}]...")
        raw_transcript = await recognizer.transcribe(path)

        # 3. Word Alignment
        aligner = self.container.get_alignment_engine()
        logger.info(f"Step 2/6: Aligning word timestamps using [{aligner.name}]...")
        aligned_transcript = await aligner.align(raw_transcript, path)

        # 4. Speaker Diarization & Temporal Reconciliation
        diarizer = self.container.get_diarization_engine()
        logger.info(f"Step 3/6: Running speaker diarization using [{diarizer.name}]...")
        diar_segments = await diarizer.diarize(path)
        reconciled_transcript = reconcile_transcript_with_diarization(aligned_transcript, diar_segments)

        # 5. Persistent Speaker Identification
        speaker_id_engine = self.container.get_speaker_identifier()
        logger.info(f"Step 4/6: Identifying speakers using [{speaker_id_engine.name}]...")
        resolved_segments = []
        for seg in reconciled_transcript.segments:
            identified_speaker = await speaker_id_engine.identify(seg, path)
            resolved_segments.append(
                seg.model_copy(update={"speaker_id": identified_speaker})
            )

        final_transcript = reconciled_transcript.model_copy(
            update={"segments": resolved_segments}
        )

        # 5. Knowledge Extraction
        extractor = self.container.get_knowledge_extractor()
        logger.info(f"Step 4/6: Extracting knowledge using [{extractor.name}]...")
        extraction_result = await extractor.extract(final_transcript)

        # 6. Markdown Export
        exporter = self.container.get_markdown_exporter()
        output_dir = self.config.storage.markdown_dir
        logger.info(f"Step 5/6: Exporting Markdown using [{exporter.name}] to {output_dir}...")
        markdown_path = await exporter.export(
            meeting=meeting,
            transcript=final_transcript,
            extraction=extraction_result,
            output_dir=output_dir,
        )

        # 7. Embedding Generation, Vector Store Indexing & Knowledge Graph Integration
        from transcribe.application.services.search_service import SearchService
        search_service = SearchService(container=self.container)
        logger.info(f"Step 6/6: Indexing meeting vectors & graph relationships...")
        await search_service.index_meeting(
            meeting=meeting,
            transcript=final_transcript,
            extraction=extraction_result,
        )

        logger.info(f"Pipeline completed successfully. Markdown generated at: {markdown_path}")
        return ProcessingPipelineResult(
            meeting=meeting,
            transcript=final_transcript,
            extraction=extraction_result,
            markdown_path=markdown_path,
        )
