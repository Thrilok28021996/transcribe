"""Unit tests for storage path resolution and automatic data cleanup."""

from pathlib import Path

from click.testing import CliRunner

from neural_agent_os.cli.main import cli
from neural_agent_os.infrastructure.config import cleanup_storage, load_config


def test_default_storage_path_resolution(tmp_path: Path) -> None:
    cfg = load_config(storage_dir=tmp_path / "custom_app_data")
    assert cfg.storage.base_dir == (tmp_path / "custom_app_data").resolve()
    assert cfg.storage.recordings_dir == (tmp_path / "custom_app_data" / "recordings").resolve()
    assert cfg.storage.markdown_dir == (tmp_path / "custom_app_data" / "markdown").resolve()


def test_cleanup_storage_recordings(tmp_path: Path) -> None:
    cfg = load_config(storage_dir=tmp_path)
    dummy_rec = cfg.storage.recordings_dir / "sample_rec.wav"
    dummy_rec.write_bytes(b"dummy wav recording content")

    assert dummy_rec.exists()

    res = cleanup_storage(cfg, delete_recordings=True, delete_all=False)
    assert res["deleted_files"] >= 1
    assert not dummy_rec.exists()



def test_cli_cleanup(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["cleanup", "-r"])
    assert result.exit_code == 0
    assert "cleanup complete" in result.output.lower()


def test_full_cleanup_resets_databases(tmp_path: Path) -> None:
    from neural_agent_os.infrastructure.graph_store import GraphNode, KnowledgeGraphStore
    from neural_agent_os.infrastructure.speaker_store import Speaker, SpeakerDatabase
    from neural_agent_os.infrastructure.vector_store import LocalVectorStore, VectorDocument

    v_store = LocalVectorStore(storage_dir=tmp_path)
    v_store.add_documents([VectorDocument(id="doc1", text="hello", vector=[0.1, 0.2])])
    assert v_store.count() == 1

    g_store = KnowledgeGraphStore(storage_dir=tmp_path)
    g_store.add_node(GraphNode(id="n1", label="Person"))
    assert g_store.stats()["total_nodes"] == 1

    s_db = SpeakerDatabase(storage_dir=tmp_path)
    s_db.add_speaker(Speaker(id="spk1", name="Alice", embedding=[0.1, 0.2]))
    assert s_db.get_speaker("spk1") is not None


    # Clear stores
    v_store.clear()
    g_store.clear()
    s_db.clear()

    assert v_store.count() == 0
    assert g_store.stats()["total_nodes"] == 0
    assert s_db.get_speaker("spk1") is None


def test_web_api_cleanup() -> None:
    from fastapi.testclient import TestClient

    from neural_agent_os.web.app import create_app

    app = create_app()
    client = TestClient(app)

    res = client.post("/api/cleanup", data={"delete_all": "true", "delete_recordings": "true"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "Storage cleanup complete" in data["message"]

