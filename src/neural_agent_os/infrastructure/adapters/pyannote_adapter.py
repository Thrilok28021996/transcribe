"""Adapter bridging PyAnnoteDiarizationPlugin to the DiarizationEngine Protocol."""

from __future__ import annotations

import uuid
from pathlib import Path

from neural_agent_os.domain.entities import TranscriptSegment
from neural_agent_os.infrastructure.logging import get_logger
from neural_agent_os.infrastructure.plugins.pyannote_diarization_plugin import PyAnnoteDiarizationPlugin

logger = get_logger(__name__)


class PyAnnoteDiarizationAdapter:
    """Wraps PyAnnoteDiarizationPlugin to satisfy the DiarizationEngine Protocol interface."""

    name: str = "pyannote"

    def __init__(self, plugin: PyAnnoteDiarizationPlugin) -> None:
        self.plugin = plugin

    async def diarize(self, audio_path: Path) -> list[TranscriptSegment]:
        """Run real pyannote diarization and return TranscriptSegment list."""
        try:
            raw_segments = self.plugin.diarize(audio_path)
            result: list[TranscriptSegment] = []
            for seg in raw_segments:
                result.append(
                    TranscriptSegment(
                        id=str(uuid.uuid4()),
                        meeting_id=audio_path.stem,
                        speaker_id=seg.speaker,
                        start=seg.start,
                        end=seg.end,
                        text="",  # Filled by reconcile_transcript_with_diarization
                        confidence=1.0,
                    )
                )
            logger.info(
                f"PyAnnote adapter produced {len(result)} diarization segments "
                f"({len({s.speaker_id for s in result})} unique speakers)"
            )
            return result
        except Exception as err:
            logger.error(f"PyAnnote diarization adapter error: {err}")
            return []
