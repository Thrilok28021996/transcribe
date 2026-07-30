"""Unit tests for core domain entities."""

import pytest
from pydantic import ValidationError
from transcribe.domain.entities import (
    Decision,
    Meeting,
    Speaker,
    Task,
    Transcript,
    TranscriptSegment,
    TranscriptWord,
)


def test_transcript_word_validation() -> None:
    word = TranscriptWord(word="hello", start=0.0, end=0.5, confidence=0.99)
    assert word.word == "hello"
    assert word.start == 0.0
    assert word.end == 0.5
    assert word.confidence == 0.99

    with pytest.raises(ValidationError):
        TranscriptWord(word="test", start=-1.0, end=1.0)


def test_transcript_full_text_property() -> None:
    seg1 = TranscriptSegment(
        meeting_id="m1",
        speaker_id="Alice",
        start=0.0,
        end=2.0,
        text="Hello world",
    )
    seg2 = TranscriptSegment(
        meeting_id="m1",
        speaker_id="Bob",
        start=2.5,
        end=4.0,
        text="Hi Alice",
    )
    transcript = Transcript(meeting_id="m1", segments=[seg1, seg2])
    text = transcript.full_text

    assert "[Alice (0.0s-2.0s)]: Hello world" in text
    assert "[Bob (2.5s-4.0s)]: Hi Alice" in text


def test_speaker_creation() -> None:
    speaker = Speaker(name="Alice Smith", aliases=["Alice S."])
    assert speaker.name == "Alice Smith"
    assert "Alice S." in speaker.aliases
    assert speaker.id is not None


def test_decision_and_task_entities() -> None:
    decision = Decision(
        meeting_id="m1",
        description="Use Python",
        owner="Alice",
        confidence=0.95,
    )
    assert decision.description == "Use Python"
    assert decision.confidence == 0.95

    task = Task(
        meeting_id="m1",
        description="Setup repo",
        owner="Bob",
        deadline="Friday",
    )
    assert task.status == "pending"
    assert task.deadline == "Friday"
