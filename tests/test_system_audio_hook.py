"""Unit and integration tests for SystemAudioHook, CLI audio commands, and web endpoints."""

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from transcribe.cli.main import cli
from transcribe.infrastructure.system_audio_hook import (
    AudioDeviceInfo,
    SystemAudioHook,
    SystemAudioSetupStatus,
)
from transcribe.web.app import create_app


def test_system_audio_hook_list_devices() -> None:
    hook = SystemAudioHook()
    devices = hook.list_devices()
    assert isinstance(devices, list)
    assert len(devices) > 0
    assert isinstance(devices[0], AudioDeviceInfo)
    assert devices[0].id is not None
    assert devices[0].kind in ["input", "loopback", "unknown"]


def test_system_audio_hook_setup_status() -> None:
    hook = SystemAudioHook()
    status = hook.get_setup_status()
    assert isinstance(status, SystemAudioSetupStatus)
    assert isinstance(status.is_ready, bool)
    assert len(status.recommendations) > 0


def test_system_audio_hook_build_record_cmd_modes(tmp_path: Path) -> None:
    hook = SystemAudioHook()
    out_wav = tmp_path / "test_out.wav"

    # Mic mode
    cmd_mic = hook.build_ffmpeg_record_cmd(out_wav, duration_seconds=5, mode="mic")
    assert "ffmpeg" in cmd_mic[0]
    assert str(out_wav.resolve()) in cmd_mic

    # System mode
    cmd_sys = hook.build_ffmpeg_record_cmd(out_wav, duration_seconds=5, mode="system")
    assert str(out_wav.resolve()) in cmd_sys

    # Mixed mode
    cmd_mix = hook.build_ffmpeg_record_cmd(out_wav, duration_seconds=5, mode="mixed")
    assert str(out_wav.resolve()) in cmd_mix


def test_system_audio_hook_record_fallback(tmp_path: Path) -> None:
    hook = SystemAudioHook()
    out_wav = tmp_path / "captured.wav"
    res_path = hook.record(output_path=out_wav, duration_seconds=1, mode="mic")
    assert res_path.exists()
    assert res_path.stat().st_size > 0


def test_cli_audio_devices() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["audio-devices"])
    assert result.exit_code == 0
    assert "Detected System Audio & Loopback Devices" in result.output
    assert "Teams/Zoom Call Capture Diagnostics" in result.output


def test_cli_record_with_system_audio_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSCRIBE_SPEECH__PROVIDER", "mock")
    monkeypatch.setenv("TRANSCRIBE_LLM__PROVIDER", "mock")
    from transcribe.infrastructure.config import default_storage_base_dir
    rec_dir = default_storage_base_dir() / "recordings"
    rec_dir.mkdir(parents=True, exist_ok=True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["record", "--duration", "1", "--mode", "mixed", "--title", "Teams Weekly Sync"],
    )
    assert result.exit_code == 0
    assert "Recording live meeting audio" in result.output
    assert "✓ Meeting processed!" in result.output or "✓ Live audio capture complete!" in result.output


def test_web_audio_devices_endpoint() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/audio/devices")
    assert response.status_code == 200
    data = response.json()
    assert "devices" in data
    assert "setup_status" in data
    assert len(data["devices"]) > 0


def test_web_backend_recording_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSCRIBE_SPEECH__PROVIDER", "mock")
    monkeypatch.setenv("TRANSCRIBE_LLM__PROVIDER", "mock")
    app = create_app()
    client = TestClient(app)

    class MockProcess:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
        def __enter__(self) -> "MockProcess":
            return self
        def __exit__(self, *args: object) -> None:
            pass
        def poll(self) -> None:
            return None
        def terminate(self) -> None:
            pass
        def wait(self, timeout: float | None = None) -> None:
            pass
        def kill(self) -> None:
            pass
        def communicate(self, *args: Any, **kwargs: Any) -> tuple[bytes, bytes]:
            return b"", b""
        @property
        def stderr(self) -> Any:
            class DummyStream:
                def read(self) -> bytes:
                    return b""
            return DummyStream()
        @property
        def stdout(self) -> Any:
            class DummyStream:
                def read(self) -> bytes:
                    return b""
            return DummyStream()

    import subprocess
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: MockProcess())

    start_resp = client.post("/api/audio/record_start", data={"mode": "mic"})
    assert start_resp.status_code == 200
    start_data = start_resp.json()
    assert start_data["status"] == "started"
    assert "filename" in start_data

    stop_resp = client.post("/api/audio/record_stop", data={"title": "Test Web Backend Meeting"})
    assert stop_resp.status_code == 200
    stop_data = stop_resp.json()
    assert "meeting_id" in stop_data
    assert stop_data["title"] == "Test Web Backend Meeting"


