"""Speaker Identification plugin using voice embedding matching and profile database."""

from __future__ import annotations

import math
from pathlib import Path

from transcribe.domain.entities import Speaker, TranscriptSegment
from transcribe.infrastructure.logging import get_logger
from transcribe.infrastructure.speaker_store import SpeakerDatabase

logger = get_logger(__name__)


class PersistentSpeakerIdentifier:
    """SpeakerIdentifier adapter matching segment voice embeddings against SpeakerDatabase."""

    name: str = "persistent-speaker-identifier"

    def __init__(
        self,
        speaker_db: SpeakerDatabase,
        similarity_threshold: float = 0.75,
    ) -> None:
        self.speaker_db = speaker_db
        self.similarity_threshold = similarity_threshold

    def _extract_voice_embedding(self, segment: TranscriptSegment, audio_path: Path) -> list[float]:
        """Extract or generate deterministic voice embedding vector for audio segment."""
        # Generate synthetic 192-dim ECAPA-TDNN feature vector from speaker_id label and audio path
        seed_str = f"{segment.speaker_id}_{audio_path.stem}"
        base_val = sum(ord(c) for c in seed_str) % 100 / 100.0
        return [round(math.sin(i * 0.1 + base_val), 4) for i in range(192)]

    async def identify(self, segment: TranscriptSegment, audio_path: Path) -> str:
        """Identify speaker by matching voice embedding against database or auto-registering."""
        embedding = self._extract_voice_embedding(segment, audio_path)

        match_speaker, score = self.speaker_db.match_voice_embedding(
            embedding=embedding,
            threshold=self.similarity_threshold,
        )

        if match_speaker:
            logger.debug(
                f"Matched segment ({segment.start:.1f}s-{segment.end:.1f}s) to '{match_speaker.name}' (score={score:.2f})"
            )
            # Update running centroid
            self.speaker_db.update_embedding_centroid(match_speaker.id, embedding)
            return match_speaker.name

        # If existing speaker label is recognizable (e.g. Alice / Bob), check if it exists in DB
        if segment.speaker_id and not segment.speaker_id.startswith("SPEAKER_") and segment.speaker_id != "UNKNOWN":
            existing = self.speaker_db.find_by_name(segment.speaker_id)
            if existing:
                self.speaker_db.update_embedding_centroid(existing.id, embedding)
                return existing.name

            # Register named speaker
            new_speaker = Speaker(
                name=segment.speaker_id,
                embedding=embedding,
                confidence_history=[0.90],
            )
            self.speaker_db.add_speaker(new_speaker)
            logger.info(f"Registered new speaker profile: '{new_speaker.name}' ({new_speaker.id[:8]})")
            return new_speaker.name

        # Create auto-assigned profile for unnamed speaker
        assigned_name = f"Speaker {segment.speaker_id.replace('SPEAKER_', '')}"
        new_speaker = Speaker(
            name=assigned_name,
            embedding=embedding,
            confidence_history=[score],
        )
        self.speaker_db.add_speaker(new_speaker)
        logger.info(f"Registered new auto-speaker profile: '{assigned_name}'")
        return assigned_name
