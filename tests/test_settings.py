"""Unit tests for settings management, model updates, CLI config-set, and REST API."""

from pathlib import Path
from click.testing import CliRunner
from fastapi.testclient import TestClient

from transcribe.cli.main import cli
from transcribe.infrastructure.config import load_config, save_config
from transcribe.web.app import create_app


def test_save_and_load_config(tmp_path: Path) -> None:
    cfg = load_config()
    cfg.speech.model_size = "medium"
    cfg.llm.model_name = "test-qwen"

    custom_yaml = tmp_path / "custom_test.yaml"
    save_config(cfg, config_path=custom_yaml)

    assert custom_yaml.exists()
    reloaded = load_config(config_path=custom_yaml)
    assert reloaded.speech.model_size == "medium"
    assert reloaded.llm.model_name == "test-qwen"


def test_cli_config_set() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "config-set",
            "--stt-model", "small",
            "--stt-device", "cpu",
            "--llm-model", "qwen2.5-7b-instruct",
        ],
    )
    assert result.exit_code == 0
    assert "Configuration updated and saved" in result.output


def test_web_settings_get_and_post() -> None:
    app = create_app()
    client = TestClient(app)

    # Test GET /api/settings
    get_res = client.get("/api/settings")
    assert get_res.status_code == 200
    data = get_res.json()
    assert "speech" in data
    assert "llm" in data
    assert "available_models" in data["speech"]
    assert "available_models" in data["llm"]

    # Test POST /api/settings
    post_res = client.post(
        "/api/settings",
        json={
            "storage_dir": str(app.state.container.config.storage.base_dir) if hasattr(app.state, "container") else "./data",
            "stt_model_size": "large-v3-turbo",
            "stt_device": "auto",
            "llm_model_name": "llama-3.2-3b-instruct",
        },
    )
    assert post_res.status_code == 200
    res_data = post_res.json()
    assert res_data["success"] is True
    assert "storage_dir" in res_data
    assert res_data["speech"]["model_size"] == "large-v3-turbo"
    assert res_data["llm"]["model_name"] == "llama-3.2-3b-instruct"
def test_huggingface_custom_stt_model() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "config-set",
            "--stt-model", "Systran/faster-whisper-large-v3",
        ],
    )
    assert result.exit_code == 0
    assert "Configuration updated and saved" in result.output

    app = create_app()
    client = TestClient(app)
    post_res = client.post(
        "/api/settings",
        json={
            "stt_model_size": "deepdml/faster-whisper-large-v3-turbo-ct2",
        },
    )
    assert post_res.status_code == 200
    res_data = post_res.json()
    assert res_data["speech"]["model_size"] == "deepdml/faster-whisper-large-v3-turbo-ct2"
