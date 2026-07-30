"""Integration tests for FastAPI Web UX server endpoints."""

import pytest
from fastapi.testclient import TestClient
from transcribe.application.container import ServiceContainer
from transcribe.infrastructure.config import load_config
from transcribe.web.app import create_app


@pytest.fixture
def client(tmp_path) -> TestClient:
    config = load_config()
    config.storage.base_dir = tmp_path / "data"
    config.storage.markdown_dir = tmp_path / "data" / "markdown"
    config.storage.speakers_dir = tmp_path / "data" / "speakers"
    config.storage.base_dir.mkdir(parents=True, exist_ok=True)
    config.storage.markdown_dir.mkdir(parents=True, exist_ok=True)
    config.storage.speakers_dir.mkdir(parents=True, exist_ok=True)

    container = ServiceContainer(config=config)
    app = create_app(container=container)
    return TestClient(app)


def test_web_stats_endpoint(client: TestClient) -> None:
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_meetings" in data
    assert "total_speakers" in data
    assert "vector_documents" in data


def test_web_meetings_endpoint(client: TestClient) -> None:
    res = client.get("/api/meetings")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_web_speakers_endpoint(client: TestClient) -> None:
    res = client.get("/api/speakers")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_web_graph_endpoint(client: TestClient) -> None:
    res = client.get("/api/graph")
    assert res.status_code == 200
    data = res.json()
    assert "stats" in data
    assert "nodes" in data
