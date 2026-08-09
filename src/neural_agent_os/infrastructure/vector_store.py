"""Local vector database index with file persistence and cosine similarity search."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from neural_agent_os.infrastructure.logging import get_logger
from neural_agent_os.infrastructure.speaker_store import cosine_similarity

logger = get_logger(__name__)


class VectorDocument(BaseModel):
    """Document entry stored in the vector database."""
    model_config = ConfigDict(frozen=True)

    id: str
    text: str
    vector: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)


class LocalVectorStore:
    """Persistent local vector database supporting cosine similarity retrieval."""

    def __init__(self, storage_dir: Path | str) -> None:
        self.storage_dir = Path(storage_dir).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_file = self.storage_dir / "vectors.json"
        self._documents: dict[str, VectorDocument] = {}
        self._load()

    def _load(self) -> None:
        """Load vector index from disk."""
        if not self.db_file.is_file():
            self._documents = {}
            return

        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    doc = VectorDocument.model_validate(item)
                    self._documents[doc.id] = doc
            logger.info(f"Loaded {len(self._documents)} vector documents from {self.db_file.name}")
        except (json.JSONDecodeError, OSError) as err:
            logger.error(f"Failed to load vector store: {err}. Initializing empty store.")
            self._documents = {}

    def _save(self) -> None:
        """Persist vector index to disk."""
        try:
            serialized = [doc.model_dump(mode="json") for doc in self._documents.values()]
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2, ensure_ascii=False)
        except OSError as err:
            logger.error(f"Failed to save vector store: {err}")

    def add_documents(self, docs: list[VectorDocument]) -> None:
        """Add or update vector documents in index."""
        for d in docs:
            self._documents[d.id] = d
        self._save()
        logger.info(f"Added {len(docs)} documents to local vector store (total: {len(self._documents)})")

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[tuple[VectorDocument, float]]:
        """Perform cosine similarity top-K search over indexed documents."""
        if not query_vector or not self._documents:
            return []

        scored: list[tuple[VectorDocument, float]] = []

        for doc in self._documents.values():
            if filter_metadata:
                match = all(
                    doc.metadata.get(k) == v
                    for k, v in filter_metadata.items()
                )
                if not match:
                    continue

            score = cosine_similarity(query_vector, doc.vector)
            scored.append((doc, round(score, 4)))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        """Total number of documents in vector store."""
        return len(self._documents)

    def clear(self) -> None:
        """Clear all documents in index and delete persistence file."""
        self._documents.clear()
        if self.db_file.exists():
            try:
                self.db_file.unlink()
            except OSError:
                pass

