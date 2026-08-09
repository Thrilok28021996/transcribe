"""Mock plugin adapters for testing and Phase 1 foundation verification."""

from __future__ import annotations

import math
from pathlib import Path

from neural_agent_os.domain.entities import (
    Decision,
    ExtractionResult,
    Meeting,
    Organization,
    Project,
    Relationship,
    Task,
    Technology,
    Transcript,
    TranscriptSegment,
    TranscriptWord,
)


class MockSpeechRecognizer:
    """Mock speech recognizer generating synthetic transcripts."""

    name: str = "mock-speech-recognizer"

    async def transcribe(self, audio_path: Path) -> Transcript:
        meeting_id = audio_path.stem
        clean_title = meeting_id.replace("_", " ").title()
        segments = [
            TranscriptSegment(
                meeting_id=meeting_id,
                speaker_id="Speaker 01",
                start=0.0,
                end=4.0,
                text=f"Recording session for {clean_title}.",
                confidence=0.95,
            ),
        ]
        return Transcript(
            meeting_id=meeting_id,
            segments=segments,
            language="en",
            confidence=0.95,
            metadata={"engine": self.name, "audio_file": str(audio_path)},
        )


class MockAlignmentEngine:
    """Mock word alignment engine assigning word timestamps."""

    name: str = "mock-alignment-engine"

    async def align(self, transcript: Transcript, audio_path: Path) -> Transcript:
        new_segments: list[TranscriptSegment] = []
        for seg in transcript.segments:
            words_raw = seg.text.split()
            if not words_raw:
                new_segments.append(seg)
                continue
            duration = seg.end - seg.start
            step = duration / len(words_raw)
            words: list[TranscriptWord] = []
            for i, w in enumerate(words_raw):
                w_start = seg.start + (i * step)
                w_end = w_start + step
                words.append(
                    TranscriptWord(
                        word=w,
                        start=round(w_start, 2),
                        end=round(w_end, 2),
                        confidence=0.95,
                    )
                )
            new_segments.append(
                TranscriptSegment(
                    id=seg.id,
                    meeting_id=seg.meeting_id,
                    speaker_id=seg.speaker_id,
                    start=seg.start,
                    end=seg.end,
                    text=seg.text,
                    words=words,
                    confidence=seg.confidence,
                )
            )
        return Transcript(
            meeting_id=transcript.meeting_id,
            segments=new_segments,
            language=transcript.language,
            confidence=transcript.confidence,
            metadata={**transcript.metadata, "aligned_by": self.name},
        )


class MockDiarizationEngine:
    """Mock diarization engine returning speaker segments."""

    name: str = "mock-diarization-engine"

    async def diarize(self, audio_path: Path) -> list[TranscriptSegment]:
        meeting_id = audio_path.stem
        return [
            TranscriptSegment(
                meeting_id=meeting_id,
                speaker_id="SPEAKER_00",
                start=0.0,
                end=5.5,
                text="",
                confidence=0.90,
            ),
            TranscriptSegment(
                meeting_id=meeting_id,
                speaker_id="SPEAKER_01",
                start=6.0,
                end=12.2,
                text="",
                confidence=0.88,
            ),
        ]


class MockSpeakerIdentifier:
    """Mock speaker identifier resolving speaker labels to names."""

    name: str = "mock-speaker-identifier"

    async def identify(self, segment: TranscriptSegment, audio_path: Path) -> str:
        if "Speaker A" in segment.speaker_id or "00" in segment.speaker_id:
            return "Alice"
        if "Speaker B" in segment.speaker_id or "01" in segment.speaker_id:
            return "Bob"
        return "Unknown Speaker"


class MockKnowledgeExtractor:
    """Mock LLM knowledge extractor returning decisions, tasks, entities."""

    name: str = "mock-knowledge-extractor"

    async def extract(self, transcript: Transcript) -> ExtractionResult:
        m_id = transcript.meeting_id
        decisions = [
            Decision(
                meeting_id=m_id,
                description="Adopt Python for AI pipeline backend infrastructure.",
                owner="Alice",
                confidence=0.96,
                context_snippet="we decided to adopt Python for our AI pipeline backend.",
            )
        ]
        tasks = [
            Task(
                meeting_id=m_id,
                description="Create initial repository structure and configure CI pipeline.",
                owner="Bob",
                deadline="Friday",
                status="pending",
                confidence=0.94,
            )
        ]
        projects = [Project(name="Transcribe AI Platform", description="Local-first meeting memory")]
        technologies = [
            Technology(name="Python", category="Language"),
            Technology(name="Faster-Whisper", category="ASR"),
        ]
        organizations = [Organization(name="Engineering Team")]
        relationships = [
            Relationship(
                source_id="Bob",
                source_type="Person",
                target_id="Create initial repository structure",
                target_type="Task",
                relation_type="owns",
                confidence=0.95,
            ),
            Relationship(
                source_id="Transcribe AI Platform",
                source_type="Project",
                target_id="Python",
                target_type="Technology",
                relation_type="uses",
                confidence=0.98,
            ),
        ]
        return ExtractionResult(
            meeting_id=m_id,
            decisions=decisions,
            tasks=tasks,
            projects=projects,
            technologies=technologies,
            organizations=organizations,
            relationships=relationships,
            summary="Discussion on architecture choices and repo setup assignments.",
        )


class MockMarkdownExporter:
    """Mock Markdown exporter generating clean Markdown documentation."""

    name: str = "mock-markdown-exporter"

    async def export(
        self,
        meeting: Meeting,
        transcript: Transcript,
        extraction: ExtractionResult,
        output_dir: Path,
    ) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"{meeting.id}.md"

        content = [
            f"# Meeting: {meeting.title}",
            "",
            f"- **Date**: {meeting.date.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"- **Duration**: {meeting.duration_seconds:.1f} seconds",
            f"- **Audio File**: `{meeting.audio_path}`",
            "",
            "## Executive Summary",
            "",
            extraction.summary or "No summary provided.",
            "",
            "## Decisions",
            "",
        ]

        if extraction.decisions:
            for d in extraction.decisions:
                content.append(f"- **{d.description}** (Owner: {d.owner or 'Unassigned'}, Confidence: {d.confidence:.2f})")
        else:
            content.append("*No decisions recorded.*")

        content.extend(["", "## Action Items", ""])
        if extraction.tasks:
            for t in extraction.tasks:
                content.append(f"- [ ] **{t.description}** — Assignee: @{t.owner or 'Unassigned'} (Deadline: {t.deadline or 'N/A'})")
        else:
            content.append("*No action items recorded.*")

        content.extend(["", "## Transcript", ""])
        for seg in transcript.segments:
            content.append(f"**[{seg.speaker_id} ({seg.start:.1f}s - {seg.end:.1f}s)]**: {seg.text}")
            content.append("")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))

        return file_path


class MockLLMProvider:
    """Mock LLM provider for text generation."""

    name: str = "mock-llm-provider"

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        return f"[Mock Response to: '{prompt[:50]}...']"


class MockEmbeddingProvider:
    """Mock embedding provider producing 384-dim dummy embeddings."""

    name: str = "mock-embedding-provider"

    async def embed(self, text: str) -> list[float]:
        # Return deterministic dummy vector based on text hash
        val = sum(ord(c) for c in text) % 100 / 100.0
        return [round(math.sin(i + val), 4) for i in range(384)]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]
