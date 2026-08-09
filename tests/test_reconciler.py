"""Unit tests for transcript-diarization temporal reconciler."""

from neural_agent_os.domain.entities import Transcript, TranscriptSegment
from neural_agent_os.domain.reconciler import compute_time_overlap, reconcile_transcript_with_diarization


def test_compute_time_overlap() -> None:
    assert compute_time_overlap(0.0, 5.0, 3.0, 8.0) == 2.0
    assert compute_time_overlap(0.0, 2.0, 3.0, 5.0) == 0.0
    assert compute_time_overlap(1.0, 4.0, 0.0, 10.0) == 3.0


def test_reconcile_transcript_with_diarization() -> None:
    transcript_segments = [
        TranscriptSegment(
            meeting_id="m1",
            speaker_id="UNKNOWN",
            start=0.5,
            end=4.0,
            text="Hello everyone",
        ),
        TranscriptSegment(
            meeting_id="m1",
            speaker_id="UNKNOWN",
            start=4.5,
            end=8.0,
            text="How are you",
        ),
    ]
    raw_transcript = Transcript(meeting_id="m1", segments=transcript_segments)

    diar_segments = [
        TranscriptSegment(
            meeting_id="m1",
            speaker_id="Speaker A",
            start=0.0,
            end=4.2,
            text="",
        ),
        TranscriptSegment(
            meeting_id="m1",
            speaker_id="Speaker B",
            start=4.3,
            end=9.0,
            text="",
        ),
    ]

    reconciled = reconcile_transcript_with_diarization(raw_transcript, diar_segments)

    assert len(reconciled.segments) == 2
    assert reconciled.segments[0].speaker_id == "Speaker A"
    assert reconciled.segments[1].speaker_id == "Speaker B"
