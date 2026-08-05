"""Unit tests for configuration system."""

from pathlib import Path

from transcribe.infrastructure.config import load_config


def test_default_config(tmp_path: Path) -> None:
    config = load_config()
    assert config.app_name == "Transcribe AI"
    assert config.speech.provider == "faster-whisper"
    assert config.llm.provider == "lm-studio"
    assert config.storage.base_dir.exists()


def test_custom_yaml_config(tmp_path: Path) -> None:
    yaml_file = tmp_path / "custom_config.yaml"
    yaml_content = """
environment: production
speech:
  provider: faster-whisper
  model_size: medium
llm:
  provider: ollama
  model_name: llama3.1
"""
    yaml_file.write_text(yaml_content, encoding="utf-8")

    config = load_config(config_path=yaml_file)
    assert config.environment == "production"
    assert config.speech.provider == "faster-whisper"
    assert config.speech.model_size == "medium"
    assert config.llm.provider == "ollama"
    assert config.llm.model_name == "llama3.1"
