"""Unit tests for LocalVectorStore."""

from pathlib import Path

from transcribe.infrastructure.vector_store import LocalVectorStore, VectorDocument


def test_vector_store_crud_and_search(tmp_path: Path) -> None:
    store = LocalVectorStore(storage_dir=tmp_path)
    assert store.count() == 0

    doc1 = VectorDocument(
        id="d1",
        text="Python backend architecture",
        vector=[1.0, 0.0, 0.0],
        metadata={"meeting_id": "m1", "doc_type": "decision"},
    )
    doc2 = VectorDocument(
        id="d2",
        text="Frontend UI design system",
        vector=[0.0, 1.0, 0.0],
        metadata={"meeting_id": "m1", "doc_type": "task"},
    )

    store.add_documents([doc1, doc2])
    assert store.count() == 2

    # Query matching doc1
    results = store.search(query_vector=[0.9, 0.1, 0.0], top_k=1)
    assert len(results) == 1
    matched_doc, score = results[0]
    assert matched_doc.id == "d1"
    assert score > 0.85

    # Filtered search
    results_filtered = store.search(query_vector=[0.9, 0.1, 0.0], filter_metadata={"doc_type": "task"})
    assert len(results_filtered) == 1
    assert results_filtered[0][0].id == "d2"
