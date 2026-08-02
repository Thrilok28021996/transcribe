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


def default_storage_base_dir() -> Path:
    """Return default storage root directory (~/.transcribe or env var)."""
    env_dir = os.environ.get("TRANSCRIBE_STORAGE_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return (Path.home() / ".transcribe").resolve()


class StorageConfig(BaseModel):
    """File storage and output directory settings."""
    base_dir: Path = Field(default_factory=default_storage_base_dir)
    meetings_dir: Path | None = None
    recordings_dir: Path | None = None
    speakers_dir: Path | None = None
    markdown_dir: Path | None = None


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


def load_config(config_path: Path | str | None = None, storage_dir: Path | str | None = None) -> AppConfig:
    """Load configuration from YAML file and override with env variables or custom storage_dir."""
    config_dict: dict[str, Any] = {}

    if config_path:
        path = Path(config_path)
        if path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    config_dict = loaded

    config = AppConfig(**config_dict)

    if storage_dir:
        config.storage.base_dir = Path(storage_dir).expanduser().resolve()

    b_dir = config.storage.base_dir
    config.storage.meetings_dir = b_dir / "meetings"
    config.storage.recordings_dir = b_dir / "recordings"
    config.storage.speakers_dir = b_dir / "speakers"
    config.storage.markdown_dir = b_dir / "markdown"

    # Ensure storage output directories exist
    b_dir.mkdir(parents=True, exist_ok=True)
    config.storage.meetings_dir.mkdir(parents=True, exist_ok=True)
    config.storage.recordings_dir.mkdir(parents=True, exist_ok=True)
    config.storage.speakers_dir.mkdir(parents=True, exist_ok=True)
    config.storage.markdown_dir.mkdir(parents=True, exist_ok=True)

    return config


def save_config(config: AppConfig, config_path: Path | str | None = None) -> Path:
    """Save configuration model to YAML file."""
    target_path = Path(config_path) if config_path else Path("transcribe.yaml")
    data = config.model_dump(mode="json")
    with open(target_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
    return target_path


def cleanup_storage(config: AppConfig, delete_recordings: bool = True, delete_all: bool = False) -> dict[str, int]:
    """Clean up accumulated raw audio recordings, vector DBs, knowledge graphs, and storage files."""
    import shutil

    freed_bytes = 0
    deleted_files = 0

    candidate_bases = [
        config.storage.base_dir.resolve(),
        Path("./data").resolve(),
        (Path.home() / ".transcribe").resolve(),
    ]

    seen_bases: set[Path] = set()

    for base_path in candidate_bases:
        if not base_path or not base_path.exists() or base_path in seen_bases:
            continue
        seen_bases.add(base_path)

        dirs_to_clean: list[Path] = []
        if delete_recordings or delete_all:
            dirs_to_clean.append(base_path / "recordings")
        if delete_all:
            dirs_to_clean.extend([
                base_path / "meetings",
                base_path / "speakers",
                base_path / "markdown",
                base_path / "vector_db",
                base_path / "graph_db",
                base_path / "qdrant",
            ])

        for target_dir in dirs_to_clean:
            if target_dir.exists():
                for p in list(target_dir.rglob("*")):
                    try:
                        if p.is_file():
                            freed_bytes += p.stat().st_size
                            p.unlink()
                            deleted_files += 1
                    except Exception:
                        pass
                try:
                    shutil.rmtree(target_dir, ignore_errors=True)
                except Exception:
                    pass

        if delete_all:
            for pattern in ["*graph.json", "*vectors.json", "*speakers.json", "*.db"]:
                for target_file in list(base_path.rglob(pattern)):
                    if target_file.is_file():
                        try:
                            freed_bytes += target_file.stat().st_size
                            target_file.unlink()
                            deleted_files += 1
                        except Exception:
                            pass


    return {"deleted_files": deleted_files, "freed_bytes": freed_bytes}




