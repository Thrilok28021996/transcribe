"""Unit tests for SpeakerDatabase and cosine similarity math."""

from pathlib import Path
import pytest
from transcribe.domain.entities import Speaker
from transcribe.infrastructure.speaker_store import SpeakerDatabase, cosine_similarity


def test_cosine_similarity() -> None:
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    v3 = [0.0, 1.0, 0.0]

    assert cosine_similarity(v1, v2) == pytest.approx(1.0)
    assert cosine_similarity(v1, v3) == pytest.approx(0.0)


def test_speaker_db_crud_and_persistence(tmp_path: Path) -> None:
    db = SpeakerDatabase(storage_dir=tmp_path)
    assert len(db.list_speakers()) == 0

    speaker = Speaker(name="Alice", aliases=["Alice S."], embedding=[1.0, 0.0, 0.0])
    db.add_speaker(speaker)

    assert len(db.list_speakers()) == 1
    assert db.get_speaker(speaker.id) is not None

    # Reload database from disk
    db_reloaded = SpeakerDatabase(storage_dir=tmp_path)
    assert len(db_reloaded.list_speakers()) == 1
    found = db_reloaded.find_by_name("alice s.")
    assert found is not None
    assert found.name == "Alice"


def test_voice_embedding_matching(tmp_path: Path) -> None:
    db = SpeakerDatabase(storage_dir=tmp_path)
    speaker_a = Speaker(name="Bob", embedding=[0.9, 0.1, 0.0])
    db.add_speaker(speaker_a)

    query_vec = [0.95, 0.05, 0.0]
    matched, score = db.match_voice_embedding(query_vec, threshold=0.75)
    assert matched is not None
    assert matched.name == "Bob"
    assert score > 0.90


def test_centroid_embedding_update(tmp_path: Path) -> None:
    db = SpeakerDatabase(storage_dir=tmp_path)
    speaker = Speaker(name="Charlie", embedding=[1.0, 0.0])
    db.add_speaker(speaker)

    updated = db.update_embedding_centroid(speaker.id, [0.0, 1.0])
    # Average of [1.0, 0.0] and [0.0, 1.0] should be [0.5, 0.5]
    assert updated.embedding == pytest.approx([0.5, 0.5])
