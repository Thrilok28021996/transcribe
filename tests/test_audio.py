"""Unit tests for audio processor and ffmpeg utilities."""

from pathlib import Path
import pytest
from transcribe.infrastructure.audio import AudioMetadata, AudioProcessor


def test_validate_format_success(tmp_path: Path) -> None:
    processor = AudioProcessor()
    dummy_wav = tmp_path / "sample.wav"
    dummy_wav.write_bytes(b"dummy wav data")

    validated = processor.validate_format(dummy_wav)
    assert validated == dummy_wav.resolve()


def test_validate_format_unsupported(tmp_path: Path) -> None:
    processor = AudioProcessor()
    dummy_txt = tmp_path / "sample.txt"
    dummy_txt.write_bytes(b"some text")

    with pytest.raises(ValueError, match="Unsupported audio format"):
        processor.validate_format(dummy_txt)


def test_get_metadata_fallback(tmp_path: Path) -> None:
    processor = AudioProcessor()
    dummy_mp3 = tmp_path / "test.mp3"
    dummy_mp3.write_bytes(b"dummy mp3 data")

    metadata = processor.get_metadata(dummy_mp3)
    assert isinstance(metadata, AudioMetadata)
    assert metadata.sample_rate == 16000
    assert metadata.channels == 1
    assert metadata.format_name == "mp3"


def test_prepare_for_whisper_creates_wav(tmp_path: Path) -> None:
    processor = AudioProcessor()
    dummy_src = tmp_path / "input.mp3"
    # Create valid minimal WAV header for ffmpeg input testing
    dummy_src.write_bytes(
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )

    out_wav = processor.prepare_for_whisper(dummy_src, target_dir=tmp_path)
    assert out_wav.exists()
    assert out_wav.name == "input_16k_mono.wav"
