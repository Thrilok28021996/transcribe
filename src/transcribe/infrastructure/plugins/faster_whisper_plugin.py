"""Faster-Whisper speech recognition plugin implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from transcribe.domain.entities import Transcript, TranscriptSegment, TranscriptWord
from transcribe.infrastructure.audio import AudioProcessor
from transcribe.infrastructure.logging import get_logger

logger = get_logger(__name__)


class FasterWhisperSpeechRecognizer:
    """SpeechRecognizer adapter backed by CTranslate2 faster-whisper engine."""

    name: str = "faster-whisper"

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "default",
        language: str | None = "en",
        audio_processor: AudioProcessor | None = None,
    ) -> None:
        self.model_size = model_size
        self.device = self._resolve_device(device)
        self.compute_type = compute_type
        self.language = language
        self.audio_processor = audio_processor or AudioProcessor()
        self._model: Any = None

    def _resolve_device(self, device: str) -> str:
        """Resolve 'auto' device selection for host hardware (Apple Silicon / CPU / CUDA)."""
        if device == "auto":
            # On macOS (Darwin / Apple Silicon), CTranslate2 runs on CPU with optimal quantization
            import platform
            if platform.system() == "Darwin":
                return "cpu"
            return "cpu"
        return device

    def _load_model(self) -> Any:
        """Lazy load the WhisperModel instance."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as err:
                raise ImportError(
                    "faster-whisper package is not installed. Install via 'pip install faster-whisper'."
                ) from err

            logger.info(
                f"Loading Faster-Whisper model '{self.model_size}' (device={self.device}, compute_type={self.compute_type})..."
            )
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    async def transcribe(self, audio_path: Path) -> Transcript:
        """Transcribe audio file into Transcript entity with word alignment timestamps asynchronously."""
        import asyncio

        def _sync_transcribe() -> Transcript:
            path = Path(audio_path).resolve()
            wav_path = self.audio_processor.prepare_for_whisper(path)

            model = self._load_model()
            logger.info(f"Transcribing audio '{wav_path.name}' with Faster-Whisper...")

            segments_iter, info = model.transcribe(
                str(wav_path),
                language=self.language,
                word_timestamps=True,
                beam_size=5,
                vad_filter=True,  # Filter non-speech segments using Silero VAD
            )

            domain_segments: list[TranscriptSegment] = []
            meeting_id = path.stem

            import math

            for seg in segments_iter:
                words: list[TranscriptWord] = []
                if seg.words:
                    for w in seg.words:
                        w_prob = float(getattr(w, "probability", 1.0))
                        w_conf = round(min(max(w_prob, 0.0), 1.0), 2)
                        words.append(
                            TranscriptWord(
                                word=w.word.strip(),
                                start=round(float(w.start), 2),
                                end=round(float(w.end), 2),
                                confidence=w_conf,
                            )
                        )

                raw_logprob = float(getattr(seg, "avg_logprob", 0.0))
                seg_conf = round(min(max(math.exp(raw_logprob), 0.0), 1.0), 2)

                domain_segments.append(
                    TranscriptSegment(
                        meeting_id=meeting_id,
                        speaker_id="UNKNOWN",  # Will be assigned by Diarization & Speaker Identification
                        start=round(float(seg.start), 2),
                        end=round(float(seg.end), 2),
                        text=seg.text.strip(),
                        words=words,
                        confidence=seg_conf,
                    )
                )

            detected_lang = getattr(info, "language", self.language or "en")
            lang_probability = getattr(info, "language_probability", 1.0)

            logger.info(
                f"Transcription finished: {len(domain_segments)} segments detected (language={detected_lang}, prob={lang_probability:.2f})"
            )

            return Transcript(
                meeting_id=meeting_id,
                segments=domain_segments,
                language=detected_lang,
                confidence=round(float(lang_probability), 2),
                metadata={
                    "engine": self.name,
                    "model_size": self.model_size,
                    "device": self.device,
                    "audio_file": str(path),
                },
            )

        return await asyncio.to_thread(_sync_transcribe)
