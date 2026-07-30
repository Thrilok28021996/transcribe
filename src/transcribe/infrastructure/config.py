"""Configuration management system for Transcribe AI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AudioConfig(BaseModel):
    """Audio ingestion settings."""
    sample_rate: int = 16000
    channels: int = 1  # mono
    format_supported: list[str] = Field(
        default_factory=lambda: ["wav", "mp3", "m4a", "aac", "mp4"]
    )


import os
os.environ["HF_HOME"] = "/Volumes/personal/huggingface"


class SpeechConfig(BaseModel):
    """Speech recognition plugin settings."""
    provider: str = "faster-whisper"  # e.g., "faster-whisper", "whisper.cpp", "mock"
    model_size: str = "large-v3-turbo"
    device: Literal["cpu", "cuda", "mps", "auto"] = "auto"
    compute_type: str = "default"
    language: str = "en"
    download_root: str = "/Volumes/personal/huggingface"


class DiarizationConfig(BaseModel):
    """Speaker diarization plugin settings."""
    provider: str = "mock"  # e.g., "pyannote", "mock"
    min_speakers: int | None = None
    max_speakers: int | None = None


class LLMConfig(BaseModel):
    """LLM provider settings for extraction and assistant."""
    provider: str = "lm-studio"  # e.g., "lm-studio", "ollama", "mock"
    model_name: str = "default"
    api_base: str = "http://localhost:1234/v1"
    temperature: float = 0.1
    max_tokens: int = 2048


class VectorStoreConfig(BaseModel):
    """Vector database configuration."""
    provider: str = "mock"  # e.g., "qdrant", "chroma", "mock"
    collection_name: str = "meeting_knowledge"
    host: str = "localhost"
    port: int = 6333
    storage_path: Path = Path("./data/qdrant")


class StorageConfig(BaseModel):
    """File storage and output directory settings."""
    base_dir: Path = Path("./data")
    meetings_dir: Path = Path("./data/meetings")
    recordings_dir: Path = Path("./data/recordings")
    speakers_dir: Path = Path("./data/speakers")
    markdown_dir: Path = Path("./data/markdown")


class AppConfig(BaseSettings):
    """Global application configuration."""
    model_config = SettingsConfigDict(
        env_prefix="TRANSCRIBE_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    app_name: str = "Transcribe AI"
    environment: str = "development"
    debug: bool = False

    audio: AudioConfig = Field(default_factory=AudioConfig)
    speech: SpeechConfig = Field(default_factory=SpeechConfig)
    diarization: DiarizationConfig = Field(default_factory=DiarizationConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    vector_store: VectorStoreConfig = Field(default_factory=VectorStoreConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)


def load_config(config_path: Path | str | None = None) -> AppConfig:
    """Load configuration from YAML file and override with env variables."""
    config_dict: dict[str, Any] = {}

    if config_path:
        path = Path(config_path)
        if path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    config_dict = loaded

    # Expand relative storage paths if needed
    config = AppConfig(**config_dict)

    # Ensure output directories exist
    config.storage.base_dir.mkdir(parents=True, exist_ok=True)
    config.storage.meetings_dir.mkdir(parents=True, exist_ok=True)
    config.storage.recordings_dir.mkdir(parents=True, exist_ok=True)
    config.storage.speakers_dir.mkdir(parents=True, exist_ok=True)
    config.storage.markdown_dir.mkdir(parents=True, exist_ok=True)

    return config
