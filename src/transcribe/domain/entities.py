"""Core domain entities for the meeting memory platform."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class TranscriptWord(BaseModel):
    """Word-level alignment timestamp."""
    model_config = ConfigDict(frozen=True)

    word: str
    start: float = Field(..., ge=0.0, description="Start time in seconds")
    end: float = Field(..., ge=0.0, description="End time in seconds")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score [0, 1]")


class TranscriptSegment(BaseModel):
    """Diarized and aligned segment of speech."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    meeting_id: str
    speaker_id: str = Field(default="UNKNOWN", description="Speaker ID or identifier label")
    start: float = Field(..., ge=0.0, description="Start time in seconds")
    end: float = Field(..., ge=0.0, description="End time in seconds")
    text: str = Field(..., description="Transcript text segment")
    words: list[TranscriptWord] = Field(default_factory=list)
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score [0, 1]")


class Transcript(BaseModel):
    """Complete transcript container for a meeting."""
    model_config = ConfigDict(frozen=True)

    meeting_id: str
    segments: list[TranscriptSegment] = Field(default_factory=list)
    language: str = Field(default="en", description="Detected or specified language code")
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    metadata: dict[str, str | float | int | bool] = Field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Concatenated plain text of all segments."""
        return "\n".join(
            f"[{seg.speaker_id} ({seg.start:.1f}s-{seg.end:.1f}s)]: {seg.text}"
            for seg in self.segments
        )


class Speaker(BaseModel):
    """Persistent speaker entity across meetings."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., min_length=1)
    aliases: list[str] = Field(default_factory=list)
    embedding: list[float] | None = Field(default=None, description="Voice embedding vector")
    confidence_history: list[float] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, str | float | int | bool] = Field(default_factory=dict)


class Meeting(BaseModel):
    """Meeting entity representing an ingested audio/video session."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    audio_path: str = Field(..., description="Path to the ingested audio file")
    duration_seconds: float = Field(0.0, ge=0.0)
    speaker_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, str | float | int | bool] = Field(default_factory=dict)


class Decision(BaseModel):
    """Decision extracted from meeting context."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    meeting_id: str
    description: str
    owner: str | None = Field(default=None, description="Speaker or person associated with decision")
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    context_snippet: str | None = Field(default=None)


class Task(BaseModel):
    """Action item / task extracted from meeting."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    meeting_id: str
    description: str
    owner: str | None = Field(default=None)
    deadline: str | None = Field(default=None)
    status: str = Field(default="pending", description="Task status (e.g. pending, completed)")
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class Project(BaseModel):
    """Project entity discussed across meetings."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str | None = Field(default=None)


class Technology(BaseModel):
    """Technology or tool referenced in meetings."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str | None = Field(default=None)


class Organization(BaseModel):
    """Organization entity referenced in meetings."""
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str


class Relationship(BaseModel):
    """Typed relationship in the Knowledge Graph."""
    model_config = ConfigDict(frozen=True)

    source_id: str
    source_type: str  # e.g., "Person", "Project", "Meeting"
    target_id: str
    target_type: str  # e.g., "Task", "Technology", "Topic"
    relation_type: str  # e.g., "owns", "depends_on", "uses", "discusses"
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class ExtractionResult(BaseModel):
    """Structured knowledge extraction output container."""
    model_config = ConfigDict(frozen=True)

    meeting_id: str
    decisions: list[Decision] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    technologies: list[Technology] = Field(default_factory=list)
    organizations: list[Organization] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)
    summary: str = Field(default="")
