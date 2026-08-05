"""LM Studio local embedding provider implementation."""

from __future__ import annotations

import math

import httpx

from transcribe.infrastructure.logging import get_logger

logger = get_logger(__name__)


class LMStudioEmbeddingProvider:
    """EmbeddingProvider adapter communicating with local LM Studio /v1/embeddings endpoint."""

    name: str = "lm-studio-embeddings"

    def __init__(
        self,
        api_base: str = "http://localhost:1234/v1",
        model_name: str = "auto",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self._resolved_model: str | None = None

    async def _resolve_model_name(self, client: httpx.AsyncClient) -> str:
        """Auto-detect embedding model from LM Studio /v1/models endpoint."""
        if self._resolved_model:
            return self._resolved_model

        if self.model_name and self.model_name != "auto":
            self._resolved_model = self.model_name
            return self.model_name

        try:
            res = await client.get(f"{self.api_base}/models")
            if res.status_code == 200:
                models = res.json().get("data", [])
                for m in models:
                    m_id = m.get("id", "")
                    if "embed" in m_id.lower() or "nomic" in m_id.lower():
                        logger.info(f"Auto-detected LM Studio embedding model: '{m_id}'")
                        self._resolved_model = m_id
                        return m_id
                if models:
                    self._resolved_model = models[0]["id"]
                    return models[0]["id"]
        except Exception as err:
            logger.debug(f"Failed to resolve LM Studio embedding model: {err}")

        self._resolved_model = "text-embedding-nomic-embed-text-v1.5@q4_k_m"
        return self._resolved_model

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string into a vector representation."""
        batch_result = await self.embed_batch([text])
        return batch_result[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of text strings via LM Studio /v1/embeddings API."""
        if not texts:
            return []

        url = f"{self.api_base}/embeddings"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                model_id = await self._resolve_model_name(client)
                payload = {
                    "input": texts if len(texts) > 1 else texts[0],
                    "model": model_id,
                }
                logger.debug(f"Requesting embeddings for {len(texts)} texts using model '{model_id}'...")
                res = await client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()

                embeddings = [item["embedding"] for item in data["data"]]
                return embeddings

        except (httpx.HTTPError, KeyError, IndexError) as err:
            logger.warning(f"LM Studio embeddings request failed ({err}). Returning synthetic vectors.")
            return [self._fallback_vector(t) for t in texts]

    def _fallback_vector(self, text: str, dim: int = 768) -> list[float]:
        """Fallback synthetic embedding vector generator."""
        val = sum(ord(c) for c in text) % 100 / 100.0
        return [round(math.sin(i * 0.05 + val), 4) for i in range(dim)]
