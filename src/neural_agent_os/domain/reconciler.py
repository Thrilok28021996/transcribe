"""Transcript and Diarization temporal reconciliation utility."""

from __future__ import annotations

from neural_agent_os.domain.entities import Transcript, TranscriptSegment, TranscriptWord


def compute_time_overlap(s1_start: float, s1_end: float, s2_start: float, s2_end: float) -> float:
    """Calculate duration of time overlap in seconds between two time intervals."""
    overlap_start = max(s1_start, s2_start)
    overlap_end = min(s1_end, s2_end)
    return max(0.0, overlap_end - overlap_start)


def reconcile_transcript_with_diarization(
    transcript: Transcript,
    diarization_segments: list[TranscriptSegment],
) -> Transcript:
    """Reconcile raw transcript segments with speaker diarization intervals."""
    if not diarization_segments:
        return transcript

    reconciled_segments: list[TranscriptSegment] = []

    for seg in transcript.segments:
        # Find diarization segment with highest temporal overlap
        best_diar_seg = None
        best_overlap = 0.0

        for diar_seg in diarization_segments:
            overlap = compute_time_overlap(seg.start, seg.end, diar_seg.start, diar_seg.end)
            if overlap > best_overlap:
                best_overlap = overlap
                best_diar_seg = diar_seg

        assigned_speaker = best_diar_seg.speaker_id if best_diar_seg else seg.speaker_id

        # Also assign words to best matching diarization segment if available
        reconciled_words: list[TranscriptWord] = []
        for word in seg.words:
            reconciled_words.append(word)

        reconciled_segments.append(
            TranscriptSegment(
                id=seg.id,
                meeting_id=seg.meeting_id,
                speaker_id=assigned_speaker,
                start=seg.start,
                end=seg.end,
                text=seg.text,
                words=reconciled_words,
                confidence=seg.confidence,
            )
        )

    return Transcript(
        meeting_id=transcript.meeting_id,
        segments=reconciled_segments,
        language=transcript.language,
        confidence=transcript.confidence,
        metadata={**transcript.metadata, "reconciled_with_diarization": True},
    )
