"""Integration tests for CLI interface."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from transcribe.cli.main import cli


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "Transcribe AI v0.1.0" in result.output


def test_cli_config_show() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["config-show"])
    assert result.exit_code == 0
    assert "System Configuration" in result.output
    assert "faster-whisper" in result.output or "mock" in result.output


def test_cli_plugins_list() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["plugins-list"])
    assert result.exit_code == 0
    assert "Registered AI Plugins" in result.output
    assert "SpeechRecognizer" in result.output


def test_cli_process(tmp_path: Path) -> None:
    dummy_audio = tmp_path / "sample.mp3"
    dummy_audio.write_bytes(b"dummy audio content")

    runner = CliRunner()
    result = runner.invoke(cli, ["process", str(dummy_audio), "--title", "CLI Sync Meeting", "--provider", "mock"])

    assert result.exit_code == 0
    assert "CLI Sync Meeting" in result.output
    assert "Processing Summary" in result.output


def test_cli_search(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSCRIBE_SPEECH__PROVIDER", "mock")
    monkeypatch.setenv("TRANSCRIBE_LLM__PROVIDER", "mock")
    runner = CliRunner()
    result = runner.invoke(cli, ["search", "Python backend"])
    assert result.exit_code == 0
    assert "Semantic Search Results" in result.output


def test_cli_ask(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSCRIBE_SPEECH__PROVIDER", "mock")
    monkeypatch.setenv("TRANSCRIBE_LLM__PROVIDER", "mock")
    runner = CliRunner()
    result = runner.invoke(cli, ["ask", "What decisions were made?"])
    assert result.exit_code == 0
    assert "Querying Meeting Memory" in result.output

