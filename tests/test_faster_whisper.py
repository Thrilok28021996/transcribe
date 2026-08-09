"""Unit and integration tests for FasterWhisperSpeechRecognizer."""

from neural_agent_os.infrastructure.plugins.faster_whisper_plugin import (
    FasterWhisperSpeechRecognizer,
)


def test_faster_whisper_device_resolution() -> None:
    recognizer = FasterWhisperSpeechRecognizer(model_size="tiny", device="auto")
    assert recognizer.device == "cpu"
    assert recognizer.name == "faster-whisper"


def test_faster_whisper_initialization() -> None:
    recognizer = FasterWhisperSpeechRecognizer(
        model_size="tiny",
        device="cpu",
        compute_type="int8",
        language="en",
    )
    assert recognizer.model_size == "tiny"
    assert recognizer.compute_type == "int8"
    assert recognizer.language == "en"
