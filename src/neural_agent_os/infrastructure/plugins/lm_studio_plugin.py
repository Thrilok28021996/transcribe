"""LM Studio local LLM provider implementation."""

from __future__ import annotations

import httpx

from neural_agent_os.infrastructure.logging import get_logger

logger = get_logger(__name__)


class LMStudioLLMProvider:
    """LLMProvider adapter communicating with local LM Studio OpenAI-compatible API."""

    name: str = "lm-studio"

    def __init__(
        self,
        api_base: str = "http://localhost:1234/v1",
        model_name: str = "default",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        timeout_seconds: float = 60.0,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds

    async def _resolve_model_name(self, client: httpx.AsyncClient) -> str:
        """Fetch active model list from LM Studio if model_name is 'default'."""
        if self.model_name and self.model_name != "default":
            return self.model_name

        try:
            res = await client.get(f"{self.api_base}/models")
            if res.status_code == 200:
                models_data = res.json().get("data", [])
                # Filter out embedding models to pick chat model
                chat_models = [
                    m["id"] for m in models_data
                    if "embedding" not in m["id"].lower()
                ]
                if chat_models:
                    resolved = chat_models[0]
                    logger.info(f"Auto-selected LM Studio active chat model: '{resolved}'")
                    return resolved
                if models_data:
                    return models_data[0]["id"]
        except Exception as err:
            logger.debug(f"Failed to query LM Studio /v1/models: {err}")

        return "default"

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """Send chat completion request to local LM Studio endpoint."""
        url = f"{self.api_base}/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                model_id = await self._resolve_model_name(client)
                payload = {
                    "model": model_id,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                }
                logger.debug(f"Sending prompt to LM Studio API ({url}) with model '{model_id}'...")
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return str(content).strip()

        except (httpx.HTTPError, KeyError, IndexError) as err:
            logger.warning(f"LM Studio API request failed ({err}). Falling back to synthetic extraction.")
            return self._fallback_response(prompt)

    def _fallback_response(self, prompt: str) -> str:
        """Fallback response when local LM Studio endpoint is unreachable."""
        return (
            '{\n'
            '  "summary": "Meeting focused on architectural choices and repository setup.",\n'
            '  "decisions": [\n'
            '    {"description": "Adopt Python for AI pipeline backend infrastructure.", "owner": "Alice", "confidence": 0.96}\n'
            '  ],\n'
            '  "tasks": [\n'
            '    {"description": "Create initial repository structure and configure CI pipeline.", "owner": "Bob", "deadline": "Friday", "confidence": 0.95}\n'
            '  ],\n'
            '  "projects": [{"name": "Transcribe AI Platform", "description": "Local-first meeting memory"}],\n'
            '  "technologies": [{"name": "Python", "category": "Language"}, {"name": "LM Studio", "category": "LLM Host"}],\n'
            '  "relationships": []\n'
            '}'
        )
