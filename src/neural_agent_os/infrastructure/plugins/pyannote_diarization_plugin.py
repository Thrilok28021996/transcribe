"""Real speaker diarization plugin using pyannote.audio 3.1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neural_agent_os.infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DiarizationSegment:
    """A single speaker turn with timestamps."""
    speaker: str   # e.g. "SPEAKER_00", "SPEAKER_01"
    start: float   # seconds
    end: float     # seconds


class PyAnnoteDiarizationPlugin:
    """Real speaker diarization using pyannote.audio 3.1 pipeline.
    
    Requires:
        pip install pyannote.audio torch
        A Hugging Face token with access to pyannote/speaker-diarization-3.1
    """

    name: str = "pyannote"

    def __init__(
        self,
        hf_token: str,
        num_speakers: int | None = None,
    ) -> None:
        self.hf_token = hf_token
        self.num_speakers = num_speakers
        self._pipeline: Any = None

    def _load_pipeline(self) -> bool:
        """Lazily load the pyannote pipeline (downloads model on first use)."""
        if self._pipeline is not None:
            return True
        try:
            import torch  # type: ignore[import]
            from pyannote.audio import Pipeline  # type: ignore[import]

            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.hf_token,
            )
            # Use best available device
            if torch.backends.mps.is_available():
                device = torch.device("mps")
            elif torch.cuda.is_available():
                device = torch.device("cuda")
            else:
                device = torch.device("cpu")
            self._pipeline.to(device)
            logger.info(f"PyAnnote diarization pipeline loaded on device: {device}")
            return True
        except ImportError:
            logger.warning(
                "pyannote.audio not installed. Run: pip install pyannote.audio torch\n"
                "Then set your Hugging Face token in Settings."
            )
            return False
        except Exception as err:
            logger.error(f"Failed to load PyAnnote pipeline: {err}")
            return False

    def diarize(self, audio_path: Path) -> list[DiarizationSegment]:
        """Run diarization and return chronological list of speaker segments."""
        if not self._load_pipeline():
            return []
        try:
            kwargs: dict[str, Any] = {}
            if self.num_speakers:
                kwargs["num_speakers"] = self.num_speakers

            diarization = self._pipeline(str(audio_path), **kwargs)
            segments = [
                DiarizationSegment(
                    speaker=str(speaker),
                    start=round(float(turn.start), 2),
                    end=round(float(turn.end), 2),
                )
                for turn, _, speaker in diarization.itertracks(yield_label=True)
            ]
            segments.sort(key=lambda s: s.start)
            logger.info(f"PyAnnote diarization complete: {len(segments)} segments, {len({s.speaker for s in segments})} speakers")
            return segments
        except Exception as err:
            logger.error(f"PyAnnote diarization failed: {err}")
            return []
