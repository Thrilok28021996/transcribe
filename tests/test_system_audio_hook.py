"""Unit and integration tests for SystemAudioHook, CLI audio commands, and web endpoints."""

from pathlib import Path
from click.testing import CliRunner
from fastapi.testclient import TestClient
import pytest

from transcribe.cli.main import cli
from transcribe.infrastructure.system_audio_hook import AudioDeviceInfo, SystemAudioHook, SystemAudioSetupStatus
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


def test_cli_record_with_system_audio_mode() -> None:
    from transcribe.infrastructure.config import default_storage_base_dir
    rec_dir = default_storage_base_dir() / "recordings"
    rec_dir.mkdir(parents=True, exist_ok=True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["record", "--duration", "1", "--mode", "mixed", "--title", "Teams Weekly Sync"],
    )
    assert result.exit_code == 0
    assert "Recording live meeting audio (MIXED mode)" in result.output
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


def test_web_backend_recording_endpoints() -> None:
    app = create_app()
    client = TestClient(app)
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

