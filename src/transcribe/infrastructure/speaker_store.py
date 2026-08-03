"""Persistent speaker database with voice embedding matching and profile management."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence

from transcribe.domain.entities import Speaker
from transcribe.infrastructure.logging import get_logger

logger = get_logger(__name__)


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Compute cosine similarity between two vector representations."""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


class SpeakerDatabase:
    """File-backed database managing speaker profiles and voice embedding vectors."""

    def __init__(self, storage_dir: Path | str) -> None:
        self.storage_dir = Path(storage_dir).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.db_file = self.storage_dir / "speakers.json"
        self._speakers: dict[str, Speaker] = {}
        self._load()

    def _load(self) -> None:
        """Load speakers from JSON file."""
        if not self.db_file.is_file():
            self._speakers = {}
            return

        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    speaker = Speaker.model_validate(item)
                    self._speakers[speaker.id] = speaker
            logger.info(f"Loaded {len(self._speakers)} speaker profiles from {self.db_file.name}")
        except (json.JSONDecodeError, OSError) as err:
            logger.error(f"Failed to load speaker database: {err}. Starting fresh.")
            self._speakers = {}

    def _save(self) -> None:
        """Persist speakers to JSON file."""
        try:
            serialized = [
                s.model_dump(mode="json")
                for s in self._speakers.values()
            ]
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2, ensure_ascii=False)
        except OSError as err:
            logger.error(f"Failed to save speaker database: {err}")

    def add_speaker(self, speaker: Speaker) -> Speaker:
        """Add or update a speaker profile."""
        self._speakers[speaker.id] = speaker
        self._save()
        return speaker

    def get_speaker(self, speaker_id: str) -> Speaker | None:
        """Retrieve speaker by ID."""
        return self._speakers.get(speaker_id)

    def find_by_name(self, name: str) -> Speaker | None:
        """Find speaker by exact or alias name match."""
        name_clean = name.strip().lower()
        for s in self._speakers.values():
            if s.name.lower() == name_clean or any(alias.lower() == name_clean for alias in s.aliases):
                return s
        return None

    def list_speakers(self) -> list[Speaker]:
        """List all stored speaker profiles."""
        return list(self._speakers.values())

    def match_voice_embedding(
        self,
        embedding: list[float],
        threshold: float = 0.75,
    ) -> tuple[Speaker | None, float]:
        """Find best matching speaker for a voice embedding vector using cosine similarity."""
        if not embedding or not self._speakers:
            return None, 0.0

        best_speaker: Speaker | None = None
        best_score = 0.0

        for speaker in self._speakers.values():
            if not speaker.embedding:
                continue
            sim = cosine_similarity(embedding, speaker.embedding)
            if sim > best_score:
                best_score = sim
                best_speaker = speaker

        if best_speaker and best_score >= threshold:
            return best_speaker, round(best_score, 4)

        return None, round(best_score, 4)

    def update_embedding_centroid(self, speaker_id: str, new_embedding: list[float]) -> Speaker:
        """Update speaker embedding vector by computing running average centroid."""
        speaker = self.get_speaker(speaker_id)
        if not speaker:
            raise KeyError(f"Speaker {speaker_id} not found.")

        if not speaker.embedding:
            updated_emb = new_embedding
            history = [1.0]
        else:
            prev_count = max(1, len(speaker.confidence_history))
            new_count = prev_count + 1
            updated_emb = [
                ((old * prev_count) + new) / new_count
                for old, new in zip(speaker.embedding, new_embedding)
            ]
            history = [*speaker.confidence_history, 1.0]

        updated_speaker = speaker.model_copy(
            update={
                "embedding": updated_emb,
                "confidence_history": history,
            }
        )
        self._speakers[speaker_id] = updated_speaker
        self._save()
        return updated_speaker

    def update_speaker_details(
        self,
        speaker_id: str,
        name: str | None = None,
        aliases: list[str] | None = None,
    ) -> Speaker:
        """Update speaker display name and/or alias list."""
        speaker = self.get_speaker(speaker_id)
        if not speaker:
            raise KeyError(f"Speaker {speaker_id} not found.")

        current_aliases = list(speaker.aliases)
        new_name = name.strip() if name and name.strip() else speaker.name

        # If name changed, preserve old name in aliases if not already present
        if new_name != speaker.name and speaker.name not in current_aliases:
            current_aliases.append(speaker.name)

        if aliases is not None:
            for alias in aliases:
                a_clean = alias.strip()
                if a_clean and a_clean not in current_aliases and a_clean != new_name:
                    current_aliases.append(a_clean)

        updated_speaker = speaker.model_copy(
            update={
                "name": new_name,
                "aliases": current_aliases,
            }
        )
        self._speakers[speaker_id] = updated_speaker
        self._save()
        return updated_speaker

    def clear(self) -> None:
        """Clear all speaker profiles and delete persistence file."""
        self._speakers.clear()
        if self.db_file.exists():
            try:
                self.db_file.unlink()
            except OSError:
                pass

