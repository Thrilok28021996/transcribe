"""Abstract plugin interfaces defining system boundaries."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol, runtime_checkable

from transcribe.domain.entities import (
    ExtractionResult,
    Meeting,
    Transcript,
    TranscriptSegment,
)


@runtime_checkable
class SpeechRecognizer(Protocol):
    """Abstract interface for Speech-to-Text engines."""

    name: str

    async def transcribe(self, audio_path: Path) -> Transcript:
        """Transcribe an audio file to raw transcript."""
        ...


@runtime_checkable
class AlignmentEngine(Protocol):
    """Abstract interface for word alignment tools (e.g. WhisperX CTC)."""

    name: str

    async def align(self, transcript: Transcript, audio_path: Path) -> Transcript:
        """Align transcript words with exact start/end timestamps."""
        ...


@runtime_checkable
class DiarizationEngine(Protocol):
    """Abstract interface for speaker diarization tools (e.g. pyannote)."""

    name: str

    async def diarize(self, audio_path: Path) -> list[TranscriptSegment]:
        """Separate audio into speaker-attributed time segments."""
        ...


@runtime_checkable
class SpeakerIdentifier(Protocol):
    """Abstract interface for persistent speaker identification."""

    name: str

    async def identify(self, segment: TranscriptSegment, audio_path: Path) -> str:
        """Match a segment's voice embedding against persistent speaker database."""
        ...


@runtime_checkable
class KnowledgeExtractor(Protocol):
    """Abstract interface for LLM-based structured knowledge extraction."""

    name: str

    async def extract(self, transcript: Transcript) -> ExtractionResult:
        """Extract decisions, action items, technologies, and relationships."""
        ...


@runtime_checkable
class MarkdownExporter(Protocol):
    """Abstract interface for Markdown file generation."""

    name: str

    async def export(
        self,
        meeting: Meeting,
        transcript: Transcript,
        extraction: ExtractionResult,
        output_dir: Path,
    ) -> Path:
        """Generate structured Markdown knowledge base files."""
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Abstract interface for text embedding models."""

    name: str

    async def embed(self, text: str) -> list[float]:
        """Embed text into a vector representation."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into vector representations."""
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """Abstract interface for local/remote LLM generation."""

    name: str

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate text response from LLM."""
        ...
