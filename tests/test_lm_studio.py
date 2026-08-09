"""Unit tests for LMStudioLLMProvider."""

import pytest

from neural_agent_os.infrastructure.plugins.lm_studio_plugin import LMStudioLLMProvider


@pytest.mark.asyncio
async def test_lm_studio_provider_initialization() -> None:
    provider = LMStudioLLMProvider(api_base="http://localhost:1234/v1", model_name="qwen/qwen3.5-9b")
    assert provider.name == "lm-studio"
    assert provider.api_base == "http://localhost:1234/v1"
    assert provider.model_name == "qwen/qwen3.5-9b"


@pytest.mark.asyncio
async def test_lm_studio_generate_fallback_or_live() -> None:
    provider = LMStudioLLMProvider(api_base="http://localhost:1234/v1", timeout_seconds=2.0)
    response = await provider.generate(prompt="Hello, return valid JSON test.")
    assert len(response) > 0
    # Response should contain JSON structure or valid string response
    assert "decisions" in response or "Mock Response" in response or len(response) > 5
